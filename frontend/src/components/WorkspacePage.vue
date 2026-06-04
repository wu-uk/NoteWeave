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

  <main v-else :class="['app-shell', 'knowledge-app', { 'theme-light': !darkTheme, 'reader-focus': isReadingNote }]">
    <aside v-if="!isReadingNote" class="workspace-nav">
      <section class="nav-account">
        <div class="user-avatar" aria-hidden="true">{{ userInitial }}</div>
        <div class="user-identity">
          <strong>{{ userDisplayName }}</strong>
          <small>{{ user?.username }} · {{ user?.system_role === "admin" ? "管理员" : "普通用户" }}</small>
        </div>
        <div class="user-actions" aria-label="用户操作">
          <button type="button" class="icon-button" title="设置" @click="openSettings">
            <Settings :size="15" />
          </button>
          <button type="button" class="icon-button" :title="darkTheme ? '切换白天模式' : '切换黑夜模式'" @click="toggleTheme">
            <Sun v-if="darkTheme" :size="15" />
            <Moon v-else :size="15" />
          </button>
          <button type="button" class="icon-button danger-soft" title="登出" @click="logout">
            <LogOut :size="15" />
          </button>
        </div>
      </section>

      <nav class="primary-nav" aria-label="工作台导航">
        <button type="button" :class="{ active: activeView === 'personal' }" @click="showPersonalNotes">
          <BookOpen :size="17" />
          <span>个人笔记</span>
        </button>
        <button type="button" :class="{ active: activeView === 'shared' }" @click="showSharedNotes">
          <Users :size="17" />
          <span>共享笔记</span>
        </button>
        <button type="button" :class="{ active: activeView === 'mistakes' }" @click="showMistakes">
          <ClipboardList :size="17" />
          <span>错题整理</span>
        </button>
        <button type="button" :class="{ active: activeView === 'qa' }" @click="showQa">
          <MessageSquare :size="17" />
          <span>AI 问答</span>
        </button>
      </nav>

    </aside>

    <section class="workspace-surface">
      <header v-if="activeView !== 'network' && !isReadingNote && !isViewingMistake" class="workspace-top">
        <div>
          <small>{{ viewKicker }}</small>
          <h1>{{ viewTitle }}</h1>
        </div>
        <div v-if="activeView !== 'personal'" class="top-actions">
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
        </div>
        <input
          ref="documentInput"
          class="visually-hidden"
          type="file"
          accept=".pdf,.doc,.docx,.md,.markdown,application/pdf,application/msword,application/vnd.openxmlformats-officedocument.wordprocessingml.document,text/markdown,text/plain"
          @change="importDocument"
        />
      </header>

      <section v-if="activeView === 'network'" class="knowledge-view">
        <div class="graph-panel knowledge-graph-panel">
          <KnowledgeGraphFlow
            :nodes="knowledgeGraphNodes"
            :links="knowledgeGraphLinks"
            :active-id="selectedTreeRowId"
            @select="selectKnowledgeGraphNode"
          />
        </div>
      </section>

      <section v-else-if="activeView === 'personal'" class="personal-workspace">
        <section v-if="noteMode === 'list'" class="personal-list-screen">
          <div class="personal-list-toolbar">
            <div class="search-box">
              <Search :size="15" />
              <input v-model.trim="keyword" placeholder="搜索个人笔记" @input="scheduleFeedSearch" />
            </div>
            <div class="personal-list-actions">
              <button type="button" class="ghost-button" :disabled="importingDocument" @click="triggerDocumentImport">
                <FileUp :size="15" />
                {{ importingDocument ? "解析中" : "上传笔记" }}
              </button>
              <button type="button" class="primary-button" @click="startNewNote">
                <Plus :size="15" />
                添加笔记
              </button>
            </div>
          </div>
          <div class="note-table">
            <article v-for="note in paginatedPersonalNotes" :key="note.id" class="note-table-row">
              <div class="note-table-main">
                <strong>{{ note.title }}</strong>
                <small>{{ note.node_path || "AI 分类中" }} · {{ visibilityLabel(note.visibility) }} · {{ note.updated_at?.slice(0, 10) }}</small>
              </div>
              <section class="markdown-snippet note-summary" v-html="renderMarkdown(note.summary || note.content_text)"></section>
              <div class="row-actions">
                <button type="button" class="ghost-button" @click="viewNote(note)">
                  <PanelRight :size="14" />
                  查看
                </button>
                <button type="button" class="ghost-button" @click="editNote(note)">
                  <Pencil :size="14" />
                  编辑
                </button>
                <button type="button" class="icon-button danger-soft" title="删除" @click="deleteNote(note)">
                  <Trash2 :size="14" />
                </button>
              </div>
            </article>
            <p v-if="!personalNotes.length" class="empty-text large-empty">还没有个人笔记。</p>
          </div>
          <div v-if="personalNotes.length" class="pagination-bar">
            <span>第 {{ personalPage }} / {{ personalTotalPages }} 页 · 共 {{ personalNotes.length }} 条</span>
            <div>
              <button type="button" class="ghost-button" :disabled="personalPage <= 1" @click="personalPage -= 1">上一页</button>
              <button type="button" class="ghost-button" :disabled="personalPage >= personalTotalPages" @click="personalPage += 1">下一页</button>
            </div>
          </div>
        </section>

        <section v-else-if="noteMode === 'view' && activeNote" class="note-reader-screen">
          <div class="note-reader-grid" :style="{ gridTemplateColumns: `${readerSplitPercent}% 10px minmax(0, 1fr)` }">
            <article class="rendered-document">
              <div class="document-title">
                <small>{{ activeNote.node_path || "未归档" }}</small>
                <div class="document-title-row">
                  <button type="button" class="ghost-button" @click="backToNoteList">返回列表</button>
                  <h2>{{ activeNote.title }}</h2>
                  <button type="button" class="primary-button" @click="editNote(activeNote)">
                    <Pencil :size="14" />
                    编辑
                  </button>
                </div>
                <a v-if="activeNoteSourceAttachment" class="source-file-link" :href="activeNoteSourceUrl" target="_blank" rel="noreferrer">
                  <FileUp :size="14" />
                  {{ activeNoteSourceAttachment.file_name }}
                </a>
              </div>
              <iframe
                v-if="activeNotePdfUrl"
                class="pdf-preview-frame"
                :src="activeNotePdfUrl"
                title="PDF 预览"
              ></iframe>
              <section v-else class="markdown-preview document-preview" v-html="renderMarkdown(activeNote.content_text)"></section>
            </article>
            <div class="reader-resizer" role="separator" aria-label="调整 Markdown 与树结构比例" @pointerdown="startReaderResize"></div>
            <aside class="note-tree-panel modora-tree-panel">
              <ModoraTreeView :tree="activeNote.content_json?.modora_tree" @jump="jumpToMarkdownContent" />
            </aside>
          </div>
        </section>

        <section v-else class="note-edit-screen">
          <form class="composer-form editor-form" @submit.prevent="saveNote">
            <div class="editor-head">
              <div>
                <small>{{ draft.editingId ? "编辑笔记" : "添加笔记" }}</small>
                <h2>{{ draft.title || "未命名笔记" }}</h2>
              </div>
              <div class="composer-actions">
                <button type="button" class="ghost-button" @click="backToNoteList">返回列表</button>
                <button type="submit" class="primary-button">
                  <UploadCloud :size="15" />
                  {{ draft.editingId ? "更新" : "保存并解析" }}
                </button>
              </div>
            </div>
            <input v-model.trim="draft.title" placeholder="标题，例如：Dijkstra 的适用条件" />
            <input v-model.trim="draft.tags" placeholder="可选标签，用逗号分隔" />
            <select v-model="draft.visibility" aria-label="可见性">
              <option value="private">个人</option>
              <option value="shared">共享</option>
            </select>
            <div class="markdown-workbench">
              <textarea v-model="draft.content" placeholder="写课堂记录、摘录、错题思路、代码片段。AI 会判断课程和知识点。" />
              <article class="markdown-preview editor-preview" v-html="markdownPreview"></article>
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
          <article v-for="note in sharedNotes" :key="note.id" class="shared-note" @click="viewNote(note)">
            <div class="shared-cover">
              <span>{{ coverInitial(note) }}</span>
              <small>{{ note.node_path || "Shared" }}</small>
            </div>
            <div class="shared-body">
              <strong>{{ note.title }}</strong>
              <small>{{ note.author_name || "未知作者" }} · {{ note.updated_at?.slice(0, 10) }}</small>
              <section class="markdown-snippet shared-summary" v-html="renderMarkdown(note.summary || note.content_text)"></section>
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

      <section v-else-if="activeView === 'mistakes'" class="mistake-workspace">
        <section v-if="activeMistake" class="mistake-detail-screen">
          <article class="rendered-document mistake-detail-document">
            <div class="document-title">
              <small>{{ activeMistake.source }}</small>
              <div class="document-title-row">
                <button type="button" class="ghost-button" @click="closeMistakeDetail">返回错题列表</button>
                <h2>{{ mistakeDetailHeading(activeMistake) }}</h2>
              </div>
              <div v-if="activeMistake.tags.length" class="tag-row mistake-detail-tags">
                <button v-for="tag in activeMistake.tags" :key="`personal-${tag}`" type="button" @click="jumpToTaggedNotes(tag, 'personal')">
                  个人：{{ tag }}
                </button>
                <button v-for="tag in activeMistake.tags" :key="`shared-${tag}`" type="button" @click="jumpToTaggedNotes(tag, 'shared')">
                  共享：{{ tag }}
                </button>
              </div>
            </div>
            <section class="mistake-detail-flow">
              <article>
                <small>错题</small>
                <div class="markdown-preview mistake-detail-markdown" v-html="renderMarkdown(activeMistake.question)"></div>
              </article>
              <article>
                <small>错误答案</small>
                <div class="markdown-preview mistake-detail-markdown" v-html="renderMarkdown(activeMistake.wrongAnswer)"></div>
              </article>
              <article>
                <small>解析 / 正确思路</small>
                <div class="markdown-preview mistake-detail-markdown" v-html="renderMarkdown(activeMistake.correction)"></div>
              </article>
              <article>
                <small>复盘</small>
                <div class="markdown-preview mistake-detail-markdown" v-html="renderMarkdown(activeMistake.reviewPoint)"></div>
              </article>
            </section>
          </article>
        </section>

        <section v-else class="focus-view">
          <section class="focus-panel mistake-board">
          <div class="mistake-board-head">
            <div>
              <ClipboardList :size="24" />
              <h2>错题整理</h2>
              <p>优先展示用户上传或标记的错题；模拟数据只用于当前测试阶段占位。</p>
            </div>
            <button type="button" class="primary-button" :disabled="importingDocument" @click="triggerDocumentImport">
              <FileUp :size="15" />
              {{ importingDocument ? "解析中" : "上传错题" }}
            </button>
          </div>
          <div class="mistake-candidates">
            <article
              v-for="mistake in mistakeCards"
              :key="mistake.id"
              class="mistake-card"
              :class="{ uploaded: mistake.uploaded }"
              @click="openMistakeDetail(mistake)"
            >
              <div class="mistake-card-top">
                <span>{{ mistake.subject }}</span>
                <small>{{ mistake.uploaded ? "用户上传" : "模拟数据" }}</small>
              </div>
              <strong>{{ mistake.title }}</strong>
              <div v-if="mistake.tags.length" class="tag-row mistake-tags">
                <button
                  v-for="tag in mistake.tags"
                  :key="`${mistake.id}-${tag}`"
                  type="button"
                  @click.stop="jumpToTaggedNotes(tag, 'personal')"
                >
                  {{ tag }}
                </button>
              </div>
              <section class="mistake-block">
                <small>题干</small>
                <div class="markdown-snippet mistake-summary" v-html="renderMarkdown(mistake.question)"></div>
              </section>
              <section class="mistake-block wrong">
                <small>错误答案</small>
                <div class="markdown-snippet mistake-summary" v-html="renderMarkdown(mistake.wrongAnswer)"></div>
              </section>
              <section class="mistake-block correct">
                <small>订正思路</small>
                <div class="markdown-snippet mistake-summary" v-html="renderMarkdown(mistake.correction)"></div>
              </section>
              <footer>
                <span>{{ mistake.reviewPoint }}</span>
                <small>{{ mistake.source }}</small>
              </footer>
            </article>
          </div>
          </section>
        </section>
      </section>

      <section v-else class="qa-workspace">
        <div class="qa-source-layout">
          <aside class="qa-source-panel">
            <div class="search-box">
              <Search :size="15" />
              <input v-model.trim="qaSourceQuery" placeholder="搜索并添加来源笔记" />
            </div>
            <div class="qa-source-list">
              <button
                v-for="note in qaSourceCandidates"
                :key="`qa-add-${note.id}`"
                type="button"
                class="qa-source-option"
                @click="toggleQaSourceNote(note)"
              >
                <strong>{{ note.title }}</strong>
                <small>{{ note.node_path || "未归档" }} · {{ visibilityLabel(note.visibility) }}</small>
              </button>
              <p v-if="!qaSourceCandidates.length" class="empty-text">没有可添加的笔记。</p>
            </div>
          </aside>
          <section class="qa-chat-panel">
            <div class="qa-compact-status">{{ selectedQaSourceNotes.length ? `${selectedQaSourceNotes.length} 个来源` : "全部可见笔记" }}</div>
            <div v-if="selectedQaSourceNotes.length" class="qa-selected-sources">
              <button
                v-for="note in selectedQaSourceNotes"
                :key="`qa-selected-${note.id}`"
                type="button"
                @click="toggleQaSourceNote(note)"
              >
                {{ note.title }}
                <X :size="13" />
              </button>
            </div>
            <p v-else class="qa-source-hint">未指定来源时，会在你可见的全部笔记中检索。</p>
            <div class="qa-dialog">
              <p v-if="!qaMessages.length" class="qa-empty-chat">选择来源笔记后开始提问。</p>
              <article v-for="message in qaMessages" :key="message.id" :class="['qa-message', message.role]">
                <div class="qa-bubble">
                  <span>{{ message.role === "user" ? "你" : "AI" }}</span>
                  <p v-if="message.role === 'user'">{{ message.content }}</p>
                  <div v-else class="qa-answer-markdown" v-html="renderMarkdown(message.content)"></div>
                  <small v-if="message.pending">正在检索笔记...</small>
                </div>
                <div v-if="message.role === 'assistant' && message.contexts?.length" class="qa-citations">
                  <button v-for="context in message.contexts" :key="`${message.id}-${context.source_id}`" type="button" @click="jumpToAnswerSource(context)">
                    {{ context.title }}
                  </button>
                </div>
              </article>
            </div>
            <form class="qa-form" @submit.prevent="askNotes">
              <textarea v-model.trim="question" placeholder="输入问题，例如：信道容量和信源熵是什么关系？" />
              <button type="submit" class="primary-button" :disabled="askingQuestion">
                <Send :size="14" />
                {{ askingQuestion ? "检索中" : "提问" }}
              </button>
            </form>
          </section>
        </div>
      </section>
    </section>

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
  ClipboardList,
  FileUp,
  LogOut,
  MessageSquare,
  Moon,
  Network,
  PanelRight,
  Pencil,
  Plus,
  Search,
  Send,
  Settings,
  Sparkles,
  Sun,
  ThumbsUp,
  Trash2,
  UploadCloud,
  Users,
  X
} from "@lucide/vue";
import katex from "katex";
import MarkdownIt from "markdown-it";
import texmath from "markdown-it-texmath";
import { computed, onMounted, onUnmounted, reactive, ref } from "vue";

import KnowledgeGraphFlow from "@/components/KnowledgeGraphFlow.vue";
import ModoraTreeView from "@/components/ModoraTreeView.vue";
import { api, resolveApiUrl, setToken, splitTags } from "@/services/api";
import type { AdminOverview, AiStatus, Comment, Course, KnowledgeNode, Mistake, Note, NoteAskContext, User } from "@/types";
import "katex/dist/katex.min.css";
import "markdown-it-texmath/css/texmath.css";

defineEmits<{ home: [] }>();

type ActiveView = "network" | "personal" | "shared" | "mistakes" | "qa";
type ParsedTreeRow = {
  id: string;
  type: "course" | "node" | "note";
  title: string;
  short: string;
  meta: string;
  depth: number;
  courseId: number;
  nodeId?: number | null;
  noteId?: number;
};
type KnowledgeGraphNode = Omit<ParsedTreeRow, "type"> & {
  type: "course" | "node";
};
type KnowledgeGraphLink = {
  id: string;
  from: KnowledgeGraphNode;
  to: KnowledgeGraphNode;
};
type NoteMode = "list" | "view" | "edit";
type MistakeCard = {
  id: string;
  subject: string;
  title: string;
  question: string;
  wrongAnswer: string;
  correction: string;
  reviewPoint: string;
  source: string;
  uploaded: boolean;
  tags: string[];
  mistake?: Mistake;
  note?: Note;
};
type QaMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  source?: string;
  contexts?: NoteAskContext[];
  pending?: boolean;
};

const backendReady = ref(false);
const user = ref<User | null>(null);
const darkTheme = ref(localStorage.getItem("noteweave_theme") !== "light");
const courses = ref<Course[]>([]);
const notes = ref<Note[]>([]);
const mistakes = ref<Mistake[]>([]);
const courseTrees = ref<Record<number, KnowledgeNode | null>>({});
const activeNote = ref<Note | null>(null);
const activeMistake = ref<MistakeCard | null>(null);
const activeView = ref<ActiveView>("network");
const noteMode = ref<NoteMode>("list");
const personalPage = ref(1);
const personalPageSize = 8;
const readerSplitPercent = ref(50);
const selectedCourseId = ref<number | null>(null);
const selectedTreeRowId = ref("");
const aiStatus = ref<AiStatus | null>(null);
const adminOverview = ref<AdminOverview | null>(null);
const keyword = ref("");
const sharedKeyword = ref("");
const question = ref("");
const qaSourceQuery = ref("");
const selectedQaSourceIds = ref<number[]>([]);
const askingQuestion = ref(false);
const qaMessages = ref<QaMessage[]>([]);
const toast = ref("");
const documentInput = ref<HTMLInputElement | null>(null);
const importingDocument = ref(false);
let searchTimer: number | undefined;
let readerResizeActive = false;
let readerResizeFrame: number | undefined;
const lastClassification = ref<{
  course_name: string;
  node_title: string;
  summary: string;
  tags: string[];
  source?: string;
} | null>(null);
const lastImport = ref<{ file_name: string; parser: string; characters: number } | null>(null);
const mockMistakes: MistakeCard[] = [
  {
    id: "mock-network-cidr",
    subject: "计算机网络",
    title: "CIDR 聚合时误把主机位保留下来",
    question: "将 `192.168.12.0/24`、`192.168.13.0/24`、`192.168.14.0/24`、`192.168.15.0/24` 聚合为最短前缀。",
    wrongAnswer: "`192.168.12.0/22`，但没有检查第三个字节的二进制边界。",
    correction: "正确聚合是 `192.168.12.0/22`。关键是确认 `12 = 00001100`，覆盖 12-15 正好固定前 6 位，后 2 位变化。",
    reviewPoint: "做路由聚合先写二进制边界，再判断起始地址是否落在块大小的整数倍上。",
    source: "模拟错题 · 等待用户上传替换",
    uploaded: false,
    tags: ["CIDR", "路由聚合", "子网掩码"]
  },
  {
    id: "mock-channel-entropy",
    subject: "语义通信",
    title: "把信源熵和信道容量混为一谈",
    question: "判断离散无记忆信源能否通过给定信道可靠传输时，应比较哪些量？",
    wrongAnswer: "只计算信源熵 $H(X)$，认为熵越小就一定能传。",
    correction: "需要比较信源编码后的信息率和信道容量 $C$。可靠传输条件是信息率不超过信道容量，而不是只看信源熵本身。",
    reviewPoint: "看到“能否可靠传输”，先找容量 $C$；看到“平均最短编码长度”，再考虑熵界。",
    source: "模拟错题 · 等待用户上传替换",
    uploaded: false,
    tags: ["联合熵", "信道容量", "可靠传输"]
  },
  {
    id: "mock-probability-bayes",
    subject: "概率统计",
    title: "贝叶斯公式里漏掉全概率分母",
    question: "某检测阳性率为 95%，误报率为 3%，患病率为 1%。求阳性时真正患病概率。",
    wrongAnswer: "直接写成 `95%`，忽略了低患病率带来的大量误报。",
    correction: "$P(D|+) = \\frac{0.95 \\times 0.01}{0.95 \\times 0.01 + 0.03 \\times 0.99} \\approx 24.2\\%$。",
    reviewPoint: "条件概率题先画事件树，分母必须包含所有导致观测结果发生的路径。",
    source: "模拟错题 · 等待用户上传替换",
    uploaded: false,
    tags: ["贝叶斯公式", "全概率", "条件概率"]
  },
  {
    id: "mock-security-xss",
    subject: "网络安全",
    title: "XSS 防护只做输入过滤",
    question: "为什么仅靠前端输入过滤不能完整防御存储型 XSS？",
    wrongAnswer: "认为禁止 `<script>` 标签就足够。",
    correction: "攻击载荷可能通过事件属性、URL scheme、富文本解析等路径进入页面。核心防护是输出编码、HTML sanitization、CSP 和服务端校验组合。",
    reviewPoint: "安全题优先区分输入校验、输出编码和运行时策略，不要只列一个过滤规则。",
    source: "模拟错题 · 等待用户上传替换",
    uploaded: false,
    tags: ["XSS", "输出编码", "CSP"]
  }
];

const markdownRenderer = new MarkdownIt({
  html: false,
  linkify: true,
  typographer: true
}).use(texmath, {
  engine: katex,
  delimiters: ["dollars", "brackets", "beg_end"],
  katexOptions: {
    throwOnError: false,
    strict: false
  }
});

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
    qa: "MoDora QA"
  };
  return labels[activeView.value];
});

const viewTitle = computed(() => {
  const labels: Record<ActiveView, string> = {
    network: "知识网络",
    personal: "个人笔记",
    shared: "共享笔记",
    mistakes: "错题整理",
    qa: "AI 问答"
  };
  return labels[activeView.value];
});

const ownNotes = computed(() => {
  return notes.value.filter((note) => {
    if (note.author_id !== user.value?.id) return false;
    return true;
  });
});

const mistakeNoteIds = computed(() => {
  const words = ["错题", "错误", "wrong", "mistake", "反思", "订正"];
  return new Set(
    ownNotes.value
      .filter((note) => {
        const haystack = `${note.title} ${note.summary || ""} ${note.content_text} ${(note.tags || []).join(" ")}`.toLowerCase();
        return words.some((word) => haystack.includes(word));
      })
      .map((note) => note.id)
  );
});

const personalNotes = computed(() => ownNotes.value.filter((note) => !mistakeNoteIds.value.has(note.id)));

const qaVisibleNotes = computed(() => {
  const visible = notes.value.filter((note) => {
    if (mistakeNoteIds.value.has(note.id)) return false;
    return note.visibility === "shared" || note.author_id === user.value?.id;
  });
  return [...visible].sort((a, b) => (b.updated_at || "").localeCompare(a.updated_at || ""));
});

const selectedQaSourceNotes = computed(() => {
  const selected = new Set(selectedQaSourceIds.value);
  return qaVisibleNotes.value.filter((note) => selected.has(note.id));
});

const qaSourceCandidates = computed(() => {
  const selected = new Set(selectedQaSourceIds.value);
  const query = qaSourceQuery.value.trim().toLowerCase();
  return qaVisibleNotes.value
    .filter((note) => {
      if (selected.has(note.id)) return false;
      if (!query) return true;
      const haystack = `${note.title} ${note.summary || ""} ${note.content_text} ${(note.tags || []).join(" ")} ${note.node_path || ""}`.toLowerCase();
      return haystack.includes(query);
    })
    .slice(0, 12);
});

const personalTotalPages = computed(() => Math.max(1, Math.ceil(personalNotes.value.length / personalPageSize)));

const paginatedPersonalNotes = computed(() => {
  if (personalPage.value > personalTotalPages.value) personalPage.value = personalTotalPages.value;
  const start = (personalPage.value - 1) * personalPageSize;
  return personalNotes.value.slice(start, start + personalPageSize);
});

const isReadingNote = computed(() => activeView.value === "personal" && noteMode.value === "view" && Boolean(activeNote.value));
const isViewingMistake = computed(() => activeView.value === "mistakes" && Boolean(activeMistake.value));

const sharedNotes = computed(() => {
  const q = sharedKeyword.value.trim().toLowerCase();
  return notes.value.filter((note) => {
    if (note.visibility !== "shared") return false;
    if (!q) return true;
    const haystack = `${note.title} ${note.summary || ""} ${note.content_text} ${(note.tags || []).join(" ")} ${note.node_path || ""}`.toLowerCase();
    return haystack.includes(q);
  });
});

const uploadedMistakeCards = computed<MistakeCard[]>(() => {
  const noteCards = ownNotes.value.filter((note) => mistakeNoteIds.value.has(note.id)).map((note) => ({
    id: `note-${note.id}`,
    subject: note.node_path || "用户上传",
    title: note.title,
    question: note.summary || note.content_text.slice(0, 220),
    wrongAnswer: "来自用户上传笔记，等待后续解析为结构化错误答案。",
    correction: note.content_text,
    reviewPoint: "已优先展示用户上传内容。后续可在上传解析阶段提取题干、错误原因和订正步骤。",
    source: `${visibilityLabel(note.visibility)} · ${note.updated_at?.slice(0, 10) || "最近"}`,
    uploaded: true,
    tags: note.tags || [],
    note
  }));
  const realMistakeCards = mistakes.value.map((mistake) => ({
    id: `mistake-${mistake.id}`,
    subject: mistake.node_path || "用户上传",
    title: mistake.question_content.slice(0, 80) || "未命名错题",
    question: mistake.question_content,
    wrongAnswer: mistake.wrong_answer || "暂无错误答案记录",
    correction: mistake.solution || mistake.correct_answer || "暂无解析",
    reviewPoint: mistake.error_reason || mistake.reflection || "暂无复盘要点",
    source: `${mistake.visibility === "shared" ? "共享错题" : "个人错题"} · ${mistake.updated_at?.slice(0, 10) || "最近"}`,
    uploaded: true,
    tags: mistake.tags || [],
    mistake
  }));
  return [...realMistakeCards, ...noteCards];
});

const mistakeCards = computed<MistakeCard[]>(() => {
  const uploaded = uploadedMistakeCards.value;
  const remaining = Math.max(0, 6 - uploaded.length);
  return [...uploaded, ...mockMistakes.slice(0, remaining)];
});

const knowledgeGraphNodes = computed<KnowledgeGraphNode[]>(() => {
  const sourceRows: ParsedTreeRow[] = [];
  for (const course of courses.value) {
    const tree = courseTrees.value[course.id];
    if (tree) {
      appendKnowledgeOnlyRows(sourceRows, tree, course.id);
    }
  }
  return sourceRows.map((row) => ({ ...row, type: row.type === "course" ? "course" : "node" }));
});

const knowledgeGraphLinks = computed<KnowledgeGraphLink[]>(() => {
  const nodes = knowledgeGraphNodes.value;
  const byNodeId = new Map<number, KnowledgeGraphNode>();
  for (const node of nodes) {
    if (node.nodeId) byNodeId.set(node.nodeId, node);
  }
  const links: { id: string; from: KnowledgeGraphNode; to: KnowledgeGraphNode }[] = [];
  for (const course of courses.value) {
    const tree = courseTrees.value[course.id];
    if (!tree) continue;
    appendKnowledgeLinks(links, tree, byNodeId);
  }
  return links;
});

const activeNoteSourceAttachment = computed(() => {
  const attachments = activeNote.value?.attachments || [];
  return attachments.find((item) => {
    const name = item.file_name.toLowerCase();
    return name.endsWith(".pdf") || name.endsWith(".doc") || name.endsWith(".docx");
  }) || attachments[0] || null;
});

const activeNoteSourceUrl = computed(() => {
  return activeNoteSourceAttachment.value ? resolveApiUrl(activeNoteSourceAttachment.value.url_path) : "";
});

const activeNotePdfUrl = computed(() => {
  const attachment = activeNote.value?.attachments?.find((item) => item.content_type === "application/pdf" || item.file_name.toLowerCase().endsWith(".pdf"));
  return attachment ? resolveApiUrl(attachment.url_path) : "";
});

const markdownPreview = computed(() => renderMarkdown(draft.content));

const userDisplayName = computed(() => user.value?.display_name || user.value?.username || "NoteWeave 用户");

const userInitial = computed(() => userDisplayName.value.trim().slice(0, 1).toUpperCase() || "N");

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

function openSettings(): void {
  notify("设置入口已就绪，后续可接入偏好配置");
}

function toggleTheme(): void {
  darkTheme.value = !darkTheme.value;
  localStorage.setItem("noteweave_theme", darkTheme.value ? "dark" : "light");
}

async function logout(): Promise<void> {
  await api.logout().catch(() => undefined);
  setToken("");
  user.value = null;
  courses.value = [];
  notes.value = [];
  mistakes.value = [];
  courseTrees.value = {};
  activeNote.value = null;
  activeView.value = "network";
  noteMode.value = "list";
  auth.password = "";
  notify("已登出");
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
  await Promise.all([loadCourseTrees(courseList), loadCourseMistakes(courseList)]);
  if (activeNote.value) {
    activeNote.value = notes.value.find((note) => note.id === activeNote.value?.id) || notes.value[0] || null;
  } else {
    activeNote.value = notes.value[0] || null;
  }
}

async function loadCourseMistakes(courseList: Course[]): Promise<void> {
  const results = await Promise.all(
    courseList.map(async (course) => {
      try {
        return await api.listMistakes(course.id);
      } catch {
        return [] as Mistake[];
      }
    })
  );
  mistakes.value = results.flat();
}

function scheduleFeedSearch(): void {
  personalPage.value = 1;
  window.clearTimeout(searchTimer);
  searchTimer = window.setTimeout(() => {
    void guarded(loadCoursesAndNotes);
  }, 260);
}

function showNetwork(): void {
  activeMistake.value = null;
  activeView.value = "network";
}

function showPersonalNotes(): void {
  activeMistake.value = null;
  activeView.value = "personal";
  noteMode.value = "list";
  personalPage.value = 1;
}

function showSharedNotes(): void {
  activeMistake.value = null;
  activeView.value = "shared";
}

function showMistakes(): void {
  activeView.value = "mistakes";
  activeMistake.value = null;
}

function showQa(): void {
  activeMistake.value = null;
  activeView.value = "qa";
}

function startNewNote(): void {
  activeMistake.value = null;
  resetDraft();
  activeView.value = "personal";
  noteMode.value = "edit";
}

async function loadCourseTrees(courseList: Course[]): Promise<void> {
  const entries = await Promise.all(
    courseList.map(async (course) => {
      try {
        const tree = await api.getTree(course.id);
        return [course.id, tree.tree] as const;
      } catch {
        return [course.id, null] as const;
      }
    })
  );
  courseTrees.value = Object.fromEntries(entries);
}

function appendKnowledgeOnlyRows(rows: ParsedTreeRow[], node: KnowledgeNode, courseId: number): void {
  const isRoot = node.parent_id === null;
  rows.push({
    id: `node-${node.id}`,
    type: isRoot ? "course" : "node",
    title: node.title,
    short: isRoot ? "课" : "点",
    meta: isRoot ? `${node.note_count || 0} 条笔记` : node.path,
    depth: node.depth,
    courseId,
    nodeId: node.id
  });
  for (const child of node.children || []) {
    appendKnowledgeOnlyRows(rows, child, courseId);
  }
}

function appendKnowledgeLinks(
  links: KnowledgeGraphLink[],
  node: KnowledgeNode,
  byNodeId: Map<number, KnowledgeGraphNode>
): void {
  const from = byNodeId.get(node.id);
  for (const child of node.children || []) {
    const to = byNodeId.get(child.id);
    if (from && to) {
      links.push({ id: `${from.id}-${to.id}`, from, to });
    }
    appendKnowledgeLinks(links, child, byNodeId);
  }
}

function selectKnowledgeGraphNode(node: KnowledgeGraphNode): void {
  selectedTreeRowId.value = node.id;
  selectedCourseId.value = node.courseId;
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
      selectedTreeRowId.value = `note-${note.id}`;
      noteMode.value = "view";
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
      selectedTreeRowId.value = `note-${result.note.id}`;
      noteMode.value = "view";
      notify("笔记已保存并完成 AI 归类");
    }
    await loadCoursesAndNotes();
    resetDraft();
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
      selectedTreeRowId.value = `note-${result.note.id}`;
      activeNote.value = result.note;
      activeView.value = "personal";
      noteMode.value = "view";
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
  if (suffix === "doc") return "application/msword";
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
  activeMistake.value = null;
  draft.editingId = note.id;
  draft.sourceNote = note;
  draft.title = note.title;
  draft.content = note.content_text || "";
  draft.tags = (note.tags || []).join(", ");
  draft.visibility = note.visibility;
  activeNote.value = note;
  activeView.value = "personal";
  noteMode.value = "edit";
}

function viewNote(note: Note): void {
  activeMistake.value = null;
  activeNote.value = note;
  activeView.value = "personal";
  noteMode.value = "view";
}

function backToNoteList(): void {
  activeMistake.value = null;
  activeView.value = "personal";
  noteMode.value = "list";
  resetDraft();
}

function openMistakeDetail(mistake: MistakeCard): void {
  activeMistake.value = mistake;
}

function closeMistakeDetail(): void {
  activeMistake.value = null;
}

function mistakeDetailHeading(mistake: MistakeCard): string {
  return mistake.subject || mistake.source || "错题详情";
}

function toggleQaSourceNote(note: Note): void {
  if (selectedQaSourceIds.value.includes(note.id)) {
    selectedQaSourceIds.value = selectedQaSourceIds.value.filter((id) => id !== note.id);
  } else {
    selectedQaSourceIds.value = [...selectedQaSourceIds.value, note.id];
  }
}

function jumpToAnswerSource(context: NoteAskContext): void {
  const note = notes.value.find((item) => item.id === context.source_id);
  if (note) viewNote(note);
}

function jumpToTaggedNotes(tag: string, target: "personal" | "shared" = "personal"): void {
  const value = tag.trim();
  if (!value) return;
  activeMistake.value = null;
  if (target === "shared") {
    sharedKeyword.value = value;
    activeView.value = "shared";
  } else {
    keyword.value = value;
    activeView.value = "personal";
    noteMode.value = "list";
    personalPage.value = 1;
    void guarded(loadCoursesAndNotes);
  }
  notify(`已按标签「${value}」筛选${target === "shared" ? "共享笔记" : "个人笔记"}`);
}

function startReaderResize(event: PointerEvent): void {
  readerResizeActive = true;
  (event.currentTarget as HTMLElement).setPointerCapture?.(event.pointerId);
  window.addEventListener("pointermove", resizeReaderPanels);
  window.addEventListener("pointerup", stopReaderResize);
}

function resizeReaderPanels(event: PointerEvent): void {
  if (!readerResizeActive) return;
  if (readerResizeFrame !== undefined) window.cancelAnimationFrame(readerResizeFrame);
  readerResizeFrame = window.requestAnimationFrame(() => {
    const grid = document.querySelector<HTMLElement>(".note-reader-grid");
    if (!grid) return;
    const rect = grid.getBoundingClientRect();
    const next = ((event.clientX - rect.left) / rect.width) * 100;
    readerSplitPercent.value = Math.min(72, Math.max(28, next));
  });
}

function stopReaderResize(): void {
  readerResizeActive = false;
  window.removeEventListener("pointermove", resizeReaderPanels);
  window.removeEventListener("pointerup", stopReaderResize);
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

async function askNotes(): Promise<void> {
  await guarded(async () => {
    const text = question.value.trim();
    if (!text) throw new Error("请先输入问题");
    if (askingQuestion.value) return;
    const userMessage: QaMessage = {
      id: `user-${Date.now()}`,
      role: "user",
      content: text
    };
    const assistantMessage: QaMessage = {
      id: `assistant-${Date.now()}`,
      role: "assistant",
      content: "正在检索笔记并生成回答...",
      contexts: [],
      pending: true
    };
    qaMessages.value = [...qaMessages.value, userMessage, assistantMessage];
    question.value = "";
    askingQuestion.value = true;
    answer.answer = "";
    answer.source = "";
    answer.contexts = [];
    try {
      const result = await api.askNotes({
        question: text,
        course_id: selectedQaSourceIds.value.length ? null : selectedCourseId.value,
        note_ids: selectedQaSourceIds.value,
        limit: 6
      });
      answer.answer = result.answer || "没有检索到可用于回答的笔记内容。";
      answer.source = result.source;
      answer.contexts = result.contexts;
      assistantMessage.content = answer.answer;
      assistantMessage.source = answer.source;
      assistantMessage.contexts = answer.contexts;
      assistantMessage.pending = false;
      qaMessages.value = [...qaMessages.value];
      if (!result.contexts.length) notify("没有检索到相关笔记");
    } finally {
      if (assistantMessage.pending) {
        assistantMessage.content = "这次请求没有完成，请稍后重试。";
        assistantMessage.pending = false;
        qaMessages.value = [...qaMessages.value];
      }
      askingQuestion.value = false;
    }
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

function renderMarkdown(value: string): string {
  if (!value.trim()) return '<p class="preview-empty">Markdown 预览</p>';
  return markdownRenderer.render(value);
}

function jumpToMarkdownContent(payload: { title: string; summary: string; data: string }): void {
  const container = document.querySelector<HTMLElement>(".document-preview");
  if (!container) return;
  const target = findMarkdownTarget(container, payload);
  if (!target) {
    notify("没有在 Markdown 中找到对应位置");
    return;
  }
  target.scrollIntoView({ behavior: "smooth", block: "start" });
  target.classList.remove("markdown-jump-highlight");
  window.setTimeout(() => {
    target.classList.add("markdown-jump-highlight");
    window.setTimeout(() => target.classList.remove("markdown-jump-highlight"), 1600);
  }, 80);
}

function findMarkdownTarget(container: HTMLElement, payload: { title: string; summary: string; data: string }): HTMLElement | null {
  const title = normalizeSearchText(payload.title.replace(/\s*\(\d+\)\s*$/, ""));
  const headingCandidates = [...container.querySelectorAll<HTMLElement>("h1, h2, h3, h4, h5, h6")];
  if (title) {
    const exact = headingCandidates.find((item) => normalizeSearchText(item.textContent || "") === title);
    if (exact) return exact;
    const partial = headingCandidates.find((item) => {
      const text = normalizeSearchText(item.textContent || "");
      return text.includes(title) || title.includes(text);
    });
    if (partial) return partial;
  }

  const dataNeedle = normalizeSearchText(payload.data).slice(0, 80);
  const summaryNeedles = payload.summary
    .split(/[;；,，]/)
    .map((item) => normalizeSearchText(item))
    .filter((item) => item.length >= 2)
    .slice(0, 5);
  const contentCandidates = [...container.querySelectorAll<HTMLElement>("p, li, blockquote, td, pre")];
  if (dataNeedle) {
    const byData = contentCandidates.find((item) => normalizeSearchText(item.textContent || "").includes(dataNeedle));
    if (byData) return byData;
  }
  if (summaryNeedles.length) {
    const bySummary = contentCandidates.find((item) => {
      const text = normalizeSearchText(item.textContent || "");
      return summaryNeedles.some((needle) => text.includes(needle));
    });
    if (bySummary) return bySummary;
  }
  return null;
}

function normalizeSearchText(value: string): string {
  return value.replace(/\s+/g, " ").trim().toLowerCase();
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

onUnmounted(() => {
  stopReaderResize();
  if (readerResizeFrame !== undefined) window.cancelAnimationFrame(readerResizeFrame);
});
</script>
