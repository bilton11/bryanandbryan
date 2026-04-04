# Architecture Research

**Domain:** Ontario Small Claims Court — Flask legal tech self-service platform
**Researched:** 2026-04-04
**Confidence:** HIGH (Flask/HTMX patterns), MEDIUM (legal-specific flows), HIGH (AI service wrapping)

---

## Standard Architecture

### System Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Client (Browser)                            │
│   Jinja2 HTML + Alpine.js (local state) + HTMX (server swaps)       │
└──────────────────────────────┬──────────────────────────────────────┘
                               │ HTTP / HTMX partial requests
┌──────────────────────────────▼──────────────────────────────────────┐
│                      Flask 3.x — Presentation Layer                 │
│                                                                     │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  main    │ │  assess  │ │documents │ │  guide   │ │dashboard │  │
│  │blueprint │ │blueprint │ │blueprint │ │blueprint │ │blueprint │  │
│  │(landing) │ │(wizard)  │ │(pdf gen) │ │(steps)   │ │(claims)  │  │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘ └────┬─────┘  │
└───────┼────────────┼────────────┼─────────────┼────────────┼────────┘
        │            │            │             │            │
┌───────▼────────────▼────────────▼─────────────▼────────────▼────────┐
│                         Service Layer                                │
│                                                                     │
│  ┌──────────────┐  ┌───────────────┐  ┌───────────────┐             │
│  │  ai_service  │  │document_service│  │deadline_service│            │
│  │ (Anthropic)  │  │  (PDF gen)    │  │  (dates/calc) │             │
│  └──────┬───────┘  └───────┬───────┘  └───────┬───────┘             │
│                            │                                         │
│  ┌──────────────┐  ┌───────┴───────┐                                 │
│  │canlii_service│  │  assessment_  │                                 │
│  │   (stub)     │  │  service      │                                 │
│  └──────────────┘  └───────────────┘                                 │
└──────────────────────────────┬──────────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────────┐
│                         Data Layer                                  │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐               │
│  │    User      │  │    Claim     │  │   Document   │               │
│  │   model      │  │    model     │  │    model     │               │
│  └──────────────┘  └──────────────┘  └──────────────┘               │
│                                                                     │
│  SQLAlchemy 2.0 ORM + Alembic migrations → PostgreSQL 15            │
└─────────────────────────────────────────────────────────────────────┘
        │
┌───────▼───────────────────────────────────────────────────────────┐
│                      External Services                             │
│  ┌────────────────┐  ┌─────────────────┐  ┌───────────────────┐   │
│  │ Anthropic API  │  │   PostgreSQL 15  │  │  Cloud Run (GCP)  │   │
│  │  (Claude)      │  │   (Cloud SQL)    │  │                   │   │
│  └────────────────┘  └─────────────────┘  └───────────────────┘   │
└────────────────────────────────────────────────────────────────────┘
```

---

## Component Responsibilities

| Component | Responsibility | Communicates With |
|-----------|----------------|-------------------|
| `main` blueprint | Landing page, static content, auth entry points | — |
| `assess` blueprint | Multi-step case assessment wizard routes | `ai_service`, `assessment_service` |
| `documents` blueprint | Document generation routes, download endpoints | `document_service`, Claim model |
| `guide` blueprint | Static procedural guide content | — |
| `dashboard` blueprint | User claims list, deadline display, status | `deadline_service`, Claim/Document models |
| `ai_service` | Anthropic API wrapper — prompts, response parsing | Anthropic API (external) |
| `document_service` | Jinja2 → HTML → WeasyPrint → PDF pipeline | Claim model, templates |
| `deadline_service` | Limitation periods, procedural date calculations | Claim model |
| `assessment_service` | Orchestrates wizard step logic, builds AI prompt inputs | `ai_service`, Claim model |
| `canlii_service` | Stub for future CanLII case law lookups | (none for now) |
| User model | Authentication, session identity | Claim model (FK) |
| Claim model | Central aggregate — facts, amounts, parties, status | Document, User models |
| Document model | Generated file records — type, path, generated_at | Claim model (FK) |

---

## Recommended Project Structure

```
small_claims/
├── app/
│   ├── __init__.py              # Application factory: create_app()
│   ├── extensions.py            # db, migrate, login_manager instances
│   ├── config.py                # Config classes (Dev, Prod, Test)
│   │
│   ├── blueprints/
│   │   ├── main/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── templates/main/  # landing.html, about.html
│   │   ├── assess/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py        # Step handlers (step_1, step_2, …, result)
│   │   │   └── templates/assess/
│   │   │       ├── wizard.html  # Shell page (progress bar, step container)
│   │   │       └── partials/    # step_1.html … step_N.html (HTMX targets)
│   │   ├── documents/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── templates/documents/
│   │   │       └── pdf/         # Form 7A.html, Form 10A.html (PDF templates)
│   │   ├── guide/
│   │   │   ├── __init__.py
│   │   │   ├── routes.py
│   │   │   └── templates/guide/
│   │   └── dashboard/
│   │       ├── __init__.py
│   │       ├── routes.py
│   │       └── templates/dashboard/
│   │
│   ├── services/
│   │   ├── ai_service.py        # Anthropic API wrapper
│   │   ├── assessment_service.py
│   │   ├── document_service.py  # PDF generation pipeline
│   │   ├── deadline_service.py
│   │   └── canlii_service.py    # Stub
│   │
│   ├── models/
│   │   ├── __init__.py          # Re-exports all models
│   │   ├── user.py
│   │   ├── claim.py             # Central aggregate
│   │   └── document.py
│   │
│   └── templates/
│       ├── base.html            # Full-page layout (head, nav, scripts)
│       └── errors/              # 404.html, 500.html
│
├── migrations/                  # Alembic migration versions
├── tests/
├── Dockerfile
├── docker-compose.yml
└── pyproject.toml
```

### Structure Rationale

- **`blueprints/` (feature folders):** Each domain owns its routes AND its templates together. Avoids the "templates in one place, routes in another" split that breaks locality of reference.
- **`services/`:** Pure Python, no Flask imports. Service functions are callable from routes, CLI commands, or tests without HTTP context.
- **`models/`:** SQLAlchemy models only — no business logic. Relationships declared here; queries go in services.
- **`templates/base.html`:** Single base layout. Blueprints extend it for full-page renders; HTMX partial requests skip it entirely.
- **`partials/` inside blueprint templates:** Co-located partial fragments returned on HTMX requests. Naming convention: `_step_1.html` (underscore prefix signals "partial only").

---

## Architectural Patterns

### Pattern 1: Blueprint Route — Full vs. Partial Render

The single most important HTMX + Flask pattern. Every route that can be triggered by HTMX must return a partial fragment; direct browser navigation must return the full page. Without this, browser refresh breaks the page.

**How to use:**

```python
# assess/routes.py
from htmx_flask import Htmx

htmx = Htmx()

@assess_bp.route("/step/<int:step_number>", methods=["GET", "POST"])
def wizard_step(step_number):
    # ... handle form data, update session ...
    partial = f"assess/partials/_step_{step_number}.html"
    if request.htmx:
        return render_template(partial, **ctx)
    # Direct navigation: wrap in full layout
    return render_template("assess/wizard.html", partial=partial, **ctx)
```

**Wizard shell template includes the partial:**

```html
{# assess/wizard.html #}
{% extends "base.html" %}
{% block content %}
  <div id="wizard-step-container">
    {% include partial %}
  </div>
{% endblock %}
```

**Trade-offs:** Requires every route to branch on `request.htmx`. A decorator can reduce the boilerplate. Partial template naming discipline matters.

---

### Pattern 2: Service Layer — Routes Delegate, Services Own Logic

Routes handle HTTP mechanics only. No database queries, no AI calls, no date math in route handlers.

**What:**
- Route parses request data, calls service, formats response
- Service validates inputs, performs work, returns domain objects or raises exceptions
- Models are plain data containers; services write the queries

**When to use:** Always. Even for "simple" operations — the discipline prevents route handler bloat.

**Example:**

```python
# assess/routes.py
@assess_bp.route("/step/2", methods=["POST"])
def step_2_post():
    form_data = request.form.to_dict()
    result = assessment_service.save_step_2(
        claim_id=session["claim_id"],
        data=form_data
    )
    if result.has_errors:
        return render_template("assess/partials/_step_2.html",
                               errors=result.errors, data=form_data)
    return redirect(url_for("assess.wizard_step", step_number=3))

# services/assessment_service.py
def save_step_2(claim_id: int, data: dict) -> StepResult:
    errors = _validate_step_2(data)
    if errors:
        return StepResult(has_errors=True, errors=errors)
    claim = db.session.get(Claim, claim_id)
    claim.defendant_name = data["defendant_name"]
    claim.defendant_address = data["defendant_address"]
    db.session.commit()
    return StepResult(has_errors=False)
```

---

### Pattern 3: AI Service Wrapper

The AI service is a thin facade over the Anthropic SDK. It owns all prompt construction and response parsing. No blueprint should ever import `anthropic` directly.

**Structure:**

```python
# services/ai_service.py
import anthropic
from dataclasses import dataclass

@dataclass
class AssessmentResult:
    strength: str          # "strong" | "moderate" | "weak"
    reasoning: str
    suggested_amount: float | None
    risks: list[str]

class AIService:
    def __init__(self, api_key: str, model: str = "claude-opus-4-5"):
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def assess_claim(self, claim_facts: dict) -> AssessmentResult:
        prompt = self._build_assessment_prompt(claim_facts)
        message = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )
        return self._parse_assessment(message.content[0].text)

    def _build_assessment_prompt(self, facts: dict) -> str:
        # Prompt construction isolated here
        ...
```

**Why this matters:** Swapping models, changing prompt structure, adding retry logic, or mocking for tests — all happen in one file.

**Confidence note:** Anthropic's API terms restrict pure-proxy wrappers (reselling API access). This architecture is compliant because it adds substantial proprietary logic: Ontario court rules, form generation, deadline calculation, and claim structuring — not a simple UI-over-messages-create pattern.

---

### Pattern 4: PDF Generation Pipeline

WeasyPrint is preferred over ReportLab for this project because legal court forms (Form 7A, 10A) have fixed layouts defined by the court — the constraint is matching an existing visual form, not precision-positioning arbitrary content. Jinja2 templates mirror the form's HTML/CSS structure exactly, making WeasyPrint's HTML-to-PDF pipeline the right fit. ReportLab's programmatic layout is unnecessary complexity when the template approach works.

**Pipeline:**

```
Claim model data
    ↓
document_service.generate_form_7a(claim_id)
    ↓
render_template("documents/pdf/form_7a.html", claim=claim)  → HTML string
    ↓
WeasyPrint HTML(string=html, base_url=...).write_pdf()  → bytes
    ↓
Write to /tmp or Cloud Storage
    ↓
Document record saved (claim_id, doc_type, path, generated_at)
    ↓
send_file() response
```

**Key detail:** `base_url=request.base_url` is required so WeasyPrint resolves relative paths for any embedded assets (court logos, CSS).

---

### Pattern 5: Multi-Step Wizard State — Server-Side via Database

For a legal context, session-cookie state (client-side) is risky: cookies expire, users switch devices, progress is lost. The claim record in the database IS the wizard state.

**Strategy:**

1. On wizard entry (Step 1), create a `Claim` record with `status="draft"` and store `claim_id` in the Flask session (just an ID, not the data).
2. Each step POST saves its fields to the `Claim` row and advances `wizard_step` column.
3. On navigation backward, the previous step re-reads from the DB and pre-fills the form.
4. `wizard_step` column tracks how far the user has progressed — allows resuming.
5. Claim becomes "submitted" only after the final step confirms.

**Why not Flask session for data storage:** Session cookies have a size limit (~4KB), are client-managed, and don't survive server restarts. For a legal platform, losing partial claim data mid-wizard is a serious UX failure.

**Alpine.js role in the wizard:** Alpine handles micro-interactions only — showing/hiding conditional fields based on in-page state (e.g., "is the defendant a business?" reveals business-name field), tooltip toggling, and character counter displays. It does NOT own wizard navigation; HTMX owns step transitions.

---

### Pattern 6: SQLAlchemy 2.0 Models — Mapped Column Style

Use the modern `Mapped[T]` + `mapped_column()` style throughout. It enables static type checking and is the recommended approach in SQLAlchemy 2.0+.

```python
# models/claim.py
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import String, Numeric, Integer, DateTime, func
from app.extensions import db

class Claim(db.Model):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(db.ForeignKey("users.id"), index=True)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    wizard_step: Mapped[int] = mapped_column(Integer, default=1)

    # Parties
    plaintiff_name: Mapped[str | None] = mapped_column(String(200))
    defendant_name: Mapped[str | None] = mapped_column(String(200))
    defendant_address: Mapped[str | None] = mapped_column(String(500))

    # Claim details
    claim_amount: Mapped[float | None] = mapped_column(Numeric(10, 2))
    incident_date: Mapped[datetime | None]
    claim_description: Mapped[str | None]

    # AI assessment output (stored, not recomputed on every load)
    ai_strength: Mapped[str | None] = mapped_column(String(20))
    ai_reasoning: Mapped[str | None]
    ai_risks: Mapped[str | None]  # JSON-serialized list

    created_at: Mapped[datetime] = mapped_column(default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="claims")
    documents: Mapped[list["Document"]] = relationship(back_populates="claim")
```

---

## Data Flow

### Case Assessment Wizard Flow

```
User lands on /assess
    ↓
GET /assess/start
  → create Claim(status="draft"), session["claim_id"] = claim.id
  → render wizard.html with _step_1.html partial
    ↓
User fills Step 1 (incident type, date, amount)
    ↓
POST /assess/step/1  [HTMX form submit]
  → assessment_service.save_step_1(claim_id, form_data)
    → validate → save to Claim row → update wizard_step=2
  → if errors: return _step_1.html partial with errors (HTMX swap)
  → if OK: return _step_2.html partial (HTMX swap into #wizard-step-container)
    ↓
[Steps 2–N: same pattern — each POST saves, advances, returns next partial]
    ↓
POST /assess/step/N (final step)
  → assessment_service.run_ai_assessment(claim_id)
    → fetch Claim → build prompt → ai_service.assess_claim()
    → store ai_strength, ai_reasoning, ai_risks on Claim
    → Claim.status = "assessed"
  → return _result.html partial (assessment summary)
```

### Document Generation Flow

```
User in dashboard, clicks "Generate Form 7A"
    ↓
POST /documents/generate/7a/<claim_id>
  → document_service.generate_form_7a(claim_id)
    → db.session.get(Claim, claim_id)  [ownership check: claim.user_id == current_user.id]
    → render_template("documents/pdf/form_7a.html", claim=claim)  → html string
    → WeasyPrint HTML(string=html, base_url=...).write_pdf()  → pdf bytes
    → write to /tmp/form_7a_{claim_id}_{timestamp}.pdf
    → Document(claim_id=claim_id, doc_type="7a", path=...).save()
  → return send_file(path, as_attachment=True)
```

### Dashboard + Deadlines Flow

```
GET /dashboard
  → fetch user's Claims (status != "draft")
  → for each Claim: deadline_service.compute_deadlines(claim)
    → limitation_deadline = incident_date + 2 years (Ontario Limitations Act)
    → filing_deadline = computed from procedural rules
  → render dashboard.html with claims + deadlines
```

### AI Service Call Flow

```
assessment_service.run_ai_assessment(claim_id)
    ↓
ai_service.assess_claim(claim_facts: dict)
    ↓
anthropic.Anthropic(api_key=...).messages.create(
    model="claude-opus-4-5",
    messages=[{"role": "user", "content": prompt}]
)
    ↓
Parse structured response (strength, reasoning, risks)
    ↓
Return AssessmentResult dataclass
    ↓
assessment_service stores result on Claim model
```

---

## Build Order (Phase Dependencies)

The build order follows hard dependencies — you cannot build Phase N until Phase N-1 exists.

| Order | Component | Depends On | Rationale |
|-------|-----------|------------|-----------|
| 1 | App factory, extensions, config | Nothing | Everything else imports from here |
| 2 | User model + auth | App factory | All features require user identity |
| 3 | Claim model + migrations | User model | Wizard and documents write to Claim |
| 4 | Base template + HTMX/Alpine setup | App factory | All blueprint templates extend this |
| 5 | `assess` blueprint skeleton (wizard shell) | Claim model, base template | Core user flow — validates HTMX pattern works |
| 6 | `ai_service` wrapper | Nothing (pure Python) | Can build in parallel with Step 5 |
| 7 | `assessment_service` (wizard step logic + AI) | Steps 5 + 6 | Connects wizard to AI |
| 8 | `deadline_service` | Claim model | Pure Python date logic, no UI deps |
| 9 | `documents` blueprint + `document_service` (PDF) | Claim model, WeasyPrint | Requires complete claim data |
| 10 | `dashboard` blueprint | Claim model, deadline_service | Requires claims to exist |
| 11 | `guide` blueprint | Base template | Static content, no data deps |
| 12 | `canlii_service` stub | Nothing | Stub only — implement last or never |
| 13 | Docker + Cloud Run deployment config | Everything | Deployment wraps the complete app |

**Critical path:** app factory → user/auth → claim model → assess wizard → AI service → document generation → dashboard.

---

## Scaling Considerations

| Scale | Architecture Adjustments |
|-------|--------------------------|
| 0–1K users | Monolith on Cloud Run, single container instance, direct Anthropic API calls, /tmp for PDF files |
| 1K–10K users | Add Cloud SQL connection pooling (Cloud SQL Auth Proxy), move generated PDFs to Cloud Storage, consider Cloud Run min-instances=1 to avoid cold starts |
| 10K+ users | AI calls become the bottleneck — add a task queue (Cloud Tasks) so PDF generation and AI assessment are async; user sees "processing" state rather than waiting on HTTP timeout |

**First bottleneck:** Anthropic API latency. A case assessment prompt + response is 3–8 seconds. Under synchronous HTTP this means long-polling or user-facing spinners. At scale, make assessment async and poll for completion.

**Second bottleneck:** PDF generation. WeasyPrint is CPU-intensive. Move to background task if generation exceeds ~2 seconds.

---

## Anti-Patterns

### Anti-Pattern 1: Business Logic in Route Handlers

**What people do:** Write `db.session.query(...)`, date calculations, and AI calls directly inside `@bp.route()` functions.

**Why it's wrong:** Routes become impossible to test without a full HTTP request cycle. Logic cannot be reused from CLI commands or background jobs. Files grow to 400+ lines.

**Do this instead:** Route calls service function, service owns all logic.

---

### Anti-Pattern 2: HTMX Returning Partial to Direct Browser Navigation

**What people do:** Return only a `<div>` fragment from every route, regardless of how the request arrived.

**Why it's wrong:** User bookmarks `/assess/step/3`, navigates directly, receives unstyled HTML with no CSS or nav.

**Do this instead:** Every HTMX-targeted route checks `request.htmx` and returns the full layout wrapper for direct navigation, partial fragment for HTMX requests.

---

### Anti-Pattern 3: Storing Wizard State in Flask Session Cookie

**What people do:** Serialize all wizard form data into `session["wizard_data"]` across steps.

**Why it's wrong:** 4KB cookie limit, data lost on cookie expiry or device switch, no server-side audit trail of incomplete claims, cannot resume on different device.

**Do this instead:** Create Claim record immediately on wizard start, store only `claim_id` in the session, persist all step data to the database.

---

### Anti-Pattern 4: Alpine.js Owning Wizard Navigation

**What people do:** Use Alpine `x-show` and step-counter variables to show/hide wizard steps entirely client-side, only submitting at the end.

**Why it's wrong:** All form data lives in the browser until final submit — back/forward reloads lose everything, no server-side validation per step, AI assessment cannot happen mid-wizard if all data is client-side.

**Do this instead:** HTMX drives step transitions (server POST per step), Alpine handles only local UI interactions within a single step (conditional field display, tooltips).

---

### Anti-Pattern 5: Importing Anthropic SDK Outside ai_service

**What people do:** Import `anthropic` directly in a route or another service for a "quick" AI call.

**Why it's wrong:** Prompt logic scattered across codebase, cannot mock uniformly for tests, API key handling duplicated.

**Do this instead:** All Anthropic calls go through `ai_service.py`. Every other module treats AI as a dependency-injected service.

---

### Anti-Pattern 6: Generating PDFs in Route Handler

**What people do:** Call WeasyPrint inside a `@bp.route()` function and block the response thread.

**Why it's wrong:** WeasyPrint PDF generation is CPU-bound and takes 1–4 seconds per document. Under Gunicorn, this ties up a worker thread.

**Do this instead:** `document_service.py` owns PDF generation. Route calls the service and returns immediately; for the current scale (MVP), this is acceptable synchronously. When scale demands it, extract to a task queue without changing the service interface.

---

## Integration Points

### External Services

| Service | Integration Pattern | Notes |
|---------|---------------------|-------|
| Anthropic API | `ai_service.py` — single `anthropic.Anthropic` client instance | Store API key in env var, never in code |
| PostgreSQL 15 | SQLAlchemy 2.0 via `flask_sqlalchemy`, migrations via Alembic | Use `db.session.get()` (new style), not `db.session.query()` |
| Cloud Run | Dockerfile + Gunicorn entrypoint | `gunicorn -w 4 -b 0.0.0.0:8080 "app:create_app()"` |
| Cloud SQL | `DATABASE_URL` env var; Cloud SQL Auth Proxy sidecar in Cloud Run | Use `pg8000` or `psycopg2` driver |

### Internal Boundaries

| Boundary | Communication | Notes |
|----------|---------------|-------|
| Blueprint → Service | Direct Python function call | Blueprints import services; services never import blueprints |
| Service → Model | SQLAlchemy ORM via `db.session` | Services own all queries; models declare schema only |
| Service → Service | Direct Python call | `assessment_service` calls `ai_service`; avoid circular imports |
| Blueprint → Blueprint | Flask `url_for()` redirects only | Never import another blueprint's routes directly |
| HTMX → Route | HTTP POST/GET with `HX-Request` header | Use `request.htmx` from `htmx-flask` to detect |

---

## Sources

- [Flask Blueprints Documentation (3.1.x)](https://flask.palletsprojects.com/en/stable/blueprints/) — HIGH confidence
- [Production-Ready Flask SaaS Architecture — LaunchStack](https://www.launchstack.space/blog/flask-saas-project-structure-production-architecture) — MEDIUM confidence
- [HTMX Multi-Step Form Patterns — Medium](https://medium.com/@alexander.heerens/htmx-patterns-01-how-to-build-a-multi-step-form-in-htmx-554d4c2a3f36) — MEDIUM confidence
- [HTMX with Flask and Jinja2 — DEV Community](https://dev.to/hexshift/implementing-htmx-with-flask-and-jinja2-for-dynamic-content-rendering-2bck) — MEDIUM confidence
- [htmx-flask library — GitHub](https://github.com/sponsfreixes/htmx-flask) — HIGH confidence
- [Flask PDF Generation Comparison — CodingEasyPeasy](https://www.codingeasypeasy.com/blog/flask-pdf-generation-reportlab-weasyprint-and-pdfkit-compared) — MEDIUM confidence
- [WeasyPrint + Flask Pipeline — Incentius](https://www.incentius.com/blog-posts/build-modern-print-ready-pdfs-with-python-flask-weasyprint/) — HIGH confidence
- [Architecture Patterns with Python — cosmicpython.com](https://www.cosmicpython.com/book/chapter_04_service_layer.html) — HIGH confidence
- [Flask App Factory Pattern — hackersandslackers.com](https://hackersandslackers.com/flask-application-factory/) — HIGH confidence
- [SQLAlchemy 2.0 ORM Documentation](https://docs.sqlalchemy.org/en/20/orm/) — HIGH confidence
- [HTMX + Flask: Modern Python Web Apps — TalkPython](https://training.talkpython.fm/courses/htmx-flask-modern-python-web-apps-hold-the-javascript) — HIGH confidence

---

*Architecture research for: Ontario Small Claims Court self-service platform (Flask)*
*Researched: 2026-04-04*
