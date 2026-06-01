from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


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

    @staticmethod
    def load() -> "Settings":
        def pick(key: str, default: str | None = None) -> str | None:
            return os.getenv(f"NOTEWEAVE_{key}", default)

        def pick_bool(key: str, default: bool) -> bool:
            raw = pick(key)
            if raw is None:
                return default
            return raw.strip().lower() in {"1", "true", "yes", "on"}

        backend_root = Path(__file__).resolve().parents[4]

        def resolve_backend_path(raw: str) -> str:
            p = Path(raw).expanduser()
            if not p.is_absolute():
                p = backend_root / p
            return str(p)

        db_path = pick("DATABASE_PATH", "data/noteweave.sqlite3")
        if db_path and db_path != ":memory:":
            db_path = resolve_backend_path(db_path)

        file_storage_dir = resolve_backend_path(pick("FILE_STORAGE_DIR", "uploads") or "uploads")

        return Settings(
            app_name=pick("APP_NAME", "NoteWeave") or "NoteWeave",
            env=pick("ENV", "dev") or "dev",
            database_path=db_path or ":memory:",
            file_storage_dir=file_storage_dir,
            max_upload_bytes=int(pick("MAX_UPLOAD_BYTES", str(5 * 1024 * 1024)) or 5 * 1024 * 1024),
            enable_ai=pick_bool("ENABLE_AI", True),
            model_base_url=pick("MODEL_BASE_URL"),
            model_api_key=pick("MODEL_API_KEY"),
            chat_model=pick("CHAT_MODEL"),
        )
