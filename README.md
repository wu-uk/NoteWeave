# NoteWeave

课程笔记协作系统。项目目标见 `docs/需求文档.md`，架构设计见 `docs/架构文档.md`，开发约定见 `docs/项目规范文档.md`。

## 后端开发

当前后端位于 `backend/`，使用 FastAPI + SQLite 实现首版 MVP API，依赖由 uv 管理。

本环境中的 uv 安装在项目内工具环境：

```bash
./.tools/uv/bin/uv --version
```

创建/安装后端环境：

```bash
cd /root/project/NoteWeave/backend
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv venv
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv pip install -e ".[dev]"
```

运行测试：

```bash
cd /root/project/NoteWeave/backend
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv run --no-sync pytest
```

启动服务：

```bash
cd /root/project/NoteWeave/backend
env UV_CACHE_DIR=/root/project/NoteWeave/.uv-cache ../.tools/uv/bin/uv run --no-sync uvicorn noteweave.api.app:app --reload --port 8000
```

健康检查：

```bash
curl http://127.0.0.1:8000/health
```
