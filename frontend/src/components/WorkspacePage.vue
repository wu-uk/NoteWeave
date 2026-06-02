<template>
  <main v-if="!user" class="auth-shell">
    <section class="auth-card">
      <button class="brand-button" type="button" @click="$emit('home')">
        <span class="brand-mark">N</span>
        <span>
          <strong>NoteWeave</strong>
          <small>back to landing</small>
        </span>
      </button>
      <div class="auth-copy">
        <small>登录后进入工作台</small>
        <h1>开始记录、上传和询问你的笔记</h1>
        <p>未登录用户只能查看 landing。登录或注册后，才能使用笔记流、文件导入、共享互动和问答功能。</p>
      </div>
      <form class="form-stack" @submit.prevent="login">
        <input v-model.trim="auth.username" placeholder="用户名" autocomplete="username" />
        <input v-model="auth.password" placeholder="密码" type="password" autocomplete="current-password" />
        <input v-model.trim="auth.displayName" placeholder="昵称（注册时可填）" />
        <div class="split-actions">
          <button type="submit" class="primary-button">登录</button>
          <button type="button" class="ghost-button" @click="register">注册</button>
        </div>
      </form>
      <div class="auth-status">
        <span :class="['status-pill', backendReady ? 'ok' : 'warn']">
          <Activity :size="14" />
          {{ backendReady ? "API 在线" : "API 未连接" }}
        </span>
        <span class="status-pill">
          <Sparkles :size="14" />
          {{ aiStatus?.remote_configured ? `模型 ${aiStatus.chat_model}` : "Fallback AI" }}
        </span>
      </div>
    </section>
  </main>

  <main v-else class="app-shell knowledge-app">
    <aside class="workspace-nav">
      <button class="brand-button nav-brand" type="button" @click="showNetwork">
        <span class="brand-mark">N</span>
        <span>
          <strong>NoteWeave</strong>
          <small>knowledge graph</small>
        </span>
      </button>

      <section class="nav-account">
        <div>
          <strong>{{ user.display_name || user.username }}</strong>
          <small>@{{ user.username }} · {{ user.system_role === "admin" ? "管理员" : "普通用户" }}</small>
        </div>
        <button type="button" class="icon-button" title="退出" @click="logout">
          <LogOut :size="15" />
        </button>
      </section>

      <nav class="primary-nav" aria-label="工作台导航">
        <button type="button" :class="{ active: activeView === 'personal' }" @click="activeView = 'personal'">
          <BookOpen :size="17" />
          <span>个人笔记</span>
        </button>
        <button type="button" :class="{ active: activeView === 'shared' }" @click="activeView = 'shared'">
          <Users :size="17" />
          <span>共享笔记</span>
        </button>
        <button type="button" :class="{ active: activeView === 'mistakes' }" @click="activeView = 'mistakes'">
          <ClipboardList :size="17" />
          <span>错题整理</span>
        </button>
        <button type="button" :class="{ active: activeView === 'daily' }" @click="activeView = 'daily'">
          <CalendarDays :size="17" />
          <span>每日一题</span>
        </button>
      </nav>

      <section v-if="user?.system_role === 'admin'" class="nav-admin">
        <div class="panel-kicker">
          <ShieldCheck :size="15" />
          <span>管理员</span>
          <button type="button" class="icon-button" title="刷新管理概览" @click="loadAdminOverview">
            <RefreshCcw :size="14" />
          </button>
        </div>
        <div v-if="adminOverview" class="admin-grid">
          <div>
            <small>用户</small>
            <strong>{{ adminOverview.stats.user_count }}</strong>
          </div>
          <div>
            <small>共享</small>
            <strong>{{ adminOverview.stats.shared_note_count }}</strong>
          </div>
          <div>
            <small>导入</small>
            <strong>{{ adminOverview.stats.attachment_count }}</strong>
          </div>
          <div>
            <small>AI</small>
            <strong>{{ adminOverview.stats.ai_result_count }}</strong>
          </div>
        </div>
      </section>

      <section class="nav-status">
        <span :class="['status-pill', backendReady ? 'ok' : 'warn']">
          <Activity :size="14" />
          {{ backendReady ? "API 在线" : "API 未连接" }}
        </span>
        <span class="status-pill">
          <Sparkles :size="14" />
          {{ aiStatus?.remote_configured ? aiStatus.chat_model : "Fallback AI" }}
        </span>
      </section>
    </aside>

    <section class="workspace-surface">
      <header class="workspace-top">
        <div>
          <small>{{ viewKicker }}</small>
          <h1>{{ viewTitle }}</h1>
        </div>
        <div class="top-actions">
          <button type="button" class="ghost-button" @click="showNetwork">
            <Network :size="15" />
            知识网络
          </button>
          <button type="button" class="ghost-button" :disabled="importingDocument" @click="triggerDocumentImport">
            <FileUp :size="15" />
            {{ importingDocument ? "解析中" : "上传" }}
          </button>
          <button type="button" class="primary-button" @click="startNewNote">
            <Plus :size="15" />
            新建
          </button>
          <input
            ref="documentInput"
            class="visually-hidden"
            type="file"
            accept=".pdf,.docx,.md,.markdown,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain"
            @change="importDocument"
          />
        </div>
      </header>

      <section v-if="activeView === 'network'" class="knowledge-view">
        <div class="graph-panel">
          <svg class="graph-lines" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true">
            <line
              v-for="link in networkLinks"
              :key="link.id"
              :x1="link.from.x"
              :y1="link.from.y"
              :x2="link.to.x"
              :y2="link.to.y"
            />
          </svg>
          <button
            v-for="node in networkNodes"
            :key="node.id"
            type="button"
            class="graph-node"
            :class="[node.kind, { active: selectedGraphNodeId === node.id }]"
            :style="{ left: `${node.x}%`, top: `${node.y}%` }"
            @click="selectGraphNode(node)"
          >
            <span>{{ node.short }}</span>
            <strong>{{ node.label }}</strong>
            <small>{{ node.meta }}</small>
          </button>
          <div v-if="!networkNodes.length" class="network-empty">
            <Sparkles :size="18" />
            <strong>还没有知识网络</strong>
            <span>保存或上传第一条笔记后，AI 会自动归档并生成节点。</span>
          </div>
        </div>

        <aside class="graph-inspector">
          <section class="compact-panel">
            <div class="panel-kicker">
              <Sparkles :size="15" />
              <span>最近解析</span>
            </div>
            <div v-if="lastClassification" class="analysis-card">
              <small>{{ lastClassification.course_name }} / {{ lastClassification.node_title }}</small>
              <strong>{{ lastClassification.summary }}</strong>
              <div class="tag-row">
                <span v-for="tag in lastClassification.tags" :key="tag">{{ tag }}</span>
              </div>
              <div v-if="lastImport" class="document-meta">
                <small>{{ lastImport.file_name }}</small>
                <span>{{ lastImport.parser }} · {{ lastImport.characters }} 字符</span>
              </div>
            </div>
            <div v-else class="analysis-card muted-card">
              <small>MoDora-inspired</small>
              <strong>解析 -> 归类 -> 检索 -> 问答</strong>
              <p>上传 PDF、Word 或 Markdown 后，后端会用远程 API 模型做轻量解析。</p>
            </div>
          </section>

          <section class="compact-panel qa-panel">
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
        </aside>
      </section>

      <section v-else-if="activeView === 'personal'" class="personal-view">
        <aside class="note-list-panel">
          <div class="list-toolbar">
            <div class="search-box">
              <Search :size="15" />
              <input v-model.trim="keyword" placeholder="搜索个人笔记" @input="scheduleFeedSearch" />
            </div>
          </div>
          <div class="note-list">
            <article
              v-for="note in personalNotes"
              :key="note.id"
              class="note-row"
              :class="{ selected: activeNote?.id === note.id }"
              @click="setActiveNote(note)"
            >
              <div>
                <strong>{{ note.title }}</strong>
                <small>{{ note.node_path || "AI 分类中" }} · {{ visibilityLabel(note.visibility) }}</small>
              </div>
              <div class="row-actions">
                <button type="button" class="icon-button" title="编辑" @click.stop="editNote(note)">
                  <Pencil :size="14" />
                </button>
                <button type="button" class="icon-button danger-soft" title="删除" @click.stop="deleteNote(note)">
                  <Trash2 :size="14" />
                </button>
              </div>
            </article>
            <p v-if="!personalNotes.length" class="empty-text large-empty">还没有个人笔记。</p>
          </div>
        </aside>

        <section class="editor-panel">
          <form class="composer-form editor-form" @submit.prevent="saveNote">
            <div class="editor-head">
              <div>
                <small>{{ draft.editingId ? "编辑笔记" : "新建笔记" }}</small>
                <h2>{{ draft.title || "未命名笔记" }}</h2>
              </div>
              <select v-model="draft.visibility" aria-label="可见性">
                <option value="private">个人</option>
                <option value="shared">共享</option>
              </select>
            </div>
            <input v-model.trim="draft.title" placeholder="标题，例如：Dijkstra 的适用条件" />
            <input v-model.trim="draft.tags" placeholder="可选标签，用逗号分隔" />
            <div class="markdown-workbench">
              <textarea v-model="draft.content" placeholder="写课堂记录、摘录、错题思路、代码片段。AI 会判断课程和知识点。" />
              <article class="markdown-preview" v-html="markdownPreview"></article>
            </div>
            <div class="composer-actions">
              <button type="button" class="ghost-button" :disabled="importingDocument" @click="triggerDocumentImport">
                <FileUp :size="15" />
                {{ importingDocument ? "解析中" : "导入文件" }}
              </button>
              <button
                v-if="draft.sourceNote && canManageNote(draft.sourceNote) && draft.sourceNote.visibility !== 'shared'"
                type="button"
                class="ghost-button"
                @click="publishNote(draft.sourceNote)"
              >
                <Users :size="15" />
                共享
              </button>
              <button
                v-if="draft.sourceNote && canManageNote(draft.sourceNote)"
                type="button"
                class="ghost-button"
                @click="generateAi(draft.sourceNote, 'summary')"
              >
                <Sparkles :size="15" />
                摘要
              </button>
              <button
                v-if="draft.sourceNote && canManageNote(draft.sourceNote)"
                type="button"
                class="ghost-button"
                @click="generateAi(draft.sourceNote, 'tags')"
              >
                <Sparkles :size="15" />
                标签
              </button>
              <button v-if="draft.editingId" type="button" class="ghost-button" @click="resetDraft">取消编辑</button>
              <button type="submit" class="primary-button">
                <UploadCloud :size="15" />
                {{ draft.editingId ? "更新" : "保存并解析" }}
              </button>
            </div>
          </form>
        </section>
      </section>

      <section v-else-if="activeView === 'shared'" class="shared-view">
        <div class="shared-search-row">
          <div class="search-box shared-search">
            <Search :size="16" />
            <input v-model.trim="sharedKeyword" placeholder="搜索共享笔记" />
          </div>
        </div>
        <section class="shared-grid">
          <article v-for="note in sharedNotes" :key="note.id" class="shared-note" @click="setActiveNote(note)">
            <div class="shared-cover">
              <span>{{ coverInitial(note) }}</span>
              <small>{{ note.node_path || "Shared" }}</small>
            </div>
            <div class="shared-body">
              <strong>{{ note.title }}</strong>
              <small>{{ note.author_name || "未知作者" }} · {{ note.updated_at?.slice(0, 10) }}</small>
              <p>{{ note.summary || note.content_text }}</p>
              <div class="shared-actions">
                <button type="button" class="ghost-button" :class="{ selected: note.is_liked }" @click.stop="toggleLike(note)">
                  <ThumbsUp :size="14" />
                  {{ note.like_count || 0 }}
                </button>
                <button type="button" class="ghost-button" @click.stop="openDiscussion(note)">
                  <MessageSquare :size="14" />
                  {{ note.comment_count || 0 }}
                </button>
              </div>
            </div>
          </article>
          <p v-if="!sharedNotes.length" class="empty-text large-empty">暂时没有符合条件的共享笔记。</p>
        </section>
      </section>

      <section v-else-if="activeView === 'mistakes'" class="focus-view">
        <section class="focus-panel">
          <ClipboardList :size="24" />
          <h2>错题整理</h2>
          <p>当前 demo 先从个人笔记中整理错题线索。后续可把错题卡片接入同一套 AI 分类、共享和问答流程。</p>
          <div class="mistake-candidates">
            <article v-for="note in mistakeCandidates" :key="note.id" @click="setActiveNote(note)">
              <strong>{{ note.title }}</strong>
              <small>{{ note.node_path || "未归档" }}</small>
              <p>{{ note.summary || note.content_text }}</p>
            </article>
          </div>
          <p v-if="!mistakeCandidates.length" class="empty-text large-empty">还没有检测到错题相关笔记。</p>
        </section>
      </section>

      <section v-else class="focus-view">
        <section class="focus-panel daily-panel">
          <CalendarDays :size="24" />
          <small>{{ todayLabel }}</small>
          <h2>{{ dailyQuestion.title }}</h2>
          <p>{{ dailyQuestion.prompt }}</p>
          <div class="daily-source">
            <span>来源</span>
            <strong>{{ dailyQuestion.source }}</strong>
          </div>
          <button type="button" class="primary-button" @click="question = dailyQuestion.prompt; activeView = 'network'">
            <Bot :size="15" />
            用笔记问答展开
          </button>
        </section>
      </section>
    </section>

    <aside v-if="activeNote && activeView !== 'personal'" class="floating-detail">
      <div class="panel-kicker">
        <PanelRight :size="15" />
        <span>当前笔记</span>
        <button type="button" class="icon-button" title="关闭" @click="activeNote = null">
          <X :size="14" />
        </button>
      </div>
      <strong>{{ activeNote.title }}</strong>
      <small>{{ activeNote.node_path || "未归档" }}</small>
      <p>{{ activeNote.content_text }}</p>
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
  BookOpen,
  Bot,
  CalendarDays,
  Check,
  ClipboardList,
  FileUp,
  LogOut,
  MessageSquare,
  Network,
  PanelRight,
  Pencil,
  Plus,
  RefreshCcw,
  Search,
  Send,
  ShieldCheck,
  Sparkles,
  ThumbsUp,
  Trash2,
  UploadCloud,
  Users,
  X
} from "@lucide/vue";
import { computed, onMounted, reactive, ref } from "vue";

import { api, setToken, splitTags } from "@/services/api";
import type { AdminOverview, AiResult, AiStatus, AiTaskType, Comment, Course, Note, NoteAskContext, User } from "@/types";

defineEmits<{ home: [] }>();

type ActiveView = "network" | "personal" | "shared" | "mistakes" | "daily";
type GraphNode = {
  id: string;
  kind: "hub" | "course" | "note";
  label: string;
  short: string;
  meta: string;
  x: number;
  y: number;
  courseId?: number | null;
  noteId?: number;
};

const backendReady = ref(false);
const user = ref<User | null>(null);
const courses = ref<Course[]>([]);
const notes = ref<Note[]>([]);
const activeNote = ref<Note | null>(null);
const activeView = ref<ActiveView>("network");
const selectedCourseId = ref<number | null>(null);
const selectedGraphNodeId = ref("hub");
const aiStatus = ref<AiStatus | null>(null);
const adminOverview = ref<AdminOverview | null>(null);
const keyword = ref("");
const sharedKeyword = ref("");
const question = ref("");
const toast = ref("");
const documentInput = ref<HTMLInputElement | null>(null);
const importingDocument = ref(false);
let searchTimer: number | undefined;
const lastClassification = ref<{
  course_name: string;
  node_title: string;
  summary: string;
  tags: string[];
  source?: string;
} | null>(null);
const lastImport = ref<{ file_name: string; parser: string; characters: number } | null>(null);

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

const viewKicker = computed(() => {
  const labels: Record<ActiveView, string> = {
    network: "Knowledge network",
    personal: "Private capture",
    shared: "Community notes",
    mistakes: "Review queue",
    daily: "Daily prompt"
  };
  return labels[activeView.value];
});

const viewTitle = computed(() => {
  const labels: Record<ActiveView, string> = {
    network: "浮动知识点网络",
    personal: "个人笔记",
    shared: "共享笔记",
    mistakes: "错题整理",
    daily: "每日一题"
  };
  return labels[activeView.value];
});

const personalNotes = computed(() => {
  return notes.value.filter((note) => {
    if (note.author_id !== user.value?.id) return false;
    if (selectedCourseId.value !== null && note.course_id !== selectedCourseId.value) return false;
    return true;
  });
});

const sharedNotes = computed(() => {
  const q = sharedKeyword.value.trim().toLowerCase();
  return notes.value.filter((note) => {
    if (note.visibility !== "shared" || note.author_id === user.value?.id) return false;
    if (!q) return true;
    const haystack = `${note.title} ${note.summary || ""} ${note.content_text} ${(note.tags || []).join(" ")} ${note.node_path || ""}`.toLowerCase();
    return haystack.includes(q);
  });
});

const mistakeCandidates = computed(() => {
  const words = ["错题", "错误", "wrong", "mistake", "反思", "订正"];
  return personalNotes.value.filter((note) => {
    const haystack = `${note.title} ${note.summary || ""} ${note.content_text} ${(note.tags || []).join(" ")}`.toLowerCase();
    return words.some((word) => haystack.includes(word));
  });
});

const networkNodes = computed<GraphNode[]>(() => {
  const nodes: GraphNode[] = [
    {
      id: "hub",
      kind: "hub",
      label: "NoteWeave",
      short: "NW",
      meta: `${notes.value.length} 条笔记`,
      x: 50,
      y: 48
    }
  ];
  const coursePositions = [
    [24, 22],
    [72, 20],
    [82, 62],
    [40, 78],
    [18, 58],
    [56, 16]
  ];
  courses.value.slice(0, 6).forEach((course, index) => {
    const [x, y] = coursePositions[index] || [28 + index * 9, 24 + index * 8];
    nodes.push({
      id: `course-${course.id}`,
      kind: "course",
      label: course.name,
      short: course.name.slice(0, 2).toUpperCase(),
      meta: `${course.note_count || 0} 条`,
      x,
      y,
      courseId: course.id
    });
  });
  const notePositions = [
    [18, 36],
    [34, 15],
    [66, 34],
    [88, 44],
    [68, 78],
    [28, 72],
    [50, 86],
    [10, 70]
  ];
  notes.value.slice(0, 8).forEach((note, index) => {
    const [x, y] = notePositions[index] || [20 + index * 8, 70 - index * 4];
    nodes.push({
      id: `note-${note.id}`,
      kind: "note",
      label: note.title,
      short: coverInitial(note),
      meta: note.node_path || visibilityLabel(note.visibility),
      x,
      y,
      courseId: note.course_id,
      noteId: note.id
    });
  });
  return nodes;
});

const networkLinks = computed(() => {
  const nodes = networkNodes.value;
  const hub = nodes[0];
  return nodes.slice(1).map((node) => {
    const parent = node.kind === "note" ? nodes.find((candidate) => candidate.id === `course-${node.courseId}`) || hub : hub;
    return { id: `${parent.id}-${node.id}`, from: parent, to: node };
  });
});

const todayLabel = computed(() => {
  return new Intl.DateTimeFormat("zh-CN", { month: "long", day: "numeric", weekday: "long" }).format(new Date());
});

const dailyQuestion = computed(() => {
  const source = activeNote.value || personalNotes.value[0] || notes.value[0];
  if (!source) {
    return {
      title: "今天先建立第一条知识线索",
      prompt: "选择一个最近学到的概念，写下定义、例子和一个容易混淆的点。",
      source: "尚无笔记"
    };
  }
  return {
    title: `复盘：${source.title}`,
    prompt: `请基于「${source.title}」解释它的核心概念，并补充一个能够检验理解程度的问题。`,
    source: source.node_path || source.title
  };
});

const markdownPreview = computed(() => renderMarkdown(draft.content));

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
    activeView.value = "network";
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
    activeView.value = "network";
    await loadWorkspace();
  });
}

async function logout(): Promise<void> {
  await api.logout().catch(() => undefined);
  setToken("");
  user.value = null;
  courses.value = [];
  notes.value = [];
  activeNote.value = null;
  selectedCourseId.value = null;
  adminOverview.value = null;
  activeView.value = "network";
}

async function loadWorkspace(): Promise<void> {
  if (!user.value) return;
  await Promise.all([loadAiStatus(), loadCoursesAndNotes(), loadAdminOverview()]);
}

async function loadAiStatus(): Promise<void> {
  if (!user.value) return;
  aiStatus.value = await api.aiStatus();
}

async function loadAdminOverview(): Promise<void> {
  if (user.value?.system_role !== "admin") return;
  adminOverview.value = await api.adminOverview();
}

async function loadCoursesAndNotes(): Promise<void> {
  if (!user.value) return;
  const [courseList, noteFeed] = await Promise.all([api.listCourses(), api.listNoteFeed(120, keyword.value)]);
  courses.value = courseList;
  notes.value = noteFeed;
  if (activeNote.value) {
    activeNote.value = notes.value.find((note) => note.id === activeNote.value?.id) || notes.value[0] || null;
  } else {
    activeNote.value = notes.value[0] || null;
  }
}

function scheduleFeedSearch(): void {
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    void guarded(loadCoursesAndNotes);
  }, 260);
}

function showNetwork(): void {
  activeView.value = "network";
}

function startNewNote(): void {
  resetDraft();
  activeView.value = "personal";
}

function selectGraphNode(node: GraphNode): void {
  selectedGraphNodeId.value = node.id;
  selectedCourseId.value = node.courseId ?? null;
  if (node.noteId) {
    activeNote.value = notes.value.find((note) => note.id === node.noteId) || null;
  }
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
      lastImport.value = null;
      selectedCourseId.value = result.course.id;
      activeNote.value = result.note;
      selectedGraphNodeId.value = `note-${result.note.id}`;
      notify("笔记已保存并完成 AI 归类");
    }
    resetDraft();
    await loadCoursesAndNotes();
  });
}

function triggerDocumentImport(): void {
  if (!user.value) {
    notify("请先登录");
    return;
  }
  documentInput.value?.click();
}

async function importDocument(event: Event): Promise<void> {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = "";
  if (!file) return;
  await guarded(async () => {
    if (!user.value) throw new Error("请先登录");
    importingDocument.value = true;
    try {
      const dataBase64 = await fileToBase64(file);
      const result = await api.importNoteDocument({
        file_name: file.name,
        content_type: file.type || inferContentType(file.name),
        data_base64: dataBase64,
        visibility: draft.visibility,
        tags: splitTags(draft.tags)
      });
      lastClassification.value = result.classification;
      lastImport.value = {
        file_name: result.document.file_name,
        parser: result.document.parser,
        characters: result.document.characters
      };
      selectedCourseId.value = result.course.id;
      selectedGraphNodeId.value = `note-${result.note.id}`;
      activeNote.value = result.note;
      activeView.value = "network";
      resetDraft();
      await loadCoursesAndNotes();
      notify("文件已解析并导入为笔记");
    } finally {
      importingDocument.value = false;
    }
  });
}

function fileToBase64(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const value = String(reader.result || "");
      resolve(value.includes(",") ? value.split(",")[1] : value);
    };
    reader.onerror = () => reject(reader.error || new Error("文件读取失败"));
    reader.readAsDataURL(file);
  });
}

function inferContentType(fileName: string): string {
  const suffix = fileName.toLowerCase().split(".").pop() || "";
  if (suffix === "pdf") return "application/pdf";
  if (suffix === "docx") return "application/vnd.openxmlformats-officedocument.wordprocessingml.document";
  if (suffix === "md" || suffix === "markdown") return "text/markdown";
  return "application/octet-stream";
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
  activeView.value = "personal";
}

function setActiveNote(note: Note): void {
  activeNote.value = note;
}

function canManageNote(note: Note): boolean {
  return Boolean(user.value && note.author_id === user.value.id);
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
      aiReview.taskType === "summary" ? { summary: aiReview.summary } : { tags: splitTags(aiReview.tagsText) }
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

function coverInitial(note: Note): string {
  const source = note.tags?.[0] || note.title || "N";
  return source.slice(0, 2).toUpperCase();
}

function escapeHtml(value: string): string {
  return value
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderInline(value: string): string {
  return escapeHtml(value)
    .replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>")
    .replace(/\*([^*]+)\*/g, "<em>$1</em>")
    .replace(/`([^`]+)`/g, "<code>$1</code>")
    .replace(/\[([^\]]+)\]\((https?:\/\/[^)\s]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>');
}

function renderMarkdown(value: string): string {
  if (!value.trim()) return '<p class="preview-empty">Markdown 预览</p>';
  const lines = value.split(/\r?\n/);
  const html: string[] = [];
  let listOpen = false;
  for (const line of lines) {
    const trimmed = line.trim();
    if (!trimmed) {
      if (listOpen) {
        html.push("</ul>");
        listOpen = false;
      }
      continue;
    }
    const heading = trimmed.match(/^(#{1,3})\s+(.+)$/);
    if (heading) {
      if (listOpen) {
        html.push("</ul>");
        listOpen = false;
      }
      html.push(`<h${heading[1].length}>${renderInline(heading[2])}</h${heading[1].length}>`);
      continue;
    }
    const bullet = trimmed.match(/^[-*]\s+(.+)$/);
    if (bullet) {
      if (!listOpen) {
        html.push("<ul>");
        listOpen = true;
      }
      html.push(`<li>${renderInline(bullet[1])}</li>`);
      continue;
    }
    if (listOpen) {
      html.push("</ul>");
      listOpen = false;
    }
    html.push(`<p>${renderInline(trimmed)}</p>`);
  }
  if (listOpen) html.push("</ul>");
  return html.join("");
}

onMounted(async () => {
  await guarded(async () => {
    backendReady.value = (await api.health()).status === "ok";
    const me = await api.me().catch(() => null);
    if (me) {
      user.value = me;
      activeView.value = "network";
      await loadWorkspace();
    }
  });
});
</script>
