from __future__ import annotations

import base64
import binascii
import secrets
import sqlite3
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request, Response, status
from fastapi.middleware.cors import CORSMiddleware

from noteweave.api.schemas import (
    AttachmentCreateRequest,
    CommentCreateRequest,
    CourseCreateRequest,
    CourseJoinRequest,
    KnowledgeNodeCreateRequest,
    KnowledgeNodeMoveRequest,
    KnowledgeNodeUpdateRequest,
    LoginRequest,
    MasteryRequest,
    MemberRoleRequest,
    MistakeCreateRequest,
    MistakeUpdateRequest,
    NoteCreateRequest,
    NoteUpdateRequest,
    ReactionCreateRequest,
    RegisterRequest,
    SuggestionCreateRequest,
    SuggestionHandleRequest,
)
from noteweave.core.ai import AIAssistService
from noteweave.core.database import Database, dumps, loads, now_iso
from noteweave.core.security import hash_password, new_token, verify_password
from noteweave.core.settings import Settings


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings.load()
    Path(settings.file_storage_dir).mkdir(parents=True, exist_ok=True)
    app = FastAPI(title=settings.app_name)
    app.state.settings = settings
    app.state.db = Database(settings.database_path)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    register_routes(app)
    return app


def register_routes(app: FastAPI) -> None:
    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/auth/register")
    async def register(payload: RegisterRequest, db: Database = Depends(get_db)):
        created_at = now_iso()
        display_name = payload.display_name or payload.username
        try:
            user_id = db.execute(
                """
                INSERT INTO users (username, password_hash, display_name, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (
                    payload.username,
                    hash_password(payload.password),
                    display_name,
                    created_at,
                ),
            )
        except sqlite3.IntegrityError:
            raise HTTPException(status_code=409, detail="username already exists")

        token = issue_token(db, user_id)
        return {"token": token, "user": serialize_user(get_user(db, user_id))}

    @app.post("/api/auth/login")
    async def login(payload: LoginRequest, db: Database = Depends(get_db)):
        user = db.one("SELECT * FROM users WHERE username = ?", (payload.username,))
        if not user or not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="invalid credentials")
        token = issue_token(db, int(user["id"]))
        return {"token": token, "user": serialize_user(user)}

    @app.post("/api/auth/logout")
    async def logout(
        token: str = Depends(get_bearer_token),
        db: Database = Depends(get_db),
    ):
        db.execute("DELETE FROM auth_tokens WHERE token = ?", (token,))
        return {"status": "ok"}

    @app.get("/api/auth/me")
    async def me(user: dict[str, Any] = Depends(current_user)):
        return serialize_user(user)

    @app.post("/api/courses")
    async def create_course(
        payload: CourseCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ts = now_iso()
        invite_code = secrets.token_urlsafe(8)
        course_id = db.execute(
            """
            INSERT INTO courses
              (name, description, semester, tags, invite_code, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.description,
                payload.semester,
                dumps(payload.tags),
                invite_code,
                user["id"],
                ts,
                ts,
            ),
        )
        db.transaction(
            [
                (
                    "INSERT INTO course_members (course_id, user_id, role, joined_at) VALUES (?, ?, ?, ?)",
                    (course_id, user["id"], "maintainer", ts),
                ),
                (
                    """
                    INSERT INTO knowledge_nodes
                      (course_id, parent_id, type, title, description, metadata, order_index, depth, path, created_by, created_at, updated_at)
                    VALUES (?, NULL, 'course_root', ?, ?, '{}', 0, 0, ?, ?, ?, ?)
                    """,
                    (course_id, payload.name, payload.description, payload.name, user["id"], ts, ts),
                ),
            ]
        )
        return serialize_course(get_course(db, course_id), db=db, user_id=user["id"])

    @app.get("/api/courses")
    async def list_courses(
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        rows = db.all(
            """
            SELECT c.*
            FROM courses c
            JOIN course_members m ON m.course_id = c.id
            WHERE m.user_id = ?
            ORDER BY c.updated_at DESC
            """,
            (user["id"],),
        )
        return [serialize_course(row, db=db, user_id=user["id"]) for row in rows]

    @app.post("/api/courses/join")
    async def join_course_by_code(
        payload: CourseJoinRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        course = db.one("SELECT * FROM courses WHERE invite_code = ?", (payload.invite_code,))
        if not course:
            raise HTTPException(status_code=404, detail="course invite not found")
        ts = now_iso()
        try:
            db.execute(
                "INSERT INTO course_members (course_id, user_id, role, joined_at) VALUES (?, ?, 'student', ?)",
                (course["id"], user["id"], ts),
            )
        except sqlite3.IntegrityError:
            pass
        return serialize_course(course, db=db, user_id=user["id"])

    @app.get("/api/courses/{course_id}")
    async def course_detail(
        course_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        return serialize_course(get_course(db, course_id), db=db, user_id=user["id"])

    @app.post("/api/courses/{course_id}/join")
    async def join_course(
        course_id: int,
        payload: CourseJoinRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        course = get_course(db, course_id)
        if course["invite_code"] != payload.invite_code:
            raise HTTPException(status_code=403, detail="invalid invite code")
        ts = now_iso()
        try:
            db.execute(
                "INSERT INTO course_members (course_id, user_id, role, joined_at) VALUES (?, ?, 'student', ?)",
                (course_id, user["id"], ts),
            )
        except sqlite3.IntegrityError:
            pass
        return serialize_course(course, db=db, user_id=user["id"])

    @app.get("/api/courses/{course_id}/members")
    async def list_members(
        course_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        return db.all(
            """
            SELECT u.id, u.username, u.display_name, m.role, m.joined_at
            FROM course_members m
            JOIN users u ON u.id = m.user_id
            WHERE m.course_id = ?
            ORDER BY m.joined_at
            """,
            (course_id,),
        )

    @app.patch("/api/courses/{course_id}/members/{member_id}")
    async def update_member_role(
        course_id: int,
        member_id: int,
        payload: MemberRoleRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_maintainer(db, course_id, user["id"])
        db.execute(
            "UPDATE course_members SET role = ? WHERE course_id = ? AND user_id = ?",
            (payload.role, course_id, member_id),
        )
        return {"status": "ok"}

    @app.get("/api/courses/{course_id}/tree")
    async def get_tree(
        course_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        rows = db.all(
            "SELECT * FROM knowledge_nodes WHERE course_id = ? ORDER BY depth, order_index, id",
            (course_id,),
        )
        return build_tree_response(db, rows)

    @app.post("/api/courses/{course_id}/tree/nodes")
    async def create_node(
        course_id: int,
        payload: KnowledgeNodeCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_maintainer(db, course_id, user["id"])
        parent = get_parent_node(db, course_id, payload.parent_id)
        ts = now_iso()
        depth = int(parent["depth"]) + 1
        path = f"{parent['path']} / {payload.title}"
        node_id = db.execute(
            """
            INSERT INTO knowledge_nodes
              (course_id, parent_id, type, title, description, metadata, order_index, depth, path, created_by, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                course_id,
                parent["id"],
                payload.type,
                payload.title,
                payload.description,
                dumps(payload.metadata),
                payload.order_index,
                depth,
                path,
                user["id"],
                ts,
                ts,
            ),
        )
        return serialize_node(get_node(db, node_id), db)

    @app.get("/api/tree/nodes/{node_id}/detail")
    async def node_detail(
        node_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        node = get_node(db, node_id)
        ensure_member(db, int(node["course_id"]), user["id"])
        return serialize_node(node, db, include_content=True, user_id=user["id"])

    @app.patch("/api/tree/nodes/{node_id}")
    async def update_node(
        node_id: int,
        payload: KnowledgeNodeUpdateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        node = get_node(db, node_id)
        ensure_maintainer(db, int(node["course_id"]), user["id"])
        title = payload.title if payload.title is not None else node["title"]
        description = payload.description if payload.description is not None else node["description"]
        metadata = payload.metadata if payload.metadata is not None else loads(node["metadata"], {})
        order_index = payload.order_index if payload.order_index is not None else node["order_index"]
        db.execute(
            """
            UPDATE knowledge_nodes
            SET title = ?, description = ?, metadata = ?, order_index = ?, updated_at = ?
            WHERE id = ?
            """,
            (title, description, dumps(metadata), order_index, now_iso(), node_id),
        )
        refresh_subtree_paths(db, node_id)
        return serialize_node(get_node(db, node_id), db)

    @app.post("/api/tree/nodes/{node_id}/move")
    async def move_node(
        node_id: int,
        payload: KnowledgeNodeMoveRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        node = get_node(db, node_id)
        if node["type"] == "course_root":
            raise HTTPException(status_code=400, detail="cannot move course root")
        ensure_maintainer(db, int(node["course_id"]), user["id"])
        parent = get_parent_node(db, int(node["course_id"]), payload.parent_id)
        if int(parent["id"]) == node_id:
            raise HTTPException(status_code=400, detail="cannot move node under itself")
        db.execute(
            "UPDATE knowledge_nodes SET parent_id = ?, order_index = ?, updated_at = ? WHERE id = ?",
            (parent["id"], payload.order_index, now_iso(), node_id),
        )
        refresh_subtree_paths(db, node_id)
        return serialize_node(get_node(db, node_id), db)

    @app.delete("/api/tree/nodes/{node_id}")
    async def delete_node(
        node_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        node = get_node(db, node_id)
        if node["type"] == "course_root":
            raise HTTPException(status_code=400, detail="cannot delete course root")
        ensure_maintainer(db, int(node["course_id"]), user["id"])
        counts = node_content_counts(db, node_id)
        if counts["note_count"] or counts["mistake_count"]:
            raise HTTPException(status_code=409, detail={"message": "node has content", "counts": counts})
        db.execute("DELETE FROM knowledge_nodes WHERE id = ?", (node_id,))
        return {"status": "ok"}

    @app.post("/api/notes")
    async def create_note(
        payload: NoteCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, payload.course_id, user["id"])
        if payload.node_id:
            ensure_node_in_course(db, payload.node_id, payload.course_id)
        ts = now_iso()
        note_id = db.execute(
            """
            INSERT INTO notes
              (course_id, node_id, title, content_json, content_text, content_format, visibility, status, tags, author_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.course_id,
                payload.node_id,
                payload.title,
                dumps(payload.content_json),
                payload.content_text,
                payload.content_format,
                payload.visibility,
                payload.status,
                dumps(payload.tags),
                user["id"],
                ts,
                ts,
            ),
        )
        create_note_version(db, note_id, user["id"], "initial")
        return serialize_note(get_note(db, note_id), db)

    @app.get("/api/notes")
    async def list_notes(
        course_id: int,
        node_id: int | None = None,
        shared_only: bool = False,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        clauses = ["course_id = ?"]
        params: list[Any] = [course_id]
        if node_id is not None:
            clauses.append("node_id = ?")
            params.append(node_id)
        if shared_only:
            clauses.append("visibility = 'shared'")
        else:
            clauses.append("(visibility = 'shared' OR author_id = ?)")
            params.append(user["id"])
        rows = db.all(
            f"SELECT * FROM notes WHERE {' AND '.join(clauses)} ORDER BY updated_at DESC",
            tuple(params),
        )
        return [serialize_note(row, db) for row in rows]

    @app.get("/api/notes/{note_id}")
    async def note_detail(
        note_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        note = get_note(db, note_id)
        ensure_note_access(db, note, user["id"])
        return serialize_note(note, db, include_comments=True)

    @app.patch("/api/notes/{note_id}")
    async def update_note(
        note_id: int,
        payload: NoteUpdateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        note = get_note(db, note_id)
        ensure_note_write(db, note, user["id"])
        updates = {
            "node_id": payload.node_id if payload.node_id is not None else note["node_id"],
            "title": payload.title if payload.title is not None else note["title"],
            "content_json": dumps(payload.content_json) if payload.content_json is not None else note["content_json"],
            "content_text": payload.content_text if payload.content_text is not None else note["content_text"],
            "visibility": payload.visibility if payload.visibility is not None else note["visibility"],
            "status": payload.status if payload.status is not None else note["status"],
            "tags": dumps(payload.tags) if payload.tags is not None else note["tags"],
        }
        if updates["node_id"]:
            ensure_node_in_course(db, int(updates["node_id"]), int(note["course_id"]))
        db.execute(
            """
            UPDATE notes
            SET node_id = ?, title = ?, content_json = ?, content_text = ?, visibility = ?, status = ?, tags = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                updates["node_id"],
                updates["title"],
                updates["content_json"],
                updates["content_text"],
                updates["visibility"],
                updates["status"],
                updates["tags"],
                now_iso(),
                note_id,
            ),
        )
        create_note_version(db, note_id, user["id"], "manual update")
        return serialize_note(get_note(db, note_id), db)

    @app.post("/api/notes/{note_id}/publish")
    async def publish_note(
        note_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        note = get_note(db, note_id)
        ensure_note_write(db, note, user["id"])
        db.execute(
            "UPDATE notes SET visibility = 'shared', status = 'published', updated_at = ? WHERE id = ?",
            (now_iso(), note_id),
        )
        create_note_version(db, note_id, user["id"], "publish")
        return serialize_note(get_note(db, note_id), db)

    @app.get("/api/notes/{note_id}/versions")
    async def note_versions(
        note_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        note = get_note(db, note_id)
        ensure_note_access(db, note, user["id"])
        rows = db.all("SELECT * FROM note_versions WHERE note_id = ? ORDER BY id DESC", (note_id,))
        return [serialize_version(row) for row in rows]

    @app.delete("/api/notes/{note_id}")
    async def delete_note(
        note_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        note = get_note(db, note_id)
        ensure_note_write(db, note, user["id"])
        delete_attachments_for_target(db, settings, "note", note_id)
        db.transaction(
            [
                ("DELETE FROM comments WHERE target_type = 'note' AND target_id = ?", (note_id,)),
                ("DELETE FROM reactions WHERE target_type = 'note' AND target_id = ?", (note_id,)),
                ("DELETE FROM suggestions WHERE target_type = 'note' AND target_id = ?", (note_id,)),
                ("DELETE FROM ai_results WHERE target_type = 'note' AND target_id = ?", (note_id,)),
                ("DELETE FROM notes WHERE id = ?", (note_id,)),
            ]
        )
        return {"status": "ok"}

    @app.post("/api/attachments")
    async def create_attachment(
        payload: AttachmentCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        ensure_member(db, payload.course_id, user["id"])
        if payload.note_id is not None:
            note = get_note(db, payload.note_id)
            ensure_note_write(db, note, user["id"])
            if int(note["course_id"]) != payload.course_id:
                raise HTTPException(status_code=400, detail="note is not in course")
        if payload.mistake_id is not None:
            mistake = get_mistake(db, payload.mistake_id)
            ensure_owner_or_maintainer(db, int(mistake["course_id"]), int(mistake["author_id"]), user["id"])
            if int(mistake["course_id"]) != payload.course_id:
                raise HTTPException(status_code=400, detail="mistake is not in course")
        if not payload.content_type.startswith("image/"):
            raise HTTPException(status_code=415, detail="only image uploads are supported")

        try:
            file_bytes = base64.b64decode(payload.data_base64, validate=True)
        except (binascii.Error, ValueError):
            raise HTTPException(status_code=400, detail="invalid base64 data")
        if not file_bytes:
            raise HTTPException(status_code=400, detail="empty file")
        if len(file_bytes) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="file is too large")

        raw_name = Path(payload.file_name).name or "image"
        safe_name = "".join(
            char if char.isascii() and (char.isalnum() or char in ".-_") else "_"
            for char in raw_name
        ).strip("._")
        if not safe_name:
            safe_name = "image"
        extension = Path(safe_name).suffix.lower()
        if len(extension) > 12:
            extension = ""
        stored_name = f"{secrets.token_urlsafe(18)}{extension}"
        storage_dir = Path(settings.file_storage_dir)
        storage_dir.mkdir(parents=True, exist_ok=True)
        target = storage_dir / stored_name
        target.write_bytes(file_bytes)

        url_path = f"/api/files/{stored_name}"
        attachment_id = db.execute(
            """
            INSERT INTO attachments
              (course_id, note_id, mistake_id, file_name, stored_name, content_type, size_bytes, url_path, uploaded_by, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.course_id,
                payload.note_id,
                payload.mistake_id,
                safe_name,
                stored_name,
                payload.content_type,
                len(file_bytes),
                url_path,
                user["id"],
                now_iso(),
            ),
        )
        return {
            **serialize_attachment(get_attachment(db, attachment_id)),
            "markdown": f"![{safe_name}]({url_path})",
        }

    @app.get("/api/files/{stored_name}")
    async def get_file(
        stored_name: str,
        db: Database = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        attachment = db.one("SELECT * FROM attachments WHERE stored_name = ?", (stored_name,))
        if not attachment:
            raise HTTPException(status_code=404, detail="file not found")
        path = Path(settings.file_storage_dir) / attachment["stored_name"]
        if not path.exists() or not path.is_file():
            raise HTTPException(status_code=404, detail="file not found")
        headers = {"Content-Disposition": f'inline; filename="{attachment["file_name"]}"'}
        return Response(path.read_bytes(), media_type=attachment["content_type"], headers=headers)

    @app.post("/api/mistakes")
    async def create_mistake(
        payload: MistakeCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, payload.course_id, user["id"])
        if payload.node_id:
            ensure_node_in_course(db, payload.node_id, payload.course_id)
        ts = now_iso()
        mistake_id = db.execute(
            """
            INSERT INTO mistakes
              (course_id, node_id, question_content, correct_answer, wrong_answer, error_reason, solution, reflection, question_type, difficulty, mastery_status, tags, visibility, author_id, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payload.course_id,
                payload.node_id,
                payload.question_content,
                payload.correct_answer,
                payload.wrong_answer,
                payload.error_reason,
                payload.solution,
                payload.reflection,
                payload.question_type,
                payload.difficulty,
                payload.mastery_status,
                dumps(payload.tags),
                payload.visibility,
                user["id"],
                ts,
                ts,
            ),
        )
        return serialize_mistake(get_mistake(db, mistake_id), db)

    @app.get("/api/mistakes")
    async def list_mistakes(
        course_id: int,
        node_id: int | None = None,
        tag: str | None = None,
        question_type: str | None = None,
        mastery_status: str | None = None,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        rows = db.all("SELECT * FROM mistakes WHERE course_id = ? ORDER BY updated_at DESC", (course_id,))
        result = []
        for row in rows:
            if row["visibility"] != "shared" and row["author_id"] != user["id"]:
                continue
            tags = loads(row["tags"], [])
            if node_id is not None and row["node_id"] != node_id:
                continue
            if tag and tag not in tags:
                continue
            if question_type and row["question_type"] != question_type:
                continue
            if mastery_status and row["mastery_status"] != mastery_status:
                continue
            result.append(serialize_mistake(row, db))
        return result

    @app.patch("/api/mistakes/{mistake_id}")
    async def update_mistake(
        mistake_id: int,
        payload: MistakeUpdateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        mistake = get_mistake(db, mistake_id)
        ensure_owner_or_maintainer(db, int(mistake["course_id"]), int(mistake["author_id"]), user["id"])
        data = dict(mistake)
        for field, value in payload.model_dump(exclude_unset=True).items():
            data[field] = dumps(value) if field == "tags" else value
        if data["node_id"]:
            ensure_node_in_course(db, int(data["node_id"]), int(mistake["course_id"]))
        db.execute(
            """
            UPDATE mistakes
            SET node_id = ?, question_content = ?, correct_answer = ?, wrong_answer = ?,
                error_reason = ?, solution = ?, reflection = ?, question_type = ?,
                difficulty = ?, mastery_status = ?, tags = ?, visibility = ?, updated_at = ?
            WHERE id = ?
            """,
            (
                data["node_id"],
                data["question_content"],
                data["correct_answer"],
                data["wrong_answer"],
                data["error_reason"],
                data["solution"],
                data["reflection"],
                data["question_type"],
                data["difficulty"],
                data["mastery_status"],
                data["tags"],
                data["visibility"],
                now_iso(),
                mistake_id,
            ),
        )
        return serialize_mistake(get_mistake(db, mistake_id), db)

    @app.patch("/api/mistakes/{mistake_id}/mastery")
    async def update_mastery(
        mistake_id: int,
        payload: MasteryRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        mistake = get_mistake(db, mistake_id)
        ensure_owner_or_maintainer(db, int(mistake["course_id"]), int(mistake["author_id"]), user["id"])
        db.execute(
            "UPDATE mistakes SET mastery_status = ?, updated_at = ? WHERE id = ?",
            (payload.mastery_status, now_iso(), mistake_id),
        )
        return serialize_mistake(get_mistake(db, mistake_id), db)

    @app.delete("/api/mistakes/{mistake_id}")
    async def delete_mistake(
        mistake_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        mistake = get_mistake(db, mistake_id)
        ensure_owner_or_maintainer(db, int(mistake["course_id"]), int(mistake["author_id"]), user["id"])
        delete_attachments_for_target(db, settings, "mistake", mistake_id)
        db.transaction(
            [
                ("DELETE FROM comments WHERE target_type = 'mistake' AND target_id = ?", (mistake_id,)),
                ("DELETE FROM reactions WHERE target_type = 'mistake' AND target_id = ?", (mistake_id,)),
                ("DELETE FROM suggestions WHERE target_type = 'mistake' AND target_id = ?", (mistake_id,)),
                ("DELETE FROM ai_results WHERE target_type = 'mistake' AND target_id = ?", (mistake_id,)),
                ("DELETE FROM mistakes WHERE id = ?", (mistake_id,)),
            ]
        )
        return {"status": "ok"}

    @app.post("/api/comments")
    async def create_comment(
        payload: CommentCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        course_id = target_course_id(db, payload.target_type, payload.target_id)
        ensure_member(db, course_id, user["id"])
        comment_id = db.execute(
            "INSERT INTO comments (target_type, target_id, content, author_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (payload.target_type, payload.target_id, payload.content, user["id"], now_iso()),
        )
        if payload.target_type == "note":
            db.execute("UPDATE notes SET comment_count = comment_count + 1 WHERE id = ?", (payload.target_id,))
        return serialize_comment(get_comment(db, comment_id))

    @app.post("/api/reactions")
    async def create_reaction(
        payload: ReactionCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        course_id = target_course_id(db, payload.target_type, payload.target_id)
        ensure_member(db, course_id, user["id"])
        try:
            reaction_id = db.execute(
                "INSERT INTO reactions (target_type, target_id, reaction_type, user_id, created_at) VALUES (?, ?, ?, ?, ?)",
                (payload.target_type, payload.target_id, payload.reaction_type, user["id"], now_iso()),
            )
            if payload.target_type == "note" and payload.reaction_type == "like":
                db.execute("UPDATE notes SET like_count = like_count + 1 WHERE id = ?", (payload.target_id,))
        except sqlite3.IntegrityError:
            existing = db.one(
                """
                SELECT * FROM reactions
                WHERE target_type = ? AND target_id = ? AND reaction_type = ? AND user_id = ?
                """,
                (payload.target_type, payload.target_id, payload.reaction_type, user["id"]),
            )
            reaction_id = int(existing["id"])
        return {"id": reaction_id, "status": "ok"}

    @app.delete("/api/reactions/{reaction_id}")
    async def delete_reaction(
        reaction_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        reaction = db.one("SELECT * FROM reactions WHERE id = ?", (reaction_id,))
        if not reaction:
            raise HTTPException(status_code=404, detail="reaction not found")
        if reaction["user_id"] != user["id"]:
            raise HTTPException(status_code=403, detail="not your reaction")
        db.execute("DELETE FROM reactions WHERE id = ?", (reaction_id,))
        if reaction["target_type"] == "note" and reaction["reaction_type"] == "like":
            db.execute(
                "UPDATE notes SET like_count = MAX(like_count - 1, 0) WHERE id = ?",
                (reaction["target_id"],),
            )
        return {"status": "ok"}

    @app.post("/api/suggestions")
    async def create_suggestion(
        payload: SuggestionCreateRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        course_id = target_course_id(db, payload.target_type, payload.target_id)
        ensure_member(db, course_id, user["id"])
        suggestion_id = db.execute(
            """
            INSERT INTO suggestions (target_type, target_id, type, content, submitter_id, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (payload.target_type, payload.target_id, payload.type, payload.content, user["id"], now_iso()),
        )
        return serialize_suggestion(get_suggestion(db, suggestion_id))

    @app.get("/api/courses/{course_id}/suggestions")
    async def list_suggestions(
        course_id: int,
        status: str | None = None,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        rows = db.all("SELECT * FROM suggestions ORDER BY created_at DESC")
        suggestions = []
        for row in rows:
            if status and row["status"] != status:
                continue
            try:
                if target_course_id(db, row["target_type"], int(row["target_id"])) != course_id:
                    continue
            except HTTPException:
                continue
            suggestions.append(serialize_suggestion(row, db=db))
        return suggestions

    @app.patch("/api/suggestions/{suggestion_id}")
    async def handle_suggestion(
        suggestion_id: int,
        payload: SuggestionHandleRequest,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        suggestion = get_suggestion(db, suggestion_id)
        course_id = target_course_id(db, suggestion["target_type"], int(suggestion["target_id"]))
        ensure_maintainer(db, course_id, user["id"])
        db.execute(
            "UPDATE suggestions SET status = ?, handler_id = ?, handled_at = ? WHERE id = ?",
            (payload.status, user["id"], now_iso(), suggestion_id),
        )
        return serialize_suggestion(get_suggestion(db, suggestion_id))

    @app.get("/api/search")
    async def search(
        course_id: int,
        q: str = Query(min_length=1),
        node_id: int | None = None,
        tag: str | None = None,
        source_type: str | None = None,
        author_id: int | None = None,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        ensure_member(db, course_id, user["id"])
        if source_type not in {None, "note", "mistake"}:
            raise HTTPException(status_code=400, detail="unsupported source type")
        query = q.strip().lower()
        results: list[dict[str, Any]] = []
        if source_type in {None, "note"}:
            notes = db.all("SELECT * FROM notes WHERE course_id = ?", (course_id,))
            for note in notes:
                if note["visibility"] != "shared" and note["author_id"] != user["id"]:
                    continue
                item = match_note(db, note, query, node_id, tag, author_id)
                if item:
                    results.append(item)
        if source_type in {None, "mistake"}:
            mistakes = db.all("SELECT * FROM mistakes WHERE course_id = ?", (course_id,))
            for mistake in mistakes:
                if mistake["visibility"] != "shared" and mistake["author_id"] != user["id"]:
                    continue
                item = match_mistake(db, mistake, query, node_id, tag, author_id)
                if item:
                    results.append(item)
        results.sort(key=lambda row: (row["score"], row["updated_at"]), reverse=True)
        for row in results[:20]:
            if row.get("node_id"):
                db.execute("UPDATE knowledge_nodes SET impact = impact + 1 WHERE id = ?", (row["node_id"],))
        return results[:20]

    @app.post("/api/ai/notes/{note_id}/summary")
    async def generate_summary(
        note_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        note = get_note(db, note_id)
        ensure_note_access(db, note, user["id"])
        output = await AIAssistService(settings).summarize_note(note["title"], note["content_text"])
        return create_ai_result(
            db,
            "note",
            note_id,
            "summary",
            output.result,
            user["id"],
            status="generated",
            error=output.error,
        )

    @app.post("/api/ai/notes/{note_id}/tags")
    async def generate_tags(
        note_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
        settings: Settings = Depends(get_settings),
    ):
        note = get_note(db, note_id)
        ensure_note_access(db, note, user["id"])
        output = await AIAssistService(settings).extract_tags(note["title"], note["content_text"])
        return create_ai_result(
            db,
            "note",
            note_id,
            "tags",
            output.result,
            user["id"],
            status="generated",
            error=output.error,
        )

    @app.get("/api/ai/results/{result_id}")
    async def ai_result_detail(
        result_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        result = get_ai_result(db, result_id)
        course_id = target_course_id(db, result["target_type"], int(result["target_id"]))
        ensure_member(db, course_id, user["id"])
        return serialize_ai_result(result)

    @app.post("/api/ai/results/{result_id}/accept")
    async def accept_ai_result(
        result_id: int,
        user: dict[str, Any] = Depends(current_user),
        db: Database = Depends(get_db),
    ):
        result = get_ai_result(db, result_id)
        if result["target_type"] != "note":
            raise HTTPException(status_code=400, detail="only note AI results are supported")
        note = get_note(db, int(result["target_id"]))
        ensure_note_write(db, note, user["id"])
        payload = loads(result["result"], {})
        if result["task_type"] == "summary":
            db.execute("UPDATE notes SET summary = ?, updated_at = ? WHERE id = ?", (payload.get("summary", ""), now_iso(), note["id"]))
        elif result["task_type"] == "tags":
            db.execute("UPDATE notes SET tags = ?, updated_at = ? WHERE id = ?", (dumps(payload.get("tags", [])), now_iso(), note["id"]))
        db.execute(
            "UPDATE ai_results SET status = 'accepted', accepted_by = ?, accepted_at = ? WHERE id = ?",
            (user["id"], now_iso(), result_id),
        )
        return serialize_ai_result(get_ai_result(db, result_id))


async def get_db(request: Request) -> Database:
    return request.app.state.db


async def get_settings(request: Request) -> Settings:
    return request.app.state.settings


async def get_bearer_token(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="missing bearer token")
    return authorization.split(" ", 1)[1].strip()


async def current_user(token: str = Depends(get_bearer_token), db: Database = Depends(get_db)) -> dict[str, Any]:
    row = db.one(
        """
        SELECT u.*
        FROM auth_tokens t
        JOIN users u ON u.id = t.user_id
        WHERE t.token = ?
        """,
        (token,),
    )
    if not row:
        raise HTTPException(status_code=401, detail="invalid token")
    return row


def issue_token(db: Database, user_id: int) -> str:
    token = new_token()
    db.execute(
        "INSERT INTO auth_tokens (token, user_id, created_at) VALUES (?, ?, ?)",
        (token, user_id, now_iso()),
    )
    return token


def get_user(db: Database, user_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM users WHERE id = ?", (user_id,))
    if not row:
        raise HTTPException(status_code=404, detail="user not found")
    return row


def serialize_user(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"],
        "system_role": row["system_role"],
        "created_at": row["created_at"],
    }


def get_course(db: Database, course_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM courses WHERE id = ?", (course_id,))
    if not row:
        raise HTTPException(status_code=404, detail="course not found")
    return row


def serialize_course(row: dict[str, Any], db: Database, user_id: int) -> dict[str, Any]:
    stats = db.one(
        """
        SELECT
          (SELECT COUNT(*) FROM notes WHERE course_id = ?) AS note_count,
          (SELECT COUNT(*) FROM mistakes WHERE course_id = ?) AS mistake_count,
          (SELECT COUNT(*) FROM knowledge_nodes WHERE course_id = ? AND type != 'course_root') AS knowledge_node_count,
          (SELECT role FROM course_members WHERE course_id = ? AND user_id = ?) AS role
        """,
        (row["id"], row["id"], row["id"], row["id"], user_id),
    )
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "semester": row["semester"],
        "tags": loads(row["tags"], []),
        "invite_code": row["invite_code"],
        "created_by": row["created_by"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        "role": stats.get("role") if stats else None,
        "stats": {
            "note_count": stats.get("note_count", 0) if stats else 0,
            "mistake_count": stats.get("mistake_count", 0) if stats else 0,
            "knowledge_node_count": stats.get("knowledge_node_count", 0) if stats else 0,
        },
    }


def member_role(db: Database, course_id: int, user_id: int) -> str | None:
    row = db.one(
        "SELECT role FROM course_members WHERE course_id = ? AND user_id = ?",
        (course_id, user_id),
    )
    return row["role"] if row else None


def ensure_member(db: Database, course_id: int, user_id: int) -> str:
    role = member_role(db, course_id, user_id)
    if not role:
        raise HTTPException(status_code=403, detail="course membership required")
    return role


def ensure_maintainer(db: Database, course_id: int, user_id: int) -> None:
    role = ensure_member(db, course_id, user_id)
    if role not in {"maintainer", "teacher"}:
        raise HTTPException(status_code=403, detail="maintainer role required")


def ensure_owner_or_maintainer(db: Database, course_id: int, owner_id: int, user_id: int) -> None:
    if owner_id == user_id:
        return
    ensure_maintainer(db, course_id, user_id)


def get_node(db: Database, node_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM knowledge_nodes WHERE id = ?", (node_id,))
    if not row:
        raise HTTPException(status_code=404, detail="knowledge node not found")
    return row


def get_parent_node(db: Database, course_id: int, parent_id: int | None) -> dict[str, Any]:
    if parent_id is None:
        row = db.one(
            "SELECT * FROM knowledge_nodes WHERE course_id = ? AND type = 'course_root'",
            (course_id,),
        )
    else:
        row = db.one("SELECT * FROM knowledge_nodes WHERE id = ? AND course_id = ?", (parent_id, course_id))
    if not row:
        raise HTTPException(status_code=404, detail="parent node not found")
    return row


def ensure_node_in_course(db: Database, node_id: int, course_id: int) -> None:
    row = db.one("SELECT id FROM knowledge_nodes WHERE id = ? AND course_id = ?", (node_id, course_id))
    if not row:
        raise HTTPException(status_code=404, detail="node not found in course")


def node_content_counts(db: Database, node_id: int) -> dict[str, int]:
    row = db.one(
        """
        SELECT
          (SELECT COUNT(*) FROM notes WHERE node_id = ?) AS note_count,
          (SELECT COUNT(*) FROM mistakes WHERE node_id = ?) AS mistake_count
        """,
        (node_id, node_id),
    )
    return {"note_count": int(row["note_count"]), "mistake_count": int(row["mistake_count"])}


def serialize_node(
    row: dict[str, Any],
    db: Database,
    include_content: bool = False,
    user_id: int | None = None,
) -> dict[str, Any]:
    counts = node_content_counts(db, int(row["id"]))
    data = {
        "id": row["id"],
        "course_id": row["course_id"],
        "parent_id": row["parent_id"],
        "type": row["type"],
        "title": row["title"],
        "description": row["description"],
        "metadata": loads(row["metadata"], {}),
        "order_index": row["order_index"],
        "depth": row["depth"],
        "path": row["path"],
        "impact": row["impact"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
        **counts,
    }
    if include_content:
        note_filter = "visibility = 'shared'"
        mistake_filter = "visibility = 'shared'"
        params: tuple[Any, ...] = (row["id"],)
        if user_id is not None:
            note_filter = "(visibility = 'shared' OR author_id = ?)"
            mistake_filter = "(visibility = 'shared' OR author_id = ?)"
            data["notes"] = [
                serialize_note(n, db)
                for n in db.all(f"SELECT * FROM notes WHERE node_id = ? AND {note_filter}", (row["id"], user_id))
            ]
            data["mistakes"] = [
                serialize_mistake(m, db)
                for m in db.all(f"SELECT * FROM mistakes WHERE node_id = ? AND {mistake_filter}", (row["id"], user_id))
            ]
        else:
            data["notes"] = [serialize_note(n, db) for n in db.all(f"SELECT * FROM notes WHERE node_id = ? AND {note_filter}", params)]
            data["mistakes"] = [serialize_mistake(m, db) for m in db.all(f"SELECT * FROM mistakes WHERE node_id = ? AND {mistake_filter}", params)]
    return data


def build_tree_response(db: Database, rows: list[dict[str, Any]]) -> dict[str, Any]:
    nodes = [serialize_node(row, db) for row in rows]
    edges = [
        {"source": row["parent_id"], "target": row["id"]}
        for row in rows
        if row["parent_id"] is not None
    ]
    by_parent: dict[int | None, list[dict[str, Any]]] = {}
    for node in nodes:
        by_parent.setdefault(node["parent_id"], []).append(node)

    def attach(node: dict[str, Any]) -> dict[str, Any]:
        children = sorted(by_parent.get(node["id"], []), key=lambda item: (item["order_index"], item["id"]))
        return {**node, "children": [attach(child) for child in children]}

    roots = by_parent.get(None, [])
    tree = attach(roots[0]) if roots else None
    return {"tree": tree, "nodes": nodes, "edges": edges}


def refresh_subtree_paths(db: Database, node_id: int) -> None:
    node = get_node(db, node_id)
    if node["parent_id"] is None:
        depth = 0
        path = node["title"]
    else:
        parent = get_node(db, int(node["parent_id"]))
        depth = int(parent["depth"]) + 1
        path = f"{parent['path']} / {node['title']}"
    db.execute("UPDATE knowledge_nodes SET depth = ?, path = ?, updated_at = ? WHERE id = ?", (depth, path, now_iso(), node_id))
    children = db.all("SELECT id FROM knowledge_nodes WHERE parent_id = ?", (node_id,))
    for child in children:
        refresh_subtree_paths(db, int(child["id"]))


def get_note(db: Database, note_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM notes WHERE id = ?", (note_id,))
    if not row:
        raise HTTPException(status_code=404, detail="note not found")
    return row


def serialize_note(row: dict[str, Any], db: Database, include_comments: bool = False) -> dict[str, Any]:
    node = db.one("SELECT id, title, path FROM knowledge_nodes WHERE id = ?", (row["node_id"],)) if row["node_id"] else None
    data = {
        "id": row["id"],
        "course_id": row["course_id"],
        "node_id": row["node_id"],
        "node_path": node["path"] if node else None,
        "title": row["title"],
        "content_json": loads(row["content_json"], {}),
        "content_text": row["content_text"],
        "content_format": row["content_format"],
        "visibility": row["visibility"],
        "status": row["status"],
        "summary": row["summary"],
        "tags": loads(row["tags"], []),
        "author_id": row["author_id"],
        "like_count": row["like_count"],
        "comment_count": row["comment_count"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }
    if include_comments:
        comments = db.all(
            "SELECT * FROM comments WHERE target_type = 'note' AND target_id = ? ORDER BY created_at",
            (row["id"],),
        )
        data["comments"] = [serialize_comment(c) for c in comments]
    return data


def ensure_note_access(db: Database, note: dict[str, Any], user_id: int) -> None:
    ensure_member(db, int(note["course_id"]), user_id)
    if note["visibility"] != "shared" and note["author_id"] != user_id:
        raise HTTPException(status_code=403, detail="note is private")


def ensure_note_write(db: Database, note: dict[str, Any], user_id: int) -> None:
    ensure_owner_or_maintainer(db, int(note["course_id"]), int(note["author_id"]), user_id)


def create_note_version(db: Database, note_id: int, user_id: int, reason: str) -> None:
    note = get_note(db, note_id)
    db.execute(
        """
        INSERT INTO note_versions (note_id, title, content_json, content_text, changed_by, change_reason, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (note_id, note["title"], note["content_json"], note["content_text"], user_id, reason, now_iso()),
    )


def serialize_version(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "note_id": row["note_id"],
        "title": row["title"],
        "content_json": loads(row["content_json"], {}),
        "content_text": row["content_text"],
        "changed_by": row["changed_by"],
        "change_reason": row["change_reason"],
        "created_at": row["created_at"],
    }


def get_attachment(db: Database, attachment_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM attachments WHERE id = ?", (attachment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="attachment not found")
    return row


def serialize_attachment(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "course_id": row["course_id"],
        "note_id": row["note_id"],
        "mistake_id": row["mistake_id"],
        "file_name": row["file_name"],
        "content_type": row["content_type"],
        "size_bytes": row["size_bytes"],
        "url_path": row["url_path"],
        "uploaded_by": row["uploaded_by"],
        "created_at": row["created_at"],
    }


def delete_attachments_for_target(db: Database, settings: Settings, target_type: str, target_id: int) -> None:
    if target_type == "note":
        column = "note_id"
    elif target_type == "mistake":
        column = "mistake_id"
    else:
        raise ValueError(f"unsupported attachment target: {target_type}")

    rows = db.all(f"SELECT id, stored_name FROM attachments WHERE {column} = ?", (target_id,))
    storage_dir = Path(settings.file_storage_dir)
    for row in rows:
        try:
            (storage_dir / row["stored_name"]).unlink()
        except FileNotFoundError:
            pass
    if rows:
        db.execute(f"DELETE FROM attachments WHERE {column} = ?", (target_id,))


def get_mistake(db: Database, mistake_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM mistakes WHERE id = ?", (mistake_id,))
    if not row:
        raise HTTPException(status_code=404, detail="mistake not found")
    return row


def serialize_mistake(row: dict[str, Any], db: Database) -> dict[str, Any]:
    node = db.one("SELECT id, title, path FROM knowledge_nodes WHERE id = ?", (row["node_id"],)) if row["node_id"] else None
    return {
        "id": row["id"],
        "course_id": row["course_id"],
        "node_id": row["node_id"],
        "node_path": node["path"] if node else None,
        "question_content": row["question_content"],
        "correct_answer": row["correct_answer"],
        "wrong_answer": row["wrong_answer"],
        "error_reason": row["error_reason"],
        "solution": row["solution"],
        "reflection": row["reflection"],
        "question_type": row["question_type"],
        "difficulty": row["difficulty"],
        "mastery_status": row["mastery_status"],
        "tags": loads(row["tags"], []),
        "visibility": row["visibility"],
        "author_id": row["author_id"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def get_comment(db: Database, comment_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM comments WHERE id = ?", (comment_id,))
    if not row:
        raise HTTPException(status_code=404, detail="comment not found")
    return row


def serialize_comment(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "content": row["content"],
        "author_id": row["author_id"],
        "created_at": row["created_at"],
    }


def get_suggestion(db: Database, suggestion_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM suggestions WHERE id = ?", (suggestion_id,))
    if not row:
        raise HTTPException(status_code=404, detail="suggestion not found")
    return row


def serialize_suggestion(row: dict[str, Any], db: Database | None = None) -> dict[str, Any]:
    data = {
        "id": row["id"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "type": row["type"],
        "content": row["content"],
        "status": row["status"],
        "submitter_id": row["submitter_id"],
        "handler_id": row["handler_id"],
        "handled_at": row["handled_at"],
        "created_at": row["created_at"],
    }
    if db is not None:
        data["target_title"] = target_title(db, row["target_type"], int(row["target_id"]))
    return data


def target_title(db: Database, target_type: str, target_id: int) -> str:
    if target_type == "note":
        return get_note(db, target_id)["title"]
    if target_type == "mistake":
        return get_mistake(db, target_id)["question_content"][:80]
    if target_type == "knowledge_node":
        return get_node(db, target_id)["title"]
    if target_type == "suggestion":
        suggestion = get_suggestion(db, target_id)
        return target_title(db, suggestion["target_type"], int(suggestion["target_id"]))
    return ""


def target_course_id(db: Database, target_type: str, target_id: int) -> int:
    if target_type == "note":
        return int(get_note(db, target_id)["course_id"])
    if target_type == "mistake":
        return int(get_mistake(db, target_id)["course_id"])
    if target_type == "knowledge_node":
        return int(get_node(db, target_id)["course_id"])
    if target_type == "suggestion":
        suggestion = get_suggestion(db, target_id)
        return target_course_id(db, suggestion["target_type"], int(suggestion["target_id"]))
    raise HTTPException(status_code=400, detail="unsupported target type")


def match_note(
    db: Database,
    note: dict[str, Any],
    query: str,
    node_id: int | None,
    tag: str | None,
    author_id: int | None,
) -> dict[str, Any] | None:
    if node_id is not None and note["node_id"] != node_id:
        return None
    if author_id is not None and note["author_id"] != author_id:
        return None
    tags = loads(note["tags"], [])
    if tag and tag not in tags:
        return None
    node = db.one("SELECT path FROM knowledge_nodes WHERE id = ?", (note["node_id"],)) if note["node_id"] else None
    fields = {
        "title": note["title"],
        "content": note["content_text"],
        "summary": note["summary"],
        "tag": " ".join(tags),
        "node": node["path"] if node else "",
    }
    matched = [name for name, value in fields.items() if query in (value or "").lower()]
    if not matched:
        return None
    score = sum({"title": 5, "tag": 4, "node": 3, "summary": 2, "content": 1}[name] for name in matched)
    score += min(int(note["like_count"]), 5)
    author = get_user(db, int(note["author_id"]))
    return {
        "source_type": "note",
        "source_id": note["id"],
        "node_id": note["node_id"],
        "author_id": note["author_id"],
        "author_name": author["display_name"],
        "title": note["title"],
        "snippet": make_snippet(note["content_text"] or note["summary"] or note["title"], query),
        "node_path": node["path"] if node else None,
        "matched_fields": matched,
        "score": score,
        "updated_at": note["updated_at"],
    }


def match_mistake(
    db: Database,
    mistake: dict[str, Any],
    query: str,
    node_id: int | None,
    tag: str | None,
    author_id: int | None,
) -> dict[str, Any] | None:
    if node_id is not None and mistake["node_id"] != node_id:
        return None
    if author_id is not None and mistake["author_id"] != author_id:
        return None
    tags = loads(mistake["tags"], [])
    if tag and tag not in tags:
        return None
    node = db.one("SELECT path FROM knowledge_nodes WHERE id = ?", (mistake["node_id"],)) if mistake["node_id"] else None
    content = " ".join(
        [
            mistake["question_content"],
            mistake["correct_answer"],
            mistake["error_reason"],
            mistake["solution"],
            mistake["reflection"],
        ]
    )
    fields = {
        "content": content,
        "tag": " ".join(tags),
        "node": node["path"] if node else "",
        "question_type": mistake["question_type"],
    }
    matched = [name for name, value in fields.items() if query in (value or "").lower()]
    if not matched:
        return None
    score = sum({"tag": 4, "node": 3, "question_type": 2, "content": 1}[name] for name in matched)
    author = get_user(db, int(mistake["author_id"]))
    return {
        "source_type": "mistake",
        "source_id": mistake["id"],
        "node_id": mistake["node_id"],
        "author_id": mistake["author_id"],
        "author_name": author["display_name"],
        "title": mistake["question_content"][:80],
        "snippet": make_snippet(content, query),
        "node_path": node["path"] if node else None,
        "matched_fields": matched,
        "score": score,
        "updated_at": mistake["updated_at"],
    }


def make_snippet(text: str, query: str, width: int = 160) -> str:
    haystack = text or ""
    idx = haystack.lower().find(query.lower())
    if idx < 0:
        return haystack[:width]
    start = max(0, idx - 40)
    end = min(len(haystack), idx + len(query) + width - 40)
    prefix = "..." if start > 0 else ""
    suffix = "..." if end < len(haystack) else ""
    return f"{prefix}{haystack[start:end]}{suffix}"


def create_ai_result(
    db: Database,
    target_type: str,
    target_id: int,
    task_type: str,
    result: dict[str, Any],
    user_id: int,
    status: str = "generated",
    error: str = "",
) -> dict[str, Any]:
    result_id = db.execute(
        """
        INSERT INTO ai_results (target_type, target_id, task_type, status, result, error, created_by, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (target_type, target_id, task_type, status, dumps(result), error, user_id, now_iso()),
    )
    return serialize_ai_result(get_ai_result(db, result_id))


def get_ai_result(db: Database, result_id: int) -> dict[str, Any]:
    row = db.one("SELECT * FROM ai_results WHERE id = ?", (result_id,))
    if not row:
        raise HTTPException(status_code=404, detail="AI result not found")
    return row


def serialize_ai_result(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": row["id"],
        "target_type": row["target_type"],
        "target_id": row["target_id"],
        "task_type": row["task_type"],
        "status": row["status"],
        "result": loads(row["result"], {}),
        "error": row["error"],
        "created_by": row["created_by"],
        "accepted_by": row["accepted_by"],
        "accepted_at": row["accepted_at"],
        "created_at": row["created_at"],
    }


app = create_app()
