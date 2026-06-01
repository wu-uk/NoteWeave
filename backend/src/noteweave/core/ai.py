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
