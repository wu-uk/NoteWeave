import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const componentRoot = new URL("../src/components", import.meta.url).pathname;
const srcRoot = new URL("../src", import.meta.url).pathname;
const forbiddenComponentPhrases = [
  "新建课程",
  "加入课程",
  "课程成员",
  "成员管理",
  "邀请码",
  "助教",
  "教师"
];
const forbiddenClientSymbols = [
  "createCourse",
  "updateCourse",
  "joinCourse",
  "listMembers",
  "updateMemberRole",
  "removeMember",
  "CourseRole",
  "CourseMember"
];

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return walk(path);
    return path.endsWith(".vue") ? [path] : [];
  });
}

const violations = [];
for (const file of walk(componentRoot)) {
  const content = readFileSync(file, "utf8");
  for (const phrase of forbiddenComponentPhrases) {
    if (content.includes(phrase)) {
      violations.push(`${file}: contains forbidden note-first entry "${phrase}"`);
    }
  }
}

for (const relativePath of ["services/api.ts", "types.ts"]) {
  const file = join(srcRoot, relativePath);
  const content = readFileSync(file, "utf8");
  for (const symbol of forbiddenClientSymbols) {
    if (content.includes(symbol)) {
      violations.push(`${file}: contains legacy course-management symbol "${symbol}"`);
    }
  }
}

const workspace = readFileSync(join(componentRoot, "WorkspacePage.vue"), "utf8");
if (!workspace.includes('<main v-if="!user" class="auth-shell">')) {
  violations.push("WorkspacePage.vue: missing unauthenticated auth-shell gate");
}
if (!workspace.includes('<main v-else class="app-shell knowledge-app">')) {
  violations.push("WorkspacePage.vue: app-shell must only render behind authenticated v-else gate");
}
for (const label of ["个人笔记", "共享笔记", "错题整理", "每日一题", "浮动知识点网络"]) {
  if (!workspace.includes(label)) {
    violations.push(`WorkspacePage.vue: redesigned workspace is missing "${label}"`);
  }
}
for (const extension of [".pdf", ".docx", ".md", ".markdown"]) {
  if (!workspace.includes(extension)) {
    violations.push(`WorkspacePage.vue: document import accept list is missing "${extension}"`);
  }
}
if (!workspace.includes("api.importNoteDocument")) {
  violations.push("WorkspacePage.vue: document import must call api.importNoteDocument");
}
if (!workspace.includes('class="qa-form"') || !workspace.includes("api.askNotes")) {
  violations.push("WorkspacePage.vue: note QA form must call api.askNotes");
}
if (!workspace.includes('class="context-list"') || !workspace.includes("answer.contexts")) {
  violations.push("WorkspacePage.vue: note QA must render retrieved contexts");
}
if (!workspace.includes('class="markdown-preview"') || !workspace.includes("renderMarkdown")) {
  violations.push("WorkspacePage.vue: personal note editor must include realtime markdown preview");
}

if (violations.length) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("note-first frontend constraints passed");
