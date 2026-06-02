from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    username: str = Field(min_length=2, max_length=64)
    password: str = Field(min_length=6, max_length=128)
    display_name: str | None = Field(default=None, max_length=80)


class LoginRequest(BaseModel):
    username: str
    password: str


class UserUpdateRequest(BaseModel):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    current_password: str | None = None
    new_password: str | None = Field(default=None, min_length=6, max_length=128)


class CourseCreateRequest(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    semester: str = ""
    tags: list[str] = []


class CourseUpdateRequest(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    semester: str | None = None
    tags: list[str] | None = None


class CourseJoinRequest(BaseModel):
    invite_code: str


class MemberRoleRequest(BaseModel):
    role: Literal["student", "maintainer", "teacher"]


class KnowledgeNodeCreateRequest(BaseModel):
    parent_id: int | None = None
    type: Literal["chapter", "knowledge_point"] = "knowledge_point"
    title: str = Field(min_length=1, max_length=160)
    description: str = ""
    order_index: int = 0
    metadata: dict[str, Any] = {}


class KnowledgeNodeUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=160)
    description: str | None = None
    order_index: int | None = None
    metadata: dict[str, Any] | None = None


class KnowledgeNodeMoveRequest(BaseModel):
    parent_id: int | None = None
    order_index: int = 0


class NoteCreateRequest(BaseModel):
    course_id: int
    node_id: int | None = None
    title: str = Field(min_length=1, max_length=180)
    content_json: dict[str, Any] = {}
    content_text: str = ""
    content_format: str = "markdown"
    visibility: Literal["private", "shared"] = "private"
    status: Literal["draft", "published"] = "draft"
    tags: list[str] = []


class NoteIngestRequest(BaseModel):
    title: str = Field(min_length=1, max_length=180)
    content_text: str = Field(min_length=1)
    visibility: Literal["private", "shared"] = "private"
    tags: list[str] = []


class NoteAskRequest(BaseModel):
    question: str = Field(min_length=1, max_length=500)
    course_id: int | None = None
    limit: int = Field(default=6, ge=1, le=12)


class NoteUpdateRequest(BaseModel):
    node_id: int | None = None
    title: str | None = Field(default=None, min_length=1, max_length=180)
    content_json: dict[str, Any] | None = None
    content_text: str | None = None
    visibility: Literal["private", "shared"] | None = None
    status: Literal["draft", "published"] | None = None
    tags: list[str] | None = None


class MistakeCreateRequest(BaseModel):
    course_id: int
    node_id: int | None = None
    question_content: str = Field(min_length=1)
    correct_answer: str = ""
    wrong_answer: str = ""
    error_reason: str = ""
    solution: str = ""
    reflection: str = ""
    question_type: str = ""
    difficulty: str = ""
    mastery_status: Literal["todo", "mastered", "retry"] = "todo"
    tags: list[str] = []
    visibility: Literal["private", "shared"] = "private"


class MistakeUpdateRequest(BaseModel):
    node_id: int | None = None
    question_content: str | None = None
    correct_answer: str | None = None
    wrong_answer: str | None = None
    error_reason: str | None = None
    solution: str | None = None
    reflection: str | None = None
    question_type: str | None = None
    difficulty: str | None = None
    mastery_status: Literal["todo", "mastered", "retry"] | None = None
    tags: list[str] | None = None
    visibility: Literal["private", "shared"] | None = None


class AttachmentCreateRequest(BaseModel):
    course_id: int
    note_id: int | None = None
    mistake_id: int | None = None
    file_name: str = Field(min_length=1, max_length=180)
    content_type: str = Field(min_length=1, max_length=120)
    data_base64: str = Field(min_length=1)


class MasteryRequest(BaseModel):
    mastery_status: Literal["todo", "mastered", "retry"]


class CommentCreateRequest(BaseModel):
    target_type: Literal["note", "mistake", "suggestion"]
    target_id: int
    content: str = Field(min_length=1)


class ReactionCreateRequest(BaseModel):
    target_type: Literal["note", "mistake"]
    target_id: int
    reaction_type: Literal["like", "favorite"]


class ViewCreateRequest(BaseModel):
    target_type: Literal["note", "mistake"]
    target_id: int


class SuggestionCreateRequest(BaseModel):
    target_type: Literal["note", "mistake", "knowledge_node"]
    target_id: int
    type: Literal["supplement", "correction"]
    content: str = Field(min_length=1)


class SuggestionHandleRequest(BaseModel):
    status: Literal["accepted", "rejected", "discussed"]


class AIResultAcceptRequest(BaseModel):
    summary: str | None = None
    tags: list[str] | None = None
