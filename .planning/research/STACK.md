# Stack Research

**Domain:** Ontario Small Claims Court self-service platform (legal tech / document generation / AI-assisted assessment)
**Researched:** 2026-04-04
**Confidence:** HIGH (all versions verified against PyPI and official docs as of research date)

---

## Recommended Stack

### Core Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Flask | 3.1.3 | Web framework | Matches existing workflow. Lightweight, no ORM coupling. Flask 3.x dropped Python 3.8 support and cleaned up deprecated APIs — 3.1.x is the current stable series. For a POC with two partners this is the right weight; Django would add unnecessary scaffolding overhead. |
| Python | 3.12 (minimum 3.10) | Runtime | 3.12 is the LTS-adjacent release with meaningful performance gains. WeasyPrint 68.1 requires Python >= 3.10 — that's the binding constraint. Use 3.12 in Docker for best performance. |
| PostgreSQL | 15 | Relational database | Mandated by project constraints. Cloud SQL PostgreSQL 15 on GCP. Mature, well-supported on Cloud SQL. Version 15 added logical replication improvements and MERGE statement — neither critical for POC but fine as a stable choice. |
| SQLAlchemy | 2.0.48 | ORM / query layer | 2.0 API is the stable modern interface. The 1.x "legacy" query style is deprecated. Use mapped_column() and DeclarativeBase — these are the 2.0-native patterns. Flask-SQLAlchemy 3.1.1 wraps it correctly. |
| Flask-SQLAlchemy | 3.1.1 | Flask-SQLAlchemy integration | The canonical bridge. Version 3.x requires SQLAlchemy 2.0+. Provides scoped session management tied to request lifecycle automatically. |
| Gunicorn | 25.3.0 | WSGI server (production) | Standard for Flask + Cloud Run. Cloud Run recommendation: `--workers 1 --threads 8 --timeout 0` for container concurrency model. Never use Flask dev server in production. |

### Frontend Technologies

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Jinja2 | 3.1.6 | Server-side templating | Built into Flask. Template fragments pattern via `jinja2-fragments` enables HTMX partial renders without duplicating templates. Fastest server-render option with no JS build step. |
| HTMX | 2.0.8 | Hypermedia interactions | Replaces most SPA patterns with HTML attributes. Ideal for multi-step wizard — submit form step, server returns next step fragment, HTMX swaps it in. No client state management needed. v2.0 is stable since June 2024. |
| Alpine.js | 3.15.9 | Client-side sprinkles | Handles UI state that HTMX can't: toggle panels, date picker interactions, conditional field visibility. Scoped `x-data` declarations prevent state leakage between wizard steps. Keep usage minimal. |
| Tailwind CSS | v3.4.x (CDN) | Utility-first CSS | Project constraint specifies CDN. For a two-person POC, the CDN tradeoff is acceptable: ~27kB gzipped, no build step. Tailwind v4 CDN exists but requires a build step for `@apply` — v3 CDN via `cdn.tailwindcss.com` includes all utilities. **Important:** v3 CDN loads the full ~3MB uncompressed build in the browser; acceptable for POC, must switch to CLI build before any real user traffic. |
| jinja2-fragments | 1.11.0 | Template fragment rendering | Enables `render_block()` in Flask routes — render only the HTMX-targeted block from a full-page template. Critical for the wizard pattern: same template serves both full-page and fragment requests. |

### Database & Migrations

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Flask-Migrate | 4.1.0 | Migration management | Wraps Alembic with Flask CLI integration (`flask db init`, `flask db migrate`, `flask db upgrade`). v4.0+ auto-enables `compare_type=True` and `render_as_batch=True`. Simpler than raw Alembic for a two-person team. |
| psycopg2-binary | 2.9.11 | PostgreSQL driver | Binary distribution avoids system-level libpq compile dependency. For Docker + Cloud Run this is the right choice — no build dependencies needed. psycopg3 would offer async gains but Flask is synchronous and the complexity is not justified for this POC. |
| python-dotenv | 1.x | Local dev env vars | Loads `.env` for local development. In production (Cloud Run), env vars come from Secret Manager — dotenv is never loaded. |

### Authentication

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Flask-Login | 0.6.3 | Session management | Standard Flask auth extension. `@login_required`, `current_user`, session persistence. No database coupling — integrates with whatever User model you define. Adequate for POC email/password auth. |
| Flask-WTF | 1.2.2 | Forms + CSRF protection | Provides CSRF tokens for all form submissions including HTMX requests. **Critical for wizard:** HTMX sends HTMX-boosted requests which bypass CSRF unless headers are explicitly configured. Flask-WTF handles this cleanly with `CSRFProtect`. |
| Werkzeug | (bundled with Flask 3.1.3) | Password hashing | `werkzeug.security.generate_password_hash` / `check_password_hash` is already a Flask dependency. Uses PBKDF2-HMAC-SHA256. Sufficient for POC without adding Flask-Bcrypt as a separate dependency. Upgrade to bcrypt or argon2 before production. |

### AI Integration

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| anthropic | 0.89.0 | Claude API client | Official Python SDK. Synchronous `client.messages.create()` is appropriate for Flask (no async runtime). Use `claude-sonnet-4-6` model string for case assessment. SDK handles retries (2x default with exponential backoff) on 429/500 errors. |

**Model to use:** `claude-sonnet-4-6`
- $3/MTok input, $15/MTok output
- Fast latency (correct for interactive wizard UX)
- 64k max output (more than sufficient for case assessment summaries)
- 1M context window

**Model NOT to use:** `claude-opus-4-6` for this use case — 2x cost premium, slower, overkill for structured assessment prompts.

### PDF Generation

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| WeasyPrint | 68.1 | HTML → PDF conversion | Best choice for court forms that must match specific layouts. Render Jinja2 templates to HTML, then WeasyPrint converts. CSS-first workflow means form layout stays in templates (no low-level drawing API). Supports CSS paged media — `@page` rules for page size, margins, headers/footers per page (required for "disclaimer on every page" constraint). |

**WeasyPrint vs alternatives:**
- **ReportLab:** Low-level drawing API. Better for programmatic charts/tables. Overkill and harder to maintain than HTML templates for form-shaped documents.
- **pdfkit/wkhtmltopdf:** Requires wkhtmltopdf system binary. Known Docker headaches, abandoned upstream. Avoid.
- **xhtml2pdf:** Uses ReportLab under the hood with HTML interface. CSS support is incomplete — complex form layouts often break. WeasyPrint handles CSS Paged Media better.

**WeasyPrint Docker requirements (non-negotiable):** Requires Pango, Cairo, and GdkPixbuf system packages. Use Debian-based image (not Alpine) for simpler dependency resolution:

```dockerfile
RUN apt-get update && apt-get install -y \
    libpango-1.0-0 \
    libpangocairo-1.0-0 \
    libcairo2 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    && rm -rf /var/lib/apt/lists/*
```

Alpine Linux requires significantly more manual work for WeasyPrint's ctypes library loading. Use `python:3.12-slim` (Debian-based) as the Docker base.

### Deployment & Infrastructure

| Technology | Version | Purpose | Why Recommended |
|------------|---------|---------|-----------------|
| Docker | Multi-stage build | Containerization | Multi-stage: builder stage installs dependencies, final stage copies only what's needed. Keeps image size down. Use `python:3.12-slim` (Debian) to satisfy WeasyPrint system dependencies. |
| GCP Cloud Run | — | Container hosting | Scales to zero — $0 idle cost for a POC. Northamerica-northeast1 (Montreal) for Canadian data residency. HTTP/2 enabled by default. Configure `--min-instances=0 --max-instances=2` for POC budget control. |
| GCP Artifact Registry | — | Container registry | Recommended over Container Registry (deprecated). Store images at `northamerica-northeast1-docker.pkg.dev`. |
| GCP Secret Manager | — | Secrets at runtime | `ANTHROPIC_API_KEY`, `DATABASE_URL`, `SECRET_KEY` stored as secrets. Cloud Run references them via env var bindings — no secrets in Docker image or env file in production. |
| GCP Cloud SQL | PostgreSQL 15 | Managed database | Cloud SQL Auth Proxy not needed for Cloud Run — use Unix socket via `?host=/cloudsql/...` in the DATABASE_URL. Enable private IP. |
| GitHub Actions | — | CI/CD | On push to `main`: build image → push to Artifact Registry → deploy to Cloud Run. Use Workload Identity Federation (keyless auth) — no long-lived service account keys. |

---

## Installation

```bash
# requirements.txt (production)
Flask==3.1.3
Flask-SQLAlchemy==3.1.1
Flask-Migrate==4.1.0
Flask-Login==0.6.3
Flask-WTF==1.2.2
SQLAlchemy==2.0.48
psycopg2-binary==2.9.11
anthropic==0.89.0
WeasyPrint==68.1
jinja2-fragments==1.11.0
gunicorn==25.3.0
python-dotenv==1.0.1

# requirements-dev.txt
pytest
pytest-flask
black
ruff
```

```html
<!-- Tailwind CSS CDN (v3, in base.html) -->
<script src="https://cdn.tailwindcss.com"></script>

<!-- HTMX CDN (in base.html) -->
<script src="https://cdn.jsdelivr.net/npm/htmx.org@2.0.8/dist/htmx.min.js"></script>

<!-- Alpine.js CDN (defer required, in base.html) -->
<script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.15.9/dist/cdn.min.js"></script>
```

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Web framework | Flask 3.1.3 | Django 5.x | Django ORM, admin, and scaffolding are unnecessary complexity for this POC scope. Flask matches existing workflow. Non-negotiable constraint. |
| Web framework | Flask 3.1.3 | FastAPI | FastAPI async model is ideal for high-concurrency APIs, not multi-step server-rendered wizard UIs. Jinja2 integration is secondary, not first-class. Flask is cleaner for this pattern. |
| PDF generation | WeasyPrint | ReportLab | ReportLab requires programmatic layout API — HTML/CSS template workflow is far simpler for form-shaped legal documents. |
| PDF generation | WeasyPrint | pdfkit/wkhtmltopdf | wkhtmltopdf is effectively abandoned. Docker image bloat. Headless Chrome alternative (Playwright) is heavier. |
| PDF generation | WeasyPrint | Puppeteer/Playwright | Adds a Node.js runtime dependency for a Python-only project. Overkill for static form PDFs. |
| ORM | SQLAlchemy 2.0 | raw psycopg2 | SQLAlchemy 2.0 provides type-safe mapped models, migration support via Flask-Migrate, and query abstraction. The ORM overhead is worthwhile for entity-heavy domain (claims, documents, deadlines, users). |
| Frontend | HTMX + Alpine.js | React/Vue SPA | SPA adds build toolchain, client state management, API design overhead. HTMX + Jinja2 keeps the stack Pythonic and eliminates a separate API layer. Perfectly suited for wizard UX. |
| Auth | Flask-Login | Flask-Security-Too | Flask-Security-Too is comprehensive (roles, TOTP) but heavy for a POC needing only email/password sessions. Flask-Login is minimal and sufficient. |
| AI model | claude-sonnet-4-6 | claude-opus-4-6 | Sonnet 4.6 is fast (interactive UX requirement) and $3/MTok vs $5/MTok. Opus would be justified for complex reasoning tasks, not structured assessment prompt completion. |
| PostgreSQL driver | psycopg2-binary | psycopg (v3) | psycopg3 shines for async. Flask is synchronous — the async advantage is moot. psycopg2-binary binary distribution simplifies Docker builds. |
| Tailwind | v3 CDN | v4 CDN | Tailwind v4 CDN requires `@tailwindcss/browser` which has limitations. v3 CDN is the established pattern. For POC, CDN vs build-step difference is acceptable. |
| Migrations | Flask-Migrate | Raw Alembic | Flask-Migrate is a thin Flask wrapper around Alembic that adds CLI commands. Same underlying tool, less boilerplate for a small team. |

---

## What NOT to Use

| Avoid | Why | Use Instead |
|-------|-----|-------------|
| Flask dev server in production (`flask run`) | Not thread-safe, no graceful shutdown, single-threaded. Cloud Run will receive concurrent requests. | Gunicorn with `--workers 1 --threads 8` |
| pdfkit / wkhtmltopdf | wkhtmltopdf upstream is abandoned. Requires large binary. Docker builds are fragile. | WeasyPrint 68.1 |
| AI-generated document content | Highest regulatory risk — hallucinated legal text in a Form 7A is a liability. LSO considers this unauthorized legal advice territory. | Deterministic Jinja2 templates only for Form 7A, 9A, Demand Letter |
| Directive language in Claude prompts | "You should file by..." or "I recommend..." language in AI output crosses from legal information to legal advice under LSO guidelines. | Statistical framing: "Cases with similar characteristics typically..." |
| Alpine base image for Docker | WeasyPrint's ctypes loading has known issues on Alpine (library path resolution failure for cairo). Multiple manual workarounds required. | python:3.12-slim (Debian-based) |
| Long-lived GCP service account keys in GitHub Secrets | Key rotation burden, security risk if repository is compromised. | Workload Identity Federation (keyless auth) in GitHub Actions |
| SQLAlchemy 1.x legacy query style (`db.session.query(Model)`) | Deprecated in SQLAlchemy 2.0. Will be removed in a future major version. More verbose than 2.0 style. | SQLAlchemy 2.0 `select()` + `db.session.execute()` |
| Tailwind v3 CDN in production (real users) | ~3MB uncompressed download, no purging, no caching by class name, browser-side JIT has FOUC risk. | Tailwind CLI build generating purged CSS for real production deployment |
| `.env` file in Docker image | Secrets baked into image layers are accessible to anyone with pull access. | GCP Secret Manager bound to Cloud Run service via env var references |
| Flask-Bcrypt (separate package) for POC | Werkzeug (already a Flask dependency) provides PBKDF2-HMAC-SHA256 which is secure for POC. Flask-Bcrypt 1.0.1 was last released April 2022 — maintenance uncertain. | `werkzeug.security.generate_password_hash` for POC; migrate to `argon2-cffi` before production |

---

## Stack Patterns by Variant

**HTMX wizard step rendering:**
- Use `jinja2-fragments` `render_block()` to return only the current step's block from a shared template
- Detect HTMX request via `request.headers.get("HX-Request")` — return full page for direct URL access, fragment for HTMX swap
- Store wizard state server-side in Flask session (not client-side) — avoids state loss on browser refresh

**PDF generation flow:**
- Render Jinja2 template to HTML string (`render_template_string` or `render_template`)
- Pass HTML to `weasyprint.HTML(string=html).write_pdf()`
- Stream bytes response with `Content-Type: application/pdf`
- Include `@page { @bottom-center { content: "LEGAL INFORMATION ONLY — NOT LEGAL ADVICE"; } }` CSS for per-page disclaimer

**Claude API integration (regulatory guardrails):**
- Construct system prompt that hardcodes the statistical framing constraint
- Never expose raw Claude output to users without post-processing filter for directive language
- Always append disclaimer block to AI-generated content before rendering
- Store prompt/response pair in DB for audit trail (partner lawyer review capability)

**CSRF with HTMX:**
- Add CSRF token to meta tag: `<meta name="csrf-token" content="{{ csrf_token() }}">`
- Configure HTMX to include it: `document.body.addEventListener('htmx:configRequest', (event) => { event.detail.headers['X-CSRFToken'] = document.querySelector('meta[name="csrf-token"]').content; })`

---

## Version Compatibility

| Package | Compatible With | Notes |
|---------|-----------------|-------|
| Flask 3.1.3 | Werkzeug 3.x, Jinja2 3.1.x | Flask pins these internally — do not install separately unless pinning exact version |
| Flask-SQLAlchemy 3.1.1 | SQLAlchemy >= 2.0.16 | Will NOT work with SQLAlchemy 1.x |
| Flask-Migrate 4.1.0 | Flask-SQLAlchemy 3.x, Alembic 1.x | Alembic 1.18.4 is the current stable; Flask-Migrate pulls it in automatically |
| WeasyPrint 68.1 | Python >= 3.10 | This is the binding minimum Python version for the entire stack |
| psycopg2-binary 2.9.11 | Python >= 3.9, PostgreSQL 9.6-16 | Works with Cloud SQL PostgreSQL 15 |
| anthropic 0.89.0 | Python >= 3.9 | Use synchronous `client = anthropic.Anthropic()` — not async client |
| jinja2-fragments 1.11.0 | Jinja2 >= 3.0, Flask >= 2.0 | Use `from jinja2_fragments.flask import render_block` |

---

## Sources

- [Flask PyPI](https://pypi.org/project/Flask/) — Version 3.1.3 confirmed (Feb 19, 2026)
- [Flask-SQLAlchemy PyPI](https://pypi.org/project/Flask-SQLAlchemy/) — Version 3.1.1 confirmed
- [SQLAlchemy blog](https://www.sqlalchemy.org/blog/2025/10/10/sqlalchemy-2.0.44-released/) — Confirmed 2.0.x active maintenance
- [anthropic PyPI](https://pypi.org/project/anthropic/) — Version 0.89.0 confirmed (Apr 3, 2026)
- [Anthropic Models Overview](https://platform.claude.com/docs/en/about-claude/models/overview) — claude-sonnet-4-6 confirmed as current recommended model (HIGH confidence, official docs)
- [WeasyPrint PyPI](https://pypi.org/project/weasyprint/) — Version 68.1 confirmed (Feb 6, 2026), Python >= 3.10 requirement
- [WeasyPrint Docs](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html) — System dependency requirements confirmed
- [Flask-Migrate PyPI](https://pypi.org/project/Flask-Migrate/) — Version 4.1.0 confirmed (Jan 10, 2025)
- [Flask-Login PyPI](https://pypi.org/project/Flask-Login/) — Version 0.6.3 confirmed
- [Flask-WTF PyPI](https://pypi.org/project/Flask-WTF/) — Version 1.2.2 confirmed (Oct 24, 2024)
- [psycopg2-binary PyPI](https://pypi.org/project/psycopg2-binary/) — Version 2.9.11 confirmed (Oct 10, 2025)
- [gunicorn PyPI](https://pypi.org/project/gunicorn/) — Version 25.3.0 confirmed (Mar 27, 2026)
- [Jinja2 PyPI](https://pypi.org/project/jinja2/) — Version 3.1.6 confirmed (Mar 5, 2025)
- [jinja2-fragments PyPI](https://pypi.org/project/jinja2-fragments/) — Version 1.11.0 confirmed (Nov 20, 2025)
- [HTMX releases](https://github.com/bigskysoftware/htmx/releases) — Version 2.0.8 confirmed as current stable 2.x
- [Alpine.js releases](https://github.com/alpinejs/alpine/releases) — Version 3.15.9 confirmed (recent, Apr 2026)
- [Google Cloud Run Python tips](https://cloud.google.com/run/docs/tips/python) — Gunicorn configuration guidance
- [Tailwind v3 CDN docs](https://v3.tailwindcss.com/docs/installation/play-cdn) — CDN dev-only caveat confirmed; acceptable for POC

---

## Confidence Notes

| Area | Confidence | Basis |
|------|------------|-------|
| All library versions | HIGH | Verified directly against PyPI as of 2026-04-04 |
| Claude model name `claude-sonnet-4-6` | HIGH | Verified against official Anthropic Models page |
| WeasyPrint Docker system deps | HIGH | Verified against official WeasyPrint 68.1 docs |
| Gunicorn Cloud Run config | MEDIUM | Based on Google official docs + community sources; test `--threads` value against your workload |
| Tailwind CDN v3 for POC acceptability | MEDIUM | Community consensus; Tailwind Labs officially discourages production CDN use |
| HTMX CSRF header pattern | MEDIUM | Documented pattern, not Flask-specific official source |

---

*Stack research for: Bryan and Bryan — Ontario Small Claims Court platform*
*Researched: 2026-04-04*
