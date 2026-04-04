# Phase 1: Foundation - Research

**Researched:** 2026-04-04
**Domain:** Flask web app skeleton, magic-link auth, regulatory disclaimer layer, AI output guardrail wrapper, GCP Cloud Run / Cloud SQL infrastructure
**Confidence:** HIGH (core stack verified via Context7 and official docs)

---

## Summary

Phase 1 establishes the skeleton every subsequent phase builds on: app factory, database models, magic-link authentication, a regulatory disclaimer that appears on every page, an AI output guardrail wrapper, and the GCP infrastructure pipeline. All five areas have well-understood standard approaches in the Flask/GCP ecosystem.

The core Flask stack (Flask 3.x + Flask-SQLAlchemy 3.x with SQLAlchemy 2.0-style mapped columns + Flask-Migrate/Alembic + Flask-Login) is stable and well-documented. Magic-link auth is implemented using `itsdangerous.URLSafeTimedSerializer` — no external auth service needed, no database token table needed (the signature IS the token). The AI guardrail is a pure Python wrapper function/class that post-processes LLM output before it reaches any template; this is a custom build but a trivially simple one. Infrastructure is Docker multi-stage build → GCP Artifact Registry → Cloud Run, with Workload Identity Federation for keyless GitHub Actions deployment.

**Primary recommendation:** Use the full standard stack below. Do not reach for external auth services (Auth0, etc.) — `itsdangerous` covers magic-link tokens cleanly with zero database overhead. Do not use Flask-Mail for production email — use `sendgrid-python` SDK directly.

---

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | 3.1.x | Web framework, routing, templating | Pallets project, HTMX/server-render friendly |
| Flask-SQLAlchemy | 3.0.x | ORM integration with Flask | Official Pallets-eco extension, SQLAlchemy 2.0 API |
| SQLAlchemy | 2.0 | ORM / database toolkit | `Mapped`/`mapped_column` type-annotated style is current standard |
| Flask-Migrate | 4.x | Alembic migrations via `flask db` CLI | Official wrapper, wraps Alembic completely |
| Flask-Login | 0.7.x | Session management, `@login_required`, user loader | De-facto standard for Flask user sessions |
| itsdangerous | 2.2.x | `URLSafeTimedSerializer` for magic-link tokens | Bundled with Flask ecosystem; no DB token storage needed |
| Flask-Limiter | 4.1.x | Rate limiting on magic-link request endpoint | Official extension, supports custom key functions |
| sendgrid-python | latest | Transactional email delivery | HTTP API more reliable than SMTP/Flask-Mail in production |
| gunicorn | latest | WSGI server for production | GCP official recommendation for Cloud Run |
| cloud-sql-python-connector | latest | Secure Cloud SQL connection from Cloud Run | GCP official library; handles IAM auth + connection pooling |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| python-dotenv | latest | `.env` file loading for local dev | Dev config only; Cloud Run uses env vars natively |
| pg8000 | latest | PostgreSQL driver for cloud-sql-python-connector | Lighter than psycopg2, pure Python, officially supported |
| Jinja2 | (Flask dep) | HTML templating + base template with disclaimer block | Already included with Flask |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| itsdangerous tokens | Database-stored tokens (UUID + expiry column) | DB tokens allow forced invalidation but require a table and queries; itsdangerous tokens are stateless and expire via signature — simpler for MVP |
| sendgrid-python | Flask-Mail + SMTP | Flask-Mail is SMTP-based; production deliverability is worse; no delivery tracking |
| cloud-sql-python-connector | Direct TCP + Cloud SQL Auth Proxy sidecar | Connector is simpler for Cloud Run (no sidecar container needed) |
| Flask-Login | Flask-Security-Too | Flask-Security-Too is heavier (includes registration flow, 2FA etc.); overkill for magic-link only |
| Flask-Limiter (in-memory) | Flask-Limiter + Redis | In-memory works for single Cloud Run instance; Redis required once multiple instances scale — use Redis (Cloud Memorystore) from the start to avoid surprises |

### Installation

```bash
pip install flask flask-sqlalchemy flask-migrate flask-login flask-limiter \
    itsdangerous sendgrid gunicorn \
    "cloud-sql-python-connector[pg8000]" python-dotenv
```

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── __init__.py          # create_app() factory
├── extensions.py        # db, migrate, login_manager, limiter (instantiated without app)
├── models/
│   ├── __init__.py
│   └── user.py          # User model (UserMixin for Flask-Login)
├── auth/
│   ├── __init__.py      # Blueprint definition
│   └── routes.py        # /login (GET/POST), /auth/verify, /logout
├── main/
│   ├── __init__.py
│   └── routes.py        # index redirect, /health
├── services/
│   └── ai_guardrail.py  # AIGuardrail wrapper class
├── templates/
│   ├── base.html        # disclaimer footer, HTMX/Alpine CDN or local, skip-nav
│   └── auth/
│       └── login.html   # magic link request form
├── static/
│   └── css/
│       └── main.css     # mobile-first base styles
└── config.py            # Config classes (Default, Development, Production)
migrations/              # Alembic migration scripts (flask db init)
Dockerfile
.github/
└── workflows/
    └── deploy.yml       # GitHub Actions → Cloud Run
```

### Pattern 1: App Factory with Extensions Module

**What:** Extensions are instantiated at module level (no app bound), then `init_app(app)` is called inside `create_app()`. This avoids circular imports and supports testing with different configs.

**When to use:** Always — this is the only correct pattern for non-trivial Flask apps.

```python
# app/extensions.py
# Source: Context7 /pallets/flask (appfactories.md)
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
limiter = Limiter(key_func=get_remote_address)

# app/__init__.py
from flask import Flask
from .extensions import db, migrate, login_manager, limiter

def create_app(config_name='default'):
    app = Flask(__name__)
    app.config.from_object(config[config_name])

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    limiter.init_app(app)

    from .auth import auth_bp
    from .main import main_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(main_bp)

    return app
```

### Pattern 2: SQLAlchemy 2.0-Style User Model

**What:** Use `Mapped` and `mapped_column` type annotations. This is the current SQLAlchemy 2.0 style — NOT `db.Column(db.String)`.

```python
# app/models/user.py
# Source: Context7 /pallets-eco/flask-sqlalchemy (quickstart.rst)
from flask_login import UserMixin
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, DateTime
from datetime import datetime, timezone
from app.extensions import db

class User(db.Model, UserMixin):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc)
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
```

Note: No `password_hash` column — this is magic-link only.

### Pattern 3: Magic Link Auth Flow

**What:** Stateless token using `itsdangerous.URLSafeTimedSerializer`. Token encodes email, is signed with app SECRET_KEY + salt, verified on click. No database lookup for the token itself.

```python
# app/services/auth_tokens.py
# Source: Context7 /pallets/itsdangerous (url_safe.md, llms.txt)
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app

MAGIC_LINK_SALT = "magic-link-auth"
MAGIC_LINK_MAX_AGE = 900  # 15 minutes recommended (see discretion section)

def generate_magic_token(email: str) -> str:
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=MAGIC_LINK_SALT)
    return s.dumps(email)

def verify_magic_token(token: str) -> str | None:
    s = URLSafeTimedSerializer(current_app.config['SECRET_KEY'], salt=MAGIC_LINK_SALT)
    try:
        email = s.loads(token, max_age=MAGIC_LINK_MAX_AGE)
        return email
    except SignatureExpired:
        return None  # expired
    except BadSignature:
        return None  # tampered
```

### Pattern 4: Flask-Login Configuration for 7-Day Sessions

**What:** `login_user(user, remember=True)` sets the remember-me cookie. Duration is controlled by `REMEMBER_COOKIE_DURATION`. Secure cookie flags must be set explicitly.

```python
# app/config.py
from datetime import timedelta

class ProductionConfig:
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)
    REMEMBER_COOKIE_DURATION = timedelta(days=7)
    REMEMBER_COOKIE_SECURE = True      # HTTPS only
    REMEMBER_COOKIE_HTTPONLY = True    # no JS access
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

# auth route: always call login_user with remember=True
# Source: Context7 /maxcountryman/flask-login (index.rst)
login_manager.session_protection = "strong"
login_manager.login_view = "auth.login"
```

**Redirect-after-login:** Flask-Login stores the original destination in `next` query parameter. Always validate it before redirecting to prevent open redirect attacks.

```python
# Source: Context7 /maxcountryman/flask-login (index.rst)
from flask import request, redirect, url_for
from flask_login import url_has_allowed_host_and_scheme

next_page = request.args.get('next')
if not next_page or not url_has_allowed_host_and_scheme(next_page, request.host):
    next_page = url_for('main.index')
return redirect(next_page)
```

### Pattern 5: AI Guardrail Wrapper

**What:** A pure Python wrapper that post-processes every LLM response before it can reach a template. The wrapper enforces statistical framing and strips/replaces directive language. This is a custom class, not a third-party library — it needs to encode the product's specific legal requirements, and the guardrails-ai framework is overkill for a single well-defined rule.

**Architecture:** The wrapper is a service class called by any route that invokes AI. It never short-circuits to "pass through" — every response is processed. The output is either transformed text or a safe error state.

```python
# app/services/ai_guardrail.py
import re
from dataclasses import dataclass
from enum import Enum

class GuardrailStatus(Enum):
    PASSED = "passed"
    TRANSFORMED = "transformed"
    BLOCKED = "blocked"

@dataclass
class GuardrailResult:
    status: GuardrailStatus
    text: str
    original: str

# Directive patterns that must never reach users
# Lawyer must review and approve this list before any AI feature ships
DIRECTIVE_PATTERNS = [
    (r'\byou should\b', 'cases with similar characteristics typically'),
    (r'\byou must\b', 'the procedure requires'),
    (r'\byou need to\b', 'the process involves'),
    (r'\bI recommend\b', 'statistically'),
    (r'\bmy advice\b', 'based on similar cases'),
    (r'\byou will win\b', 'cases with these characteristics have'),
    (r'\byou will lose\b', 'cases with these characteristics have'),
]

class AIGuardrail:
    def process(self, raw_output: str) -> GuardrailResult:
        text = raw_output
        transformed = False

        for pattern, replacement in DIRECTIVE_PATTERNS:
            new_text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
            if new_text != text:
                transformed = True
                text = new_text

        status = GuardrailStatus.TRANSFORMED if transformed else GuardrailStatus.PASSED
        return GuardrailResult(status=status, text=text, original=raw_output)

guardrail = AIGuardrail()
```

**IMPORTANT:** The specific directive patterns require supervising lawyer sign-off before any AI feature ships (noted blocker in STATE.md). The architecture ships in Phase 1; the pattern list is a placeholder pending legal review.

### Pattern 6: Docker Multi-Stage Build

**What:** Builder stage installs deps into a venv; runtime stage copies only the venv and app code. Result is a minimal image on `python:3.12-slim`.

```dockerfile
# Dockerfile
# Source: Verified via multiple 2025-2026 sources including GCP official docs

FROM python:3.12-slim AS builder
WORKDIR /app
RUN python -m venv /app/.venv
COPY requirements.txt .
RUN /app/.venv/bin/pip install --no-cache-dir -r requirements.txt

FROM python:3.12-slim AS runtime
WORKDIR /app
# Non-root user for security
RUN useradd --create-home appuser
COPY --from=builder /app/.venv /app/.venv
COPY . .
RUN chown -R appuser:appuser /app
USER appuser

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1

EXPOSE 8080
CMD exec gunicorn --bind :$PORT --workers 1 --threads 8 --timeout 0 "app:create_app()"
```

**Cloud Run binding:** Must use `$PORT` env var (Cloud Run sets it to 8080). `--workers 1 --threads 8` is Google's recommended starting configuration.

### Pattern 7: Cloud SQL Python Connector with SQLAlchemy

**What:** Use the `cloud-sql-python-connector` instead of Unix socket path or TCP + Auth Proxy. The connector handles IAM authentication and connection creation; SQLAlchemy handles pooling via the `creator` pattern.

```python
# app/db.py
# Source: github.com/GoogleCloudPlatform/cloud-sql-python-connector README
from google.cloud.sql.connector import Connector
import sqlalchemy

def get_engine(connector: Connector):
    def getconn():
        return connector.connect(
            instance_connection_name=os.environ["CLOUD_SQL_INSTANCE"],  # "project:region:instance"
            driver="pg8000",
            db=os.environ["DB_NAME"],
            enable_iam_auth=True,   # use Cloud Run service account, no password needed
            user=os.environ["DB_USER"],
        )
    return sqlalchemy.create_engine("postgresql+pg8000://", creator=getconn)
```

### Pattern 8: GitHub Actions → Cloud Run Deployment

**What:** Workload Identity Federation (keyless) is the current best practice. No service account key JSON stored in GitHub Secrets.

```yaml
# .github/workflows/deploy.yml
name: Deploy to Cloud Run
on:
  push:
    branches: [main]

jobs:
  deploy:
    runs-on: ubuntu-latest
    permissions:
      contents: read
      id-token: write   # required for WIF

    steps:
      - uses: actions/checkout@v4

      - id: auth
        uses: google-github-actions/auth@v3
        with:
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Build and push image
        run: |
          gcloud auth configure-docker northamerica-northeast1-docker.pkg.dev
          docker build -t northamerica-northeast1-docker.pkg.dev/$PROJECT_ID/app/app:${{ github.sha }} .
          docker push northamerica-northeast1-docker.pkg.dev/$PROJECT_ID/app/app:${{ github.sha }}

      - uses: google-github-actions/deploy-cloudrun@v3
        with:
          service: small-claims-app
          region: northamerica-northeast1
          image: northamerica-northeast1-docker.pkg.dev/${{ secrets.GCP_PROJECT_ID }}/app/app:${{ github.sha }}
```

### Pattern 9: Health Check Endpoint

```python
# app/main/routes.py
from flask import jsonify

@main_bp.route('/health')
def health():
    return jsonify({"status": "healthy"}), 200
```

### Pattern 10: Regulatory Disclaimer in Base Template

**What:** A Jinja2 block in `base.html` that cannot be overridden to nothing — it contains the static disclaimer text. The `{% block disclaimer %}` exists but always renders the default content if empty.

```html
<!-- app/templates/base.html (excerpt) -->
<!-- Source: WCAG 2.1 AA landmark pattern from W3C WAI -->
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}Bryan and Bryan{% endblock %}</title>
    <link rel="stylesheet" href="{{ url_for('static', filename='css/main.css') }}">
</head>
<body>
    <a href="#main-content" class="skip-nav">Skip to main content</a>

    <header role="banner">
        <nav role="navigation" aria-label="Main navigation">
            {% block nav %}{% endblock %}
        </nav>
    </header>

    <main id="main-content" role="main">
        {% block content %}{% endblock %}
    </main>

    <footer role="contentinfo">
        <div class="disclaimer">
            <p>
                <strong>Legal Information, Not Legal Advice:</strong>
                The information provided by this tool is for general informational purposes only
                and does not constitute legal advice. It is not a substitute for advice from a
                qualified lawyer or paralegal. For advice about your specific situation,
                please consult a licensed legal professional.
            </p>
            <p>
                AI-generated assessments describe statistical patterns in similar cases and
                do not predict outcomes in your case.
            </p>
        </div>
    </footer>
</body>
</html>
```

**Disclaimer wording basis:** Modelled on the Ontario government's own Guide to Procedures in Small Claims Court disclaimer: *"Nothing contained...is intended as, or should be taken or understood as, legal advice."* The exact wording should be reviewed and approved by the supervising lawyer before launch.

### Anti-Patterns to Avoid

- **Old-style `db.Column()` syntax:** Use `Mapped[type] = mapped_column(...)` — the `db.Column` style still works but is the SQLAlchemy 1.x API. New code should use the 2.0 style.
- **Storing magic-link tokens in the database:** Unnecessary complexity. `itsdangerous` tokens are self-expiring and cryptographically signed.
- **`login_user()` without `remember=True`:** Session ends on browser close, which contradicts the 7-day session requirement.
- **No salt on `URLSafeTimedSerializer`:** Always pass `salt=` to distinguish token contexts (magic-link token vs any future token type).
- **`SESSION_COOKIE_SECURE = False` in production:** Must be `True` or the cookie transmits over HTTP.
- **Pinning GitHub Actions to mutable tags:** Pin to full SHA for security (e.g., `actions/checkout@v4` is acceptable; custom actions should be SHA-pinned).
- **Passing `next` redirect without validation:** Open redirect vulnerability. Always call `url_has_allowed_host_and_scheme()`.
- **Flask-Limiter with default in-memory storage on multi-instance Cloud Run:** In-memory limits are per-instance. Use Redis (Cloud Memorystore) as the storage backend so rate limits are enforced globally.
- **`DB.Column` with `TRACK_MODIFICATIONS = True`:** Deprecated config that generates warnings; always set `SQLALCHEMY_TRACK_MODIFICATIONS = False`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Time-limited signed tokens | Custom JWT or UUID stored in DB | `itsdangerous.URLSafeTimedSerializer` | Handles signing, timestamp, expiry, and tamper detection — all in 3 lines |
| Session management / login flow | Custom cookie + session logic | Flask-Login | Handles remember-me cookies, session protection, user loader, `@login_required`, `next` URL — all edge-cased |
| Database migrations | Manual SQL files | Flask-Migrate + Alembic | Auto-detects model changes, generates versioned migration scripts, handles upgrades and rollbacks |
| Rate limiting | Counter in Redis with manual TTL | Flask-Limiter | Multiple storage backends, per-route and per-key configuration, 429 responses automatic |
| Cloud SQL IAM connection | Unix socket path construction | cloud-sql-python-connector | Handles IAM auth, connection refresh, socket path length limits (108-char Linux limit is a real footgun) |
| Output directive filtering | Hand-coded regex in route handlers | `AIGuardrail` service class called from one place | Centralised = auditable; can't be skipped by adding a new route |

**Key insight:** The magic-link flow looks simple but has 4 security edge cases (open redirect, token replay, timing attacks, rate limiting per-email). Using `itsdangerous` + Flask-Login handles all of them except rate limiting, which is one Flask-Limiter decorator.

---

## Common Pitfalls

### Pitfall 1: In-Memory Rate Limiter on Cloud Run

**What goes wrong:** Flask-Limiter defaults to `memory://` storage. Cloud Run scales to multiple instances. Each instance has its own counter. A user can send 5×N magic link emails (where N = instance count).

**Why it happens:** Works fine locally and in single-instance staging, breaks silently in production.

**How to avoid:** Configure Flask-Limiter with `storage_uri="redis://..."` pointing to Cloud Memorystore from the start.

**Warning signs:** No errors, but users report receiving more emails than the stated limit.

### Pitfall 2: Magic Link Delivered but Already Expired

**What goes wrong:** User receives email, clicks 30 minutes later, gets "invalid link" error with no explanation.

**Why it happens:** Short token expiry (e.g., 10 minutes) + slow email delivery.

**How to avoid:** 15-minute expiry is the recommended minimum for magic links (balances security vs. email delivery delays). Show a clear "link expired — request a new one" message on the verify endpoint when `SignatureExpired` is caught. Always distinguish expired vs. invalid in the UX.

**Warning signs:** User support reports about "broken links".

### Pitfall 3: PERMANENT_SESSION_LIFETIME Not Activated

**What goes wrong:** Set `PERMANENT_SESSION_LIFETIME = timedelta(days=7)` but sessions still expire on browser close.

**Why it happens:** The setting only applies when `session.permanent = True` is set, OR when `login_user(user, remember=True)` is called. The config alone does nothing.

**How to avoid:** Always call `login_user(user, remember=True)` in the magic link verify route.

### Pitfall 4: Cloud SQL Unix Socket Path Too Long

**What goes wrong:** Connection to Cloud SQL via unix socket fails with "OSError: AF_UNIX path too long".

**Why it happens:** Linux has a 108-character limit on unix socket paths. Cloud Run's default `/cloudsql/project:region:instance/.s.PGSQL.5432` can exceed this for long project names.

**How to avoid:** Use `cloud-sql-python-connector` instead of direct socket path. The connector manages the socket internally.

### Pitfall 5: `db.Column` Legacy Style Mixed with `Mapped` Style

**What goes wrong:** SQLAlchemy emits deprecation warnings or behaves unexpectedly when models mix old-style `db.Column(db.String)` and new-style `Mapped[str] = mapped_column()`.

**Why it happens:** Flask-SQLAlchemy documentation has both old and new examples; easy to copy the wrong one.

**How to avoid:** Use only the 2.0-style (`Mapped` + `mapped_column`) across all models. Establish this as a project standard in the first commit.

### Pitfall 6: Disclaimer Template Block That Can Be Overridden to Nothing

**What goes wrong:** A child template does `{% block disclaimer %}{% endblock %}` with empty content, accidentally hiding the legal disclaimer.

**Why it happens:** Standard Jinja2 block override semantics allow this.

**How to avoid:** Don't use a block for the disclaimer. Hardcode the disclaimer in `base.html` without a wrapping block. Or, if styling flexibility is needed, use a `{% block disclaimer_class %}{% endblock %}` for CSS only, not for content.

### Pitfall 7: REMEMBER_COOKIE_SECURE Not Set in Production

**What goes wrong:** Session cookies transmit over HTTP, making them vulnerable to interception.

**Why it happens:** Flask defaults `SESSION_COOKIE_SECURE = False` to allow dev over HTTP.

**How to avoid:** Use separate `DevelopmentConfig` and `ProductionConfig` classes. `ProductionConfig` always sets `SESSION_COOKIE_SECURE = True` and `REMEMBER_COOKIE_SECURE = True`. Cloud Run always serves HTTPS.

---

## Code Examples

Verified patterns from official sources:

### Flask-Migrate Workflow (verified via Context7)

```bash
# First time setup
flask db init
flask db migrate -m "Initial schema: users table"
flask db upgrade

# After model changes
flask db migrate -m "Add last_login_at to users"
flask db upgrade
```

### Rate Limiting Magic Link Requests (verified via Context7)

```python
# Source: Context7 /alisaifee/flask-limiter (llms.txt, recipes.md)
from flask_limiter.util import get_remote_address
from flask import request

# Rate limit by IP AND by submitted email (belt + suspenders)
def get_email_from_form():
    return request.form.get('email', 'anonymous').lower()

@auth_bp.route('/login', methods=['POST'])
@limiter.limit("5 per hour", key_func=get_remote_address)            # per IP
@limiter.limit("3 per hour", key_func=get_email_from_form)           # per email
def send_magic_link():
    ...
```

### User Loader for Flask-Login (verified via Context7)

```python
# Source: Context7 /maxcountryman/flask-login (index.rst)
from app.extensions import login_manager
from app.models.user import User

@login_manager.user_loader
def load_user(user_id: str):
    return db.session.get(User, int(user_id))
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `db.Column(db.String)` model style | `Mapped[str] = mapped_column()` | SQLAlchemy 2.0 (2023) | IDE type checking, cleaner syntax |
| Service account key JSON in GitHub Secrets | Workload Identity Federation (OIDC) | GCP recommended since 2022, standard by 2024 | Keyless auth, no secret rotation |
| Flask-Mail SMTP for transactional email | Direct provider SDK (sendgrid-python) | Ongoing | Better deliverability, tracking, no SMTP config |
| `pip install` in Dockerfile final stage | Multi-stage build, copy venv | Standard since Docker BuildKit | 50-60% smaller images |
| `db.create_all()` for schema | Alembic migrations via Flask-Migrate | Flask-Migrate since 2012, still correct | Versioned, reversible schema changes |

**Deprecated/outdated:**
- `SQLALCHEMY_TRACK_MODIFICATIONS = True`: Deprecated, set to `False` or omit.
- Storing magic tokens in DB: Still common in tutorials but unnecessary with `itsdangerous`.
- Service account key JSON stored in GitHub: Still documented but superseded by WIF.

---

## Claude's Discretion: Recommendations

These areas were left to Claude's judgment in CONTEXT.md.

### Magic Link Expiry Duration

**Recommendation: 15 minutes.**
10 minutes is too short — transactional email can take 3-7 minutes in practice. 30 minutes is the maximum before security benefit starts to erode. 15 minutes is the documented middle ground. The verify endpoint must clearly distinguish "expired" (offer re-send) from "invalid/tampered" (show generic error, no re-send hint).

### Rate Limiting on Magic Link Requests

**Recommendation:** Two limits stacked:
- 5 requests per hour per IP address
- 3 requests per hour per submitted email address

This prevents both IP-based spam and email enumeration/flooding attacks.

**Storage backend:** Use Redis (Cloud Memorystore) from day one, not `memory://`. Cost is minimal; avoids the multi-instance pitfall.

### Disclaimer Presentation

**Recommendation:** Fixed footer, never a block that can be overridden. Two-sentence structure:
1. "The information provided by this tool is for general informational purposes only and does not constitute legal advice."
2. "AI-generated assessments describe statistical patterns in similar cases and do not predict outcomes in your case."

Style: subtle but visible — low-contrast grey on white background undermines the legal purpose. Use a clearly readable font size (min 14px), mild border-top separator. Should be noticeable but not distracting.

**Wording must be reviewed and approved by the supervising lawyer before any user-facing feature ships.** Use placeholder wording in Phase 1 implementation; finalize during Phase 2 or before launch.

### AI Guardrail UX: Transparent vs Visible

**Recommendation: Transparent** (i.e., the user sees the processed output, not an indication that filtering occurred). The filtering is a compliance mechanism, not a feature. Showing users "this response was modified" creates confusion and draws attention to the constraint in an unhelpful way. The guardrail's job is to ensure every output is already in compliant form — users should never see an "unfiltered" variant.

**Exception:** If the guardrail blocks an output entirely (e.g., all text was directive and replacement failed), show a neutral "assessment unavailable for this case — please consult a lawyer" message.

### Visual Foundation

**Recommendation:** Professional, trust-building, Ontario-appropriate.
- Color: Deep navy (`#1B2A4A`) primary, clean white backgrounds, gold accent (`#C9A84C`) for CTAs. Avoids "startup tech" palette; signals legal gravitas.
- Typography: System font stack (`-apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif`) — no web font load for performance; system fonts are accessible and fast.
- Tone: Calm, clear, competent. No consumer-app casualness.
- Mobile-first: 320px minimum, single-column login page, large touch targets (44px minimum per WCAG 2.5.5).

### Login Page Layout

**Recommendation:** Single centered card, above the fold on mobile.
- Headline: "Sign in to Bryan and Bryan"
- One email input field, labelled (not just placeholder — WCAG 1.3.1)
- Submit button: "Send login link"
- Below the fold: brief one-line description ("Enter your email and we'll send you a secure login link.")
- No "register" / "create account" language — first magic link request creates the account silently.

---

## Open Questions

1. **Email provider selection**
   - What we know: SendGrid is the standard recommendation; Postmark is favoured for deliverability in 2025-2026 testing.
   - What's unclear: Whether the supervising lawyer's firm has an existing provider or preference.
   - Recommendation: Default to SendGrid (widely documented, simple Python SDK). Switch to Postmark if deliverability issues arise. Either works with the same service abstraction.

2. **Flask-Limiter Redis backend timing**
   - What we know: In-memory works for a single instance but breaks at scale.
   - What's unclear: Whether Cloud Memorystore (Redis) is budgeted for Phase 1 or can wait until auto-scaling is needed.
   - Recommendation: Provision a Cloud Memorystore Basic instance (cheapest tier) in Phase 1. If truly constrained, document the in-memory limitation and add a TODO to switch before enabling multi-instance scaling.

3. **First-use account creation behaviour**
   - What we know: The decisions specify magic-link auth with no explicit "registration" step.
   - What's unclear: Should a first-time email request create the user record immediately, or only on successful link verification?
   - Recommendation: Create the user record on successful link verification only. This prevents user records for mistyped emails.

4. **AI guardrail directive pattern list**
   - What we know: The architecture (wrapper class + regex patterns) is defined. The specific patterns require lawyer review.
   - What's unclear: Exact approval timeline.
   - Recommendation: Ship the wrapper class with placeholder patterns clearly marked `# LAWYER_REVIEW_REQUIRED`. The architecture is complete; the content list is a legal deliverable.

5. **Workload Identity Federation GCP setup**
   - What we know: WIF is the correct approach; the YAML pattern is documented.
   - What's unclear: GCP project ID, service account names, and Artifact Registry repository must be pre-provisioned before CI/CD pipeline can be wired up.
   - Recommendation: Pre-provision GCP resources (Cloud Run service, Artifact Registry repo, Cloud SQL instance, WIF pool + provider) before beginning Plan 01-02.

---

## Sources

### Primary (HIGH confidence)

- Context7 `/pallets/flask` — app factory pattern, blueprint registration
- Context7 `/pallets-eco/flask-sqlalchemy` — SQLAlchemy 2.0-style model definitions, `Mapped`/`mapped_column`
- Context7 `/miguelgrinberg/flask-migrate` — CLI commands, init/migrate/upgrade flow
- Context7 `/maxcountryman/flask-login` — user_loader, `@login_required`, session config, redirect validation
- Context7 `/pallets/itsdangerous` — `URLSafeTimedSerializer`, `dumps`/`loads`, `max_age`, `SignatureExpired`
- Context7 `/alisaifee/flask-limiter` — custom key functions, stacked decorators, storage backends
- `github.com/google-github-actions/deploy-cloudrun` (official) — WIF workflow YAML, inputs
- `github.com/GoogleCloudPlatform/cloud-sql-python-connector` README — `creator` pattern, pg8000 driver, IAM auth
- `docs.cloud.google.com/run/docs/tips/python` — gunicorn worker/thread config, PORT binding, `--timeout 0`

### Secondary (MEDIUM confidence)

- W3C WAI WCAG 2.1 Techniques / ARIA11 — landmark roles (skip-nav, banner, main, navigation, contentinfo)
- `miguelgrinberg.com` Cookie Security posts — `REMEMBER_COOKIE_SECURE`, `SESSION_COOKIE_SECURE` production config
- Ontario Government "Guide to Procedures in Small Claims Court" disclaimer — wording reference
- Multiple 2025-2026 sources on multi-stage Docker builds with `python:3.12-slim`

### Tertiary (LOW confidence — flag for validation)

- Disclaimer exact wording: derived from government source example, but must be lawyer-reviewed before production use
- AI guardrail directive pattern list: placeholder patterns only — content requires legal sign-off
- Email provider recommendation: based on 2025 deliverability comparisons from third-party blog posts

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — verified via Context7 and official GCP docs
- Architecture patterns: HIGH — all code examples sourced from Context7 official documentation
- Magic-link token flow: HIGH — Context7 itsdangerous docs confirm stateless approach
- CI/CD pipeline: HIGH — official google-github-actions repo confirmed
- Pitfalls: HIGH (technical) / MEDIUM (rate limiting Redis timing) — multiple sources agree
- Disclaimer wording: LOW — placeholder pending lawyer review
- AI guardrail patterns: LOW — architecture HIGH, specific regex list requires legal sign-off

**Research date:** 2026-04-04
**Valid until:** 2026-07-04 (90 days — stable ecosystem; Flask/SQLAlchemy/GCP don't change rapidly)
