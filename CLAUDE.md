# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

Course Materials RAG System — AI-powered assistant that answers questions about DeepLearning.AI course materials using semantic search (ChromaDB) and Claude AI (Anthropic tool use).

## Commands

```bash
# Install dependencies
uv sync

# Run the app (from project root)
./run.sh
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000

# Access
# Web UI: http://localhost:8000
# API docs: http://localhost:8000/docs
```

No test suite or linter is configured yet.

## Architecture

```
Frontend (Vanilla JS)
    ↓ POST /api/query
FastAPI (app.py)
    ↓
RAGSystem (rag_system.py) — orchestrator
    ├─ DocumentProcessor — parses course .txt files → chunks (800 chars, 100 overlap)
    ├─ VectorStore — ChromaDB with 2 collections: course_catalog + course_content
    ├─ AIGenerator — Claude API with tool_choice:auto
    ├─ ToolManager → CourseSearchTool — vector search invoked by Claude via tool_use
    └─ SessionManager — in-memory conversation history (max 2 exchanges)
```

### Query flow

1. Frontend sends `{query, session_id}` to `/api/query`
2. `RAGSystem.query()` wraps the query in a prompt, retrieves session history
3. `AIGenerator` calls Claude with `search_course_content` tool available
4. If Claude decides to search: `CourseSearchTool` → `VectorStore.search()` → ChromaDB semantic search → results sent back to Claude for a second API call
5. Response + sources returned to frontend, session history updated

### Key design decisions

- **Tool-based RAG**: Claude autonomously decides when to search (vs. always searching)
- **Two ChromaDB collections**: `course_catalog` for metadata resolution (course name → title matching), `course_content` for actual content chunks
- **Sentence-based chunking**: splits on sentence boundaries with regex, not fixed character offsets
- **Static frontend**: served directly by FastAPI's StaticFiles mount at `/`

## Configuration

All tunables are in `backend/config.py` (dataclass): model name, chunk size/overlap, max results, max history, ChromaDB path. API key loaded from `.env` via python-dotenv.

## Data format

Course documents in `docs/` follow a specific format:
```
Course Title: ...
Course Link: ...
Course Instructor: ...

Lesson 0: Title
Lesson Link: ...
[content]
```

Documents are auto-loaded from `docs/` on app startup.
