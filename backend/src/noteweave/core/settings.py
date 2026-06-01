from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class Settings:
    app_name: str = "NoteWeave"
    env: str = "dev"
    database_path: str = "data/noteweave.sqlite3"
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

        db_path = pick("DATABASE_PATH", "data/noteweave.sqlite3")
        if db_path and db_path != ":memory:":
            p = Path(db_path).expanduser()
            if not p.is_absolute():
                backend_root = Path(__file__).resolve().parents[4]
                p = backend_root / p
            db_path = str(p)

        return Settings(
            app_name=pick("APP_NAME", "NoteWeave") or "NoteWeave",
            env=pick("ENV", "dev") or "dev",
            database_path=db_path or ":memory:",
            enable_ai=pick_bool("ENABLE_AI", True),
            model_base_url=pick("MODEL_BASE_URL"),
            model_api_key=pick("MODEL_API_KEY"),
            chat_model=pick("CHAT_MODEL"),
        )

