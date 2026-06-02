import { readFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const root = new URL("../src/components", import.meta.url).pathname;
const forbidden = [
  "新建课程",
  "加入课程",
  "课程成员",
  "成员管理",
  "邀请码",
  "助教",
  "教师"
];

function walk(dir) {
  return readdirSync(dir).flatMap((name) => {
    const path = join(dir, name);
    if (statSync(path).isDirectory()) return walk(path);
    return path.endsWith(".vue") ? [path] : [];
  });
}

const violations = [];
for (const file of walk(root)) {
  const content = readFileSync(file, "utf8");
  for (const phrase of forbidden) {
    if (content.includes(phrase)) {
      violations.push(`${file}: contains forbidden note-first entry "${phrase}"`);
    }
  }
}

if (violations.length) {
  console.error(violations.join("\n"));
  process.exit(1);
}

console.log("note-first frontend constraints passed");
