from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Settings:
    app_name: str = "NoteWeave"
    env: str = "dev"
    database_path: str = "data/noteweave.sqlite3"
    file_storage_dir: str = "uploads"
    max_upload_bytes: int = 5 * 1024 * 1024
    enable_ai: bool = True
    model_base_url: str | None = None
    model_api_key: str | None = None
    chat_model: str | None = None
    request_timeout_seconds: float = 10.0
    paddle_ocr_enabled: bool = False
    paddle_ocr_job_url: str | None = None
    paddle_ocr_token: str | None = None
    paddle_ocr_model: str = "PP-StructureV3"
    paddle_ocr_poll_interval_seconds: float = 5.0
    paddle_ocr_timeout_seconds: float = 300.0
    paddle_ocr_use_doc_orientation_classify: bool = False
    paddle_ocr_use_doc_unwarping: bool = False
    paddle_ocr_use_chart_recognition: bool = False

    @staticmethod
    def load() -> "Settings":
        project_root = Path(__file__).resolve().parents[4]
        config = load_config(project_root)

        def config_value(*path: str) -> str | None:
            value: Any = config
            for key in path:
                if not isinstance(value, dict) or key not in value:
                    return None
                value = value[key]
            if value is None:
                return None
            return str(value)

        def pick(key: str, default: str | None = None, *config_path: str) -> str | None:
            env_value = os.getenv(f"NOTEWEAVE_{key}")
            if env_value is not None:
                return env_value
            if config_path:
                file_value = config_value(*config_path)
                if file_value is not None:
                    return file_value
            return default

        def pick_bool(key: str, default: bool, *config_path: str) -> bool:
            raw = pick(key, None, *config_path)
            if raw is None:
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        def pick_float(key: str, default: float, *config_path: str) -> float:
            raw = pick(key, None, *config_path)
            if raw is None:
                return default
            try:
                return float(raw)
            except ValueError:
                return default

        def resolve_backend_path(raw: str) -> str:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = project_root / p
            return str(p)

        db_path = pick("DATABASE_PATH", "data/noteweave.sqlite3", "app", "database_path")
        if db_path and db_path != ":memory:":
            db_path = resolve_backend_path(db_path)

        file_storage_dir = resolve_backend_path(pick("FILE_STORAGE_DIR", "uploads", "app", "file_storage_dir") or "uploads")

        return Settings(
            app_name=pick("APP_NAME", "NoteWeave", "app", "name") or "NoteWeave",
            env=pick("ENV", "dev", "app", "env") or "dev",
            database_path=db_path or ":memory:",
            file_storage_dir=file_storage_dir,
            max_upload_bytes=int(pick("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024), "app", "max_upload_bytes") or 5 * 1024 * 1024),
            enable_ai=pick_bool("ENABLE_AI", True, "ai", "enabled"),
            model_base_url=pick("MODEL_BASE_URL", None, "ai", "base_url"),
            model_api_key=pick("MODEL_API_KEY", None, "ai", "api_key"),
            chat_model=pick("CHAT_MODEL", None, "ai", "chat_model"),
            request_timeout_seconds=max(
                1.0,
                pick_float("REQUEST_TIMEOUT_SECONDS", 10.0, "ai", "request_timeout_seconds"),
            ),
            paddle_ocr_enabled=pick_bool("PADDLE_OCR_ENABLED", False, "paddle_ocr", "enabled"),
            paddle_ocr_job_url=pick(
                "PADDLE_OCR_JOB_URL",
                None,
                "paddle_ocr",
                "job_url",
            ),
            paddle_ocr_token=pick("PADDLE_OCR_TOKEN", None, "paddle_ocr", "token"),
            paddle_ocr_model=pick("PADDLE_OCR_MODEL", "PP-StructureV3", "paddle_ocr", "model") or "PP-StructureV3",
            paddle_ocr_poll_interval_seconds=max(
                0.5,
                pick_float("PADDLE_OCR_POLL_INTERVAL_SECONDS", 5.0, "paddle_ocr", "poll_interval_seconds"),
            ),
            paddle_ocr_timeout_seconds=max(
                5.0,
                pick_float("PADDLE_OCR_TIMEOUT_SECONDS", 300.0, "paddle_ocr", "timeout_seconds"),
            ),
            paddle_ocr_use_doc_orientation_classify=pick_bool(
                "PADDLE_OCR_USE_DOC_ORIENTATION_CLASSIFY",
                False,
                "paddle_ocr",
                "use_doc_orientation_classify",
            ),
            paddle_ocr_use_doc_unwarping=pick_bool(
                "PADDLE_OCR_USE_DOC_UNWARPING",
                False,
                "paddle_ocr",
                "use_doc_unwarping",
            ),
            paddle_ocr_use_chart_recognition=pick_bool(
                "PADDLE_OCR_USE_CHART_RECOGNITION",
                False,
                "paddle_ocr",
                "use_chart_recognition",
            ),
        )


def load_config(project_root: Path) -> dict[str, Any]:
    raw_path = os.getenv("NOTEWEAVE_CONFIG_PATH", "config.yaml")
    config_path = Path(raw_path).expanduser()
    if not config_path.is_absolute():
        config_path = project_root / config_path
    if raw_path == "config.yaml" and not config_path.exists():
        for fallback_name in ("config.ymal", "config.yml"):
            fallback_path = project_root / fallback_name
            if fallback_path.exists():
                config_path = fallback_path
                break
    if not config_path.exists():
        return {}
    return parse_simple_yaml(config_path.read_text(encoding="utf-8"))


def parse_simple_yaml(content: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    current_section: dict[str, Any] | None = None
    for line in content.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(line) - len(line.lstrip(" "))
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        if indent == 0 and not raw_value:
            current_section = {}
            root[key] = current_section
            continue
        value = parse_yaml_scalar(raw_value)
        if indent > 0 and current_section is not None:
            current_section[key] = value
        else:
            current_section = None
            root[key] = value
    return root


def parse_yaml_scalar(value: str) -> Any:
    if value.startswith(("'", '"')) and value.endswith(("'", '"')) and len(value) >= 2:
        return value[1:-1]
    lowered = value.lower()
    if lowered in {"true", "yes", "on"}:
        return True
    if lowered in {"false", "no", "off"}:
        return False
    if lowered in {"null", "none", "~"}:
        return None
    try:
        return int(value)
    except ValueError:
        return value
