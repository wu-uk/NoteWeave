from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Any

import httpx

from noteweave.core.settings import Settings


@dataclass(frozen=True)
class AIOutput:
    result: dict[str, Any]
    source: str
    error: str = ""


class AIAssistService:
    def __init__(self, settings: Settings):
        self.settings = settings

    async def summarize_note(self, title: str, content: str) -> AIOutput:
        fallback = {"summary": fallback_summary(content), "source": "fallback"}
        prompt = (
            "请为下面课程笔记生成 120 字以内中文摘要。只返回摘要文本。\n\n"
            f"标题：{title}\n正文：{content}"
        )
        remote = await self._call_remote(prompt)
        if not remote:
            return AIOutput(fallback, "fallback")
        return AIOutput({"summary": remote.strip(), "source": "remote"}, "remote")

    async def extract_tags(self, title: str, content: str) -> AIOutput:
        fallback = {"tags": fallback_tags(f"{title} {content}"), "source": "fallback"}
        prompt = (
            "请从课程笔记中提取 3 到 8 个关键词标签。"
            "只返回 JSON 数组，例如 [\"排序\", \"复杂度\"]。\n\n"
            f"标题：{title}\n正文：{content}"
        )
        remote = await self._call_remote(prompt)
        if not remote:
            return AIOutput(fallback, "fallback")
        tags = parse_tag_response(remote)
        if not tags:
            return AIOutput(fallback, "fallback", error="remote response did not contain tags")
        return AIOutput({"tags": tags, "source": "remote"}, "remote")

    async def classify_note(self, title: str, content: str, tags: list[str] | None = None) -> AIOutput:
        fallback = fallback_classification(title, content, tags or [])
        prompt = (
            "你是课程笔记归档助手。请根据笔记内容决定它最适合归入哪个课程和知识点，并生成摘要与标签。"
            "只返回 JSON 对象，字段为 course_name, node_title, summary, tags。"
            "course_name 使用简短课程名，node_title 使用具体知识点名，tags 为 3 到 8 个字符串。\n\n"
            f"标题：{title}\n用户标签：{json.dumps(tags or [], ensure_ascii=False)}\n正文：{content}"
        )
        remote = await self._call_remote(prompt)
        if not remote:
            return AIOutput(fallback, "fallback")
        parsed = parse_object_response(remote)
        result = normalize_classification(parsed, fallback)
        if result["source"] == "fallback":
            return AIOutput(fallback, "fallback", error="remote response did not contain classification")
        return AIOutput(result, "remote")

    async def answer_question(self, question: str, contexts: list[dict[str, Any]]) -> AIOutput:
        fallback = fallback_answer(question, contexts)
        if not contexts:
            return AIOutput(fallback, "fallback")
        context_text = "\n\n".join(
            f"[{index + 1}] {item.get('title', '')}\n路径：{item.get('node_path') or '未归档'}\n{item.get('content', '')}"
            for index, item in enumerate(contexts)
        )
        prompt = (
            "你是学习笔记问答助手。只能基于给定笔记片段回答，不要编造。"
            "如果片段不足以回答，请说明缺少信息。返回简洁中文答案，并在答案末尾列出引用编号。\n\n"
            f"问题：{question}\n\n笔记片段：\n{context_text}"
        )
        remote = await self._call_remote(prompt)
        if not remote:
            return AIOutput(fallback, "fallback")
        return AIOutput({"answer": remote.strip(), "source": "remote"}, "remote")

    async def _call_remote(self, prompt: str) -> str | None:
        if not self.settings.enable_ai:
            return None
        if not self.settings.model_base_url or not self.settings.model_api_key or not self.settings.chat_model:
            return None

        base = self.settings.model_base_url.rstrip("/")
        url = base if base.endswith("/chat/completions") else f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.settings.model_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self.settings.chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
        }
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(url, headers=headers, json=payload)
                response.raise_for_status()
                data = response.json()
        except Exception:
            return None

        try:
            return data["choices"][0]["message"]["content"] or None
        except (KeyError, IndexError, TypeError):
            return None


def fallback_summary(content: str) -> str:
    content = re.sub(r"\s+", " ", content or "").strip()
    if not content:
        return "暂无可摘要内容。"
    return content[:240] + ("..." if len(content) > 240 else "")


def fallback_tags(content: str) -> list[str]:
    tokens = re.findall(r"[A-Za-z0-9_]{2,}|[\u4e00-\u9fff]{2,}", content or "")
    seen: list[str] = []
    for token in tokens:
        token = token.strip().lower()
        if token and token not in seen:
            seen.append(token)
        if len(seen) >= 8:
            break
    return seen


def parse_tag_response(value: str) -> list[str]:
    text = value.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        return [str(item).strip() for item in parsed if str(item).strip()][:8]
    return fallback_tags(text)


def parse_object_response(value: str) -> dict[str, Any]:
    text = value.strip()
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def fallback_classification(title: str, content: str, tags: list[str]) -> dict[str, Any]:
    all_tags = [*tags, *fallback_tags(f"{title} {content}")]
    deduped: list[str] = []
    for tag in all_tags:
        clean = str(tag).strip()
        if clean and clean not in deduped:
            deduped.append(clean)
        if len(deduped) >= 8:
            break
    first_tag = deduped[0] if deduped else "综合笔记"
    return {
        "course_name": infer_course_name(title, content, first_tag),
        "node_title": first_tag,
        "summary": fallback_summary(content),
        "tags": deduped,
        "source": "fallback",
    }


def normalize_classification(parsed: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    course_name = str(parsed.get("course_name") or parsed.get("course") or "").strip()
    node_title = str(parsed.get("node_title") or parsed.get("topic") or "").strip()
    summary = str(parsed.get("summary") or "").strip()
    tags = parsed.get("tags")
    clean_tags = [str(item).strip() for item in tags if str(item).strip()] if isinstance(tags, list) else []
    if not course_name and not node_title and not clean_tags:
        return fallback
    return {
        "course_name": course_name[:120] or fallback["course_name"],
        "node_title": node_title[:160] or fallback["node_title"],
        "summary": summary[:500] or fallback["summary"],
        "tags": clean_tags[:8] or fallback["tags"],
        "source": "remote",
    }


def infer_course_name(title: str, content: str, first_tag: str) -> str:
    text = f"{title} {content}".lower()
    buckets = [
        ("计算机科学", ["algorithm", "复杂度", "排序", "数据结构", "python", "java", "递归", "graph", "数据库"]),
        ("数学", ["calculus", "algebra", "概率", "矩阵", "导数", "积分", "函数", "证明"]),
        ("英语", ["grammar", "vocabulary", "reading", "writing", "听力", "语法", "单词"]),
        ("物理", ["力学", "电磁", "quantum", "热力学", "速度", "加速度"]),
        ("经济学", ["供给", "需求", "market", "宏观", "微观", "价格", "成本"]),
    ]
    for name, keywords in buckets:
        if any(keyword.lower() in text for keyword in keywords):
            return name
    return first_tag or "综合笔记"


def fallback_answer(question: str, contexts: list[dict[str, Any]]) -> dict[str, Any]:
    if not contexts:
        return {
            "answer": "当前没有找到足够相关的笔记片段，无法回答这个问题。",
            "source": "fallback",
        }
    preview = "；".join(f"[{index + 1}] {item.get('snippet') or item.get('content', '')[:120]}" for index, item in enumerate(contexts[:3]))
    return {
        "answer": f"根据已检索到的笔记片段，建议先查看：{preview}",
        "source": "fallback",
    }
