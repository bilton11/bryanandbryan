---
phase: 01-foundation
plan: 01-01
subsystem: auth
tags: [flask, sqlalchemy, flask-login, magic-link, alembic, rate-limiting, itsdangerous]
one-liner: "Flask app factory with SQLAlchemy 2.0 User model, stateless magic-link auth (itsdangerous), Alembic migrations, and per-IP/per-email rate limiting"

dependency-graph:
  requires: []
  provides:
    - flask-app-factory
    - user-model
    - magic-link-auth
    - alembic-migrations
    - health-check
  affects:
    - 01-02
    - all-subsequent-phases

tech-stack:
  added:
    - flask 3.1
    - flask-sqlalchemy 3.1 (SQLAlchemy 2.0.49)
    - flask-migrate 4.1 (Alembic)
    - flask-login 0.6
    - flask-limiter 4.x
    - itsdangerous 2.x
    - sendgrid 6.x
    - cloud-sql-python-connector[pg8000] 1.x
    - gunicorn 22.x
    - python-dotenv 1.x
  patterns:
    - app-factory (create_app with config_name)
    - SQLAlchemy 2.0 Mapped/mapped_column style
    - stateless magic-link tokens (URLSafeTimedSerializer, 15-min TTL)
    - create-on-verify user registration
    - remember=True for 7-day sessions

key-files:
  created:
    - app/__init__.py
    - app/config.py
    - app/extensions.py
    - app/models/__init__.py
    - app/models/user.py
    - app/services/__init__.py
    - app/services/auth_tokens.py
    - app/auth/__init__.py
    - app/auth/routes.py
    - app/main/__init__.py
    - app/main/routes.py
    - app/templates/base.html
    - app/templates/auth/login.html
    - app/templates/auth/check_email.html
    - app/templates/auth/link_expired.html
    - app/templates/main/index.html
    - app/static/css/main.css
    - requirements.txt
    - .env.example
    - migrations/ (full Alembic directory)
  modified: []

decisions:
  - id: flask-login-version
    choice: "flask-login>=0.6 (not >=0.7 as planned)"
    reason: "0.7 does not exist; latest is 0.6.x"
  - id: sqlalchemy-minimum-pin
    choice: "sqlalchemy>=2.0.49"
    reason: "Python 3.14 breaks Optional[T] handling in SQLAlchemy <2.0.49 (TypeError in make_union_type)"
  - id: from-future-annotations
    choice: "Added from __future__ import annotations to user.py"
    reason: "Required for Python 3.14 compatibility with SQLAlchemy Mapped types"
  - id: rate-limit-approach
    choice: "Flask-Limiter @limiter.limit decorators on login route with methods=[POST] filter"
    reason: "Applying limits directly to route function with POST-only filter is the idiomatic Flask-Limiter 4.x approach"

metrics:
  duration: "5 minutes"
  completed: "2026-04-05"
  tasks-completed: 2
  tasks-total: 2
---

# Phase 01 Plan 01: App Factory and Magic-Link Auth Summary

**One-liner:** Flask app factory with SQLAlchemy 2.0 User model, stateless magic-link auth (itsdangerous), Alembic migrations, and per-IP/per-email rate limiting

## What Was Built

A complete Flask application skeleton with:

- **App factory** (`create_app(config_name)`) wiring all extensions and blueprints
- **User model** using SQLAlchemy 2.0 `Mapped`/`mapped_column` style — id, email, created_at, last_login_at
- **Alembic migration** initialized, first migration generated and applied (users table with email index)
- **Magic-link auth flow**: POST email → generate token → send/show link → verify → create-or-fetch user → login with 7-day session
- **Three auth templates**: login form (WCAG label), check-email confirmation, link-expired error page
- **Rate limiting**: 5 requests/hour per IP and 3 requests/hour per email on login POST
- **Health check** at `/health` (no auth required) returning `{"status": "healthy"}`
- **Config hierarchy**: DefaultConfig → DevelopmentConfig (SQLite fallback) → ProductionConfig (Cloud SQL via connector)
- **Dev-mode magic link**: when SENDGRID_API_KEY is absent, link is printed to console and flashed — dev works with zero external services

## Task Commits

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| 1 | App factory, config, extensions, User model | 1db36d3 | app/__init__.py, app/config.py, app/extensions.py, app/models/user.py, requirements.txt, migrations/ |
| 2 | Magic-link auth routes, templates, rate limiting | a5c125c | app/auth/routes.py, app/services/auth_tokens.py, all templates |

## Decisions Made

| Decision | Choice | Reason |
|----------|--------|--------|
| flask-login version | `>=0.6` | 0.7 tag does not exist on PyPI; latest is 0.6.x |
| SQLAlchemy minimum | `>=2.0.49` | Python 3.14 breaks `Optional[T]` type resolution in SQLAlchemy <2.0.49 |
| `from __future__ import annotations` | Added to user.py | Required for Python 3.14 SQLAlchemy Mapped type compatibility |
| Rate limit implementation | `@limiter.limit` with `methods=["POST"]` | Flask-Limiter 4.x idiomatic approach for POST-only limits on a GET+POST route |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Flask-Login version pin `>=0.7` does not exist**

- **Found during:** Task 1 — `pip install -r requirements.txt` failed
- **Issue:** The plan specified `flask-login>=0.7,<1` but 0.7 has never been released; latest is 0.6.3
- **Fix:** Changed pin to `flask-login>=0.6,<1`
- **Files modified:** `requirements.txt`
- **Commit:** 1db36d3

**2. [Rule 1 - Bug] SQLAlchemy 2.0.40 crashes on Python 3.14 with `Optional[T]` Mapped columns**

- **Found during:** Task 1 — `create_app('development')` raised `TypeError: descriptor '__getitem__' requires a 'typing.Union' object but received a 'tuple'`
- **Issue:** Python 3.14 changed internal `Union.__getitem__` behavior; SQLAlchemy 2.0.40 used the old API
- **Fix:** Upgraded to `sqlalchemy==2.0.49` (latest patch with Python 3.14 fix) and added `from __future__ import annotations` to user.py; pinned `sqlalchemy>=2.0.49,<3` in requirements.txt
- **Files modified:** `requirements.txt`, `app/models/user.py`
- **Commit:** 1db36d3

## Verification Results

All success criteria confirmed:

- `python -c "from app import create_app; app = create_app('development'); print('OK')"` → `OK`
- `flask db current` → `feb6e53d0a3e (head)`
- `Mapped` in user.py: confirmed; `db.Column` count: 0
- Full auth cycle tested programmatically: login form → POST → check-email → verify token → create user → login → logout → redirect to login
- `/health` returns `{"status": "healthy"}` without authentication
- Rate limiting decorators active on login POST endpoint
- Invalid tokens render link_expired page correctly

## Next Phase Readiness

Plan 01-02 can proceed. It should:

- Add CSS/styles to `app/static/css/main.css` (currently a placeholder)
- Enhance `app/templates/base.html` with disclaimer banner per legal requirements
- The app factory, User model, and auth flow are stable foundations
