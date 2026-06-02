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
if (!workspace.includes('<main v-else class="app-shell">')) {
  violations.push("WorkspacePage.vue: app-shell must only render behind authenticated v-else gate");
}

if (violations.length) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("note-first frontend constraints passed");
