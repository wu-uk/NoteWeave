# Repository Guidelines

## Project Structure & Module Organization

NoteWeave is split into a FastAPI backend and a Vue 3 frontend.

- `backend/src/noteweave/`: backend package. API routes live in `api/`, core services and settings live in `core/`.
- `backend/tests/`: pytest coverage for MVP flows.
- `frontend/src/`: Vue application source. Components are in `components/`, shared types in `types.ts`, API helpers in `services/api.ts`, and global styles in `styles/main.css`.
- `frontend/scripts/`: frontend verification scripts.
- `docs/`: Chinese project requirements, architecture, deployment, and development notes.
- `frontend-old/`: preserved legacy static frontend. Do not modify unless the task explicitly targets it.

## Build, Test, and Development Commands

Backend commands should run from `backend/`:

```bash
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv pip install -e ".[dev]"
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv run --no-sync pytest
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv run --no-sync uvicorn noteweave.api.app:app --reload --port 8000
```

Frontend commands should run from `frontend/`:

```bash
npm install
npm run dev
npm run typecheck
npm run build
npm run verify:note-first
```

Use `curl http://127.0.0.1:8000/health` to confirm the backend is available.

## Production Deployment

Current demo production is the public test domain `http://wu-uk.com/noteweave/` and `https://wu-uk.com/noteweave/`. There are no real users yet, so every completed code change should be deployed directly after local verification.

Production shape:

- Nginx serves `frontend/dist` from `/var/www/wu-uk.com/html/noteweave/`.
- Nginx proxies `/noteweave/api/` to `127.0.0.1:8000/api/`.
- `noteweave-backend.service` runs FastAPI from `backend/` with SQLite data in `/var/lib/noteweave/`.

Deploy frontend changes:

```bash
cd /root/project/NoteWeave/frontend
npm run build:noteweave
rsync -a --delete dist/ /var/www/wu-uk.com/html/noteweave/
```

Deploy backend changes:

```bash
cd /root/project/NoteWeave/backend
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv pip install -e ".[dev]"
systemctl restart noteweave-backend
```

Verify after deployment:

```bash
curl -I http://wu-uk.com/noteweave/
curl http://wu-uk.com/noteweave/health
systemctl status noteweave-backend --no-pager
```

## Coding Style & Naming Conventions

Backend code uses Python 3.11+, type hints, and small modules grouped by API/core responsibility. Prefer explicit Pydantic/FastAPI schemas over ad hoc dictionaries at boundaries.

Frontend code uses Vue single-file components with `<script setup lang="ts">`. Use PascalCase for Vue components, camelCase for variables/functions, and keep shared types in `frontend/src/types.ts`. Match existing 2-space indentation in TypeScript/Vue/CSS and keep CSS class names kebab-case.

## Testing Guidelines

Backend tests use pytest and are named `test_*.py`. Add or update tests in `backend/tests/` when changing API behavior, persistence, authentication, AI integration, or document import flows.

Frontend validation currently relies on TypeScript build checks and `frontend/scripts/verify-note-first-frontend.mjs`. Run `npm run typecheck` and `npm run build` before handing off UI changes.

## Commit & Pull Request Guidelines

Recent history uses Conventional Commit-style prefixes, for example `feat:`, `test:`, and `docs:`. Keep commit messages imperative and scoped, such as `feat: add workspace theme toggle`.

Pull requests should include a concise summary, test commands run, linked issue or requirement, screenshots for UI changes, and notes about configuration or migration impact.

## Security & Configuration Tips

Do not commit real secrets, API keys, uploaded files, local databases, or generated caches. Use `config.example.yaml` as the public template and keep local overrides in ignored config files.
