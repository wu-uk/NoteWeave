from __future__ import annotations

import base64

import pytest
from httpx import ASGITransport, AsyncClient

from noteweave.api.app import create_app
from noteweave.core.settings import Settings


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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
        alice = auth_headers(alice_token)

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
        accept_summary_res = await client.post(
            f"/api/ai/results/{summary_id}/accept", headers=alice
        )
        assert accept_summary_res.status_code == 200
        assert accept_summary_res.json()["status"] == "accepted"

        tags_res = await client.post(f"/api/ai/notes/{note_id}/tags", headers=alice)
        assert tags_res.status_code == 200
        assert tags_res.json()["result"]["source"] == "fallback"
        accept_tags_res = await client.post(
            f"/api/ai/results/{tags_res.json()['id']}/accept", headers=alice
        )
        assert accept_tags_res.status_code == 200

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
        assert all(item["author_name"] == "Alice" for item in search_results)

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
        delete_temp_note_res = await client.delete(f"/api/notes/{temp_note_id}", headers=alice)
        assert delete_temp_note_res.status_code == 200
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
        mistakes_after_delete_res = await client.get(
            "/api/mistakes",
            headers=alice,
            params={"course_id": course["id"]},
        )
        assert temp_mistake_id not in {item["id"] for item in mistakes_after_delete_res.json()}

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
