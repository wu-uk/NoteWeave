const API_BASE = localStorage.getItem("noteweave_api_base") || "http://127.0.0.1:8000";
const TOKEN_KEY = "noteweave_token";

const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  user: null,
  courses: [],
  currentCourse: null,
  tree: null,
  selectedNode: null,
  notes: [],
  mistakes: [],
  suggestions: [],
  activeView: "overview"
};

const $ = (id) => document.getElementById(id);

const refs = {
  apiBaseLabel: $("api-base-label"),
  authForm: $("auth-form"),
  userBar: $("user-bar"),
  currentUserName: $("current-user-name"),
  currentUserRole: $("current-user-role"),
  loginButton: $("login-button"),
  registerButton: $("register-button"),
  logoutButton: $("logout-button"),
  courseList: $("course-list"),
  courseTitle: $("course-title"),
  courseRole: $("course-role"),
  createCourseButton: $("create-course-button"),
  joinCourseButton: $("join-course-button"),
  tabs: $("tabs"),
  knowledgeTree: $("knowledge-tree"),
  treeMeta: $("tree-meta"),
  selectedNodePath: $("selected-node-path"),
  nodeSummary: $("node-summary"),
  nodeForm: $("node-form"),
  noteForm: $("note-form"),
  noteList: $("note-list"),
  noteCount: $("note-count"),
  mistakeForm: $("mistake-form"),
  mistakeList: $("mistake-list"),
  mistakeCount: $("mistake-count"),
  searchForm: $("search-form"),
  searchResults: $("search-results"),
  sharedNoteList: $("shared-note-list"),
  suggestionForm: $("suggestion-form"),
  suggestionList: $("suggestion-list"),
  toast: $("toast")
};

refs.apiBaseLabel.textContent = API_BASE;

function authHeaders() {
  return state.token ? { Authorization: `Bearer ${state.token}` } : {};
}

async function api(path, options = {}) {
  const headers = {
    "Content-Type": "application/json",
    ...authHeaders(),
    ...(options.headers || {})
  };
  const response = await fetch(`${API_BASE}${path}`, {
    ...options,
    headers
  });
  const text = await response.text();
  const data = text ? JSON.parse(text) : null;
  if (!response.ok) {
    const detail = data && data.detail ? data.detail : `HTTP ${response.status}`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  return data;
}

function showToast(message) {
  refs.toast.textContent = message;
  refs.toast.classList.remove("hidden");
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => refs.toast.classList.add("hidden"), 2800);
}

function tagsFromInput(value) {
  return value
    .split(/[，,]/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function text(value) {
  return value === null || value === undefined || value === "" ? "未设置" : String(value);
}

function formatTags(tags, tone = "") {
  if (!tags || tags.length === 0) return "";
  return `<div class="tag-row">${tags
    .map((tag) => `<span class="tag ${tone}">${escapeHtml(tag)}</span>`)
    .join("")}</div>`;
}

function escapeHtml(value) {
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function setToken(token) {
  state.token = token || "";
  if (state.token) {
    localStorage.setItem(TOKEN_KEY, state.token);
  } else {
    localStorage.removeItem(TOKEN_KEY);
  }
}

function requireCourse() {
  if (!state.currentCourse) {
    showToast("请先选择课程");
    return false;
  }
  return true;
}

function currentNodeId() {
  return state.selectedNode ? state.selectedNode.id : null;
}

async function boot() {
  bindEvents();
  renderAuth();
  if (state.token) {
    try {
      state.user = await api("/api/auth/me");
      await loadCourses();
    } catch (error) {
      setToken("");
      state.user = null;
      showToast(`登录状态失效：${error.message}`);
    }
  }
  render();
}

function bindEvents() {
  refs.loginButton.addEventListener("click", () => submitAuth("login"));
  refs.registerButton.addEventListener("click", () => submitAuth("register"));
  refs.logoutButton.addEventListener("click", logout);
  refs.createCourseButton.addEventListener("click", createCourse);
  refs.joinCourseButton.addEventListener("click", joinCourse);
  refs.tabs.addEventListener("click", onTabClick);
  $("refresh-tree-button").addEventListener("click", loadTree);
  $("refresh-notes-button").addEventListener("click", loadNotes);
  $("refresh-mistakes-button").addEventListener("click", loadMistakes);
  $("mistake-filter-tag").addEventListener("input", renderMistakes);
  $("mistake-filter-mastery").addEventListener("change", renderMistakes);
  refs.nodeForm.addEventListener("submit", createNode);
  refs.noteForm.addEventListener("submit", createNote);
  refs.mistakeForm.addEventListener("submit", createMistake);
  refs.searchForm.addEventListener("submit", search);
  refs.suggestionForm.addEventListener("submit", createSuggestion);
}

async function submitAuth(mode) {
  const username = $("auth-username").value.trim();
  const password = $("auth-password").value;
  const displayName = $("auth-display-name").value.trim();
  if (!username || !password) {
    showToast("请填写用户名和密码");
    return;
  }

  try {
    const payload =
      mode === "register"
        ? { username, password, display_name: displayName || username }
        : { username, password };
    const data = await api(`/api/auth/${mode === "register" ? "register" : "login"}`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    setToken(data.token);
    state.user = data.user;
    await loadCourses();
    showToast(mode === "register" ? "注册成功" : "登录成功");
  } catch (error) {
    showToast(error.message);
  }
  render();
}

async function logout() {
  try {
    if (state.token) await api("/api/auth/logout", { method: "POST" });
  } catch {
    /* local logout still applies */
  }
  setToken("");
  state.user = null;
  state.courses = [];
  state.currentCourse = null;
  state.tree = null;
  state.selectedNode = null;
  state.notes = [];
  state.mistakes = [];
  render();
}

async function loadCourses() {
  state.courses = await api("/api/courses");
  if (!state.currentCourse && state.courses.length > 0) {
    state.currentCourse = state.courses[0];
  } else if (state.currentCourse) {
    state.currentCourse =
      state.courses.find((course) => course.id === state.currentCourse.id) || state.courses[0] || null;
  }
  if (state.currentCourse) {
    await Promise.all([loadTree(), loadNotes(), loadMistakes(), loadSuggestions()]);
  }
}

async function createCourse() {
  if (!state.token) {
    showToast("请先登录");
    return;
  }
  const name = $("course-name").value.trim();
  if (!name) {
    showToast("课程名称不能为空");
    return;
  }
  try {
    const course = await api("/api/courses", {
      method: "POST",
      body: JSON.stringify({
        name,
        semester: $("course-semester").value.trim(),
        description: "",
        tags: []
      })
    });
    $("course-name").value = "";
    $("course-semester").value = "";
    await loadCourses();
    state.currentCourse = state.courses.find((item) => item.id === course.id) || course;
    await Promise.all([loadTree(), loadNotes(), loadMistakes(), loadSuggestions()]);
    showToast("课程已创建");
  } catch (error) {
    showToast(error.message);
  }
  render();
}

async function joinCourse() {
  if (!state.token) {
    showToast("请先登录");
    return;
  }
  const inviteCode = $("invite-code").value.trim();
  if (!inviteCode) {
    showToast("请填写邀请码");
    return;
  }
  try {
    const joined = await api("/api/courses/join", {
      method: "POST",
      body: JSON.stringify({ invite_code: inviteCode })
    });
    $("invite-code").value = "";
    await loadCourses();
    state.currentCourse = state.courses.find((course) => course.id === joined.id) || joined;
    await Promise.all([loadTree(), loadNotes(), loadMistakes(), loadSuggestions()]);
    showToast("已加入课程");
  } catch (error) {
    showToast(error.message);
  }
  render();
}

async function selectCourse(courseId) {
  state.currentCourse = state.courses.find((course) => course.id === courseId) || null;
  state.selectedNode = null;
  await Promise.all([loadTree(), loadNotes(), loadMistakes(), loadSuggestions()]);
  render();
}

async function loadTree() {
  if (!state.currentCourse) return;
  try {
    state.tree = await api(`/api/courses/${state.currentCourse.id}/tree`);
    if (!state.selectedNode && state.tree.tree) {
      state.selectedNode = state.tree.tree;
    } else if (state.selectedNode) {
      state.selectedNode = state.tree.nodes.find((node) => node.id === state.selectedNode.id) || state.tree.tree;
    }
  } catch (error) {
    showToast(error.message);
  }
  renderTree();
  renderSelectedNode();
}

async function createNode(event) {
  event.preventDefault();
  if (!requireCourse()) return;
  const title = $("node-title").value.trim();
  if (!title) {
    showToast("节点标题不能为空");
    return;
  }
  try {
    const parentId = currentNodeId();
    await api(`/api/courses/${state.currentCourse.id}/tree/nodes`, {
      method: "POST",
      body: JSON.stringify({
        parent_id: parentId,
        type: $("node-type").value,
        title,
        description: $("node-description").value.trim()
      })
    });
    $("node-title").value = "";
    $("node-description").value = "";
    await loadTree();
    showToast("节点已新增");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadNotes() {
  if (!state.currentCourse) return;
  try {
    state.notes = await api(`/api/notes?course_id=${state.currentCourse.id}`);
  } catch (error) {
    showToast(error.message);
  }
  renderNotes();
  renderSharedNotes();
}

async function createNote(event) {
  event.preventDefault();
  if (!requireCourse()) return;
  const title = $("note-title").value.trim();
  const content = $("note-content").value.trim();
  if (!title || !content) {
    showToast("请填写标题和正文");
    return;
  }
  try {
    await api("/api/notes", {
      method: "POST",
      body: JSON.stringify({
        course_id: state.currentCourse.id,
        node_id: currentNodeId(),
        title,
        content_json: { type: "plain_text", text: content },
        content_text: content,
        content_format: "markdown",
        visibility: $("note-visibility").value,
        status: $("note-status").value,
        tags: tagsFromInput($("note-tags").value)
      })
    });
    refs.noteForm.reset();
    await Promise.all([loadNotes(), loadTree()]);
    showToast("笔记已保存");
  } catch (error) {
    showToast(error.message);
  }
}

async function publishNote(noteId) {
  try {
    await api(`/api/notes/${noteId}/publish`, { method: "POST" });
    await loadNotes();
    showToast("笔记已发布");
  } catch (error) {
    showToast(error.message);
  }
}

async function likeNote(noteId) {
  try {
    await api("/api/reactions", {
      method: "POST",
      body: JSON.stringify({ target_type: "note", target_id: noteId, reaction_type: "like" })
    });
    await loadNotes();
    showToast("已点赞");
  } catch (error) {
    showToast(error.message);
  }
}

async function commentNote(noteId) {
  const content = window.prompt("评论内容");
  if (!content) return;
  try {
    await api("/api/comments", {
      method: "POST",
      body: JSON.stringify({ target_type: "note", target_id: noteId, content })
    });
    await loadNotes();
    showToast("评论已发布");
  } catch (error) {
    showToast(error.message);
  }
}

async function runAi(noteId, type) {
  try {
    const result = await api(`/api/ai/notes/${noteId}/${type}`, { method: "POST" });
    await api(`/api/ai/results/${result.id}/accept`, { method: "POST" });
    await loadNotes();
    showToast(type === "summary" ? "摘要已采纳" : "标签已采纳");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadMistakes() {
  if (!state.currentCourse) return;
  try {
    state.mistakes = await api(`/api/mistakes?course_id=${state.currentCourse.id}`);
  } catch (error) {
    showToast(error.message);
  }
  renderMistakes();
}

async function createMistake(event) {
  event.preventDefault();
  if (!requireCourse()) return;
  const question = $("mistake-question").value.trim();
  if (!question) {
    showToast("题目内容不能为空");
    return;
  }
  try {
    await api("/api/mistakes", {
      method: "POST",
      body: JSON.stringify({
        course_id: state.currentCourse.id,
        node_id: currentNodeId(),
        question_content: question,
        correct_answer: $("mistake-correct").value.trim(),
        wrong_answer: $("mistake-wrong").value.trim(),
        error_reason: $("mistake-reason").value.trim(),
        solution: $("mistake-solution").value.trim(),
        reflection: "",
        question_type: $("mistake-type").value.trim(),
        mastery_status: $("mistake-mastery").value,
        tags: tagsFromInput($("mistake-tags").value),
        visibility: "shared"
      })
    });
    refs.mistakeForm.reset();
    await Promise.all([loadMistakes(), loadTree()]);
    showToast("错题已保存");
  } catch (error) {
    showToast(error.message);
  }
}

async function updateMastery(mistakeId, masteryStatus) {
  try {
    await api(`/api/mistakes/${mistakeId}/mastery`, {
      method: "PATCH",
      body: JSON.stringify({ mastery_status: masteryStatus })
    });
    await loadMistakes();
    showToast("复习状态已更新");
  } catch (error) {
    showToast(error.message);
  }
}

async function search(event) {
  event.preventDefault();
  if (!requireCourse()) return;
  const q = $("search-query").value.trim();
  if (!q) {
    showToast("请输入关键词");
    return;
  }
  const params = new URLSearchParams({
    course_id: state.currentCourse.id,
    q
  });
  const tag = $("search-tag").value.trim();
  const sourceType = $("search-type").value;
  if (tag) params.set("tag", tag);
  if (sourceType) params.set("source_type", sourceType);
  try {
    const results = await api(`/api/search?${params.toString()}`);
    renderSearchResults(results);
    await loadTree();
  } catch (error) {
    showToast(error.message);
  }
}

async function createSuggestion(event) {
  event.preventDefault();
  if (!requireCourse()) return;
  const targetType = $("suggestion-target-type").value;
  const targetId = Number($("suggestion-target-id").value);
  const content = $("suggestion-content").value.trim();
  if (!targetId || !content) {
    showToast("请填写目标 ID 和建议内容");
    return;
  }
  try {
    const suggestion = await api("/api/suggestions", {
      method: "POST",
      body: JSON.stringify({
        target_type: targetType,
        target_id: targetId,
        type: $("suggestion-type").value,
        content
      })
    });
    refs.suggestionForm.reset();
    await loadSuggestions();
    showToast("建议已提交");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadSuggestions() {
  if (!state.currentCourse) return;
  try {
    state.suggestions = await api(`/api/courses/${state.currentCourse.id}/suggestions`);
  } catch (error) {
    showToast(error.message);
  }
  renderSuggestions();
}

async function handleSuggestion(id, status) {
  try {
    await api(`/api/suggestions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ status })
    });
    await loadSuggestions();
    showToast("建议状态已更新");
  } catch (error) {
    showToast(error.message);
  }
}

function onTabClick(event) {
  const button = event.target.closest("button[data-view]");
  if (!button) return;
  state.activeView = button.dataset.view;
  renderTabs();
}

function render() {
  renderAuth();
  renderCourses();
  renderCourseHeader();
  renderTabs();
  renderTree();
  renderSelectedNode();
  renderNotes();
  renderSharedNotes();
  renderMistakes();
  renderSuggestions();
}

function renderAuth() {
  if (state.user) {
    refs.authForm.classList.add("hidden");
    refs.userBar.classList.remove("hidden");
    refs.currentUserName.textContent = state.user.display_name || state.user.username;
    refs.currentUserRole.textContent = state.user.system_role;
  } else {
    refs.authForm.classList.remove("hidden");
    refs.userBar.classList.add("hidden");
  }
}

function renderCourses() {
  if (!state.user) {
    refs.courseList.innerHTML = `<div class="meta">登录后显示课程</div>`;
    return;
  }
  if (state.courses.length === 0) {
    refs.courseList.innerHTML = `<div class="meta">暂无课程</div>`;
    return;
  }
  refs.courseList.innerHTML = state.courses
    .map(
      (course) => `
        <div class="course-row ${state.currentCourse && state.currentCourse.id === course.id ? "active" : ""}" data-course-id="${course.id}">
          <strong>${escapeHtml(course.name)}</strong>
          <span>${escapeHtml(course.semester || "未设置学期")} · ${escapeHtml(course.role || "")}</span>
          <span>邀请码 ${escapeHtml(course.invite_code)}</span>
        </div>
      `
    )
    .join("");
  refs.courseList.querySelectorAll("[data-course-id]").forEach((row) => {
    row.addEventListener("click", () => selectCourse(Number(row.dataset.courseId)));
  });
}

function renderCourseHeader() {
  if (!state.currentCourse) {
    refs.courseTitle.textContent = "课程工作台";
    refs.courseRole.textContent = "未选择课程";
    return;
  }
  refs.courseTitle.textContent = state.currentCourse.name;
  refs.courseRole.textContent = `${state.currentCourse.semester || "未设置学期"} · ${state.currentCourse.role || "成员"}`;
}

function renderTabs() {
  refs.tabs.querySelectorAll("button[data-view]").forEach((button) => {
    button.classList.toggle("active", button.dataset.view === state.activeView);
  });
  document.querySelectorAll(".view").forEach((view) => {
    view.classList.toggle("active", view.id === `view-${state.activeView}`);
  });
}

function renderTree() {
  if (!state.currentCourse) {
    refs.treeMeta.textContent = "选择课程后加载章节和知识点";
    refs.knowledgeTree.innerHTML = `<div class="meta">暂无课程</div>`;
    return;
  }
  if (!state.tree || !state.tree.tree) {
    refs.treeMeta.textContent = "暂无知识树";
    refs.knowledgeTree.innerHTML = `<div class="meta">暂无节点</div>`;
    return;
  }
  refs.treeMeta.textContent = `${state.tree.nodes.length - 1} 个章节/知识点`;
  refs.knowledgeTree.innerHTML = renderTreeNode(state.tree.tree);
  refs.knowledgeTree.querySelectorAll("[data-node-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedNode = state.tree.nodes.find((node) => node.id === Number(button.dataset.nodeId));
      renderTree();
      renderSelectedNode();
    });
  });
}

function renderTreeNode(node) {
  const isActive = state.selectedNode && state.selectedNode.id === node.id;
  const children = node.children || [];
  return `
    <ul>
      <li>
        <button class="${isActive ? "active" : ""}" data-node-id="${node.id}">
          <span>${escapeHtml(node.title)}</span>
          <span class="node-pill">${node.type === "course_root" ? "课程" : node.type === "chapter" ? "章节" : "知识点"} · ${node.note_count || 0}/${node.mistake_count || 0}</span>
        </button>
        ${children.map(renderTreeNode).join("")}
      </li>
    </ul>
  `;
}

function renderSelectedNode() {
  const node = state.selectedNode;
  if (!node) {
    refs.selectedNodePath.textContent = "未选择节点";
    refs.nodeSummary.innerHTML = "";
    $("suggestion-target-id").value = "";
    return;
  }
  refs.selectedNodePath.textContent = node.path;
  refs.nodeSummary.innerHTML = `
    <div class="metric"><strong>${node.note_count || 0}</strong><span>笔记</span></div>
    <div class="metric"><strong>${node.mistake_count || 0}</strong><span>错题</span></div>
    <div class="metric"><strong>${node.impact || 0}</strong><span>热度</span></div>
  `;
  if ($("suggestion-target-type").value === "knowledge_node") {
    $("suggestion-target-id").value = node.id;
  }
}

function renderNotes() {
  const notes = state.notes || [];
  refs.noteCount.textContent = `${notes.length} 条`;
  if (!state.currentCourse) {
    refs.noteList.innerHTML = `<div class="meta">选择课程后显示笔记</div>`;
    return;
  }
  if (notes.length === 0) {
    refs.noteList.innerHTML = `<div class="meta">暂无笔记</div>`;
    return;
  }
  refs.noteList.innerHTML = notes.map(renderNoteItem).join("");
  bindNoteActions(refs.noteList);
}

function renderSharedNotes() {
  const notes = (state.notes || []).filter((note) => note.visibility === "shared");
  if (!state.currentCourse) {
    refs.sharedNoteList.innerHTML = `<div class="meta">选择课程后显示共享笔记</div>`;
    return;
  }
  if (notes.length === 0) {
    refs.sharedNoteList.innerHTML = `<div class="meta">暂无共享笔记</div>`;
    return;
  }
  refs.sharedNoteList.innerHTML = notes.map(renderNoteItem).join("");
  bindNoteActions(refs.sharedNoteList);
}

function renderNoteItem(note) {
  return `
    <article class="item" data-note-id="${note.id}">
      <strong class="item-title">#${note.id} ${escapeHtml(note.title)}</strong>
      <div class="item-meta">${escapeHtml(note.node_path || "未归档")} · ${escapeHtml(note.visibility)} · ${escapeHtml(note.status)} · ${note.like_count} 赞 · ${note.comment_count} 评</div>
      ${formatTags(note.tags, "green")}
      ${note.summary ? `<div class="item-body">${escapeHtml(note.summary)}</div>` : `<div class="item-body">${escapeHtml(note.content_text.slice(0, 180))}</div>`}
      <div class="item-actions">
        <button class="secondary" data-action="publish">发布</button>
        <button class="secondary" data-action="like">点赞</button>
        <button class="secondary" data-action="comment">评论</button>
        <button class="secondary" data-action="summary">AI 摘要</button>
        <button class="secondary" data-action="tags">AI 标签</button>
        <button class="text" data-action="suggest-target">设为建议目标</button>
      </div>
    </article>
  `;
}

function bindNoteActions(container) {
  container.querySelectorAll("[data-note-id]").forEach((item) => {
    const noteId = Number(item.dataset.noteId);
    item.querySelectorAll("[data-action]").forEach((button) => {
      button.addEventListener("click", () => {
        const action = button.dataset.action;
        if (action === "publish") publishNote(noteId);
        if (action === "like") likeNote(noteId);
        if (action === "comment") commentNote(noteId);
        if (action === "summary") runAi(noteId, "summary");
        if (action === "tags") runAi(noteId, "tags");
        if (action === "suggest-target") {
          $("suggestion-target-type").value = "note";
          $("suggestion-target-id").value = noteId;
          state.activeView = "collab";
          renderTabs();
        }
      });
    });
  });
}

function renderMistakes() {
  const tagFilter = $("mistake-filter-tag").value.trim();
  const masteryFilter = $("mistake-filter-mastery").value;
  let mistakes = state.mistakes || [];
  if (tagFilter) {
    mistakes = mistakes.filter((mistake) => (mistake.tags || []).includes(tagFilter));
  }
  if (masteryFilter) {
    mistakes = mistakes.filter((mistake) => mistake.mastery_status === masteryFilter);
  }
  refs.mistakeCount.textContent = `${mistakes.length} 条`;
  if (!state.currentCourse) {
    refs.mistakeList.innerHTML = `<div class="meta">选择课程后显示错题</div>`;
    return;
  }
  if (mistakes.length === 0) {
    refs.mistakeList.innerHTML = `<div class="meta">暂无错题</div>`;
    return;
  }
  refs.mistakeList.innerHTML = mistakes
    .map(
      (mistake) => `
        <article class="item" data-mistake-id="${mistake.id}">
          <strong class="item-title">#${mistake.id} ${escapeHtml(mistake.question_content)}</strong>
          <div class="item-meta">${escapeHtml(mistake.node_path || "未归档")} · ${escapeHtml(mistake.question_type || "未分类")} · ${escapeHtml(mistake.mastery_status)}</div>
          ${formatTags(mistake.tags, "amber")}
          <div class="item-body">正确答案：${escapeHtml(text(mistake.correct_answer))}\n错误原因：${escapeHtml(text(mistake.error_reason))}</div>
          <div class="item-actions">
            <button class="secondary" data-status="todo">待复习</button>
            <button class="secondary" data-status="retry">需再练</button>
            <button class="secondary" data-status="mastered">已掌握</button>
          </div>
        </article>
      `
    )
    .join("");
  refs.mistakeList.querySelectorAll("[data-mistake-id]").forEach((item) => {
    const id = Number(item.dataset.mistakeId);
    item.querySelectorAll("[data-status]").forEach((button) => {
      button.addEventListener("click", () => updateMastery(id, button.dataset.status));
    });
  });
}

function renderSearchResults(results = []) {
  if (results.length === 0) {
    refs.searchResults.innerHTML = `<div class="meta">没有匹配结果</div>`;
    return;
  }
  refs.searchResults.innerHTML = results
    .map(
      (item) => `
        <article class="item">
          <strong class="item-title">${escapeHtml(item.source_type)} #${item.source_id} · ${escapeHtml(item.title)}</strong>
          <div class="item-meta">${escapeHtml(item.node_path || "未归档")} · 匹配 ${escapeHtml(item.matched_fields.join(", "))} · 分数 ${item.score}</div>
          <div class="item-body">${escapeHtml(item.snippet)}</div>
        </article>
      `
    )
    .join("");
}

function renderSuggestions() {
  if (state.suggestions.length === 0) {
    refs.suggestionList.innerHTML = `<div class="meta">暂无建议</div>`;
    return;
  }
  refs.suggestionList.innerHTML = state.suggestions
    .map(
      (suggestion) => `
        <article class="item" data-suggestion-id="${suggestion.id}">
          <strong class="item-title">#${suggestion.id} ${escapeHtml(suggestion.type)} · ${escapeHtml(suggestion.status)}</strong>
          <div class="item-meta">${escapeHtml(suggestion.target_type)} #${suggestion.target_id} · ${escapeHtml(suggestion.target_title || "未命名目标")}</div>
          <div class="item-body">${escapeHtml(suggestion.content)}</div>
          <div class="item-actions">
            <button class="secondary" data-status="accepted">采纳</button>
            <button class="secondary" data-status="discussed">讨论</button>
            <button class="danger" data-status="rejected">拒绝</button>
          </div>
        </article>
      `
    )
    .join("");
  refs.suggestionList.querySelectorAll("[data-suggestion-id]").forEach((item) => {
    const id = Number(item.dataset.suggestionId);
    item.querySelectorAll("[data-status]").forEach((button) => {
      button.addEventListener("click", () => handleSuggestion(id, button.dataset.status));
    });
  });
}

boot();
