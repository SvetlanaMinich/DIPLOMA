# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**AutoSTP** is a web platform for automated formatting of academic papers (coursework and diploma theses) per BSUIR standard STP 01-2024. It uses LLMs for semantic text segmentation and declarative templates for formatting rules.

## Commands

### Docker (recommended)
```bash
cd AutoSTP
docker compose --file docker/docker-compose.yml up -d
# API: http://localhost:8000/docs
# Postgres: localhost:5432
```

### Local backend development
```bash
cd AutoSTP/backend
python -m venv venv
venv\Scripts\activate   # Windows
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### Testing
```bash
cd AutoSTP/backend

# Create test DB once
docker exec autostp_postgres psql -U autostp -d postgres -c "CREATE DATABASE autostp_test_db;"

pytest                                        # all tests
pytest tests/test_auth.py                     # single file
pytest --cov=app --cov-report=html            # with coverage
```

### Code quality
```bash
cd AutoSTP/backend
black .           # format (line-length 100)
isort .           # sort imports (profile=black)
mypy app/         # type check
```

## Architecture

### Backend Stack
- **FastAPI** (Python 3.11+) with async/await throughout
- **SQLAlchemy** async ORM + **asyncpg** driver → PostgreSQL 16
- **JWT** via `python-jose` + `bcrypt` for auth; access token (1h) + refresh token in DB (30d)
- **OpenRouter API** (OpenAI-compatible) for LLM calls; all logic in `services/openrouter_service.py`

### Key Directories
```
AutoSTP/backend/app/
├── api/v1/         # route handlers (auth, documents, templates, admin)
├── core/           # config.py (Settings), database.py (engine/Base), security.py (JWT/bcrypt)
├── models/         # SQLAlchemy ORM models — must be imported in models/__init__.py
├── schemas/        # Pydantic request/response models
├── services/       # business logic: auth_service, document_service, template_service, openrouter_service
├── utils/          # storage.py (file I/O), doc_text.py (DOCX/TXT extraction)
└── prompts/        # LLM prompt strings
```

### Database (13 tables, auto-created on startup)
- `users`, `roles` — JWT auth, student/admin roles
- `documents`, `document_versions` — DOCX/TXT uploads, versioned snapshots
- `sections`, `text_elements`, `document_tables`, `document_images` — structured document content
- `templates` — formatting rules stored as JSONB + `work_structure` (expected sections)
- `sessions` — refresh token storage
- `audit_logs`, `ai_suggestions`, `bibliographic_references`, `citations`

All models must be imported in `app/models/__init__.py` so `Base.metadata.create_all()` picks them up in the lifespan handler in `app/main.py`.

### API Layout
All routes are under `/api/v1/` aggregated in `app/api/v1/api.py`:
- `POST /api/v1/auth/register|login|refresh|logout`, `GET /me`
- `POST /api/v1/documents/upload`, `GET|PUT|DELETE /api/v1/documents/{id}`
- `GET|POST|PUT|DELETE /api/v1/templates/{id}`
- `GET /api/v1/admin/ping`

### Configuration
Single `Settings` pydantic-settings class in `core/config.py`; loaded from `.env` (at both `backend/.env` and `AutoSTP/.env`). Required vars: `DATABASE_URL`, `SECRET_KEY`, `OPENROUTER_API_KEY`. See `.env.example` for full list.

### Testing Setup
`tests/conftest.py` creates an async SQLAlchemy session pointed at `autostp_test_db` and overrides FastAPI's `get_db` dependency. LLM service tests use mocks (no network required).

## Development Plan

The project follows a 14-stage roadmap tracked in `AutoSTP/PLAN.md`. Stages 1–4.1 are complete (infrastructure, auth, document management, templates, OpenRouter integration). Frontend (React 18 + Slate.js + PDF.js) is planned for Stage 6.
