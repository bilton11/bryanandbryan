# Phase 4: Dashboard and Deployment — Research

**Researched:** 2026-04-06
**Domain:** Flask dashboard (HTMX + Alpine.js), deadline calculation, CSS timeline, Cloud Run production hardening, GitHub Actions + Workload Identity Federation, WCAG/AODA audit
**Confidence:** HIGH for stack patterns (fits existing codebase); MEDIUM for deployment pipeline migration; MEDIUM for Python 3.14 compatibility risk

---

## Summary

Phase 4 has two sub-phases: 04-01 builds the user-facing dashboard with deadline tracker and timeline visualization; 04-02 hardens deployment and adds the lawyer escalation pathway. The codebase is already well-structured and consistent — the dashboard blueprint follows the exact same Flask + HTMX + Alpine.js pattern established in phases 1–3.

The dashboard's data model is already in place. `Claim.step_data["limitation"]` stores the pre-calculated limitation deadline. Three other deadlines (defence deadline, settlement conference window, trial request deadline) require user-entered dates (service date, settlement conference outcome date) not currently captured in any model. These must be added as new user-input fields, either as a lightweight `Claim` step_data extension or as a dedicated `claim_dates` JSONB sub-key. The planner should model these as a simple form on the dashboard — not a new wizard step.

The `cloudbuild.yaml` is already configured for Cloud Build → Cloud Run. The roadmap requires migrating to GitHub Actions with Workload Identity Federation. This is a new workflow file (`.github/workflows/deploy.yml`) replacing the Cloud Build trigger. The existing `cloudbuild.yaml` can remain as a fallback or be deleted. The Python 3.14 incompatibility with Flask, Werkzeug, SQLAlchemy, and gunicorn is a risk that must be verified before touching the Docker base image — the current `Dockerfile` pins `python:3.12-slim` which is safe.

**Primary recommendation:** Keep the existing stack exactly as-is. Add a `dashboard` blueprint (no URL prefix), build the deadline tracker as a pure Python service function, render the timeline with semantic CSS + ordered-list HTML (no JS library), and do the GitHub Actions migration as a separate task with proper IAM setup documented as a prerequisite.

---

## Standard Stack

All items already in `requirements.txt` unless noted.

### Core (already installed)
| Library | Version pinned | Purpose | Why |
|---------|----------------|---------|-----|
| Flask | >=3.1,<4 | Web framework + blueprints | Established pattern in codebase |
| Flask-SQLAlchemy | >=3.0,<4 | ORM, queries for dashboard data | Existing models |
| Flask-Login | >=0.6,<1 | `@login_required`, `current_user` | Already in all blueprints |
| python-dateutil | >=2.9,<3 | `relativedelta` for deadline math | Already used in `limitation_service.py` |
| Flask-Limiter | >=4.0,<5 | Rate limiting on PDF download routes | Already on download endpoints |

### Supporting (already installed)
| Library | Version pinned | Purpose | When to Use |
|---------|----------------|---------|-------------|
| gunicorn | >=22.0,<23 | Production WSGI server | Dockerfile CMD |
| cloud-sql-python-connector | >=1.0,<2 | Cloud SQL IAM auth | ProductionConfig |
| WeasyPrint | >=68.0,<69 | PDF generation | Existing doc pipeline only |

### New additions needed
| Library | Version | Purpose | Install |
|---------|---------|---------|---------|
| None required | — | All functionality built from existing stack | — |

No new Python dependencies needed for Phase 4. The GitHub Actions workflow uses Google-managed actions (not Python packages).

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| CSS-only timeline | Chart.js / Vis.js | JS libraries are overkill; CSS `ol` with pseudo-elements is sufficient for 4-8 dates and has zero JS dependency risk |
| Pure Python deadline math | APScheduler | No background jobs needed — deadlines are calculated on request from stored dates |
| GitHub Actions WIF | Service account key | Keys are long-lived credentials; WIF is keyless and required by the roadmap |

---

## Architecture Patterns

### Recommended Project Structure — New Files
```
app/
├── dashboard/
│   ├── __init__.py          # blueprint definition (no url_prefix)
│   └── routes.py            # GET / (dashboard index), POST /dashboard/dates
├── services/
│   └── deadline_service.py  # pure-function deadline calculations
templates/
└── dashboard/
    ├── index.html           # main dashboard page
    └── partials/
        ├── claims_list.html     # HTMX partial — claims table
        ├── documents_list.html  # HTMX partial — documents with download links
        ├── deadline_timeline.html # timeline visualization partial
        └── escalation_panel.html  # lawyer escalation CTA
.github/
└── workflows/
    └── deploy.yml           # GitHub Actions CI/CD (replaces Cloud Build trigger)
```

### Pattern 1: Dashboard Blueprint Registration
**What:** Same pattern as `assessment` and `documents` — no URL prefix, routes define their own paths.
**When to use:** Always — this is the established codebase convention.
**Example:**
```python
# app/dashboard/__init__.py
from flask import Blueprint
dashboard_bp = Blueprint("dashboard", __name__)
from app.dashboard import routes  # noqa

# app/__init__.py — add alongside other blueprints
from app.dashboard import dashboard_bp
app.register_blueprint(dashboard_bp)
```

### Pattern 2: Dashboard Index — Eager-Load Related Data
**What:** A single query fetching user's claims with eager-loaded documents avoids N+1 queries.
**When to use:** Dashboard index route — always loads claims + documents together.
**Example:**
```python
# Source: SQLAlchemy 2.0 docs — selectinload for collections
from sqlalchemy.orm import selectinload
from app.models.claim import Claim
from app.models.document import Document

@dashboard_bp.route("/")
@login_required
def index():
    claims = (
        db.session.execute(
            db.select(Claim)
            .where(Claim.user_id == current_user.id)
            .options(selectinload(Claim.documents))
            .order_by(Claim.updated_at.desc())
        )
        .scalars()
        .all()
    )
    documents = (
        db.session.execute(
            db.select(Document)
            .where(Document.user_id == current_user.id)
            .order_by(Document.updated_at.desc())
        )
        .scalars()
        .all()
    )
    # Build deadline data for each claim
    from app.services.deadline_service import build_claim_deadlines
    claim_deadlines = {c.id: build_claim_deadlines(c) for c in claims}
    return render_template(
        "dashboard/index.html",
        claims=claims,
        documents=documents,
        claim_deadlines=claim_deadlines,
    )
```

**Note:** `User.claims` and `User.documents` relationships use `lazy="dynamic"` — do NOT iterate them directly or call `.all()` on them in templates. Always query via `db.select()` with explicit loading.

### Pattern 3: Deadline Service — Pure Function
**What:** All deadline math lives in `app/services/deadline_service.py`. No side effects. Mirrors the existing `limitation_service.py` pattern.
**When to use:** Always for deadline calculations — keeps routes thin.

```python
# app/services/deadline_service.py
from __future__ import annotations
from dataclasses import dataclass, field
from datetime import date
from typing import Optional
from dateutil.relativedelta import relativedelta
from app.ontario_constants import (
    DEFENCE_DEADLINE_DAYS,
    TRIAL_REQUEST_DEADLINE_DAYS,
)

@dataclass
class ClaimDeadlines:
    limitation_deadline: Optional[date]     # from claim.step_data["limitation"]
    defence_deadline: Optional[date]        # service_date + 20 days
    settlement_conf_date: Optional[date]    # user-entered
    trial_request_deadline: Optional[date]  # settlement_conf_date + 30 days
    overdue_items: list[str] = field(default_factory=list)

def build_claim_deadlines(claim, today: date | None = None) -> ClaimDeadlines:
    """
    Build all court deadlines for a claim from stored step_data and
    the claim_dates sub-key. Returns ClaimDeadlines with None for any
    deadline where the required input date is not yet provided.
    """
    if today is None:
        today = date.today()
    step_data = claim.step_data or {}
    limitation = step_data.get("limitation", {})
    claim_dates = step_data.get("claim_dates", {})

    # Limitation deadline — already calculated by limitation_service
    lim_str = limitation.get("basic_deadline")
    lim_date = date.fromisoformat(lim_str) if lim_str else None

    # Defence deadline — 20 days from service date
    service_str = claim_dates.get("service_date")
    defence_date = None
    if service_str:
        try:
            defence_date = date.fromisoformat(service_str) + relativedelta(days=DEFENCE_DEADLINE_DAYS)
        except ValueError:
            pass

    # Settlement conference date — user-entered
    sc_str = claim_dates.get("settlement_conference_date")
    sc_date = date.fromisoformat(sc_str) if sc_str else None

    # Trial request deadline — 30 days after settlement conference
    trial_date = None
    if sc_date:
        trial_date = sc_date + relativedelta(days=TRIAL_REQUEST_DEADLINE_DAYS)

    overdue = []
    for label, d in [
        ("Limitation period", lim_date),
        ("Defence deadline", defence_date),
        ("Trial request deadline", trial_date),
    ]:
        if d and d < today:
            overdue.append(label)

    return ClaimDeadlines(
        limitation_deadline=lim_date,
        defence_deadline=defence_date,
        settlement_conf_date=sc_date,
        trial_request_deadline=trial_date,
        overdue_items=overdue,
    )
```

### Pattern 4: Storing User-Entered Dates
**What:** Service dates and settlement conference dates need to be stored. Extend `claim.step_data` with a `claim_dates` sub-key — no schema migration required.
**When to use:** POST `/dashboard/dates/<claim_id>` saves user-entered key dates.

```python
@dashboard_bp.route("/dashboard/dates/<int:claim_id>", methods=["POST"])
@login_required
def save_dates(claim_id: int):
    claim = db.session.get(Claim, claim_id)
    if claim is None or claim.user_id != current_user.id:
        abort(404)
    form_data = request.form.to_dict()
    # Validate dates before storing
    step_data = dict(claim.step_data or {})
    claim_dates = {}
    for key in ("service_date", "settlement_conference_date"):
        val = form_data.get(key, "").strip()
        if val:
            try:
                date.fromisoformat(val)
                claim_dates[key] = val
            except ValueError:
                pass
    step_data["claim_dates"] = claim_dates
    claim.step_data = step_data
    db.session.commit()
    # HTMX: return updated timeline partial
    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        from app.services.deadline_service import build_claim_deadlines
        deadlines = build_claim_deadlines(claim)
        return render_template(
            "dashboard/partials/deadline_timeline.html",
            claim=claim,
            deadlines=deadlines,
        )
    return redirect(url_for("dashboard.index"))
```

### Pattern 5: CSS Timeline — Semantic Ordered List
**What:** The timeline is a styled `<ol>` with CSS pseudo-elements for the vertical line and dots. No JS library. WCAG-compatible with proper ARIA.
**Source:** Multiple CSS reference sites confirm semantic `<ol>` is the correct HTML element for sequential timeline events.

```html
<!-- dashboard/partials/deadline_timeline.html -->
<section class="timeline-section" aria-label="Deadline timeline">
  <ol class="deadline-timeline" role="list">
    {% set deadlines = [
        ("Limitation Period Expiry", deadlines.limitation_deadline, "critical"),
        ("Defence Filing Deadline (20 days after service)", deadlines.defence_deadline, "warning"),
        ("Settlement Conference", deadlines.settlement_conf_date, "info"),
        ("Trial Request Deadline (30 days after settlement)", deadlines.trial_request_deadline, "warning"),
    ] %}
    {% for label, d, severity in deadlines %}
    {% if d %}
    <li class="deadline-item deadline-item--{{ severity }}{% if d < today %} deadline-item--overdue{% endif %}">
      <span class="deadline-date">{{ d.strftime("%B %d, %Y") }}</span>
      <span class="deadline-label">{{ label }}</span>
    </li>
    {% endif %}
    {% endfor %}
  </ol>
</section>
```

**CSS approach:**
```css
.deadline-timeline {
  list-style: none;
  padding: 0 0 0 2rem;
  margin: 0;
  position: relative;
}
.deadline-timeline::before {
  content: "";
  position: absolute;
  left: 0.6rem;
  top: 0;
  bottom: 0;
  width: 2px;
  background-color: var(--color-border);
}
.deadline-item {
  position: relative;
  padding: 0.75rem 0 0.75rem 1.5rem;
  margin-bottom: 0.5rem;
}
.deadline-item::before {
  content: "";
  position: absolute;
  left: 0;
  top: 1rem;
  width: 1.25rem;
  height: 1.25rem;
  border-radius: 50%;
  background-color: var(--color-border);
  border: 2px solid var(--color-bg);
}
.deadline-item--overdue::before { background-color: var(--color-error); }
.deadline-item--critical::before { background-color: var(--color-accent); }
```

### Pattern 6: Complexity Detection for Escalation
**What:** Detect cases flagged for escalation from `claim.step_data`. This is pure logic, no new data fields needed.
**When to use:** Rendered in the escalation panel partial whenever the user's claim meets escalation criteria.

```python
def is_escalation_required(claim) -> bool:
    """
    Returns True if claim exceeds $25K, has corporate defendant,
    or has a tolled/expired limitation requiring lawyer review.
    Source: DASH-04 requirements + ontario_constants.INFREQUENT_CLAIMANT_LIMIT
    """
    from app.ontario_constants import INFREQUENT_CLAIMANT_LIMIT
    step_data = claim.step_data or {}
    amount_data = step_data.get("amount", {})
    try:
        amount = int(amount_data.get("amount", 0))
    except (ValueError, TypeError):
        amount = 0
    if amount > INFREQUENT_CLAIMANT_LIMIT:
        return True
    party = step_data.get("opposing_party", {})
    if party.get("party_type") == "business":
        return True
    limitation = step_data.get("limitation", {})
    if limitation.get("status") in (
        "requires_lawyer_review", "expired", "ultimate_expired"
    ):
        return True
    return False
```

### Pattern 7: GitHub Actions CI/CD Workflow
**What:** Replace Cloud Build trigger with `.github/workflows/deploy.yml` using Workload Identity Federation.
**Source:** google-github-actions/auth@v3 and deploy-cloudrun@v3 official repos (fetched above).

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
      contents: 'read'
      id-token: 'write'

    steps:
      - uses: 'actions/checkout@v4'

      - uses: 'google-github-actions/auth@v3'
        with:
          project_id: ${{ vars.GCP_PROJECT_ID }}
          workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
          service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}

      - name: Configure Docker for Artifact Registry
        run: gcloud auth configure-docker northamerica-northeast1-docker.pkg.dev --quiet

      - name: Build and push image
        run: |
          IMAGE=northamerica-northeast1-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/bryanandbryan-images/app:${{ github.sha }}
          docker build -t $IMAGE .
          docker push $IMAGE

      - name: Run tests
        run: |
          pip install --quiet -r requirements.txt pytest
          python -m pytest tests/ -v --tb=short

      - uses: 'google-github-actions/deploy-cloudrun@v3'
        with:
          service: 'bryanandbryan'
          region: 'northamerica-northeast1'
          image: 'northamerica-northeast1-docker.pkg.dev/${{ vars.GCP_PROJECT_ID }}/bryanandbryan-images/app:${{ github.sha }}'
          secrets: |-
            DATABASE_URL=claimpilot-db-url:latest
            ANTHROPIC_API_KEY=anthropic-api-key:latest
            SECRET_KEY=flask-secret-key:latest
```

**Note:** Tests should run BEFORE `docker push` in a proper sequence — adjust order based on whether test environment needs the full Docker image.

### Anti-Patterns to Avoid
- **Iterating `User.claims` dynamically in templates:** The `lazy="dynamic"` relationship returns a query object, not a list. Always query explicitly with `db.select()`.
- **Storing service dates in a separate DB table:** JSONB sub-key (`claim_dates` within `step_data`) avoids a migration and is consistent with how `limitation` data is already stored.
- **Using a JS timeline library (Chart.js, Vis.js, etc.):** Adds bundle weight and complicates the no-SPA policy. CSS-only semantic list is sufficient for 4–8 dates.
- **Embedding deadlines in the main wizard flow:** The defence deadline and settlement conference date depend on events that happen AFTER filing, so they belong on the dashboard, not in the assessment wizard.
- **Hard-coding escalation logic in templates:** `is_escalation_required()` must be a Python function so it can be tested and so the lawyer can review it.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| OIDC token exchange with GCP | Custom auth code | `google-github-actions/auth@v3` | Handles OIDC exchange, credential rotation, all edge cases |
| Cloud Run deployment step | `gcloud` commands inline | `google-github-actions/deploy-cloudrun@v3` | Handles traffic migration, rollback, revision naming |
| Accessibility audit | Manual HTML review | `axe-playwright-python` in pytest or browser DevTools axe extension | Axe-core catches ~57% of WCAG violations automatically |
| Date formatting in templates | Jinja2 custom filter | Python `date.strftime()` passed from route | Keeps formatting server-side, testable |
| Deadline urgency logic | CSS classes from template conditionals | Python function returns severity level (critical/warning/info) | Logic must be testable; Jinja2 conditionals are hard to unit test |

**Key insight:** The deadline service is the most test-critical component. Every deadline calculation should be a pure function with explicit `today` parameter injection (same pattern as `limitation_service.py`).

---

## Common Pitfalls

### Pitfall 1: N+1 Queries on Dashboard
**What goes wrong:** Dashboard loads claims, then for each claim loads documents in a loop — one DB query per claim.
**Why it happens:** `Claim.documents` relationship defaults to `lazy="select"` (lazy load per access).
**How to avoid:** Use `selectinload(Claim.documents)` in the dashboard query. One query for claims, one for all their documents.
**Warning signs:** Dashboard response time scales linearly with number of claims.

### Pitfall 2: Python 3.14 Incompatibility
**What goes wrong:** The runtime reports Python 3.14 is in use, but Flask, Werkzeug, SQLAlchemy, and gunicorn do NOT officially support Python 3.14 as of April 2026 (per pyreadiness.org). WeasyPrint compatibility is unknown.
**Why it happens:** The STATE.md notes "Python 3.14 in use" but the `Dockerfile` pins `python:3.12-slim`. This discrepancy needs to be resolved.
**How to avoid:** Keep `python:3.12-slim` in the Dockerfile. Do not upgrade to 3.14 unless all key dependencies explicitly support it.
**Warning signs:** Any `ImportError` or build failure mentioning missing C extensions after a base image change.

### Pitfall 3: Dynamic Relationship Iteration
**What goes wrong:** Template does `{% for doc in current_user.documents %}` — this fires a lazy dynamic query per template render, and may not behave as expected for filtering.
**Why it happens:** `User.documents` is declared with `lazy="dynamic"`, which returns a query object in SQLAlchemy 2.x legacy mode (deprecated).
**How to avoid:** Always query documents with `db.select(Document).where(...)` in the route, pass the result list to the template.
**Warning signs:** `LegacyAPIWarning` in logs about dynamic relationships.

### Pitfall 4: `claim_dates` JSONB Mutation Tracking
**What goes wrong:** Doing `claim.step_data["claim_dates"] = {...}` in-place does NOT trigger SQLAlchemy's change tracking with `MutableDict`.
**Why it happens:** `MutableDict` tracks reassignment of the top-level key (`claim.step_data = ...`) but not nested mutations.
**How to avoid:** Always do `step_data = dict(claim.step_data or {}); step_data["claim_dates"] = {...}; claim.step_data = step_data`. The existing `routes.py` already uses this pattern consistently — follow it.
**Warning signs:** Date updates not persisting to DB despite no errors.

### Pitfall 5: HTMX Partial Returns Break Browser Refresh
**What goes wrong:** Routes that return partial HTML for HTMX requests return unstyled partial HTML when navigated to directly in the browser.
**Why it happens:** Missing full-page wrapper for non-HTMX requests.
**How to avoid:** Check `HX-Request` header as existing routes do: `is_htmx = request.headers.get("HX-Request") == "true"`. Partial endpoints (`/dashboard/dates/<id>`) are POST-only so browser refresh is not a concern.
**Warning signs:** Team member reports unstyled HTML when testing a URL directly.

### Pitfall 6: AODA/WCAG Timeline Element Accessibility
**What goes wrong:** Timeline rendered as `<div>` soup with no semantic meaning — screen readers announce list items out of order or skip them.
**Why it happens:** CSS timelines online are often divs with no ARIA structure.
**How to avoid:** Use `<ol>` (ordered list, dates are sequential). Add `aria-label` to the container. Sort the Jinja2 list chronologically by date before rendering. Each `<li>` gets the date and label as visible text (not just CSS content).
**Warning signs:** axe-core reports "list" or "landmark" violations.

### Pitfall 7: Workload Identity Federation Setup Requires GCP CLI Work
**What goes wrong:** Developer adds the GitHub Actions workflow YAML but hasn't created the WIF pool/provider in GCP. Deployment fails with auth errors.
**Why it happens:** WIF requires one-time GCP setup that is separate from writing the workflow file.
**How to avoid:** The plan must include a task to: (1) create the workload identity pool, (2) create the provider, (3) bind the service account, (4) grant `roles/run.admin`, `roles/artifactregistry.writer`, and `roles/iam.serviceAccountUser`. These are separate from writing the YAML.
**Warning signs:** `Error: google-github-actions/auth failed` in Actions log.

### Pitfall 8: Cloud Build vs GitHub Actions Conflict
**What goes wrong:** Both `cloudbuild.yaml` and `.github/workflows/deploy.yml` are active, triggering two deployments on every push.
**Why it happens:** Cloud Build can be connected to a GitHub repo via a trigger that runs `cloudbuild.yaml` automatically.
**How to avoid:** Disable the Cloud Build GitHub trigger in GCP Console BEFORE enabling the GitHub Actions workflow, or delete `cloudbuild.yaml`.
**Warning signs:** Two deployments appear in Cloud Run revision history per push.

---

## Code Examples

Verified patterns from official sources:

### HTMX Request Detection (existing pattern in codebase)
```python
# Source: existing assessment/routes.py and documents/routes.py
is_htmx = request.headers.get("HX-Request") == "true"
if is_htmx:
    return render_template("dashboard/partials/deadline_timeline.html", ...)
return render_template("dashboard/index.html", ...)
```

### Workload Identity Federation Auth Step
```yaml
# Source: google-github-actions/auth GitHub repo (v3, fetched 2026-04-06)
- uses: 'google-github-actions/auth@v3'
  with:
    project_id: ${{ vars.GCP_PROJECT_ID }}
    workload_identity_provider: ${{ secrets.WIF_PROVIDER }}
    service_account: ${{ secrets.WIF_SERVICE_ACCOUNT }}
```

### Cloud Run Deployment with Secrets
```yaml
# Source: google-github-actions/deploy-cloudrun GitHub repo (v3, fetched 2026-04-06)
- uses: 'google-github-actions/deploy-cloudrun@v3'
  with:
    service: 'bryanandbryan'
    region: 'northamerica-northeast1'
    image: 'IMAGE:SHA'
    secrets: |-
      DATABASE_URL=claimpilot-db-url:latest
      ANTHROPIC_API_KEY=anthropic-api-key:latest
      SECRET_KEY=flask-secret-key:latest
```

### SQLAlchemy 2.0 Eager Load
```python
# Source: SQLAlchemy 2.0 docs — selectinload
from sqlalchemy.orm import selectinload
claims = (
    db.session.execute(
        db.select(Claim)
        .where(Claim.user_id == current_user.id)
        .options(selectinload(Claim.documents))
        .order_by(Claim.updated_at.desc())
    )
    .scalars()
    .all()
)
```

### AODA Compliance — WCAG 2.0 Level AA
The following are the primary WCAG 2.0 AA criteria applicable to this UI (no video, no live captions):
- **1.1.1** Non-text content — alt text on any icons used (HIGH risk: none visible in current UI)
- **1.3.1** Info and Relationships — semantic HTML (timeline `<ol>`, form labels)
- **1.4.3** Contrast (Minimum) — 4.5:1 for normal text; navy #1B2A4A on white passes
- **2.1.1** Keyboard — all interactive elements reachable by Tab
- **2.4.3** Focus Order — logical tab sequence on dashboard
- **2.4.6** Headings and Labels — all form fields must have `<label>`
- **3.3.1** Error Identification — errors on date inputs must be text-described

The existing codebase already has: skip-nav link, `role="banner"`, `role="navigation"`, `role="main"`, visible focus ring, 44px touch targets. The dashboard must maintain these.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|------------------|--------|
| Service account key in GitHub Secrets | Workload Identity Federation (keyless) | No long-lived credentials to rotate or leak |
| Cloud Build YAML trigger | GitHub Actions with WIF | Keeps CI/CD in the same repo, visible in PR checks |
| `--timeout 0` (disabled) | `--timeout 0` remains correct for Cloud Run | Cloud Run handles its own request timeout at the infrastructure level |
| `python:3.12-slim` (Dockerfile) | Stay on `python:3.12-slim` | 3.14 not supported by Flask ecosystem as of April 2026 |

**Deprecated/outdated:**
- `Claim.query.filter_by(...)`: SQLAlchemy 2.0 legacy API — existing code uses it, but new dashboard routes should prefer `db.select(Claim).where(...)`. Do not refactor existing routes as part of this phase.
- `lazy="dynamic"` on User relationships: SQLAlchemy 2.0 deprecated this. Do not add new `lazy="dynamic"` relationships. Existing ones are not blocking but generate warnings.

---

## Open Questions

1. **Python 3.14 claim in STATE.md vs Dockerfile**
   - What we know: STATE.md says "Python 3.14 in use" but `Dockerfile` pins `python:3.12-slim`. Flask/SQLAlchemy/gunicorn do not support 3.14 as of April 2026.
   - What's unclear: Is Python 3.14 the local dev interpreter only, or is there intent to change the Docker base image?
   - Recommendation: Plan should include a verification task. Do NOT change the Docker base image. Local dev interpreter does not affect production.

2. **Cloud Build trigger status**
   - What we know: `cloudbuild.yaml` exists and is configured for Artifact Registry + Cloud Run.
   - What's unclear: Whether a Cloud Build GitHub trigger is actively enabled in the GCP project.
   - Recommendation: The deployment plan (04-02) must include a task to check and disable the Cloud Build trigger before enabling GitHub Actions deployment to avoid double-deploys.

3. **Secret name discrepancy in cloudbuild.yaml**
   - What we know: `cloudbuild.yaml` references `claimpilot-db-url` and `flask-secret-key` as Secret Manager secrets. The service is branded "Bryan and Bryan" but secrets use old `claimpilot` naming.
   - What's unclear: Whether these secrets exist in GCP Secret Manager with these exact names.
   - Recommendation: The deployment task should verify secret names in Secret Manager before writing the GitHub Actions YAML. If renaming is needed, do it before cutting over.

4. **`CLOUD_SQL_INSTANCE` env var**
   - What we know: `app/config.py` reads `CLOUD_SQL_INSTANCE` to configure Cloud SQL connector, but `cloudbuild.yaml` doesn't pass this as a secret — it appears to rely on `DATABASE_URL` only.
   - What's unclear: Whether the Cloud SQL connector is actually being used in production or whether `DATABASE_URL` is a full connection string.
   - Recommendation: Verify the production Cloud Run service's env vars in GCP Console before writing the GitHub Actions deployment step.

5. **Load test scope**
   - What we know: The roadmap mentions a load test for 04-02.
   - What's unclear: What threshold constitutes "passing" — there's no explicit RPS or latency target defined in DASH-04.
   - Recommendation: Define a minimal target (e.g., 50 concurrent users, p95 < 2s) in the plan task. Use `locust` headless mode against the deployed staging URL.

---

## Sources

### Primary (HIGH confidence)
- google-github-actions/auth GitHub repo — fetched 2026-04-06, current version v3, WIF YAML pattern confirmed
- google-github-actions/deploy-cloudrun GitHub repo — fetched 2026-04-06, current version v3, secrets config confirmed
- `docs.cloud.google.com/run/docs/tips/python` — fetched 2026-04-06, gunicorn worker/thread config confirmed (`--workers 1 --threads 8 --timeout 0`)
- `docs.cloud.google.com/run/docs/configuring/healthchecks` — fetched 2026-04-06, health check probe types and defaults confirmed
- Codebase review — `app/models/claim.py`, `app/models/document.py`, `app/services/limitation_service.py`, `app/ontario_constants.py`, `cloudbuild.yaml`, `Dockerfile`, `requirements.txt`
- `wcag2.com/aoda-websites` — fetched 2026-04-06, AODA WCAG 2.0 Level AA exceptions confirmed (1.2.4, 1.2.5)

### Secondary (MEDIUM confidence)
- `pyreadiness.org/3.14` — fetched 2026-04-06: Flask, Werkzeug, SQLAlchemy, gunicorn listed as incompatible with Python 3.14
- WebSearch: HTMX Flask dashboard patterns 2025 — consistent with existing codebase pattern; verified against codebase
- WebSearch: AODA IASR WCAG 2.0 Level AA 2025 — consistent with wcag2.com authoritative source
- WebSearch: CSS-only semantic timeline 2025 — multiple sources agree on `<ol>` with pseudo-elements approach
- WebSearch: Locust load testing Flask Cloud Run — tool exists and is current (v2.32.10)

### Tertiary (LOW confidence)
- WebSearch: `docs.cloud.google.com` secrets + Cloud Run 2025 — GCP docs confirm Cloud Run secret injection via `--set-secrets` flag matches existing `cloudbuild.yaml` syntax
- Flask-Limiter Python 3.14 support noted from changelog search — specific to Flask-Limiter only, does not imply Flask core supports 3.14

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new dependencies; all patterns already established in codebase
- Architecture: HIGH — dashboard blueprint follows identical pattern to assessment/documents; deadline service mirrors limitation_service.py
- Deadline logic: HIGH — `ontario_constants.py` already has the constants; `dateutil.relativedelta` already installed
- GitHub Actions / WIF: MEDIUM — pattern confirmed from official repos, but actual GCP setup (pool/provider creation) is a manual step that may have already been done or not
- WCAG/AODA: MEDIUM — requirements verified from official AODA source; actual audit pass/fail requires testing against live rendered pages
- Pitfalls: HIGH — derived directly from reading the existing codebase (lazy="dynamic", MutableDict mutation, HTMX partial patterns)

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable stack; GCP action versions should be re-checked if planning is delayed beyond this date)
