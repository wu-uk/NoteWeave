const API_BASE = localStorage.getItem("noteweave_api_base") || "http://127.0.0.1:8000";
const TOKEN_KEY = "noteweave_token";
const PAGE_SIZE = 10;

const state = {
  token: localStorage.getItem(TOKEN_KEY) || "",
  user: null,
  courses: [],
  currentCourse: null,
  tree: null,
  selectedNode: null,
  expandedNodeIds: new Set(),
  nodeDetail: null,
  notes: [],
  sharedNotes: [],
  mistakes: [],
  suggestions: [],
  members: [],
  auditLogs: [],
  aiStatus: null,
  reviewItems: [],
  paging: {
    notesHasMore: false,
    sharedNotesHasMore: false,
    mistakesHasMore: false,
    reviewHasMore: false
  },
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
  editProfileButton: $("edit-profile-button"),
  changePasswordButton: $("change-password-button"),
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
  reviewForm: $("review-form"),
  reviewList: $("review-list"),
  searchForm: $("search-form"),
  searchResults: $("search-results"),
  sharedNoteList: $("shared-note-list"),
  suggestionForm: $("suggestion-form"),
  suggestionList: $("suggestion-list"),
  courseSettingsForm: $("course-settings-form"),
  memberList: $("member-list"),
  aiStatusPanel: $("ai-status-panel"),
  auditLogList: $("audit-log-list"),
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

function renderMarkdown(value) {
  return window.NoteWeaveRender
    ? window.NoteWeaveRender.renderMarkdown(value)
    : escapeHtml(value).replace(/\n/g, "<br />");
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

function resetPaging() {
  state.paging = {
    notesHasMore: false,
    sharedNotesHasMore: false,
    mistakesHasMore: false,
    reviewHasMore: false
  };
}

async function boot() {
  bindEvents();
  renderAuth();
  if (state.token) {
    try {
      state.user = await api("/api/auth/me");
      await loadAiStatus();
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
  refs.editProfileButton.addEventListener("click", editProfile);
  refs.changePasswordButton.addEventListener("click", changePassword);
  refs.logoutButton.addEventListener("click", logout);
  refs.createCourseButton.addEventListener("click", createCourse);
  refs.joinCourseButton.addEventListener("click", joinCourse);
  refs.tabs.addEventListener("click", onTabClick);
  $("refresh-tree-button").addEventListener("click", loadTree);
  $("tree-search").addEventListener("input", renderTree);
  $("expand-tree-button").addEventListener("click", expandTree);
  $("collapse-tree-button").addEventListener("click", collapseTree);
  $("refresh-notes-button").addEventListener("click", () => loadNotes());
  $("load-more-notes-button").addEventListener("click", () => loadNotes(true));
  $("refresh-shared-notes-button").addEventListener("click", () => loadSharedNotes());
  $("load-more-shared-notes-button").addEventListener("click", () => loadSharedNotes(true));
  $("shared-note-sort").addEventListener("change", () => loadSharedNotes());
  $("refresh-mistakes-button").addEventListener("click", () => loadMistakes());
  $("load-more-mistakes-button").addEventListener("click", () => loadMistakes(true));
  $("refresh-review-button").addEventListener("click", () => loadReview());
  $("load-more-review-button").addEventListener("click", () => loadReview(true));
  $("mistake-filter-tag").addEventListener("input", renderMistakes);
  $("mistake-filter-mastery").addEventListener("change", renderMistakes);
  $("note-image-button").addEventListener("click", () => uploadImage("note"));
  $("mistake-image-button").addEventListener("click", () => uploadImage("mistake"));
  refs.nodeForm.addEventListener("submit", createNode);
  refs.noteForm.addEventListener("submit", createNote);
  refs.mistakeForm.addEventListener("submit", createMistake);
  refs.reviewForm.addEventListener("submit", (event) => {
    event.preventDefault();
    loadReview();
  });
  refs.searchForm.addEventListener("submit", search);
  refs.suggestionForm.addEventListener("submit", createSuggestion);
  refs.courseSettingsForm.addEventListener("submit", updateCourseSettings);
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
    await loadAiStatus();
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
  state.expandedNodeIds = new Set();
  state.nodeDetail = null;
  state.notes = [];
  state.sharedNotes = [];
  state.mistakes = [];
  state.suggestions = [];
  state.members = [];
  state.auditLogs = [];
  state.aiStatus = null;
  state.reviewItems = [];
  resetPaging();
  render();
}

async function loadAiStatus() {
  if (!state.token) return;
  try {
    state.aiStatus = await api("/api/ai/config/status");
  } catch {
    state.aiStatus = null;
  }
  renderSettings();
}

async function editProfile() {
  if (!state.user) return;
  const displayName = window.prompt("新的昵称", state.user.display_name || state.user.username);
  if (displayName === null) return;
  const trimmed = displayName.trim();
  if (!trimmed) {
    showToast("昵称不能为空");
    return;
  }
  try {
    state.user = await api("/api/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ display_name: trimmed })
    });
    renderAuth();
    showToast("昵称已更新");
  } catch (error) {
    showToast(error.message);
  }
}

async function changePassword() {
  if (!state.user) return;
  const currentPassword = window.prompt("当前密码");
  if (currentPassword === null) return;
  const newPassword = window.prompt("新密码，至少 6 位");
  if (newPassword === null) return;
  if (newPassword.length < 6) {
    showToast("新密码至少 6 位");
    return;
  }
  try {
    await api("/api/auth/me", {
      method: "PATCH",
      body: JSON.stringify({ current_password: currentPassword, new_password: newPassword })
    });
    showToast("密码已更新");
  } catch (error) {
    showToast(error.message);
  }
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
    await Promise.all([loadTree(), loadNotes(), loadSharedNotes(), loadMistakes(), loadSuggestions(), loadMembers(), loadAuditLogs(), loadReview()]);
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
    await Promise.all([loadTree(), loadNotes(), loadSharedNotes(), loadMistakes(), loadSuggestions(), loadMembers(), loadAuditLogs(), loadReview()]);
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
    await Promise.all([loadTree(), loadNotes(), loadSharedNotes(), loadMistakes(), loadSuggestions(), loadMembers(), loadAuditLogs(), loadReview()]);
    showToast("已加入课程");
  } catch (error) {
    showToast(error.message);
  }
  render();
}

async function selectCourse(courseId) {
  state.currentCourse = state.courses.find((course) => course.id === courseId) || null;
  state.selectedNode = null;
  state.expandedNodeIds = new Set();
  state.nodeDetail = null;
  await Promise.all([loadTree(), loadNotes(), loadSharedNotes(), loadMistakes(), loadSuggestions(), loadMembers(), loadAuditLogs(), loadReview()]);
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
    if (state.tree.tree) {
      state.expandedNodeIds.add(state.tree.tree.id);
    }
  } catch (error) {
    showToast(error.message);
  }
  renderTree();
  renderSelectedNode();
  await loadSelectedNodeDetail();
}

async function loadMembers() {
  if (!state.currentCourse) return;
  try {
    state.members = await api(`/api/courses/${state.currentCourse.id}/members`);
  } catch (error) {
    state.members = [];
    showToast(error.message);
  }
  renderSettings();
}

async function loadAuditLogs() {
  if (!state.currentCourse) return;
  try {
    state.auditLogs = await api(`/api/courses/${state.currentCourse.id}/audit-logs?limit=20`);
  } catch {
    state.auditLogs = [];
  }
  renderSettings();
}

async function updateCourseSettings(event) {
  event.preventDefault();
  if (!requireCourse()) return;
  const name = $("settings-course-name").value.trim();
  if (!name) {
    showToast("课程名称不能为空");
    return;
  }
  try {
    const updated = await api(`/api/courses/${state.currentCourse.id}`, {
      method: "PATCH",
      body: JSON.stringify({
        name,
        semester: $("settings-course-semester").value.trim(),
        description: $("settings-course-description").value.trim(),
        tags: tagsFromInput($("settings-course-tags").value)
      })
    });
    state.currentCourse = updated;
    await Promise.all([loadCourses(), loadTree(), loadAuditLogs()]);
    render();
    showToast("课程信息已更新");
  } catch (error) {
    showToast(error.message);
  }
}

async function updateMemberRole(memberId, role) {
  if (!requireCourse()) return;
  try {
    await api(`/api/courses/${state.currentCourse.id}/members/${memberId}`, {
      method: "PATCH",
      body: JSON.stringify({ role })
    });
    await Promise.all([loadCourses(), loadMembers(), loadAuditLogs()]);
    showToast("成员角色已更新");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadReview(append = false) {
  if (!state.currentCourse) return;
  const params = new URLSearchParams({
    mode: $("review-mode").value,
    limit: PAGE_SIZE,
    offset: append ? state.reviewItems.length : 0
  });
  const tag = $("review-tag").value.trim();
  const questionType = $("review-question-type").value.trim();
  if (tag) params.set("tag", tag);
  if (questionType) params.set("question_type", questionType);
  if ($("review-current-node").checked) {
    if (!state.selectedNode) {
      showToast("请先选择知识树节点");
      return;
    }
    params.set("node_id", state.selectedNode.id);
  }
  try {
    const rows = await api(`/api/courses/${state.currentCourse.id}/review?${params.toString()}`);
    state.reviewItems = append ? [...state.reviewItems, ...rows] : rows;
    state.paging.reviewHasMore = rows.length === PAGE_SIZE;
  } catch (error) {
    if (!append) state.reviewItems = [];
    state.paging.reviewHasMore = false;
    showToast(error.message);
  }
  renderReview();
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

async function loadNotes(append = false) {
  if (!state.currentCourse) return;
  const offset = append ? state.notes.length : 0;
  try {
    const rows = await api(`/api/notes?course_id=${state.currentCourse.id}&limit=${PAGE_SIZE}&offset=${offset}`);
    state.notes = append ? [...state.notes, ...rows] : rows;
    state.paging.notesHasMore = rows.length === PAGE_SIZE;
  } catch (error) {
    if (!append) state.notes = [];
    state.paging.notesHasMore = false;
    showToast(error.message);
  }
  renderNotes();
}

async function loadSharedNotes(append = false) {
  if (!state.currentCourse) return;
  const sort = $("shared-note-sort").value;
  const offset = append ? state.sharedNotes.length : 0;
  try {
    const rows = await api(`/api/notes?course_id=${state.currentCourse.id}&shared_only=true&sort=${sort}&limit=${PAGE_SIZE}&offset=${offset}`);
    state.sharedNotes = append ? [...state.sharedNotes, ...rows] : rows;
    state.paging.sharedNotesHasMore = rows.length === PAGE_SIZE;
  } catch (error) {
    if (!append) state.sharedNotes = [];
    state.paging.sharedNotesHasMore = false;
    showToast(error.message);
  }
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
    await Promise.all([loadNotes(), loadSharedNotes(), loadTree()]);
    showToast("笔记已保存");
  } catch (error) {
    showToast(error.message);
  }
}

async function uploadImage(target) {
  if (!requireCourse()) return;
  const fileInput = $(target === "note" ? "note-image" : "mistake-image");
  const textInput = $(target === "note" ? "note-content" : "mistake-question");
  const preview = $(target === "note" ? "note-image-preview" : "mistake-image-preview");
  const file = fileInput.files && fileInput.files[0];
  if (!file) {
    showToast("请先选择图片");
    return;
  }
  if (!file.type.startsWith("image/")) {
    showToast("只能上传图片");
    return;
  }
  try {
    const dataBase64 = await readFileAsBase64(file);
    const attachment = await api("/api/attachments", {
      method: "POST",
      body: JSON.stringify({
        course_id: state.currentCourse.id,
        file_name: file.name,
        content_type: file.type || "image/png",
        data_base64: dataBase64
      })
    });
    appendMarkdown(textInput, attachment.markdown);
    preview.classList.remove("hidden");
    preview.innerHTML = `<img src="${API_BASE}${attachment.url_path}" alt="${escapeHtml(attachment.file_name)}" /><span>${escapeHtml(attachment.file_name)}</span>`;
    fileInput.value = "";
    showToast("图片已插入正文");
  } catch (error) {
    showToast(error.message);
  }
}

function readFileAsBase64(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || "");
      resolve(result.includes(",") ? result.split(",", 2)[1] : result);
    };
    reader.onerror = () => reject(new Error("读取图片失败"));
    reader.readAsDataURL(file);
  });
}

function appendMarkdown(textInput, markdown) {
  const prefix = textInput.value.trimEnd();
  textInput.value = prefix ? `${prefix}\n\n${markdown}\n` : `${markdown}\n`;
  textInput.focus();
}

async function publishNote(noteId) {
  try {
    await api(`/api/notes/${noteId}/publish`, { method: "POST" });
    await Promise.all([loadNotes(), loadSharedNotes()]);
    showToast("笔记已发布");
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleLikeNote(noteId, likeReactionId) {
  try {
    if (likeReactionId) {
      await api(`/api/reactions/${likeReactionId}`, { method: "DELETE" });
    } else {
      await api("/api/reactions", {
        method: "POST",
        body: JSON.stringify({ target_type: "note", target_id: noteId, reaction_type: "like" })
      });
    }
    await Promise.all([loadNotes(), loadSharedNotes()]);
    showToast(likeReactionId ? "已取消点赞" : "已点赞");
  } catch (error) {
    showToast(error.message);
  }
}

async function toggleFavoriteContent(targetType, targetId, favoriteReactionId) {
  try {
    if (favoriteReactionId) {
      await api(`/api/reactions/${favoriteReactionId}`, { method: "DELETE" });
    } else {
      await api("/api/reactions", {
        method: "POST",
        body: JSON.stringify({ target_type: targetType, target_id: targetId, reaction_type: "favorite" })
      });
    }
    await Promise.all([loadNotes(), loadSharedNotes(), loadMistakes(), loadReview()]);
    showToast(favoriteReactionId ? "已取消收藏" : "已收藏");
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
    await Promise.all([loadNotes(), loadSharedNotes()]);
    showToast("评论已发布");
  } catch (error) {
    showToast(error.message);
  }
}

async function viewComments(targetType, targetId) {
  try {
    const params = new URLSearchParams({
      target_type: targetType,
      target_id: String(targetId),
      limit: "20",
      offset: "0"
    });
    const comments = await api(`/api/comments?${params.toString()}`);
    const text = comments.length
      ? comments.map((comment) => `#${comment.id} 用户 ${comment.author_id}: ${comment.content}`).join("\n")
      : "暂无评论";
    window.alert(text);
  } catch (error) {
    showToast(error.message);
  }
}

async function viewNoteVersions(noteId) {
  try {
    const versions = await api(`/api/notes/${noteId}/versions`);
    const text = versions.length
      ? versions
          .map((version) => {
            const date = version.created_at ? version.created_at.slice(0, 19).replace("T", " ") : "";
            return `#${version.id} ${date} · 用户 ${version.changed_by} · ${version.change_reason}\n${version.title}`;
          })
          .join("\n\n")
      : "暂无版本记录";
    window.alert(text);
  } catch (error) {
    showToast(error.message);
  }
}

async function runAi(noteId, type) {
  try {
    const result = await api(`/api/ai/notes/${noteId}/${type}`, { method: "POST" });
    const generated = result.result || {};
    const payload = {};
    if (type === "summary") {
      const editedSummary = window.prompt("确认或编辑 AI 摘要；取消则放弃本次结果", generated.summary || "");
      if (editedSummary === null) {
        await api(`/api/ai/results/${result.id}/reject`, { method: "POST" });
        showToast("AI 摘要已放弃");
        return;
      }
      payload.summary = editedSummary.trim();
    } else {
      const editedTags = window.prompt(
        "确认或编辑 AI 标签，用逗号分隔；取消则放弃本次结果",
        (generated.tags || []).join(", ")
      );
      if (editedTags === null) {
        await api(`/api/ai/results/${result.id}/reject`, { method: "POST" });
        showToast("AI 标签已放弃");
        return;
      }
      payload.tags = tagsFromInput(editedTags);
    }
    await api(`/api/ai/results/${result.id}/accept`, {
      method: "POST",
      body: JSON.stringify(payload)
    });
    await Promise.all([loadNotes(), loadSharedNotes()]);
    showToast(type === "summary" ? "摘要已采纳" : "标签已采纳");
  } catch (error) {
    showToast(error.message);
  }
}

async function loadMistakes(append = false) {
  if (!state.currentCourse) return;
  const offset = append ? state.mistakes.length : 0;
  try {
    const rows = await api(`/api/mistakes?course_id=${state.currentCourse.id}&limit=${PAGE_SIZE}&offset=${offset}`);
    state.mistakes = append ? [...state.mistakes, ...rows] : rows;
    state.paging.mistakesHasMore = rows.length === PAGE_SIZE;
  } catch (error) {
    if (!append) state.mistakes = [];
    state.paging.mistakesHasMore = false;
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
  const authorId = $("search-author").value.trim();
  if (tag) params.set("tag", tag);
  if (sourceType) params.set("source_type", sourceType);
  if (authorId) params.set("author_id", authorId);
  if ($("search-current-node").checked) {
    if (!state.selectedNode) {
      showToast("请先选择知识树节点");
      return;
    }
    params.set("node_id", state.selectedNode.id);
  }
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
  renderReview();
  renderSuggestions();
  renderSettings();
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
  const query = $("tree-search").value.trim();
  const filtered = window.NoteWeaveTree
    ? window.NoteWeaveTree.filterTreeByQuery(state.tree.tree, query)
    : { tree: state.tree.tree, matchedIds: [] };
  const matchedIds = new Set(filtered.matchedIds || []);
  if (!filtered.tree) {
    refs.treeMeta.textContent = `${state.tree.nodes.length - 1} 个章节/知识点 · 0 个匹配`;
    refs.knowledgeTree.innerHTML = `<div class="meta">没有匹配的节点</div>`;
    return;
  }
  const visibleExpandedIds = query && window.NoteWeaveTree
    ? new Set(window.NoteWeaveTree.collectNodeIds(filtered.tree))
    : state.expandedNodeIds;
  refs.treeMeta.textContent = query
    ? `${state.tree.nodes.length - 1} 个章节/知识点 · ${matchedIds.size} 个匹配`
    : `${state.tree.nodes.length - 1} 个章节/知识点`;
  refs.knowledgeTree.innerHTML = renderTreeNode(filtered.tree, visibleExpandedIds, matchedIds);
  refs.knowledgeTree.querySelectorAll("[data-select-node-id]").forEach((button) => {
    button.addEventListener("click", () => {
      state.selectedNode = state.tree.nodes.find((node) => node.id === Number(button.dataset.selectNodeId));
      state.nodeDetail = null;
      renderTree();
      renderSelectedNode();
      loadSelectedNodeDetail();
    });
  });
  refs.knowledgeTree.querySelectorAll("[data-toggle-node-id]").forEach((button) => {
    button.addEventListener("click", () => {
      const id = Number(button.dataset.toggleNodeId);
      if (state.expandedNodeIds.has(id)) {
        state.expandedNodeIds.delete(id);
      } else {
        state.expandedNodeIds.add(id);
      }
      $("tree-search").value = "";
      renderTree();
    });
  });
}

function renderTreeNode(node, expandedIds = state.expandedNodeIds, matchedIds = new Set()) {
  const isActive = state.selectedNode && state.selectedNode.id === node.id;
  const children = node.children || [];
  const isExpanded = expandedIds.has(node.id);
  const hasChildren = children.length > 0;
  const isMatched = matchedIds.has(node.id);
  return `
    <ul>
      <li>
        <div class="tree-node-row">
          <button class="tree-toggle" data-toggle-node-id="${node.id}" ${hasChildren ? "" : "disabled"} title="${isExpanded ? "折叠" : "展开"}">${hasChildren ? (isExpanded ? "▾" : "▸") : ""}</button>
          <button class="tree-node ${isActive ? "active" : ""} ${isMatched ? "matched" : ""}" data-select-node-id="${node.id}">
            <span>${escapeHtml(node.title)}</span>
            <span class="node-pill">${node.type === "course_root" ? "课程" : node.type === "chapter" ? "章节" : "知识点"} · ${node.note_count || 0}/${node.mistake_count || 0}</span>
          </button>
        </div>
        ${hasChildren && isExpanded ? children.map((child) => renderTreeNode(child, expandedIds, matchedIds)).join("") : ""}
      </li>
    </ul>
  `;
}

function expandTree() {
  if (!state.tree || !state.tree.tree || !window.NoteWeaveTree) return;
  state.expandedNodeIds = new Set(window.NoteWeaveTree.collectNodeIds(state.tree.tree));
  $("tree-search").value = "";
  renderTree();
}

function collapseTree() {
  if (!state.tree || !state.tree.tree) return;
  state.expandedNodeIds = new Set([state.tree.tree.id]);
  $("tree-search").value = "";
  renderTree();
}

async function loadSelectedNodeDetail() {
  if (!state.selectedNode) return;
  try {
    state.nodeDetail = await api(`/api/tree/nodes/${state.selectedNode.id}/detail`);
  } catch (error) {
    state.nodeDetail = null;
    showToast(error.message);
  }
  renderSelectedNode();
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
    ${renderNodeDetailPanel(state.nodeDetail)}
  `;
  if ($("suggestion-target-type").value === "knowledge_node") {
    $("suggestion-target-id").value = node.id;
  }
  bindNodeDetailActions();
}

function renderNodeDetailPanel(detail) {
  if (!detail) {
    return `<div class="node-detail-panel"><div class="meta">正在加载节点关联内容</div></div>`;
  }
  const notes = detail.notes || [];
  const mistakes = detail.mistakes || [];
  const summaries = detail.summaries || [];
  const comments = detail.recent_comments || [];
  return `
    <div class="node-detail-panel">
      <div class="node-detail-section">
        <strong>标签</strong>
        ${
          detail.tag_summary && detail.tag_summary.length
            ? `<div class="tag-row">${detail.tag_summary.map((item) => `<span class="tag green">${escapeHtml(item.tag)} × ${item.count}</span>`).join("")}</div>`
            : `<div class="meta">暂无标签</div>`
        }
      </div>
      <div class="node-detail-section">
        <strong>摘要</strong>
        ${
          summaries.length
            ? summaries.map((item) => `<div class="node-detail-card"><span>${escapeHtml(item.title)}</span><p>${escapeHtml(item.summary)}</p></div>`).join("")
            : `<div class="meta">暂无摘要</div>`
        }
      </div>
      <div class="node-detail-section">
        <strong>关联内容</strong>
        ${
          notes.length || mistakes.length
            ? [
                ...notes.slice(0, 3).map((note) => `<button class="text node-open" data-node-open-type="note" data-node-open-id="${note.id}">笔记 #${note.id} ${escapeHtml(note.title)}</button>`),
                ...mistakes.slice(0, 3).map((mistake) => `<button class="text node-open" data-node-open-type="mistake" data-node-open-id="${mistake.id}">错题 #${mistake.id} ${escapeHtml(mistake.question_content.slice(0, 40))}</button>`)
              ].join("")
            : `<div class="meta">暂无关联内容</div>`
        }
      </div>
      <div class="node-detail-section">
        <strong>最近讨论</strong>
        ${
          comments.length
            ? comments.map((comment) => `<div class="node-detail-card"><span>${escapeHtml(comment.target_title)}</span><p>${escapeHtml(comment.content)}</p></div>`).join("")
            : `<div class="meta">暂无讨论</div>`
        }
      </div>
    </div>
  `;
}

function bindNodeDetailActions() {
  refs.nodeSummary.querySelectorAll("[data-node-open-type]").forEach((button) => {
    button.addEventListener("click", () => {
      openSearchResult(button.dataset.nodeOpenType, Number(button.dataset.nodeOpenId));
    });
  });
}

function renderNotes() {
  const notes = state.notes || [];
  refs.noteCount.textContent = `${notes.length} 条`;
  $("load-more-notes-button").classList.toggle("hidden", !state.paging.notesHasMore);
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
  const notes = state.sharedNotes || [];
  $("load-more-shared-notes-button").classList.toggle("hidden", !state.paging.sharedNotesHasMore);
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
  const favoriteAction = note.favorite_reaction_id || "";
  const likeAction = note.like_reaction_id || "";
  return `
    <article class="item" data-note-id="${note.id}">
      <strong class="item-title">#${note.id} ${escapeHtml(note.title)}</strong>
      <div class="item-meta">${escapeHtml(note.node_path || "未归档")} · ${escapeHtml(note.visibility)} · ${escapeHtml(note.status)} · ${note.like_count} 赞 · ${note.comment_count} 评 · ${note.is_liked ? "已点赞" : "未点赞"} · ${note.is_favorite ? "已收藏" : "未收藏"}</div>
      ${formatTags(note.tags, "green")}
      ${note.summary ? `<div class="note-summary">${escapeHtml(note.summary)}</div>` : ""}
      <div class="markdown-body">${renderMarkdown(note.content_text || "")}</div>
      <div class="item-actions">
        <button class="secondary" data-action="publish">发布</button>
        <button class="secondary" data-action="like" data-like-reaction-id="${likeAction}">${note.is_liked ? "取消点赞" : "点赞"}</button>
        <button class="secondary" data-action="favorite" data-favorite-reaction-id="${favoriteAction}">${note.is_favorite ? "取消收藏" : "收藏"}</button>
        <button class="secondary" data-action="comment">评论</button>
        <button class="secondary" data-action="view-comments">查看评论</button>
        <button class="secondary" data-action="versions">版本</button>
        <button class="secondary" data-action="summary">AI 摘要</button>
        <button class="secondary" data-action="tags">AI 标签</button>
        <button class="text" data-action="suggest-target">设为建议目标</button>
        <button class="text danger-text" data-action="delete">删除</button>
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
        if (action === "like") toggleLikeNote(noteId, Number(button.dataset.likeReactionId) || null);
        if (action === "favorite") toggleFavoriteContent("note", noteId, Number(button.dataset.favoriteReactionId) || null);
        if (action === "comment") commentNote(noteId);
        if (action === "view-comments") viewComments("note", noteId);
        if (action === "versions") viewNoteVersions(noteId);
        if (action === "summary") runAi(noteId, "summary");
        if (action === "tags") runAi(noteId, "tags");
        if (action === "delete") deleteNote(noteId);
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

async function deleteNote(noteId) {
  if (!window.confirm("确认删除这篇笔记？")) return;
  try {
    await api(`/api/notes/${noteId}`, { method: "DELETE" });
    await Promise.all([loadNotes(), loadSharedNotes(), loadTree()]);
    showToast("笔记已删除");
  } catch (error) {
    showToast(error.message);
  }
}

function renderMistakes() {
  $("load-more-mistakes-button").classList.toggle("hidden", !state.paging.mistakesHasMore);
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
      (mistake) => {
        const favoriteAction = mistake.favorite_reaction_id || "";
        return `
        <article class="item" data-mistake-id="${mistake.id}">
          <strong class="item-title">#${mistake.id} ${escapeHtml(mistake.question_content)}</strong>
          <div class="item-meta">${escapeHtml(mistake.node_path || "未归档")} · ${escapeHtml(mistake.question_type || "未分类")} · ${escapeHtml(mistake.mastery_status)} · ${mistake.is_favorite ? "已收藏" : "未收藏"}</div>
          ${formatTags(mistake.tags, "amber")}
          <div class="markdown-body compact">
            <h4>题目</h4>
            ${renderMarkdown(mistake.question_content || "")}
            <h4>正确答案</h4>
            ${renderMarkdown(text(mistake.correct_answer))}
            <h4>错误原因</h4>
            ${renderMarkdown(text(mistake.error_reason))}
            ${mistake.solution ? `<h4>解题思路</h4>${renderMarkdown(mistake.solution)}` : ""}
          </div>
          <div class="item-actions">
            <button class="secondary" data-status="todo">待复习</button>
            <button class="secondary" data-status="retry">需再练</button>
            <button class="secondary" data-status="mastered">已掌握</button>
            <button class="secondary" data-action="favorite" data-favorite-reaction-id="${favoriteAction}">${mistake.is_favorite ? "取消收藏" : "收藏"}</button>
            <button class="text danger-text" data-action="delete">删除</button>
          </div>
        </article>
      `;
      }
    )
    .join("");
  refs.mistakeList.querySelectorAll("[data-mistake-id]").forEach((item) => {
    const id = Number(item.dataset.mistakeId);
    item.querySelectorAll("[data-status]").forEach((button) => {
      button.addEventListener("click", () => updateMastery(id, button.dataset.status));
    });
    item.querySelectorAll("[data-action='delete']").forEach((button) => {
      button.addEventListener("click", () => deleteMistake(id));
    });
    item.querySelectorAll("[data-action='favorite']").forEach((button) => {
      button.addEventListener("click", () => toggleFavoriteContent("mistake", id, Number(button.dataset.favoriteReactionId) || null));
    });
  });
}

function renderReview() {
  $("load-more-review-button").classList.toggle("hidden", !state.paging.reviewHasMore);
  if (!state.currentCourse) {
    refs.reviewList.innerHTML = `<div class="meta">选择课程后显示复习资料</div>`;
    return;
  }
  if (!state.reviewItems || state.reviewItems.length === 0) {
    refs.reviewList.innerHTML = `<div class="meta">暂无复习资料</div>`;
    return;
  }
  refs.reviewList.innerHTML = state.reviewItems
    .map(
      (item) => {
        const favoriteAction = item.favorite_reaction_id || "";
        return `
        <article class="item" data-review-type="${escapeHtml(item.source_type)}" data-review-id="${item.source_id}">
          <strong class="item-title">${escapeHtml(item.source_type)} #${item.source_id} · ${escapeHtml(item.title)}</strong>
          <div class="item-meta">${escapeHtml(item.node_path || "未归档")} · ${item.is_favorite ? "已收藏" : "未收藏"}${item.last_viewed_at ? ` · 浏览 ${escapeHtml(item.last_viewed_at.slice(0, 10))}` : ""}${item.question_type ? ` · ${escapeHtml(item.question_type)}` : ""}${item.mastery_status ? ` · ${escapeHtml(item.mastery_status)}` : ""}</div>
          ${formatTags(item.tags, item.source_type === "note" ? "green" : "amber")}
          <div class="item-body">${escapeHtml(item.snippet || "")}</div>
          <div class="item-actions">
            <button class="secondary" data-action="open-review">打开位置</button>
            <button class="secondary" data-action="favorite-review" data-favorite-reaction-id="${favoriteAction}">${item.is_favorite ? "取消收藏" : "收藏"}</button>
          </div>
        </article>
      `;
      }
    )
    .join("");
  refs.reviewList.querySelectorAll("[data-review-id]").forEach((item) => {
    const sourceType = item.dataset.reviewType;
    const sourceId = Number(item.dataset.reviewId);
    item.querySelector("[data-action='open-review']").addEventListener("click", () => {
      openSearchResult(sourceType, sourceId);
    });
    item.querySelector("[data-action='favorite-review']").addEventListener("click", () => {
      toggleFavoriteContent(sourceType, sourceId, Number(item.querySelector("[data-action='favorite-review']").dataset.favoriteReactionId) || null);
    });
  });
}

async function deleteMistake(mistakeId) {
  if (!window.confirm("确认删除这道错题？")) return;
  try {
    await api(`/api/mistakes/${mistakeId}`, { method: "DELETE" });
    await Promise.all([loadMistakes(), loadTree()]);
    showToast("错题已删除");
  } catch (error) {
    showToast(error.message);
  }
}

function renderSearchResults(results = []) {
  if (results.length === 0) {
    refs.searchResults.innerHTML = `<div class="meta">没有匹配结果</div>`;
    return;
  }
  refs.searchResults.innerHTML = results
    .map(
      (item) => `
        <article class="item search-result" data-source-type="${escapeHtml(item.source_type)}" data-source-id="${item.source_id}">
          <strong class="item-title">${escapeHtml(item.source_type)} #${item.source_id} · ${escapeHtml(item.title)}</strong>
          <div class="item-meta">${escapeHtml(item.node_path || "未归档")} · 作者 ${escapeHtml(item.author_name || String(item.author_id || ""))} · 匹配 ${escapeHtml(item.matched_fields.join(", "))} · 分数 ${item.score}</div>
          <div class="item-body">${escapeHtml(item.snippet)}</div>
          <div class="item-actions">
            <button class="secondary" data-action="open-result">打开位置</button>
          </div>
        </article>
      `
    )
    .join("");
  refs.searchResults.querySelectorAll("[data-action='open-result']").forEach((button) => {
    button.addEventListener("click", () => {
      const item = button.closest("[data-source-type]");
      openSearchResult(item.dataset.sourceType, Number(item.dataset.sourceId));
    });
  });
}

async function openSearchResult(sourceType, sourceId) {
  await recordContentView(sourceType, sourceId);
  state.activeView = sourceType === "mistake" ? "mistakes" : "notes";
  renderTabs();
  if (sourceType === "mistake") {
    await loadMistakes();
    highlightItem(`[data-mistake-id="${sourceId}"]`);
    return;
  }
  await loadNotes();
  highlightItem(`[data-note-id="${sourceId}"]`);
}

async function recordContentView(sourceType, sourceId) {
  try {
    await api("/api/views", {
      method: "POST",
      body: JSON.stringify({ target_type: sourceType, target_id: sourceId })
    });
    await loadReview();
  } catch (error) {
    showToast(error.message);
  }
}

function highlightItem(selector) {
  const item = document.querySelector(selector);
  if (!item) return;
  item.classList.add("flash");
  item.scrollIntoView({ block: "center", behavior: "smooth" });
  window.setTimeout(() => item.classList.remove("flash"), 1400);
}

function renderSuggestions() {
  if (!state.currentCourse) {
    refs.suggestionList.innerHTML = `<div class="meta">选择课程后显示建议</div>`;
    return;
  }
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

function renderSettings() {
  if (!state.currentCourse) {
    refs.courseSettingsForm.reset();
    refs.memberList.innerHTML = `<div class="meta">选择课程后显示设置</div>`;
    refs.aiStatusPanel.innerHTML = `<div class="meta">登录后显示 AI 配置状态</div>`;
    refs.auditLogList.innerHTML = `<div class="meta">选择课程后显示审计日志</div>`;
    return;
  }
  $("settings-course-name").value = state.currentCourse.name || "";
  $("settings-course-semester").value = state.currentCourse.semester || "";
  $("settings-course-description").value = state.currentCourse.description || "";
  $("settings-course-tags").value = (state.currentCourse.tags || []).join(", ");

  if (!state.members || state.members.length === 0) {
    refs.memberList.innerHTML = `<div class="meta">暂无成员</div>`;
  } else {
    refs.memberList.innerHTML = state.members
      .map(
        (member) => `
        <article class="item" data-member-id="${member.id}">
          <strong class="item-title">${escapeHtml(member.display_name || member.username)}</strong>
          <div class="item-meta">#${member.id} · ${escapeHtml(member.username)} · 加入 ${escapeHtml(member.joined_at.slice(0, 10))}</div>
          <div class="row member-role-row">
            <select data-role-select>
              <option value="student" ${member.role === "student" ? "selected" : ""}>普通学生</option>
              <option value="maintainer" ${member.role === "maintainer" ? "selected" : ""}>课程维护者</option>
              <option value="teacher" ${member.role === "teacher" ? "selected" : ""}>教师/助教</option>
            </select>
            <button class="secondary" data-action="save-role" type="button">保存角色</button>
          </div>
        </article>
      `
      )
      .join("");
    refs.memberList.querySelectorAll("[data-member-id]").forEach((item) => {
      const memberId = Number(item.dataset.memberId);
      item.querySelector("[data-action='save-role']").addEventListener("click", () => {
        updateMemberRole(memberId, item.querySelector("[data-role-select]").value);
      });
    });
  }

  refs.aiStatusPanel.innerHTML = renderAiStatusPanel();
  if (!state.auditLogs || state.auditLogs.length === 0) {
    refs.auditLogList.innerHTML = `<div class="meta">暂无审计日志，或当前角色无权查看</div>`;
    return;
  }
  refs.auditLogList.innerHTML = state.auditLogs
    .map(
      (log) => `
        <article class="item audit-item">
          <strong class="item-title">${escapeHtml(log.action)} · ${escapeHtml(log.target_type)} #${log.target_id}</strong>
          <div class="item-meta">操作者 #${log.actor_id} · ${escapeHtml(log.created_at.slice(0, 19))}</div>
          ${Object.keys(log.metadata || {}).length ? `<div class="item-body">${escapeHtml(JSON.stringify(log.metadata))}</div>` : ""}
        </article>
      `
    )
    .join("");
}

function renderAiStatusPanel() {
  const status = state.aiStatus;
  if (!status) {
    return `<div class="meta">暂未获取 AI 配置状态</div>`;
  }
  return `
    <article class="item">
      <strong class="item-title">${status.enabled ? "AI 已启用" : "AI 已关闭"} · ${status.remote_configured ? "远程模型已配置" : "使用本地降级"}</strong>
      <div class="item-meta">模型：${escapeHtml(status.chat_model || "未配置")} · Base URL：${status.base_url_configured ? "已配置" : "未配置"} · API Key：${status.api_key_configured ? "已配置" : "未配置"}</div>
      <div class="item-body">本地摘要和标签降级：${status.fallback_available ? "可用" : "不可用"}</div>
    </article>
  `;
}

boot();
