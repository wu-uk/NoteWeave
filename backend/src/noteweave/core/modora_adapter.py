from __future__ import annotations

import math
import asyncio
import json
import logging
import re
import textwrap
import zipfile
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

from fastapi import HTTPException
import httpx

from noteweave.core.ai import AIAssistService, fallback_tags
from noteweave.core.settings import Settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Location:
    bbox: list[float]
    page: int
    file_name: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data: dict[str, Any] = {"bbox": self.bbox, "page": self.page}
        if self.file_name:
            data["file_name"] = self.file_name
        return data


@dataclass(slots=True)
class Component:
    type: str
    title: str
    title_level: int = 1
    metadata: str = ""
    data: str = ""
    location: list[Location] = field(default_factory=list)


@dataclass(slots=True)
class OCRBlock:
    page_id: int
    block_id: int
    bbox: list[float]
    label: str
    content: str

    def is_title(self) -> bool:
        return self.label in {"title", "paragraph_title", "doc_title"}

    def is_figure(self) -> bool:
        return self.label in {"image", "chart", "table"}

    def is_figure_title(self) -> bool:
        return self.label in {"figure_title", "vision_footnote"}

    def is_header(self) -> bool:
        return self.label == "header"

    def is_footer(self) -> bool:
        return self.label == "footer"

    def is_number(self) -> bool:
        return self.label == "number"

    def is_aside(self) -> bool:
        return self.label == "aside_text"

    def to_dict(self) -> dict[str, Any]:
        return {
            "page_id": self.page_id,
            "block_id": self.block_id,
            "bbox": self.bbox,
            "label": self.label,
            "content": self.content,
        }


@dataclass(slots=True)
class CCTreeNode:
    type: str
    metadata: str = ""
    data: str = ""
    location: list[Location] = field(default_factory=list)
    children: dict[str, "CCTreeNode"] = field(default_factory=dict)
    height: int = 1
    depth: int = 1
    keyword_cnt: int = 0
    impact: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "type": self.type,
            "metadata": self.metadata,
            "data": self.data,
            "location": [loc.to_dict() for loc in self.location],
            "children": {key: child.to_dict() for key, child in self.children.items()},
            "height": self.height,
            "depth": self.depth,
            "keyword_cnt": self.keyword_cnt,
            "impact": self.impact,
        }


@dataclass(slots=True)
class ModoraDocument:
    text: str
    tree: dict[str, Any]
    metadata: dict[str, Any]
    source_pdf_bytes: bytes | None = None
    source_pdf_name: str | None = None


@dataclass(slots=True)
class PaddleOCRDocument:
    markdown: str = ""
    blocks: list[OCRBlock] = field(default_factory=list)

    @property
    def text(self) -> str:
        if self.markdown.strip():
            return self.markdown.strip()
        return "\n\n".join(block.content for block in self.blocks if block.content.strip()).strip()


async def parse_document_with_modora_flow(
    *,
    file_name: str,
    content_type: str,
    file_bytes: bytes,
    ai: AIAssistService,
    settings: Settings,
) -> ModoraDocument:
    suffix = Path(file_name).suffix.lower()
    normalized_type = content_type.lower()
    safe_name = safe_file_name(file_name)

    if suffix in {".md", ".markdown"} or normalized_type in {"text/markdown", "text/x-markdown", "text/plain"}:
        text = normalize_document_text(decode_text_file(file_bytes))
        components = markdown_components(text, safe_name)
        parser = "modora-markdown-heading"
        source_pdf_bytes = None
        source_pdf_name = None
    elif suffix in {".doc", ".docx"} or normalized_type in {
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }:
        text = normalize_document_text(extract_docx_text(file_bytes) if suffix == ".docx" else decode_text_file(file_bytes))
        source_pdf_bytes = text_to_pdf_bytes(text, document_title(file_name))
        source_pdf_name = f"{Path(safe_name).stem or 'document'}.pdf"
        paddle_doc = await paddle_ocr_document(source_pdf_name, "application/pdf", source_pdf_bytes, settings)
        if paddle_doc.text:
            text = normalize_document_text(paddle_doc.text)
            components = ocr_components(paddle_doc.blocks, source_pdf_name) if paddle_doc.blocks else markdown_components(text, source_pdf_name)
            parser = "paddleocr-doc-to-pdf"
        else:
            components = pdf_components_from_text(text, source_pdf_name)
            parser = "modora-doc-to-pdf"
    elif suffix == ".pdf" or normalized_type == "application/pdf":
        source_pdf_bytes = file_bytes
        source_pdf_name = safe_name
        paddle_doc = await paddle_ocr_document(safe_name, content_type, file_bytes, settings)
        if paddle_doc.text:
            text = normalize_document_text(paddle_doc.text)
            components = ocr_components(paddle_doc.blocks, safe_name) if paddle_doc.blocks else markdown_components(text, safe_name)
            parser = "paddleocr-pp-structure-v3"
        else:
            text, components = pdf_components(file_bytes, safe_name)
            parser = "modora-pdf"
    else:
        raise HTTPException(status_code=415, detail="only PDF, DOC/DOCX, and Markdown imports are supported")

    if not text.strip():
        raise HTTPException(status_code=422, detail="document text could not be extracted")

    tree = construct_tree(components)
    await generate_metadata(tree, ai)
    root = tree.to_dict()
    metadata = {
        "file_name": safe_name,
        "content_type": content_type,
        "parser": parser,
        "characters": len(text),
        "tree_type": "modora-cctree",
        "semantic_tags": metadata_tags(tree.metadata),
        "source_pdf_name": source_pdf_name,
    }
    return ModoraDocument(
        text=text,
        tree=root,
        metadata=metadata,
        source_pdf_bytes=source_pdf_bytes,
        source_pdf_name=source_pdf_name,
    )


async def paddle_ocr_markdown(file_name: str, content_type: str, file_bytes: bytes, settings: Settings) -> str:
    return (await paddle_ocr_document(file_name, content_type, file_bytes, settings)).markdown


async def paddle_ocr_document(file_name: str, content_type: str, file_bytes: bytes, settings: Settings) -> PaddleOCRDocument:
    if not settings.paddle_ocr_enabled:
        logger.info("PaddleOCR skipped: disabled")
        return PaddleOCRDocument()
    if not settings.paddle_ocr_job_url or not settings.paddle_ocr_token:
        logger.warning("PaddleOCR skipped: job_url or token is missing")
        return PaddleOCRDocument()

    headers = {"Authorization": f"bearer {settings.paddle_ocr_token}"}
    optional_payload = {
        "useDocOrientationClassify": settings.paddle_ocr_use_doc_orientation_classify,
        "useDocUnwarping": settings.paddle_ocr_use_doc_unwarping,
        "useChartRecognition": settings.paddle_ocr_use_chart_recognition,
    }
    timeout = httpx.Timeout(settings.request_timeout_seconds)
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                settings.paddle_ocr_job_url,
                headers=headers,
                data={
                    "model": settings.paddle_ocr_model,
                    "optionalPayload": json.dumps(optional_payload),
                },
                files={"file": (file_name, file_bytes, content_type or "application/octet-stream")},
            )
            response.raise_for_status()
            job_id = response.json()["data"]["jobId"]
            logger.info("PaddleOCR job submitted", extra={"file_name": file_name, "job_id": str(job_id)})
            jsonl_url = await poll_paddle_job(client, settings, headers, str(job_id))
            if not jsonl_url:
                logger.warning("PaddleOCR finished without result url", extra={"file_name": file_name, "job_id": str(job_id)})
                return PaddleOCRDocument()
            jsonl_response = await client.get(jsonl_url)
            jsonl_response.raise_for_status()
            document = extract_paddle_document(jsonl_response.text)
            logger.info(
                "PaddleOCR document extracted",
                extra={
                    "file_name": file_name,
                    "job_id": str(job_id),
                    "characters": len(document.text),
                    "blocks": len(document.blocks),
                },
            )
            return document
    except Exception as exc:
        logger.warning("PaddleOCR request failed", extra={"file_name": file_name, "error": str(exc)})
        return PaddleOCRDocument()


async def poll_paddle_job(
    client: httpx.AsyncClient,
    settings: Settings,
    headers: dict[str, str],
    job_id: str,
) -> str:
    deadline = asyncio.get_running_loop().time() + settings.paddle_ocr_timeout_seconds
    job_url = settings.paddle_ocr_job_url.rstrip("/") if settings.paddle_ocr_job_url else ""
    while asyncio.get_running_loop().time() < deadline:
        response = await client.get(f"{job_url}/{job_id}", headers=headers)
        response.raise_for_status()
        data = response.json().get("data") or {}
        state = data.get("state")
        if state == "done":
            result_url = data.get("resultUrl") or {}
            return str(result_url.get("jsonUrl") or "")
        if state == "failed":
            logger.warning("PaddleOCR job failed", extra={"job_id": job_id, "error": data.get("errorMsg")})
            return ""
        await asyncio.sleep(settings.paddle_ocr_poll_interval_seconds)
    return ""


def extract_paddle_markdown(jsonl_text: str) -> str:
    return extract_paddle_document(jsonl_text).markdown


def extract_paddle_document(jsonl_text: str) -> PaddleOCRDocument:
    pages: list[str] = []
    blocks: list[OCRBlock] = []
    page_id = 0
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError:
            continue
        result = payload.get("result") if isinstance(payload, dict) else None
        layout_results = result.get("layoutParsingResults") if isinstance(result, dict) else None
        if not isinstance(layout_results, list):
            continue
        for item in layout_results:
            if not isinstance(item, dict):
                continue
            page_id += 1
            markdown = item.get("markdown")
            if isinstance(markdown, dict):
                text = str(markdown.get("text") or "").strip()
                if text:
                    pages.append(text)
            blocks.extend(extract_paddle_blocks(item, page_id))
    return PaddleOCRDocument(markdown="\n\n".join(pages).strip(), blocks=blocks)


def extract_paddle_blocks(layout_result: dict[str, Any], page_id: int) -> list[OCRBlock]:
    pruned = layout_result.get("prunedResult")
    parsing_res = pruned.get("parsing_res_list") if isinstance(pruned, dict) else None
    if not isinstance(parsing_res, list):
        return []
    blocks: list[OCRBlock] = []
    for index, item in enumerate(parsing_res):
        if not isinstance(item, dict):
            continue
        label = str(item.get("block_label") or item.get("label") or "").strip()
        content = str(item.get("block_content") or item.get("content") or "").strip()
        if not label or not content:
            continue
        raw_bbox = item.get("block_bbox") or item.get("bbox") or [0, 0, 0, 0]
        bbox = normalize_paddle_bbox(raw_bbox)
        block_id = item.get("block_id")
        try:
            block_id_int = int(block_id)
        except (TypeError, ValueError):
            block_id_int = index
        blocks.append(OCRBlock(page_id=page_id, block_id=block_id_int, bbox=bbox, label=label, content=content))
    return blocks


def normalize_paddle_bbox(raw_bbox: Any) -> list[float]:
    if not isinstance(raw_bbox, list) or len(raw_bbox) < 4:
        return [0.0, 0.0, 0.0, 0.0]
    try:
        values = [float(value) for value in raw_bbox[:4]]
    except (TypeError, ValueError):
        return [0.0, 0.0, 0.0, 0.0]
    return [0.5 * value for value in values]


def ocr_components(blocks: list[OCRBlock], file_name: str) -> list[Component]:
    components: list[Component] = []
    current_title = document_title(file_name)
    current = Component(type="text", title=current_title)
    non_text_cache: list[Component] = []
    figure_title = "Default Title"

    def append_current() -> None:
        nonlocal current
        if current.title != document_title(file_name) or current.data.strip():
            components.append(current)

    for index, block in enumerate(blocks):
        location = Location(bbox=block.bbox, page=block.page_id, file_name=file_name)
        if block.is_title():
            append_current()
            components.extend(non_text_cache)
            non_text_cache.clear()
            current_title = block.content
            current = Component(type="text", title=current_title, data=current_title, location=[location])
        elif block.is_figure():
            figure = Component(type=block.label, title=figure_title, data=block.content, location=[location])
            if index > 0 and blocks[index - 1].is_figure_title():
                figure.title = blocks[index - 1].content
            elif index + 1 < len(blocks) and blocks[index + 1].is_figure_title():
                figure.title = blocks[index + 1].content
            non_text_cache.append(figure)
        elif block.is_header() or block.is_footer() or block.is_number() or block.is_aside() or block.is_figure_title():
            continue
        else:
            current.data = f"{current.data}\n\n{block.content}".strip()
            current.location.append(location)

    append_current()
    components.extend(non_text_cache)
    return components or [Component(type="text", title=document_title(file_name), data="")]


def construct_tree(components: list[Component]) -> CCTreeNode:
    root = CCTreeNode(type="root", metadata="", data="", children={})
    stack: list[tuple[CCTreeNode, int]] = [(root, 0)]
    for component in components:
        node = CCTreeNode(
            type=component.type,
            metadata=component.metadata,
            data=component.data,
            location=component.location,
            children={},
        )
        level = max(1, int(component.title_level or 1))
        while stack and stack[-1][1] >= level:
            stack.pop()
        parent = stack[-1][0] if stack else root
        parent.children[unique_child_key(parent, component.title)] = node
        stack.append((node, level))
    return root


async def generate_metadata(root: CCTreeNode, ai: AIAssistService) -> None:
    async def visit(node: CCTreeNode, parent: CCTreeNode | None = None) -> None:
        if parent is not None:
            node.depth = parent.depth + 1
        for child in node.children.values():
            await visit(child, node)
            node.height = max(node.height, child.height + 1)
        node.keyword_cnt = keyword_count(node)
        if node.type == "text":
            node.metadata = await ai.generate_metadata(node.data, node.keyword_cnt)
            if node.children:
                node.metadata = await ai.integrate_metadata([node.metadata, *[child.metadata for child in node.children.values()]], node.keyword_cnt)
        elif node.type == "root":
            node.metadata = await ai.integrate_metadata([child.metadata for child in node.children.values()], node.keyword_cnt)
        elif not node.metadata:
            node.metadata = fallback_metadata(node.data, node.keyword_cnt)

    await visit(root)


def keyword_count(node: CCTreeNode, n0: int = 2, growth_rate: float = 2.0) -> int:
    if not node.children:
        return n0
    total = max(1, sum(child.keyword_cnt for child in node.children.values()))
    depth = max(1, node.depth)
    return math.ceil(((depth + node.height - 1) / depth) + math.log2(pow(total, growth_rate)) + 1)


def markdown_components(text: str, file_name: str) -> list[Component]:
    blocks: list[tuple[int, str, str]] = []
    preface: list[str] = []
    current_title = ""
    current_level = 0
    buffer: list[str] = []

    def flush_heading() -> None:
        nonlocal buffer
        if not current_title:
            return
        blocks.append((current_level, current_title, "\n".join(buffer).strip()))
        buffer = []

    for line in text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            heading_title = match.group(2).strip()
            if len(heading_title) <= 1:
                target = buffer if current_title else preface
                target.append(heading_title)
                continue
            flush_heading()
            current_level = len(match.group(1))
            current_title = heading_title
            buffer = []
        elif current_title:
            buffer.append(line)
        else:
            preface.append(line)
    flush_heading()

    components: list[Component] = []
    preface_text = "\n".join(preface).strip()
    if preface_text:
        components.append(Component(type="text", title=document_title(file_name), title_level=1, data=preface_text))

    if not blocks:
        if not components:
            components.append(Component(type="text", title=document_title(file_name), title_level=1, data=text.strip()))
        return components

    min_heading_level = min(level for level, _, _ in blocks)
    base_offset = min_heading_level - 1
    for level, title, data in blocks:
        components.append(
            Component(
                type="text",
                title=title,
                title_level=max(1, level - base_offset),
                data=data,
            )
        )
    return components


def pdf_components(file_bytes: bytes, file_name: str) -> tuple[str, list[Component]]:
    pages = extract_pdf_pages(file_bytes)
    text = normalize_document_text("\n\n".join(pages))
    return text, pdf_components_from_pages(pages, file_name)


def pdf_components_from_text(text: str, file_name: str) -> list[Component]:
    return pdf_components_from_pages([text], file_name)


def pdf_components_from_pages(pages: list[str], file_name: str) -> list[Component]:
    components: list[Component] = []
    for page_index, page_text in enumerate(pages, start=1):
        paragraphs = [part.strip() for part in re.split(r"\n\s*\n", page_text) if part.strip()]
        if not paragraphs:
            paragraphs = [line.strip() for line in page_text.splitlines() if line.strip()]
        for index, paragraph in enumerate(paragraphs):
            title = first_line_title(paragraph, fallback=f"Page {page_index} Block {index + 1}")
            level = infer_title_level(paragraph, index)
            components.append(
                Component(
                    type="text",
                    title=title,
                    title_level=level,
                    data=paragraph,
                    location=[Location(bbox=[0.0, 0.0, 0.0, 0.0], page=page_index, file_name=file_name)],
                )
            )
    return components


def extract_pdf_pages(file_bytes: bytes) -> list[str]:
    try:
        from pypdf import PdfReader

        reader = PdfReader(BytesIO(file_bytes))
        return [page.extract_text() or "" for page in reader.pages]
    except Exception as exc:
        raise HTTPException(status_code=422, detail=f"pdf text extraction failed: {exc}")


def infer_title_level(text: str, index: int) -> int:
    first = text.strip().splitlines()[0] if text.strip() else ""
    if re.match(r"^\d+(?:\.\d+)*\s+", first):
        return min(6, first.split()[0].count(".") + 1)
    if index == 0 or (len(first) <= 80 and not first.endswith((".", "。", "；", ";"))):
        return 1
    return 2


def first_line_title(text: str, fallback: str) -> str:
    first = text.strip().splitlines()[0].strip() if text.strip() else fallback
    return first[:160] or fallback


def unique_child_key(parent: CCTreeNode, title: str) -> str:
    base = (title or "Default Title").strip() or "Default Title"
    if base not in parent.children:
        return base
    index = 1
    while f"{base}_{index}" in parent.children:
        index += 1
    return f"{base}_{index}"


def metadata_tags(value: str) -> list[str]:
    return [tag.strip() for tag in (value or "").split(";") if tag.strip()][:8]


def decode_text_file(file_bytes: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-8", "gb18030", "latin-1"):
        try:
            return file_bytes.decode(encoding)
        except UnicodeDecodeError:
            continue
    return file_bytes.decode("utf-8", errors="replace")


def extract_docx_text(file_bytes: bytes) -> str:
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as archive:
            xml_bytes = archive.read("word/document.xml")
    except (KeyError, zipfile.BadZipFile):
        raise HTTPException(status_code=422, detail="invalid docx document")
    try:
        root = ElementTree.fromstring(xml_bytes)
    except ElementTree.ParseError:
        raise HTTPException(status_code=422, detail="invalid docx xml")
    namespace = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
    paragraphs: list[str] = []
    for paragraph in root.iter(f"{namespace}p"):
        texts = [node.text or "" for node in paragraph.iter(f"{namespace}t")]
        line = "".join(texts).strip()
        if line:
            paragraphs.append(line)
    return "\n".join(paragraphs)


def normalize_document_text(text: str) -> str:
    lines = [line.strip() for line in (text or "").replace("\r", "\n").splitlines()]
    cleaned_lines: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if not blank:
                cleaned_lines.append("")
            blank = True
            continue
        cleaned_lines.append(line)
        blank = False
    return "\n".join(cleaned_lines).strip()


def document_title(file_name: str) -> str:
    return Path(file_name).stem.strip()[:180] or "Imported document"


def safe_file_name(file_name: str, fallback: str = "file") -> str:
    raw_name = Path(file_name).name or fallback
    safe_name = "".join(
        char if char.isascii() and (char.isalnum() or char in ".-_") else "_"
        for char in raw_name
    ).strip("._")
    return safe_name or fallback


def text_to_pdf_bytes(text: str, title: str) -> bytes:
    body_lines: list[str] = [title, ""]
    for paragraph in text.splitlines():
        body_lines.extend(textwrap.wrap(paragraph, width=78) or [""])
    page_text = "\n".join(body_lines[:48])
    commands = ["BT", "/F1 12 Tf", "72 740 Td", "14 TL"]
    for line in page_text.splitlines():
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        commands.append(f"({escaped}) Tj")
        commands.append("T*")
    commands.append("ET")
    stream = "\n".join(commands).encode("latin-1", errors="replace")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(stream)).encode("ascii") + b" >>\nstream\n" + stream + b"\nendstream",
    ]
    pdf = bytearray(b"%PDF-1.4\n")
    offsets: list[int] = []
    for index, payload in enumerate(objects, start=1):
        offsets.append(len(pdf))
        pdf.extend(f"{index} 0 obj\n".encode("ascii"))
        pdf.extend(payload)
        pdf.extend(b"\nendobj\n")
    xref_offset = len(pdf)
    pdf.extend(f"xref\n0 {len(objects) + 1}\n".encode("ascii"))
    pdf.extend(b"0000000000 65535 f \n")
    for offset in offsets:
        pdf.extend(f"{offset:010d} 00000 n \n".encode("ascii"))
    pdf.extend(
        f"trailer\n<< /Root 1 0 R /Size {len(objects) + 1} >>\nstartxref\n{xref_offset}\n%%EOF\n".encode("ascii")
    )
    return bytes(pdf)


def fallback_metadata(text: str, count: int) -> str:
    tags = fallback_tags(text)[: max(1, count)]
    return ";".join(tags or ["Document"])
