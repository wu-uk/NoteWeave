import type {
  AiStatus,
  AiResult,
  AiTaskType,
  AdminOverview,
  Attachment,
  Comment,
  Course,
  AuditLog,
  KnowledgeNode,
  Mistake,
  Note,
  NoteAskResult,
  NoteImportResult,
  NoteIngestResult,
  NoteVersion,
  SearchResult,
  Suggestion,
  SuggestionStatus,
  TreeResponse,
  User
} from "@/types";

const TOKEN_KEY = "noteweave_token";
const API_BASE_KEY = "noteweave_api_base";

function defaultApiBase(): string {
  const baseUrl = import.meta.env.BASE_URL || "/";
  return baseUrl === "/" ? "" : baseUrl.replace(/\/$/, "");
}

export const apiBase = localStorage.getItem(API_BASE_KEY) || import.meta.env.VITE_NOTEWEAVE_API_BASE || defaultApiBase();

export function resolveApiUrl(path: string): string {
  if (!path) return "";
  if (/^https?:\/\//i.test(path)) return path;
  if (!path.startsWith("/")) return path;
  return `${apiBase}${path}`;
}

export function getToken(): string {
  return localStorage.getItem(TOKEN_KEY) || "";
}

export function setToken(token: string): void {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getToken();

  if (!headers.has("Content-Type") && options.body) {
    headers.set("Content-Type", "application/json");
  }
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${apiBase}${path}`, { ...options, headers });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;

  if (!response.ok) {
    const detail = data?.detail ?? `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }

  return data as T;
}

export const api = {
  baseUrl: apiBase,

  health() {
    return request<{ status: string }>("/health");
  },

  register(payload: { username: string; password: string; display_name?: string }) {
    return request<{ token: string; user: User }>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  login(payload: { username: string; password: string }) {
    return request<{ token: string; user: User }>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  logout() {
    return request<{ status: string }>("/api/auth/logout", {
      method: "POST"
    });
  },

  me() {
    return request<User>("/api/auth/me");
  },

  adminOverview() {
    return request<AdminOverview>("/api/admin/overview");
  },

  aiStatus() {
    return request<AiStatus>("/api/ai/config/status");
  },

  generateNoteAi(noteId: number, type: AiTaskType) {
    return request<AiResult>(`/api/ai/notes/${noteId}/${type}`, {
      method: "POST"
    });
  },

  acceptAiResult(resultId: number, payload: { summary?: string; tags?: string[] }) {
    return request<AiResult>(`/api/ai/results/${resultId}/accept`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  rejectAiResult(resultId: number) {
    return request<AiResult>(`/api/ai/results/${resultId}/reject`, {
      method: "POST"
    });
  },

  listCourses() {
    return request<Course[]>("/api/courses");
  },

  listAuditLogs(courseId: number, limit = 50) {
    const params = new URLSearchParams({ limit: String(limit) });
    return request<AuditLog[]>(`/api/courses/${courseId}/audit-logs?${params.toString()}`);
  },

  getTree(courseId: number) {
    return request<TreeResponse>(`/api/courses/${courseId}/tree`);
  },

  createNode(courseId: number, payload: { parent_id: number | null; type: "chapter" | "knowledge_point"; title: string; description?: string }) {
    return request<KnowledgeNode>(`/api/courses/${courseId}/tree/nodes`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listNotes(courseId: number, nodeId?: number | null) {
    const params = new URLSearchParams({ course_id: String(courseId), limit: "50" });
    if (nodeId) params.set("node_id", String(nodeId));
    return request<Note[]>(`/api/notes?${params.toString()}`);
  },

  listNoteFeed(limit = 100, q = "") {
    const params = new URLSearchParams({ limit: String(limit) });
    if (q.trim()) params.set("q", q.trim());
    return request<Note[]>(`/api/notes/feed?${params.toString()}`);
  },

  createNote(payload: {
    course_id: number;
    node_id: number | null;
    title: string;
    content_text: string;
    visibility: "private" | "shared";
    status: "draft" | "published";
    tags: string[];
  }) {
    return request<Note>("/api/notes", {
      method: "POST",
      body: JSON.stringify({ ...payload, content_format: "markdown", content_json: {} })
    });
  },

  ingestNote(payload: {
    title: string;
    content_text: string;
    visibility: "private" | "shared";
    tags: string[];
  }) {
    return request<NoteIngestResult>("/api/notes/ingest", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  importNoteDocument(payload: {
    file_name: string;
    content_type: string;
    data_base64: string;
    visibility: "private" | "shared";
    tags: string[];
  }) {
    return request<NoteImportResult>("/api/notes/import", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  updateNote(noteId: number, payload: {
    node_id?: number | null;
    title?: string;
    content_text?: string;
    visibility?: "private" | "shared";
    status?: "draft" | "published";
    tags?: string[];
  }) {
    return request<Note>(`/api/notes/${noteId}`, {
      method: "PATCH",
      body: JSON.stringify({ ...payload, content_json: {} })
    });
  },

  deleteNote(noteId: number) {
    return request<{ status: string }>(`/api/notes/${noteId}`, {
      method: "DELETE"
    });
  },

  publishNote(noteId: number) {
    return request<Note>(`/api/notes/${noteId}/publish`, {
      method: "POST"
    });
  },

  askNotes(payload: { question: string; course_id?: number | null; note_ids?: number[]; limit?: number }) {
    return request<NoteAskResult>("/api/notes/ask", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  createAttachment(payload: {
    course_id: number;
    note_id?: number | null;
    mistake_id?: number | null;
    file_name: string;
    content_type: string;
    data_base64: string;
  }) {
    return request<Attachment>("/api/attachments", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listNoteVersions(noteId: number) {
    return request<NoteVersion[]>(`/api/notes/${noteId}/versions`);
  },

  listMistakes(courseId: number, nodeId?: number | null) {
    const params = new URLSearchParams({ course_id: String(courseId), limit: "50" });
    if (nodeId) params.set("node_id", String(nodeId));
    return request<Mistake[]>(`/api/mistakes?${params.toString()}`);
  },

  createMistake(payload: {
    course_id: number;
    node_id: number | null;
    question_content: string;
    correct_answer?: string;
    wrong_answer?: string;
    error_reason?: string;
    solution?: string;
    reflection?: string;
    question_type?: string;
    difficulty?: string;
    mastery_status?: "todo" | "mastered" | "retry";
    tags?: string[];
    visibility?: "private" | "shared";
  }) {
    return request<Mistake>("/api/mistakes", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  updateMistake(mistakeId: number, payload: {
    node_id?: number | null;
    question_content?: string;
    correct_answer?: string;
    wrong_answer?: string;
    error_reason?: string;
    solution?: string;
    reflection?: string;
    question_type?: string;
    difficulty?: string;
    mastery_status?: "todo" | "mastered" | "retry";
    tags?: string[];
    visibility?: "private" | "shared";
  }) {
    return request<Mistake>(`/api/mistakes/${mistakeId}`, {
      method: "PATCH",
      body: JSON.stringify(payload)
    });
  },

  deleteMistake(mistakeId: number) {
    return request<{ status: string }>(`/api/mistakes/${mistakeId}`, {
      method: "DELETE"
    });
  },

  updateMistakeMastery(mistakeId: number, mastery_status: "todo" | "mastered" | "retry") {
    return request<Mistake>(`/api/mistakes/${mistakeId}/mastery`, {
      method: "PATCH",
      body: JSON.stringify({ mastery_status })
    });
  },

  createReaction(payload: { target_type: "note" | "mistake"; target_id: number; reaction_type: "like" | "favorite" }) {
    return request<{ id: number; status: string }>("/api/reactions", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  deleteReaction(reactionId: number) {
    return request<{ status: string }>(`/api/reactions/${reactionId}`, {
      method: "DELETE"
    });
  },

  listComments(targetType: "note" | "mistake", targetId: number, offset = 0, limit = 20) {
    const params = new URLSearchParams({
      target_type: targetType,
      target_id: String(targetId),
      offset: String(offset),
      limit: String(limit)
    });
    return request<Comment[]>(`/api/comments?${params.toString()}`);
  },

  createComment(payload: { target_type: "note" | "mistake"; target_id: number; content: string }) {
    return request<Comment>("/api/comments", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  listSuggestions(courseId: number, status?: SuggestionStatus) {
    const params = new URLSearchParams();
    if (status) params.set("status", status);
    const query = params.toString();
    return request<Suggestion[]>(`/api/courses/${courseId}/suggestions${query ? `?${query}` : ""}`);
  },

  createSuggestion(payload: {
    target_type: "note" | "mistake" | "knowledge_node";
    target_id: number;
    type: "supplement" | "correction";
    content: string;
  }) {
    return request<Suggestion>("/api/suggestions", {
      method: "POST",
      body: JSON.stringify(payload)
    });
  },

  handleSuggestion(suggestionId: number, status: Extract<SuggestionStatus, "accepted" | "rejected" | "discussed">) {
    return request<Suggestion>(`/api/suggestions/${suggestionId}`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
  },

  search(courseId: number, query: string) {
    const params = new URLSearchParams({ course_id: String(courseId), q: query });
    return request<SearchResult[]>(`/api/search?${params.toString()}`);
  }
};

export function splitTags(value: string): string[] {
  return value
    .split(/[,\uff0c]/)
    .map((item) => item.trim())
    .filter(Boolean);
}
