from __future__ import annotations

import base64
import zipfile
from io import BytesIO

import pytest
from httpx import ASGITransport, AsyncClient

from noteweave.api.app import create_app
from noteweave.core.settings import Settings


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def make_docx_bytes(text: str) -> bytes:
    buffer = BytesIO()
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        f"<w:p><w:r><w:t>{text}</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>"
    )
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("word/document.xml", document_xml)
    return buffer.getvalue()


@pytest.mark.anyio
async def test_course_note_collaboration_search_and_ai_flow(tmp_path):
    app = create_app(
        Settings(
            database_path=str(tmp_path / "noteweave.sqlite3"),
            file_storage_dir=str(tmp_path / "uploads"),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        alice_res = await client.post(
            "/api/auth/register",
            json={
                "username": "alice",
                "password": "password123",
                "display_name": "Alice",
            },
        )
        assert alice_res.status_code == 200
        alice_token = alice_res.json()["token"]
        alice_id = alice_res.json()["user"]["id"]
        assert alice_res.json()["user"]["system_role"] == "admin"
        alice = auth_headers(alice_token)

        profile_update_res = await client.patch(
            "/api/auth/me",
            headers=alice,
            json={"display_name": "Alice Cooper"},
        )
        assert profile_update_res.status_code == 200
        assert profile_update_res.json()["display_name"] == "Alice Cooper"
        me_res = await client.get("/api/auth/me", headers=alice)
        assert me_res.status_code == 200
        assert me_res.json()["display_name"] == "Alice Cooper"
        assert me_res.json()["system_role"] == "admin"

        admin_overview_res = await client.get("/api/admin/overview", headers=alice)
        assert admin_overview_res.status_code == 200
        assert admin_overview_res.json()["stats"]["user_count"] == 1
        wrong_password_update_res = await client.patch(
            "/api/auth/me",
            headers=alice,
            json={"current_password": "wrong-password", "new_password": "new-password123"},
        )
        assert wrong_password_update_res.status_code == 403
        password_update_res = await client.patch(
            "/api/auth/me",
            headers=alice,
            json={"current_password": "password123", "new_password": "new-password123"},
        )
        assert password_update_res.status_code == 200
        logout_res = await client.post("/api/auth/logout", headers=alice)
        assert logout_res.status_code == 200
        logged_out_me_res = await client.get("/api/auth/me", headers=alice)
        assert logged_out_me_res.status_code == 401
        old_login_res = await client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "password123"},
        )
        assert old_login_res.status_code == 401
        new_login_res = await client.post(
            "/api/auth/login",
            json={"username": "alice", "password": "new-password123"},
        )
        assert new_login_res.status_code == 200
        alice_token = new_login_res.json()["token"]
        alice = auth_headers(alice_token)

        ai_status_res = await client.get("/api/ai/config/status", headers=alice)
        assert ai_status_res.status_code == 200
        ai_status = ai_status_res.json()
        assert ai_status["enabled"] is True
        assert ai_status["remote_configured"] is False
        assert ai_status["fallback_available"] is True
        assert "model_api_key" not in ai_status

        course_res = await client.post(
            "/api/courses",
            headers=alice,
            json={
                "name": "Data Structures",
                "description": "Course notes",
                "semester": "2026 Spring",
                "tags": ["cs", "algorithm"],
            },
        )
        assert course_res.status_code == 200
        course = course_res.json()
        assert course["role"] == "maintainer"
        assert course["stats"]["knowledge_node_count"] == 0

        tree_res = await client.get(f"/api/courses/{course['id']}/tree", headers=alice)
        assert tree_res.status_code == 200
        root_id = tree_res.json()["tree"]["id"]

        chapter_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=alice,
            json={
                "parent_id": root_id,
                "type": "chapter",
                "title": "Sorting",
            },
        )
        assert chapter_res.status_code == 200
        chapter_id = chapter_res.json()["id"]

        point_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=alice,
            json={
                "parent_id": chapter_id,
                "type": "knowledge_point",
                "title": "Quick Sort",
                "description": "Divide and conquer sorting",
            },
        )
        assert point_res.status_code == 200
        point_id = point_res.json()["id"]

        note_res = await client.post(
            "/api/notes",
            headers=alice,
            json={
                "course_id": course["id"],
                "node_id": point_id,
                "title": "Quick sort complexity",
                "content_text": "Quick sort uses partitioning. Average complexity is O(n log n).",
                "content_json": {"type": "markdown"},
                "visibility": "private",
                "status": "draft",
                "tags": ["sorting", "quick-sort"],
            },
        )
        assert note_res.status_code == 200
        note_id = note_res.json()["id"]
        note_chunk = app.state.db.one(
            "SELECT * FROM search_chunks WHERE source_type = 'note' AND source_id = ?",
            (note_id,),
        )
        assert note_chunk is not None
        assert note_chunk["content"] == "Quick sort uses partitioning. Average complexity is O(n log n)."
        assert note_chunk["tags_text"].splitlines() == ["sorting", "quick-sort"]

        image_bytes = base64.b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
        )
        attachment_res = await client.post(
            "/api/attachments",
            headers=alice,
            json={
                "course_id": course["id"],
                "note_id": note_id,
                "file_name": "partition.png",
                "content_type": "image/png",
                "data_base64": base64.b64encode(image_bytes).decode("ascii"),
            },
        )
        assert attachment_res.status_code == 200
        attachment = attachment_res.json()
        assert attachment["size_bytes"] == len(image_bytes)
        assert attachment["markdown"].startswith("![partition.png](/api/files/")

        file_res = await client.get(attachment["url_path"])
        assert file_res.status_code == 200
        assert file_res.headers["content-type"] == "image/png"
        assert file_res.content == image_bytes

        note_with_image_res = await client.patch(
            f"/api/notes/{note_id}",
            headers=alice,
            json={
                "content_text": f"{note_res.json()['content_text']}\n\n{attachment['markdown']}",
                "content_json": {"type": "markdown", "attachments": [attachment["id"]]},
            },
        )
        assert note_with_image_res.status_code == 200
        assert attachment["markdown"] in note_with_image_res.json()["content_text"]

        publish_res = await client.post(f"/api/notes/{note_id}/publish", headers=alice)
        assert publish_res.status_code == 200
        assert publish_res.json()["visibility"] == "shared"
        versions_res = await client.get(f"/api/notes/{note_id}/versions", headers=alice)
        assert versions_res.status_code == 200
        versions = versions_res.json()
        assert [version["change_reason"] for version in versions[:3]] == ["publish", "manual update", "initial"]
        assert versions[0]["content_text"] == note_with_image_res.json()["content_text"]
        assert attachment["markdown"] in versions[0]["content_text"]

        popular_note_res = await client.post(
            "/api/notes",
            headers=alice,
            json={
                "course_id": course["id"],
                "node_id": point_id,
                "title": "Popular sorting note",
                "content_text": "A short shared sorting note.",
                "visibility": "shared",
                "status": "published",
                "tags": ["sorting"],
            },
        )
        assert popular_note_res.status_code == 200
        popular_note_id = popular_note_res.json()["id"]

        summary_res = await client.post(f"/api/ai/notes/{note_id}/summary", headers=alice)
        assert summary_res.status_code == 200
        summary_id = summary_res.json()["id"]
        assert summary_res.json()["result"]["source"] == "fallback"
        summary_text = f"{summary_res.json()['result']['summary']} Edited by Alice."
        accept_summary_res = await client.post(
            f"/api/ai/results/{summary_id}/accept",
            headers=alice,
            json={"summary": summary_text},
        )
        assert accept_summary_res.status_code == 200
        assert accept_summary_res.json()["status"] == "accepted"
        assert accept_summary_res.json()["result"]["summary"] == summary_text
        assert accept_summary_res.json()["result"]["edited_by"] == alice_id
        summary_chunk = app.state.db.one(
            "SELECT * FROM search_chunks WHERE source_type = 'note' AND source_id = ?",
            (note_id,),
        )
        assert summary_chunk["summary"] == summary_text

        tags_res = await client.post(f"/api/ai/notes/{note_id}/tags", headers=alice)
        assert tags_res.status_code == 200
        assert tags_res.json()["result"]["source"] == "fallback"
        extracted_tags = [*tags_res.json()["result"]["tags"], "manual-review"]
        accept_tags_res = await client.post(
            f"/api/ai/results/{tags_res.json()['id']}/accept",
            headers=alice,
            json={"tags": extracted_tags},
        )
        assert accept_tags_res.status_code == 200
        assert accept_tags_res.json()["result"]["tags"] == extracted_tags
        tags_chunk = app.state.db.one(
            "SELECT * FROM search_chunks WHERE source_type = 'note' AND source_id = ?",
            (note_id,),
        )
        assert tags_chunk["tags_text"].splitlines() == extracted_tags

        rejected_summary_res = await client.post(f"/api/ai/notes/{popular_note_id}/summary", headers=alice)
        assert rejected_summary_res.status_code == 200
        reject_ai_res = await client.post(
            f"/api/ai/results/{rejected_summary_res.json()['id']}/reject",
            headers=alice,
        )
        assert reject_ai_res.status_code == 200
        assert reject_ai_res.json()["status"] == "rejected"
        popular_note_detail_res = await client.get(f"/api/notes/{popular_note_id}", headers=alice)
        assert popular_note_detail_res.status_code == 200
        assert popular_note_detail_res.json()["summary"] == ""

        comment_res = await client.post(
            "/api/comments",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": note_id,
                "content": "This is useful for exam review.",
            },
        )
        assert comment_res.status_code == 200

        reaction_res = await client.post(
            "/api/reactions",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": note_id,
                "reaction_type": "like",
            },
        )
        assert reaction_res.status_code == 200

        popular_reaction_res = await client.post(
            "/api/reactions",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": popular_note_id,
                "reaction_type": "like",
            },
        )
        assert popular_reaction_res.status_code == 200
        popular_comment_res = await client.post(
            "/api/comments",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": popular_note_id,
                "content": "Extra discussion.",
            },
        )
        assert popular_comment_res.status_code == 200
        popular_second_comment_res = await client.post(
            "/api/comments",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": popular_note_id,
                "content": "Another discussion point.",
            },
        )
        assert popular_second_comment_res.status_code == 200
        paged_comments_res = await client.get(
            "/api/comments",
            headers=alice,
            params={"target_type": "note", "target_id": popular_note_id, "limit": 1, "offset": 1},
        )
        assert paged_comments_res.status_code == 200
        assert [comment["content"] for comment in paged_comments_res.json()] == ["Another discussion point."]

        favorite_note_res = await client.post(
            "/api/reactions",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": note_id,
                "reaction_type": "favorite",
            },
        )
        assert favorite_note_res.status_code == 200

        mistake_res = await client.post(
            "/api/mistakes",
            headers=alice,
            json={
                "course_id": course["id"],
                "node_id": point_id,
                "question_content": "What is quick sort worst-case complexity?",
                "correct_answer": "O(n^2)",
                "wrong_answer": "O(n log n)",
                "error_reason": "Ignored unbalanced partitions.",
                "solution": "Use randomized pivot to reduce worst-case probability.",
                "reflection": "Check partition balance.",
                "question_type": "complexity",
                "mastery_status": "todo",
                "tags": ["sorting"],
                "visibility": "shared",
            },
        )
        assert mistake_res.status_code == 200
        mistake_id = mistake_res.json()["id"]
        mistake_chunk = app.state.db.one(
            "SELECT * FROM search_chunks WHERE source_type = 'mistake' AND source_id = ?",
            (mistake_id,),
        )
        assert mistake_chunk is not None
        assert "Ignored unbalanced partitions." in mistake_chunk["content"]

        favorite_mistake_res = await client.post(
            "/api/reactions",
            headers=alice,
            json={
                "target_type": "mistake",
                "target_id": mistake_id,
                "reaction_type": "favorite",
            },
        )
        assert favorite_mistake_res.status_code == 200

        mastery_res = await client.patch(
            f"/api/mistakes/{mistake_id}/mastery",
            headers=alice,
            json={"mastery_status": "retry"},
        )
        assert mastery_res.status_code == 200
        assert mastery_res.json()["mastery_status"] == "retry"

        suggestion_res = await client.post(
            "/api/suggestions",
            headers=alice,
            json={
                "target_type": "note",
                "target_id": note_id,
                "type": "correction",
                "content": "Add worst-case complexity notes.",
            },
        )
        assert suggestion_res.status_code == 200
        handle_res = await client.patch(
            f"/api/suggestions/{suggestion_res.json()['id']}",
            headers=alice,
            json={"status": "accepted"},
        )
        assert handle_res.status_code == 200
        assert handle_res.json()["status"] == "accepted"

        suggestions_res = await client.get(
            f"/api/courses/{course['id']}/suggestions", headers=alice
        )
        assert suggestions_res.status_code == 200
        suggestions = suggestions_res.json()
        assert suggestions[0]["status"] == "accepted"
        assert suggestions[0]["target_title"] == "Quick sort complexity"

        node_detail_res = await client.get(f"/api/tree/nodes/{point_id}/detail", headers=alice)
        assert node_detail_res.status_code == 200
        node_detail = node_detail_res.json()
        assert {note["id"] for note in node_detail["notes"]} >= {note_id, popular_note_id}
        assert {mistake["id"] for mistake in node_detail["mistakes"]} == {mistake_id}
        assert {"sorting", "manual-review"}.issubset({item["tag"] for item in node_detail["tag_summary"]})
        assert node_detail["summaries"][0]["summary"] == summary_text
        assert {comment["content"] for comment in node_detail["recent_comments"]} >= {
            "This is useful for exam review.",
            "Extra discussion.",
            "Another discussion point.",
        }

        search_res = await client.get(
            "/api/search",
            headers=alice,
            params={"course_id": course["id"], "q": "quick"},
        )
        assert search_res.status_code == 200
        search_results = search_res.json()
        assert {item["source_type"] for item in search_results} == {"note", "mistake"}
        assert all("node_path" in item for item in search_results)
        assert all(item["author_id"] == alice_id for item in search_results)
        assert all(item["author_name"] == "Alice Cooper" for item in search_results)

        scoped_search_res = await client.get(
            "/api/search",
            headers=alice,
            params={
                "course_id": course["id"],
                "q": "quick",
                "node_id": point_id,
                "author_id": alice_id,
                "source_type": "note",
            },
        )
        assert scoped_search_res.status_code == 200
        scoped_results = scoped_search_res.json()
        assert {item["source_type"] for item in scoped_results} == {"note"}
        assert all(item["node_id"] == point_id for item in scoped_results)
        assert note_id in {item["source_id"] for item in scoped_results}

        missing_author_search_res = await client.get(
            "/api/search",
            headers=alice,
            params={"course_id": course["id"], "q": "quick", "author_id": 999999},
        )
        assert missing_author_search_res.status_code == 200
        assert missing_author_search_res.json() == []

        review_res = await client.get(
            f"/api/courses/{course['id']}/review",
            headers=alice,
            params={"mode": "favorites", "node_id": point_id},
        )
        assert review_res.status_code == 200
        review_items = review_res.json()
        assert {item["source_type"] for item in review_items} == {"note", "mistake"}
        assert all(item["is_favorite"] for item in review_items)

        paged_notes_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"], "limit": 1, "offset": 1},
        )
        assert paged_notes_res.status_code == 200
        assert len(paged_notes_res.json()) == 1

        paged_mistakes_res = await client.get(
            "/api/mistakes",
            headers=alice,
            params={"course_id": course["id"], "limit": 1, "offset": 0},
        )
        assert paged_mistakes_res.status_code == 200
        assert len(paged_mistakes_res.json()) == 1

        paged_review_res = await client.get(
            f"/api/courses/{course['id']}/review",
            headers=alice,
            params={"mode": "all", "limit": 1, "offset": 1},
        )
        assert paged_review_res.status_code == 200
        assert len(paged_review_res.json()) == 1

        review_mistake_res = await client.get(
            f"/api/courses/{course['id']}/review",
            headers=alice,
            params={"tag": "sorting", "question_type": "complexity"},
        )
        assert review_mistake_res.status_code == 200
        assert any(item["source_id"] == mistake_id for item in review_mistake_res.json())

        note_list_with_favorite_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"]},
        )
        assert note_list_with_favorite_res.status_code == 200
        note_item = next(item for item in note_list_with_favorite_res.json() if item["id"] == note_id)
        assert note_item["is_liked"] is True
        assert note_item["like_reaction_id"] == reaction_res.json()["id"]
        assert note_item["like_count"] == 1
        assert note_item["is_favorite"] is True
        assert note_item["favorite_reaction_id"] == favorite_note_res.json()["id"]

        cancel_like_res = await client.delete(
            f"/api/reactions/{reaction_res.json()['id']}",
            headers=alice,
        )
        assert cancel_like_res.status_code == 200
        note_list_after_unlike_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"]},
        )
        note_after_unlike = next(item for item in note_list_after_unlike_res.json() if item["id"] == note_id)
        assert note_after_unlike["is_liked"] is False
        assert note_after_unlike["like_reaction_id"] is None
        assert note_after_unlike["like_count"] == 0

        cancel_favorite_note_res = await client.delete(
            f"/api/reactions/{favorite_note_res.json()['id']}",
            headers=alice,
        )
        assert cancel_favorite_note_res.status_code == 200
        note_list_after_cancel_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"]},
        )
        note_after_cancel = next(item for item in note_list_after_cancel_res.json() if item["id"] == note_id)
        assert note_after_cancel["is_favorite"] is False
        assert note_after_cancel["favorite_reaction_id"] is None

        review_after_cancel_res = await client.get(
            f"/api/courses/{course['id']}/review",
            headers=alice,
            params={"mode": "favorites", "node_id": point_id},
        )
        assert review_after_cancel_res.status_code == 200
        assert {item["source_type"] for item in review_after_cancel_res.json()} == {"mistake"}

        note_view_res = await client.post(
            "/api/views",
            headers=alice,
            json={"target_type": "note", "target_id": note_id},
        )
        assert note_view_res.status_code == 200
        mistake_view_res = await client.post(
            "/api/views",
            headers=alice,
            json={"target_type": "mistake", "target_id": mistake_id},
        )
        assert mistake_view_res.status_code == 200
        viewed_review_res = await client.get(
            f"/api/courses/{course['id']}/review",
            headers=alice,
            params={"mode": "viewed", "node_id": point_id},
        )
        assert viewed_review_res.status_code == 200
        viewed_items = viewed_review_res.json()
        assert {item["source_type"] for item in viewed_items} == {"note", "mistake"}
        assert all(item["last_viewed_at"] for item in viewed_items)

        shared_by_likes_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"], "shared_only": True, "sort": "likes"},
        )
        assert shared_by_likes_res.status_code == 200
        assert [item["id"] for item in shared_by_likes_res.json()[:2]] == [popular_note_id, note_id]

        shared_by_comments_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"], "shared_only": True, "sort": "comments"},
        )
        assert shared_by_comments_res.status_code == 200
        assert [item["id"] for item in shared_by_comments_res.json()[:2]] == [popular_note_id, note_id]

        invalid_sort_res = await client.get(
            "/api/notes",
            headers=alice,
            params={"course_id": course["id"], "sort": "unknown"},
        )
        assert invalid_sort_res.status_code == 400

        bob_res = await client.post(
            "/api/auth/register",
            json={"username": "bob", "password": "password123"},
        )
        assert bob_res.status_code == 200
        bob = auth_headers(bob_res.json()["token"])

        before_join = await client.get(f"/api/courses/{course['id']}", headers=bob)
        assert before_join.status_code == 403
        course_search_res = await client.get(
            "/api/courses/search",
            headers=bob,
            params={"q": "Data"},
        )
        assert course_search_res.status_code == 200
        search_results = course_search_res.json()
        assert search_results[0]["id"] == course["id"]
        assert "invite_code" not in search_results[0]
        assert search_results[0]["role"] is None
        search_join_res = await client.post(f"/api/courses/{course['id']}/join-public", headers=bob)
        assert search_join_res.status_code == 200
        assert search_join_res.json()["role"] == "student"

        join_res = await client.post(
            "/api/courses/join",
            headers=bob,
            json={"invite_code": course["invite_code"]},
        )
        assert join_res.status_code == 200
        assert join_res.json()["role"] == "student"

        bob_update_course_res = await client.patch(
            f"/api/courses/{course['id']}",
            headers=bob,
            json={"name": "Unauthorized Rename"},
        )
        assert bob_update_course_res.status_code == 403

        course_update_res = await client.patch(
            f"/api/courses/{course['id']}",
            headers=alice,
            json={
                "name": "Advanced Data Structures",
                "description": "Updated course notes",
                "semester": "2026 Summer",
                "tags": ["cs", "review"],
            },
        )
        assert course_update_res.status_code == 200
        assert course_update_res.json()["name"] == "Advanced Data Structures"
        assert course_update_res.json()["tags"] == ["cs", "review"]

        renamed_tree_res = await client.get(f"/api/courses/{course['id']}/tree", headers=alice)
        assert renamed_tree_res.status_code == 200
        renamed_tree = renamed_tree_res.json()
        assert renamed_tree["tree"]["title"] == "Advanced Data Structures"
        renamed_point = next(node for node in renamed_tree["nodes"] if node["id"] == point_id)
        assert renamed_point["path"].startswith("Advanced Data Structures /")

        shared_notes_res = await client.get(
            "/api/notes",
            headers=bob,
            params={"course_id": course["id"], "shared_only": True},
        )
        assert shared_notes_res.status_code == 200
        assert shared_notes_res.json()[0]["id"] == note_id

        bob_delete_note_res = await client.delete(f"/api/notes/{note_id}", headers=bob)
        assert bob_delete_note_res.status_code == 403

        temp_note_res = await client.post(
            "/api/notes",
            headers=alice,
            json={
                "course_id": course["id"],
                "node_id": point_id,
                "title": "Temporary draft",
                "content_text": "This draft should be deleted.",
            },
        )
        assert temp_note_res.status_code == 200
        temp_note_id = temp_note_res.json()["id"]
        bob_private_note_comments_res = await client.get(
            "/api/comments",
            headers=bob,
            params={"target_type": "note", "target_id": temp_note_id},
        )
        assert bob_private_note_comments_res.status_code == 403
        delete_temp_note_res = await client.delete(f"/api/notes/{temp_note_id}", headers=alice)
        assert delete_temp_note_res.status_code == 200
        assert (
            app.state.db.one(
                "SELECT id FROM search_chunks WHERE source_type = 'note' AND source_id = ?",
                (temp_note_id,),
            )
            is None
        )
        deleted_note_res = await client.get(f"/api/notes/{temp_note_id}", headers=alice)
        assert deleted_note_res.status_code == 404

        temp_mistake_res = await client.post(
            "/api/mistakes",
            headers=alice,
            json={
                "course_id": course["id"],
                "node_id": point_id,
                "question_content": "Temporary mistake",
                "visibility": "private",
            },
        )
        assert temp_mistake_res.status_code == 200
        temp_mistake_id = temp_mistake_res.json()["id"]
        bob_delete_mistake_res = await client.delete(f"/api/mistakes/{mistake_id}", headers=bob)
        assert bob_delete_mistake_res.status_code == 403
        delete_temp_mistake_res = await client.delete(f"/api/mistakes/{temp_mistake_id}", headers=alice)
        assert delete_temp_mistake_res.status_code == 200
        assert (
            app.state.db.one(
                "SELECT id FROM search_chunks WHERE source_type = 'mistake' AND source_id = ?",
                (temp_mistake_id,),
            )
            is None
        )
        mistakes_after_delete_res = await client.get(
            "/api/mistakes",
            headers=alice,
            params={"course_id": course["id"]},
        )
        assert temp_mistake_id not in {item["id"] for item in mistakes_after_delete_res.json()}

        bob_audit_res = await client.get(f"/api/courses/{course['id']}/audit-logs", headers=bob)
        assert bob_audit_res.status_code == 403

        members_res = await client.get(f"/api/courses/{course['id']}/members", headers=alice)
        assert members_res.status_code == 200
        bob_id = next(member["id"] for member in members_res.json() if member["username"] == "bob")
        role_update_res = await client.patch(
            f"/api/courses/{course['id']}/members/{bob_id}",
            headers=alice,
            json={"role": "teacher"},
        )
        assert role_update_res.status_code == 200
        updated_members_res = await client.get(f"/api/courses/{course['id']}/members", headers=alice)
        assert next(member["role"] for member in updated_members_res.json() if member["id"] == bob_id) == "teacher"

        audit_res = await client.get(f"/api/courses/{course['id']}/audit-logs", headers=alice)
        assert audit_res.status_code == 200
        audit_logs = audit_res.json()
        audit_actions = {item["action"] for item in audit_logs}
        assert {
            "course.update",
            "note.publish",
            "note.delete",
            "mistake.delete",
            "suggestion.accepted",
            "ai.accept",
            "ai.reject",
            "member.role_update",
        }.issubset(audit_actions)
        member_audit = next(item for item in audit_logs if item["action"] == "member.role_update")
        assert member_audit["actor_id"] == alice_id
        assert member_audit["target_type"] == "user"
        assert member_audit["target_id"] == bob_id
        assert member_audit["metadata"]["role"] == "teacher"


@pytest.mark.anyio
async def test_course_member_lifecycle(tmp_path):
    app = create_app(
        Settings(
            database_path=str(tmp_path / "noteweave.sqlite3"),
            file_storage_dir=str(tmp_path / "uploads"),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        alice_res = await client.post(
            "/api/auth/register",
            json={"username": "alice", "password": "password123", "display_name": "Alice"},
        )
        assert alice_res.status_code == 200
        alice = auth_headers(alice_res.json()["token"])
        alice_id = alice_res.json()["user"]["id"]

        course_res = await client.post(
            "/api/courses",
            headers=alice,
            json={
                "name": "Algorithms",
                "description": "Lifecycle test",
                "semester": "2026",
                "tags": ["cs"],
            },
        )
        assert course_res.status_code == 200
        course = course_res.json()

        bob_res = await client.post(
            "/api/auth/register",
            json={"username": "bob", "password": "password123", "display_name": "Bob"},
        )
        assert bob_res.status_code == 200
        bob_id = bob_res.json()["user"]["id"]
        bob = auth_headers(bob_res.json()["token"])

        carol_res = await client.post(
            "/api/auth/register",
            json={"username": "carol", "password": "password123", "display_name": "Carol"},
        )
        assert carol_res.status_code == 200
        carol_id = carol_res.json()["user"]["id"]
        carol = auth_headers(carol_res.json()["token"])

        dave_res = await client.post(
            "/api/auth/register",
            json={"username": "dave", "password": "password123", "display_name": "Dave"},
        )
        assert dave_res.status_code == 200
        dave_id = dave_res.json()["user"]["id"]
        dave = auth_headers(dave_res.json()["token"])

        for token in (bob, carol, dave):
            res = await client.post(f"/api/courses/{course['id']}/join-public", headers=token)
            assert res.status_code == 200

        last_downgrade_res = await client.patch(
            f"/api/courses/{course['id']}/members/{alice_id}",
            headers=alice,
            json={"role": "student"},
        )
        assert last_downgrade_res.status_code == 409
        assert "last maintainer" in last_downgrade_res.json()["detail"]

        remove_member_res = await client.delete(
            f"/api/courses/{course['id']}/members/{bob_id}", headers=alice
        )
        assert remove_member_res.status_code == 200

        bob_course_res = await client.get(f"/api/courses/{course['id']}", headers=bob)
        assert bob_course_res.status_code == 403

        non_maintainer_remove_res = await client.delete(
            f"/api/courses/{course['id']}/members/{carol_id}",
            headers=bob,
        )
        assert non_maintainer_remove_res.status_code == 403

        leave_res = await client.post(f"/api/courses/{course['id']}/leave", headers=carol)
        assert leave_res.status_code == 200

        last_maintainer_leave_res = await client.post(
            f"/api/courses/{course['id']}/leave",
            headers=alice,
        )
        assert last_maintainer_leave_res.status_code == 409
        assert "last maintainer" in last_maintainer_leave_res.json()["detail"]

        promote_dave_res = await client.patch(
            f"/api/courses/{course['id']}/members/{dave_id}",
            headers=alice,
            json={"role": "maintainer"},
        )
        assert promote_dave_res.status_code == 200

        alice_leave_res = await client.post(
            f"/api/courses/{course['id']}/leave",
            headers=alice,
        )
        assert alice_leave_res.status_code == 200
        assert (
            app.state.db.one(
                "SELECT role FROM course_members WHERE course_id = ? AND user_id = ?",
                (course["id"], alice_id),
            )
            is None
        )

        final_leave_res = await client.post(f"/api/courses/{course['id']}/leave", headers=dave)
        assert final_leave_res.status_code == 409
        assert "last maintainer" in final_leave_res.json()["detail"]

        self_remove_res = await client.delete(
            f"/api/courses/{course['id']}/members/{dave_id}",
            headers=dave,
        )
        assert self_remove_res.status_code == 400


@pytest.mark.anyio
async def test_node_deletion_blocked_by_subtree_content(tmp_path):
    app = create_app(
        Settings(
            database_path=str(tmp_path / "noteweave.sqlite3"),
            file_storage_dir=str(tmp_path / "uploads"),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_res = await client.post(
            "/api/auth/register",
            json={"username": "maintainer", "password": "password123", "display_name": "Maintainer"},
        )
        assert auth_res.status_code == 200
        headers = auth_headers(auth_res.json()["token"])

        course_res = await client.post(
            "/api/courses",
            headers=headers,
            json={"name": "Algorithms", "description": "", "semester": "", "tags": []},
        )
        assert course_res.status_code == 200
        course = course_res.json()

        tree_res = await client.get(f"/api/courses/{course['id']}/tree", headers=headers)
        assert tree_res.status_code == 200
        root_id = tree_res.json()["tree"]["id"]

        chapter_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=headers,
            json={"parent_id": root_id, "type": "chapter", "title": "Chapter"},
        )
        assert chapter_res.status_code == 200
        chapter_id = chapter_res.json()["id"]

        point_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=headers,
            json={"parent_id": chapter_id, "type": "knowledge_point", "title": "Point"},
        )
        assert point_res.status_code == 200
        point_id = point_res.json()["id"]

        subpoint_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=headers,
            json={"parent_id": point_id, "type": "knowledge_point", "title": "Sub Point"},
        )
        assert subpoint_res.status_code == 200
        subpoint_id = subpoint_res.json()["id"]

        note_res = await client.post(
            "/api/notes",
            headers=headers,
            json={
                "course_id": course["id"],
                "node_id": subpoint_id,
                "title": "Nested note",
                "content_text": "content",
                "visibility": "private",
                "status": "draft",
            },
        )
        assert note_res.status_code == 200

        delete_chapter_res = await client.delete(f"/api/tree/nodes/{chapter_id}", headers=headers)
        assert delete_chapter_res.status_code == 409
        detail = delete_chapter_res.json()["detail"]
        assert detail["message"] == "node has content"
        assert detail["counts"]["subtree_node_count"] == 3
        assert detail["counts"]["note_count"] == 1
        assert detail["counts"]["mistake_count"] == 0

        note_delete_res = await client.delete(f"/api/notes/{note_res.json()['id']}", headers=headers)
        assert note_delete_res.status_code == 200

        delete_subpoint_res = await client.delete(f"/api/tree/nodes/{subpoint_id}", headers=headers)
        assert delete_subpoint_res.status_code == 200
        delete_point_res = await client.delete(f"/api/tree/nodes/{point_id}", headers=headers)
        assert delete_point_res.status_code == 200
        delete_chapter_after_content_clear_res = await client.delete(f"/api/tree/nodes/{chapter_id}", headers=headers)
        assert delete_chapter_after_content_clear_res.status_code == 200


@pytest.mark.anyio
async def test_node_move_rejects_cyclic_hierarchy(tmp_path):
    app = create_app(
        Settings(
            database_path=str(tmp_path / "noteweave.sqlite3"),
            file_storage_dir=str(tmp_path / "uploads"),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_res = await client.post(
            "/api/auth/register",
            json={"username": "maintainer", "password": "password123", "display_name": "Maintainer"},
        )
        assert auth_res.status_code == 200
        headers = auth_headers(auth_res.json()["token"])

        course_res = await client.post(
            "/api/courses",
            headers=headers,
            json={"name": "Deep Tree", "description": "", "semester": "", "tags": []},
        )
        assert course_res.status_code == 200
        course = course_res.json()

        tree_res = await client.get(f"/api/courses/{course['id']}/tree", headers=headers)
        assert tree_res.status_code == 200
        root_id = tree_res.json()["tree"]["id"]

        chapter_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=headers,
            json={"parent_id": root_id, "type": "chapter", "title": "Chapter A"},
        )
        assert chapter_res.status_code == 200
        chapter_id = chapter_res.json()["id"]

        point_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=headers,
            json={"parent_id": chapter_id, "type": "knowledge_point", "title": "Point A"},
        )
        assert point_res.status_code == 200
        point_id = point_res.json()["id"]

        subpoint_res = await client.post(
            f"/api/courses/{course['id']}/tree/nodes",
            headers=headers,
            json={"parent_id": point_id, "type": "knowledge_point", "title": "Sub Point A"},
        )
        assert subpoint_res.status_code == 200
        subpoint_id = subpoint_res.json()["id"]

        reject_move_res = await client.post(
            f"/api/tree/nodes/{chapter_id}/move",
            headers=headers,
            json={"parent_id": subpoint_id, "order_index": 0},
        )
        assert reject_move_res.status_code == 400
        assert reject_move_res.json()["detail"] == "cannot move node into its own subtree"

        move_to_root_res = await client.post(
            f"/api/tree/nodes/{subpoint_id}/move",
            headers=headers,
            json={"parent_id": root_id, "order_index": 0},
        )
        assert move_to_root_res.status_code == 200


@pytest.mark.anyio
async def test_document_import_creates_classified_notes_and_qa_context(tmp_path):
    app = create_app(
        Settings(
            database_path=str(tmp_path / "noteweave.sqlite3"),
            file_storage_dir=str(tmp_path / "uploads"),
        )
    )

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        auth_res = await client.post(
            "/api/auth/register",
            json={"username": "importer", "password": "password123", "display_name": "Importer"},
        )
        assert auth_res.status_code == 200
        headers = auth_headers(auth_res.json()["token"])

        markdown = "# Dijkstra\n\nDijkstra only works with non-negative graph edges."
        md_res = await client.post(
            "/api/notes/import",
            headers=headers,
            json={
                "file_name": "dijkstra.md",
                "content_type": "text/markdown",
                "data_base64": base64.b64encode(markdown.encode("utf-8")).decode("ascii"),
                "visibility": "shared",
                "tags": ["graph"],
            },
        )
        assert md_res.status_code == 200
        imported = md_res.json()
        assert imported["note"]["title"] == "dijkstra"
        assert "non-negative graph edges" in imported["note"]["content_text"]
        assert imported["classification"]["course_name"]
        assert imported["document"]["parser"] == "markdown"
        assert imported["attachment"]["file_name"] == "dijkstra.md"

        docx_res = await client.post(
            "/api/notes/import",
            headers=headers,
            json={
                "file_name": "sorting.docx",
                "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                "data_base64": base64.b64encode(make_docx_bytes("Quick sort uses partitioning.")).decode("ascii"),
                "visibility": "private",
                "tags": ["sorting"],
            },
        )
        assert docx_res.status_code == 200
        assert docx_res.json()["document"]["parser"] == "docx-xml"
        assert "Quick sort uses partitioning." in docx_res.json()["note"]["content_text"]
        private_note_id = docx_res.json()["note"]["id"]

        qa_res = await client.post(
            "/api/notes/ask",
            headers=headers,
            json={"question": "When does Dijkstra work?", "limit": 5},
        )
        assert qa_res.status_code == 200
        qa = qa_res.json()
        assert qa["source"] == "fallback"
        assert qa["contexts"]
        assert any("Dijkstra" in context["title"] or "Dijkstra" in context["content"] for context in qa["contexts"])

        bob_res = await client.post(
            "/api/auth/register",
            json={"username": "reader", "password": "password123", "display_name": "Reader"},
        )
        assert bob_res.status_code == 200
        assert bob_res.json()["user"]["system_role"] == "user"
        bob = auth_headers(bob_res.json()["token"])

        bob_admin_res = await client.get("/api/admin/overview", headers=bob)
        assert bob_admin_res.status_code == 403

        feed_res = await client.get("/api/notes/feed", headers=bob)
        assert feed_res.status_code == 200
        feed = feed_res.json()
        assert any(note["id"] == imported["note"]["id"] for note in feed)
        assert all(note["id"] != private_note_id for note in feed)

        search_feed_res = await client.get("/api/notes/feed?q=Dijkstra%20graph", headers=bob)
        assert search_feed_res.status_code == 200
        search_feed = search_feed_res.json()
        assert [note["id"] for note in search_feed] == [imported["note"]["id"]]

        private_search_feed_res = await client.get("/api/notes/feed?q=partitioning", headers=bob)
        assert private_search_feed_res.status_code == 200
        assert private_search_feed_res.json() == []

        comment_res = await client.post(
            "/api/comments",
            headers=bob,
            json={"target_type": "note", "target_id": imported["note"]["id"], "content": "Helpful shared note."},
        )
        assert comment_res.status_code == 200
        assert comment_res.json()["author_name"] == "Reader"

        reaction_res = await client.post(
            "/api/reactions",
            headers=bob,
            json={"target_type": "note", "target_id": imported["note"]["id"], "reaction_type": "like"},
        )
        assert reaction_res.status_code == 200

        bob_qa_res = await client.post(
            "/api/notes/ask",
            headers=bob,
            json={"question": "Dijkstra graph edges", "limit": 5},
        )
        assert bob_qa_res.status_code == 200
        assert any(context["source_id"] == imported["note"]["id"] for context in bob_qa_res.json()["contexts"])

        private_comment_res = await client.post(
            "/api/comments",
            headers=bob,
            json={"target_type": "note", "target_id": private_note_id, "content": "Should not work."},
        )
        assert private_comment_res.status_code == 403
