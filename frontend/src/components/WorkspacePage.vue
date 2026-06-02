<template>
  <main class="app-shell">
    <aside class="rail">
      <button class="brand-button" type="button" @click="$emit('home')">
        <span class="brand-mark">N</span>
        <span>
          <strong>NoteWeave</strong>
          <small>note first workspace</small>
        </span>
      </button>

      <section class="quiet-panel">
        <div class="panel-kicker">
          <UserRound :size="15" />
          <span>账号</span>
        </div>
        <div v-if="user" class="account-card">
          <strong>{{ user.display_name || user.username }}</strong>
          <small>@{{ user.username }} · {{ user.system_role === "admin" ? "管理员" : "普通用户" }}</small>
          <button type="button" class="ghost-button" @click="logout">退出</button>
        </div>
        <form v-else class="form-stack" @submit.prevent="login">
          <input v-model.trim="auth.username" placeholder="用户名" autocomplete="username" />
          <input v-model="auth.password" placeholder="密码" type="password" autocomplete="current-password" />
          <input v-model.trim="auth.displayName" placeholder="昵称（注册时可填）" />
          <div class="split-actions">
            <button type="submit" class="primary-button">登录</button>
            <button type="button" class="ghost-button" @click="register">注册</button>
          </div>
        </form>
      </section>

      <section class="quiet-panel">
        <div class="panel-kicker">
          <FolderKanban :size="15" />
          <span>AI 分类</span>
          <button type="button" class="icon-button" title="刷新" @click="loadWorkspace">
            <RefreshCcw :size="14" />
          </button>
        </div>
        <button type="button" class="folder-row" :class="{ active: selectedCourseId === null }" @click="selectCourse(null)">
          <span>全部笔记</span>
          <small>{{ notes.length }} 条</small>
        </button>
        <button
          v-for="course in courses"
          :key="course.id"
          type="button"
          class="folder-row"
          :class="{ active: selectedCourseId === course.id }"
          @click="selectCourse(course.id)"
        >
          <span>{{ course.name }}</span>
          <small>{{ course.note_count || 0 }} 条 · AI</small>
        </button>
        <p v-if="user && !courses.length" class="empty-text">保存第一条笔记后，AI 会自动生成分类。</p>
      </section>
    </aside>

    <section class="note-stage">
      <header class="top-strip">
        <div>
          <small>笔记中心</small>
          <h1>先记录，再由 AI 归档</h1>
        </div>
        <div class="status-cluster">
          <span :class="['status-pill', backendReady ? 'ok' : 'warn']">
            <Activity :size="14" />
            {{ backendReady ? "API 在线" : "API 未连接" }}
          </span>
          <span class="status-pill">
            <Sparkles :size="14" />
            {{ aiStatus?.remote_configured ? `模型 ${aiStatus.chat_model}` : "Fallback AI" }}
          </span>
        </div>
      </header>

      <section class="composer">
        <div class="composer-head">
          <div>
            <span>Capture</span>
            <h2>{{ draft.editingId ? "编辑笔记" : "添加笔记" }}</h2>
          </div>
          <select v-model="draft.visibility" aria-label="可见性">
            <option value="private">个人</option>
            <option value="shared">共享</option>
          </select>
        </div>
        <form class="composer-form" @submit.prevent="saveNote">
          <input v-model.trim="draft.title" placeholder="标题，例如：Dijkstra 的适用条件" />
          <textarea v-model="draft.content" placeholder="写课堂记录、摘录、错题思路、代码片段。AI 会判断课程和知识点。" />
          <div class="composer-actions">
            <input v-model.trim="draft.tags" placeholder="可选标签，用逗号分隔" />
            <button v-if="draft.editingId" type="button" class="ghost-button" @click="resetDraft">取消编辑</button>
            <button type="submit" class="primary-button">
              <UploadCloud :size="15" />
              {{ draft.editingId ? "更新" : "保存并解析" }}
            </button>
          </div>
        </form>
      </section>

      <section class="feed-header">
        <div>
          <small>{{ selectedCourseName }}</small>
          <h2>笔记流</h2>
        </div>
        <div class="search-box">
          <Search :size="15" />
          <input v-model.trim="keyword" placeholder="筛选当前笔记" />
        </div>
      </section>

      <section class="note-feed">
        <article v-for="note in filteredNotes" :key="note.id" class="note-card" :class="{ selected: activeNote?.id === note.id }" @click="setActiveNote(note)">
          <div class="note-card-top">
            <div>
              <strong>{{ note.title }}</strong>
              <small>{{ note.node_path || "AI 分类中" }} · {{ visibilityLabel(note.visibility) }} · {{ note.updated_at?.slice(0, 10) }}</small>
            </div>
            <button type="button" class="icon-button" title="编辑" @click.stop="editNote(note)">
              <Pencil :size="14" />
            </button>
          </div>
          <p class="summary-text">{{ note.summary || note.content_text }}</p>
          <div class="tag-row">
            <span v-for="tag in note.tags" :key="tag">{{ tag }}</span>
          </div>
          <div class="action-row">
            <button v-if="note.visibility !== 'shared'" type="button" class="ghost-button" @click.stop="publishNote(note)">
              <Share2 :size="14" />
              共享
            </button>
            <button type="button" class="ghost-button" :class="{ selected: note.is_liked }" @click.stop="toggleLike(note)">
              <ThumbsUp :size="14" />
              {{ note.like_count || 0 }}
            </button>
            <button type="button" class="ghost-button" @click.stop="openDiscussion(note)">
              <MessageSquare :size="14" />
              {{ note.comment_count || 0 }}
            </button>
            <button type="button" class="ghost-button" @click.stop="generateAi(note, 'summary')">
              <Sparkles :size="14" />
              摘要
            </button>
            <button type="button" class="ghost-button" @click.stop="generateAi(note, 'tags')">
              <Tags :size="14" />
              标签
            </button>
            <button type="button" class="ghost-button danger-soft" @click.stop="deleteNote(note)">
              <Trash2 :size="14" />
              删除
            </button>
          </div>
        </article>
        <p v-if="user && !filteredNotes.length" class="empty-text large-empty">还没有符合条件的笔记。</p>
        <p v-if="!user" class="empty-text large-empty">登录后即可添加和共享笔记。</p>
      </section>
    </section>

    <aside class="inspector">
      <section class="quiet-panel analysis-panel">
        <div class="panel-kicker">
          <Sparkles :size="15" />
          <span>解析</span>
        </div>
        <div v-if="lastClassification" class="analysis-card">
          <small>上次归档</small>
          <strong>{{ lastClassification.course_name }} / {{ lastClassification.node_title }}</strong>
          <p>{{ lastClassification.summary }}</p>
          <div class="tag-row">
            <span v-for="tag in lastClassification.tags" :key="tag">{{ tag }}</span>
          </div>
        </div>
        <div v-else class="analysis-card muted-card">
          <small>MoDora-inspired</small>
          <strong>解析 -> 归类 -> 检索 -> 问答</strong>
          <p>这里使用轻量文本摄取和 API 模型，不引入 OCR、本地模型或 GPU 依赖。</p>
        </div>
      </section>

      <section class="quiet-panel qa-panel">
        <div class="panel-kicker">
          <Bot :size="15" />
          <span>笔记问答</span>
        </div>
        <form class="qa-form" @submit.prevent="askNotes">
          <textarea v-model.trim="question" placeholder="问一个和笔记有关的问题" />
          <button type="submit" class="primary-button">
            <Send :size="14" />
            提问
          </button>
        </form>
        <div v-if="answer.answer" class="answer-card">
          <small>{{ answer.source === "remote" ? "模型回答" : "本地 fallback" }}</small>
          <p>{{ answer.answer }}</p>
        </div>
        <div class="context-list">
          <article v-for="context in answer.contexts" :key="context.source_id">
            <strong>{{ context.title }}</strong>
            <small>{{ context.node_path || "未归档" }} · score {{ context.score }}</small>
            <p>{{ context.snippet }}</p>
          </article>
        </div>
      </section>

      <section v-if="activeNote" class="quiet-panel detail-panel">
        <div class="panel-kicker">
          <PanelRight :size="15" />
          <span>当前笔记</span>
        </div>
        <strong>{{ activeNote.title }}</strong>
        <small>{{ activeNote.node_path || "未归档" }}</small>
        <p>{{ activeNote.content_text }}</p>
      </section>
    </aside>

    <aside v-if="discussion.open" class="overlay" @click.self="closeDiscussion">
      <section class="modal-panel">
        <header class="modal-head">
          <div>
            <small>评论</small>
            <h2>{{ discussion.title }}</h2>
          </div>
          <button type="button" class="icon-button" title="关闭" @click="closeDiscussion">
            <X :size="16" />
          </button>
        </header>
        <div class="comment-list">
          <article v-for="comment in discussion.items" :key="comment.id" class="comment-item">
            <strong>{{ comment.author_name || `用户 #${comment.author_id}` }}</strong>
            <small>{{ comment.created_at?.slice(0, 19).replace("T", " ") }}</small>
            <p>{{ comment.content }}</p>
          </article>
          <p v-if="!discussion.items.length" class="empty-text">还没有评论。</p>
        </div>
        <form class="modal-form" @submit.prevent="submitDiscussion">
          <textarea v-model.trim="discussionDraft" placeholder="写评论、补充或纠错线索" />
          <button type="submit" class="primary-button">发布评论</button>
        </form>
      </section>
    </aside>

    <aside v-if="aiReview.open" class="overlay" @click.self="closeAiReview">
      <section class="modal-panel">
        <header class="modal-head">
          <div>
            <small>AI 结果</small>
            <h2>{{ aiReview.title }}</h2>
          </div>
          <button type="button" class="icon-button" title="关闭" @click="closeAiReview">
            <X :size="16" />
          </button>
        </header>
        <form class="modal-form" @submit.prevent="acceptAiReview">
          <p class="empty-text">来源：{{ aiReview.source || "fallback" }}。采纳前可以编辑。</p>
          <textarea v-if="aiReview.taskType === 'summary'" v-model.trim="aiReview.summary" />
          <textarea v-else v-model.trim="aiReview.tagsText" />
          <div class="split-actions">
            <button type="submit" class="primary-button">
              <Check :size="14" />
              采纳
            </button>
            <button type="button" class="ghost-button danger-soft" @click="rejectAiReview">
              <X :size="14" />
              放弃
            </button>
          </div>
        </form>
      </section>
    </aside>

    <aside v-if="confirmDialog.open" class="overlay" @click.self="closeConfirm">
      <section class="confirm-panel">
        <strong>{{ confirmDialog.title }}</strong>
        <p>{{ confirmDialog.message }}</p>
        <div class="split-actions">
          <button type="button" class="primary-button danger-button" @click="runConfirm">确认删除</button>
          <button type="button" class="ghost-button" @click="closeConfirm">取消</button>
        </div>
      </section>
    </aside>

    <div v-if="toast" class="toast">{{ toast }}</div>
  </main>
</template>

<script setup lang="ts">
import {
  Activity,
  Bot,
  Check,
  FolderKanban,
  MessageSquare,
  PanelRight,
  Pencil,
  RefreshCcw,
  Search,
  Send,
  Share2,
  Sparkles,
  Tags,
  ThumbsUp,
  Trash2,
  UploadCloud,
  UserRound,
  X
} from "@lucide/vue";
import { computed, onMounted, reactive, ref } from "vue";

import { api, setToken, splitTags } from "@/services/api";
import type { AiResult, AiStatus, AiTaskType, Comment, Course, Note, NoteAskContext, User } from "@/types";

defineEmits<{ home: [] }>();

const backendReady = ref(false);
const user = ref<User | null>(null);
const courses = ref<Course[]>([]);
const notes = ref<Note[]>([]);
const activeNote = ref<Note | null>(null);
const selectedCourseId = ref<number | null>(null);
const aiStatus = ref<AiStatus | null>(null);
const keyword = ref("");
const question = ref("");
const toast = ref("");
const lastClassification = ref<{
  course_name: string;
  node_title: string;
  summary: string;
  tags: string[];
  source?: string;
} | null>(null);

const auth = reactive({ username: "", password: "", displayName: "" });
const draft = reactive({
  editingId: null as number | null,
  sourceNote: null as Note | null,
  title: "",
  content: "",
  tags: "",
  visibility: "private" as "private" | "shared"
});
const answer = reactive<{ answer: string; source: string; contexts: NoteAskContext[] }>({
  answer: "",
  source: "",
  contexts: []
});
const discussionDraft = ref("");
const discussion = reactive<{
  open: boolean;
  noteId: number | null;
  title: string;
  items: Comment[];
}>({ open: false, noteId: null, title: "", items: [] });
const aiReview = reactive<{
  open: boolean;
  resultId: number | null;
  taskType: AiTaskType | null;
  title: string;
  summary: string;
  tagsText: string;
  source: string;
}>({ open: false, resultId: null, taskType: null, title: "", summary: "", tagsText: "", source: "" });
const confirmDialog = reactive<{
  open: boolean;
  title: string;
  message: string;
  action: null | (() => Promise<void>);
}>({ open: false, title: "", message: "", action: null });

const selectedCourseName = computed(() => {
  if (selectedCourseId.value === null) return "全部 AI 分类";
  return courses.value.find((course) => course.id === selectedCourseId.value)?.name || "AI 分类";
});

const filteredNotes = computed(() => {
  const term = keyword.value.trim().toLowerCase();
  return notes.value.filter((note) => {
    if (selectedCourseId.value !== null && note.course_id !== selectedCourseId.value) return false;
    if (!term) return true;
    return [note.title, note.content_text, note.summary, note.node_path, ...(note.tags || [])]
      .join(" ")
      .toLowerCase()
      .includes(term);
  });
});

function notify(message: string): void {
  toast.value = message;
  window.setTimeout(() => {
    toast.value = "";
  }, 2400);
}

async function guarded(action: () => Promise<void>): Promise<void> {
  try {
    await action();
  } catch (error) {
    notify(error instanceof Error ? error.message : "操作失败");
  }
}

async function login(): Promise<void> {
  await guarded(async () => {
    const result = await api.login({ username: auth.username, password: auth.password });
    setToken(result.token);
    user.value = result.user;
    await loadWorkspace();
  });
}

async function register(): Promise<void> {
  await guarded(async () => {
    const result = await api.register({
      username: auth.username,
      password: auth.password,
      display_name: auth.displayName || undefined
    });
    setToken(result.token);
    user.value = result.user;
    await loadWorkspace();
  });
}

function logout(): void {
  setToken("");
  user.value = null;
  courses.value = [];
  notes.value = [];
  activeNote.value = null;
  selectedCourseId.value = null;
}

async function loadWorkspace(): Promise<void> {
  if (!user.value) return;
  await Promise.all([loadAiStatus(), loadCoursesAndNotes()]);
}

async function loadAiStatus(): Promise<void> {
  if (!user.value) return;
  aiStatus.value = await api.aiStatus();
}

async function loadCoursesAndNotes(): Promise<void> {
  if (!user.value) return;
  courses.value = await api.listCourses();
  const groups = await Promise.all(courses.value.map((course) => api.listNotes(course.id)));
  notes.value = groups.flat().sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
  if (activeNote.value) {
    activeNote.value = notes.value.find((note) => note.id === activeNote.value?.id) || notes.value[0] || null;
  } else {
    activeNote.value = notes.value[0] || null;
  }
}

function selectCourse(courseId: number | null): void {
  selectedCourseId.value = courseId;
}

async function saveNote(): Promise<void> {
  await guarded(async () => {
    if (!user.value) throw new Error("请先登录");
    if (!draft.title) throw new Error("请填写标题");
    if (!draft.content.trim()) throw new Error("请填写笔记内容");
    if (draft.editingId && draft.sourceNote) {
      const note = await api.updateNote(draft.editingId, {
        node_id: draft.sourceNote.node_id,
        title: draft.title,
        content_text: draft.content,
        visibility: draft.visibility,
        status: draft.visibility === "shared" ? "published" : "draft",
        tags: splitTags(draft.tags)
      });
      activeNote.value = note;
      notify("笔记已更新");
    } else {
      const result = await api.ingestNote({
        title: draft.title,
        content_text: draft.content,
        visibility: draft.visibility,
        tags: splitTags(draft.tags)
      });
      lastClassification.value = result.classification;
      selectedCourseId.value = result.course.id;
      activeNote.value = result.note;
      notify("笔记已保存并完成 AI 归类");
    }
    resetDraft();
    await loadCoursesAndNotes();
  });
}

function resetDraft(): void {
  draft.editingId = null;
  draft.sourceNote = null;
  draft.title = "";
  draft.content = "";
  draft.tags = "";
  draft.visibility = "private";
}

function editNote(note: Note): void {
  draft.editingId = note.id;
  draft.sourceNote = note;
  draft.title = note.title;
  draft.content = note.content_text || "";
  draft.tags = (note.tags || []).join(", ");
  draft.visibility = note.visibility;
  activeNote.value = note;
}

function setActiveNote(note: Note): void {
  activeNote.value = note;
}

async function publishNote(note: Note): Promise<void> {
  await guarded(async () => {
    activeNote.value = await api.publishNote(note.id);
    await loadCoursesAndNotes();
    notify("笔记已共享");
  });
}

async function toggleLike(note: Note): Promise<void> {
  await guarded(async () => {
    if (note.like_reaction_id) {
      await api.deleteReaction(note.like_reaction_id);
    } else {
      await api.createReaction({ target_type: "note", target_id: note.id, reaction_type: "like" });
    }
    await loadCoursesAndNotes();
  });
}

async function deleteNote(note: Note): Promise<void> {
  confirmDialog.open = true;
  confirmDialog.title = "删除笔记";
  confirmDialog.message = `确定删除「${note.title}」吗？`;
  confirmDialog.action = async () => {
    await api.deleteNote(note.id);
    if (activeNote.value?.id === note.id) activeNote.value = null;
    await loadCoursesAndNotes();
    notify("笔记已删除");
  };
}

async function generateAi(note: Note, taskType: AiTaskType): Promise<void> {
  await guarded(async () => {
    const result = await api.generateNoteAi(note.id, taskType);
    openAiReview(result, note.title);
  });
}

function openAiReview(result: AiResult, title: string): void {
  aiReview.open = true;
  aiReview.resultId = result.id;
  aiReview.taskType = result.task_type;
  aiReview.title = title;
  aiReview.summary = result.result.summary || "";
  aiReview.tagsText = (result.result.tags || []).join(", ");
  aiReview.source = result.result.source || "fallback";
}

function closeAiReview(): void {
  aiReview.open = false;
  aiReview.resultId = null;
}

async function acceptAiReview(): Promise<void> {
  await guarded(async () => {
    if (!aiReview.resultId || !aiReview.taskType) return;
    await api.acceptAiResult(
      aiReview.resultId,
      aiReview.taskType === "summary"
        ? { summary: aiReview.summary }
        : { tags: splitTags(aiReview.tagsText) }
    );
    closeAiReview();
    await loadCoursesAndNotes();
    notify("AI 结果已采纳");
  });
}

async function rejectAiReview(): Promise<void> {
  await guarded(async () => {
    if (aiReview.resultId) await api.rejectAiResult(aiReview.resultId);
    closeAiReview();
  });
}

async function askNotes(): Promise<void> {
  await guarded(async () => {
    if (!question.value.trim()) throw new Error("请先输入问题");
    const result = await api.askNotes({
      question: question.value,
      course_id: selectedCourseId.value,
      limit: 6
    });
    answer.answer = result.answer;
    answer.source = result.source;
    answer.contexts = result.contexts;
  });
}

async function openDiscussion(note: Note): Promise<void> {
  await guarded(async () => {
    discussion.open = true;
    discussion.noteId = note.id;
    discussion.title = note.title;
    discussion.items = await api.listComments("note", note.id);
  });
}

function closeDiscussion(): void {
  discussion.open = false;
  discussion.noteId = null;
  discussionDraft.value = "";
}

async function submitDiscussion(): Promise<void> {
  await guarded(async () => {
    if (!discussion.noteId || !discussionDraft.value) return;
    await api.createComment({ target_type: "note", target_id: discussion.noteId, content: discussionDraft.value });
    discussionDraft.value = "";
    discussion.items = await api.listComments("note", discussion.noteId);
    await loadCoursesAndNotes();
  });
}

function closeConfirm(): void {
  confirmDialog.open = false;
  confirmDialog.action = null;
}

async function runConfirm(): Promise<void> {
  await guarded(async () => {
    if (confirmDialog.action) await confirmDialog.action();
    closeConfirm();
  });
}

function visibilityLabel(value: Note["visibility"]): string {
  return value === "shared" ? "共享" : "个人";
}

onMounted(async () => {
  await guarded(async () => {
    backendReady.value = (await api.health()).status === "ok";
    const me = await api.me().catch(() => null);
    if (me) {
      user.value = me;
      await loadWorkspace();
    }
  });
});
</script>
