export type ViewMode = "landing" | "workspace";

export type User = {
  id: number;
  username: string;
  display_name: string;
  role?: string;
  system_role?: string;
};

export type Course = {
  id: number;
  name: string;
  description: string;
  semester: string;
  invite_code?: string;
  is_public?: boolean;
  tags: string[];
  role?: string;
  member_count?: number;
  node_count?: number;
  note_count?: number;
  mistake_count?: number;
};

export type CourseRole = "student" | "maintainer" | "teacher";

export type CourseMember = {
  id: number;
  username: string;
  display_name: string;
  role: CourseRole;
  joined_at: string;
};

export type AuditLog = {
  id: number;
  course_id: number;
  actor_id: number;
  action: string;
  target_type: string;
  target_id: number;
  metadata: Record<string, unknown>;
  created_at: string;
};

export type KnowledgeNodeType = "course_root" | "chapter" | "knowledge_point";

export type KnowledgeNode = {
  id: number;
  course_id: number;
  parent_id: number | null;
  type: KnowledgeNodeType;
  title: string;
  description: string;
  path: string;
  depth: number;
  order_index: number;
  note_count?: number;
  mistake_count?: number;
  comment_count?: number;
  tags?: string[];
  children: KnowledgeNode[];
};

export type TreeResponse = {
  course_id: number;
  root: KnowledgeNode | null;
};

export type Note = {
  id: number;
  course_id: number;
  node_id: number | null;
  node_path?: string | null;
  title: string;
  content_text: string;
  summary?: string;
  visibility: "private" | "shared";
  status: "draft" | "published";
  tags: string[];
  author_id: number;
  author_name?: string;
  like_count?: number;
  comment_count?: number;
  is_liked?: boolean;
  like_reaction_id?: number | null;
  is_favorite?: boolean;
  favorite_reaction_id?: number | null;
  updated_at: string;
};

export type NoteVersion = {
  id: number;
  note_id: number;
  title: string;
  content_json: Record<string, unknown>;
  content_text: string;
  changed_by: number;
  change_reason: string;
  created_at: string;
};

export type Mistake = {
  id: number;
  course_id: number;
  node_id: number | null;
  node_path?: string | null;
  question_content: string;
  correct_answer: string;
  wrong_answer: string;
  error_reason: string;
  solution: string;
  reflection: string;
  question_type: string;
  difficulty: string;
  mastery_status: "todo" | "mastered" | "retry";
  tags: string[];
  visibility: "private" | "shared";
  author_id: number;
  is_favorite?: boolean;
  favorite_reaction_id?: number | null;
  updated_at: string;
};

export type Comment = {
  id: number;
  target_type: "note" | "mistake" | "suggestion";
  target_id: number;
  content: string;
  author_id: number;
  author_name?: string;
  created_at: string;
};

export type SuggestionStatus = "pending" | "accepted" | "rejected" | "discussed";

export type Suggestion = {
  id: number;
  target_type: "note" | "mistake" | "knowledge_node";
  target_id: number;
  target_title?: string;
  type: "supplement" | "correction";
  content: string;
  status: SuggestionStatus;
  submitter_id: number;
  handler_id?: number | null;
  handled_at?: string | null;
  created_at: string;
};

export type SearchResult = {
  source_type: "note" | "mistake";
  source_id: number;
  title: string;
  snippet: string;
  node_path?: string;
  matched_fields: string[];
  score: number;
};

export type AiStatus = {
  enabled: boolean;
  remote_configured: boolean;
  chat_model?: string;
  base_url_configured: boolean;
  api_key_configured: boolean;
  fallback_available: boolean;
};

export type AiTaskType = "summary" | "tags";

export type AiResult = {
  id: number;
  target_type: "note";
  target_id: number;
  task_type: AiTaskType;
  status: "generated" | "accepted" | "rejected";
  result: {
    summary?: string;
    tags?: string[];
    source?: "remote" | "fallback" | string;
  };
  error?: string;
  created_by: number;
  accepted_by?: number | null;
  accepted_at?: string | null;
  created_at: string;
};

export type NoteIngestResult = {
  note: Note;
  course: Course;
  node: KnowledgeNode;
  classification: {
    course_name: string;
    node_title: string;
    summary: string;
    tags: string[];
    source?: string;
  };
};

export type NoteAskContext = {
  source_type: "note";
  source_id: number;
  title: string;
  content: string;
  summary?: string;
  snippet: string;
  node_path?: string | null;
  score: number;
  updated_at: string;
};

export type NoteAskResult = {
  answer: string;
  source: string;
  contexts: NoteAskContext[];
};
