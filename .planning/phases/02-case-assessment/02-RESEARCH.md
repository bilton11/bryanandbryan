# Phase 2: Case Assessment - Research

**Researched:** 2026-04-05
**Domain:** Multi-step HTMX wizard, limitation period logic, AI integration, WeasyPrint PDF generation
**Confidence:** HIGH (core stack verified against official sources)

## Summary

Phase 2 builds four distinct subsystems: a DB-backed HTMX wizard (ASMT-01, ASMT-02), a limitation period
calculator with tolling branches (ASMT-03), jurisdiction/evidence checkers (ASMT-04, ASMT-05), and AI case
strength + PDF export (ASMT-06, ASMT-07). Each subsystem is well-supported by the existing stack.

The HTMX wizard pattern is server-driven: each step submits a POST, the server validates, updates a `Claim`
model in the database, and returns a partial HTML fragment that replaces the step container via `hx-swap:
innerHTML`. No client-side state beyond the claim ID is needed. This approach aligns with the project's
Flask + HTMX philosophy and means progress survives page refreshes.

WeasyPrint 68.1 (with Flask-WeasyPrint 1.2.0) handles PDF generation. The per-page disclaimer requirement
maps directly to WeasyPrint's CSS `running()` / `element()` feature, which places a named element into the
`@page` margin box on every page without requiring any Python-level hackery. The Anthropic SDK 0.89.0 with
model `claude-sonnet-4-6` is the right choice for the AI case strength indicator — correct price/speed
tradeoff, and the AIGuardrail class already in `app/services/ai_guardrail.py` wraps its output.

**Primary recommendation:** Build the `Claim` model with a `JSONB` step-data column (mutation-tracked via
`MutableDict.as_mutable(JSONB)`), drive the wizard with HTMX partial responses, keep limitation logic in a
pure Python service class with no ORM dependencies, and generate PDFs from a Jinja2 template rendered to a
string then passed to `flask_weasyprint.HTML(string=...).write_pdf()`.

---

## Standard Stack

### Core (all already in requirements.txt or needed additions)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| flask | >=3.1,<4 | Already installed | App framework |
| flask-sqlalchemy | >=3.0,<4 | Already installed | ORM |
| sqlalchemy | >=2.0.49,<3 | Already installed | Core ORM + JSONB support |
| weasyprint | >=68.0,<69 | PDF generation | Current stable; required by flask-weasyprint 1.2.0 |
| flask-weasyprint | >=1.2.0,<2 | Flask PDF integration | Short-circuits WSGI, respects Flask routing |
| anthropic | >=0.89.0,<1 | Claude API client | Official SDK, Python 3.14 compatible |
| htmx | 2.x (CDN) | Already loaded via base.html | Partial page swap; already in use in Phase 1 |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| sqlalchemy-json | >=0.7.0 | Nested JSONB mutation tracking | If step_data dict has nested mutation; MutableDict alone tracks only top-level keys |
| jinja2 | (via Flask) | PDF HTML template rendering | Render assessment summary to string before passing to WeasyPrint |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint | ReportLab | WeasyPrint uses HTML+CSS (matches existing templates); ReportLab is programmatic API — harder to maintain alongside Jinja2 templates |
| WeasyPrint | xhtml2pdf | WeasyPrint has superior CSS support (Flexbox, Grid, running elements); xhtml2pdf is older and less actively maintained |
| flask-weasyprint | Direct WeasyPrint | flask-weasyprint handles Flask request context and URL fetching automatically; direct use requires manual base_url setup |
| claude-sonnet-4-6 | claude-haiku-4-5 | Sonnet is better at nuanced legal text pattern recognition; cost difference is small for low-volume legal assessment |
| JSONB step_data column | Separate step tables | JSONB is flexible as wizard steps evolve; separate tables require migrations every time a step field changes |

**Installation additions to requirements.txt:**
```
weasyprint>=68.0,<69
flask-weasyprint>=1.2.0,<2
anthropic>=0.89.0,<1
```

**Dockerfile additions (before COPY requirements.txt):**
```dockerfile
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpango-1.0-0 \
    libpangoft2-1.0-0 \
    libharfbuzz-subset0 \
    && rm -rf /var/lib/apt/lists/*
```
These three packages are WeasyPrint's only runtime requirements on Debian/python:3.12-slim. No MSYS2 or
extra build tools needed when installing from wheels (which pip uses by default).

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── assessment/              # New blueprint (parallel to auth/, main/)
│   ├── __init__.py          # assessment_bp
│   └── routes.py            # Wizard, limitation, jurisdiction, evidence, AI endpoints
├── models/
│   ├── user.py              # Existing
│   └── claim.py             # New: Claim + ClaimStatus enum
├── services/
│   ├── ai_guardrail.py      # Existing
│   ├── auth_tokens.py       # Existing
│   ├── limitation_service.py  # New: pure-Python limitation period calculator
│   ├── assessment_service.py  # New: AI case strength indicator (calls Anthropic SDK)
│   └── pdf_service.py         # New: WeasyPrint PDF generation
└── templates/
    ├── assessment/
    │   ├── wizard_shell.html      # Full page: step container + progress bar
    │   ├── steps/
    │   │   ├── step_dispute_type.html   # HTMX partial
    │   │   ├── step_facts.html          # HTMX partial
    │   │   ├── step_amount.html         # HTMX partial
    │   │   ├── step_opposing_party.html # HTMX partial
    │   │   └── step_summary.html        # HTMX partial (review before submit)
    │   └── pdf/
    │       └── assessment_report.html   # PDF-only template (not for browser)
    └── base.html                # Existing
```

### Pattern 1: DB-Backed HTMX Wizard

**What:** Each wizard step is a route that accepts POST, validates the step's fields, persists them to
`Claim.step_data` (JSONB), advances `Claim.current_step`, and returns the next step's partial HTML.
**When to use:** Any multi-step form where progress must survive page refresh and browser back navigation.

The key structural rule: the wizard shell (`wizard_shell.html`) is a full-page template containing a
`<div id="wizard-step-container">`. Each step partial is placed inside that div via `hx-swap="innerHTML"`.
The shell does NOT use `{% extends "base.html" %}` for the step partials — partials are bare HTML fragments.

```python
# app/assessment/routes.py
from flask import render_template, request, redirect, url_for, abort
from flask_login import login_required, current_user
from app.assessment import assessment_bp
from app.extensions import db
from app.models.claim import Claim, ClaimStatus

WIZARD_STEPS = [
    "dispute_type",
    "facts",
    "amount",
    "opposing_party",
    "summary",
]

@assessment_bp.route("/assess/step/<step_name>", methods=["GET", "POST"])
@login_required
def wizard_step(step_name):
    if step_name not in WIZARD_STEPS:
        abort(404)

    claim = _get_or_create_draft_claim(current_user.id)

    if request.method == "POST":
        errors = _validate_step(step_name, request.form)
        if errors:
            # Return same step partial with errors — no redirect
            return render_template(
                f"assessment/steps/step_{step_name}.html",
                claim=claim,
                errors=errors,
            )
        _persist_step(claim, step_name, request.form)
        next_step = _next_step(step_name)
        if next_step is None:
            return redirect(url_for("assessment.review"))
        return render_template(
            f"assessment/steps/step_{next_step}.html",
            claim=claim,
        )

    # GET: render current step
    return render_template(
        f"assessment/steps/step_{step_name}.html",
        claim=claim,
    )
```

HTMX attributes on the step form:
```html
<!-- Inside step_dispute_type.html (bare partial, no extends) -->
<form hx-post="{{ url_for('assessment.wizard_step', step_name='dispute_type') }}"
      hx-target="#wizard-step-container"
      hx-swap="innerHTML">
  ...
  <button type="submit">Next</button>
</form>
```

### Pattern 2: Claim Model with JSONB Step Data

**What:** A single `Claim` row tracks the entire wizard lifecycle. `step_data` is a JSONB column that
stores all collected field values keyed by step name. `current_step` tracks where the user is. Status
progresses through a `ClaimStatus` enum.

```python
# app/models/claim.py
from __future__ import annotations

import enum
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.extensions import db


class ClaimStatus(enum.Enum):
    DRAFT = "draft"
    ASSESSED = "assessed"
    FILED = "filed"


class Claim(db.Model):
    __tablename__ = "claims"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus), default=ClaimStatus.DRAFT, nullable=False
    )
    current_step: Mapped[str] = mapped_column(String(50), default="dispute_type", nullable=False)
    # JSONB with MutableDict so in-place key updates are detected by SQLAlchemy
    step_data: Mapped[Optional[dict]] = mapped_column(
        MutableDict.as_mutable(JSONB), nullable=True, default=dict
    )
    ai_assessment: Mapped[Optional[str]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship("User", back_populates="claims")
```

**Critical:** `MutableDict.as_mutable(JSONB)` is required. Without it, SQLAlchemy will not detect
in-place mutations like `claim.step_data["amount"] = 5000` and will not emit an UPDATE.

**Migration note:** After adding `Claim`, run `flask db migrate -m "add claims table"` and `flask db
upgrade`. For production startup using `db.create_all()`, the new table will be created automatically.

### Pattern 3: Limitation Period Calculator (Pure Service)

**What:** A stateless Python function that takes structured inputs and returns a `LimitationResult`
dataclass. No ORM imports — fully unit-testable.

The Ontario Limitations Act, 2002 rules implemented:
- **Basic period:** 2 years from discovery (s.4) — discovery is when plaintiff first knew/ought to have
  known of the claim. Use `discovery_date`, not incident date.
- **Minors/incapacitated:** Basic 2-year period does not run while claimant lacks capacity or is an
  unrepresented minor (s.6, s.7). Clock starts when disability ends (turn 18, or regain capacity).
- **Ultimate period:** 15 years from act/omission regardless of discovery (s.15). Cannot be tolled by
  minor status if claim arises before disability starts — lawyer must review.
- **Municipal notice:** 10-day written notice required before suing a municipality (Municipal Act, 2001,
  s.44(12)) — already in `ontario_constants.MUNICIPAL_NOTICE_DAYS`.

```python
# app/services/limitation_service.py
from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import date
from dateutil.relativedelta import relativedelta  # pip install python-dateutil


class LimitationStatus(enum.Enum):
    WITHIN_PERIOD = "within_period"
    WARNING = "warning"          # less than 90 days remaining
    EXPIRED = "expired"
    ULTIMATE_EXPIRED = "ultimate_expired"
    REQUIRES_LAWYER_REVIEW = "requires_lawyer_review"


@dataclass
class LimitationResult:
    status: LimitationStatus
    basic_deadline: date | None
    ultimate_deadline: date | None
    days_remaining: int | None
    warning_message: str | None
    # Set True when minor/incapacity tolling applies — triggers lawyer review flag
    tolling_applied: bool = False
    municipal_notice_required: bool = False


def calculate_limitation(
    discovery_date: date,
    incident_date: date,
    is_minor: bool,
    minor_dob: date | None,
    is_incapacitated: bool,
    incapacity_end_date: date | None,
    is_municipal_defendant: bool,
    today: date | None = None,
) -> LimitationResult:
    """
    Calculate the limitation deadline for an Ontario Small Claims matter.
    Source: Limitations Act, 2002, S.O. 2002, c. 24, Sched. B, ss. 4, 6, 7, 15.
    """
    if today is None:
        today = date.today()

    # Ultimate limitation from incident date (not tolled by minor status — s.15(4)(b)
    # applies only if claim ARISES while claimant is a minor without litigation guardian)
    ultimate_deadline = incident_date + relativedelta(years=15)

    # Basic limitation starts from discovery date
    basic_start = discovery_date

    # Tolling: minor (unrepresented, no litigation guardian)
    tolling_applied = False
    if is_minor and minor_dob is not None:
        age_18 = minor_dob + relativedelta(years=18)
        if age_18 > basic_start:
            basic_start = age_18
            tolling_applied = True

    # Tolling: incapacity
    if is_incapacitated and incapacity_end_date is not None:
        if incapacity_end_date > basic_start:
            basic_start = incapacity_end_date
            tolling_applied = True

    basic_deadline = basic_start + relativedelta(years=2)

    # Check ultimate period
    if today > ultimate_deadline:
        return LimitationResult(
            status=LimitationStatus.ULTIMATE_EXPIRED,
            basic_deadline=basic_deadline,
            ultimate_deadline=ultimate_deadline,
            days_remaining=0,
            warning_message=(
                "The 15-year ultimate limitation period has expired. "
                "This claim likely cannot proceed."
            ),
            tolling_applied=tolling_applied,
            municipal_notice_required=is_municipal_defendant,
        )

    # Check basic period
    if today > basic_deadline:
        return LimitationResult(
            status=LimitationStatus.EXPIRED,
            basic_deadline=basic_deadline,
            ultimate_deadline=ultimate_deadline,
            days_remaining=0,
            warning_message=(
                "The 2-year basic limitation period appears to have expired. "
                "Consult a lawyer before proceeding — exceptions may apply."
            ),
            tolling_applied=tolling_applied,
            municipal_notice_required=is_municipal_defendant,
        )

    days_remaining = (basic_deadline - today).days
    status = LimitationStatus.WARNING if days_remaining < 90 else LimitationStatus.WITHIN_PERIOD
    warning_message = None
    if status == LimitationStatus.WARNING:
        warning_message = (
            f"Your limitation deadline is in {days_remaining} days "
            f"({basic_deadline.isoformat()}). Act promptly."
        )

    if tolling_applied:
        status = LimitationStatus.REQUIRES_LAWYER_REVIEW

    return LimitationResult(
        status=status,
        basic_deadline=basic_deadline,
        ultimate_deadline=ultimate_deadline,
        days_remaining=days_remaining,
        warning_message=warning_message,
        tolling_applied=tolling_applied,
        municipal_notice_required=is_municipal_defendant,
    )
```

**Add to requirements.txt:** `python-dateutil>=2.9,<3` — provides `relativedelta` for accurate
year/month arithmetic (avoids off-by-one on leap years and month boundaries that `timedelta` causes).

### Pattern 4: AI Case Strength Indicator

**What:** Calls `client.messages.create()` with a system prompt enforcing statistical framing, passes
claim data, runs output through the existing `AIGuardrail`, returns `GuardrailResult`.

```python
# app/services/assessment_service.py
from __future__ import annotations

import os
from anthropic import Anthropic
from app.services.ai_guardrail import guardrail, GuardrailResult

_SYSTEM_PROMPT = """
You are a legal information assistant describing statistical patterns in Ontario Small Claims Court cases.

Rules you MUST follow:
- ONLY describe statistical patterns. Never give legal advice.
- NEVER say "you should", "you must", "I recommend", "you will win", "you will lose".
- Frame ALL observations as: "Cases with similar characteristics in Ontario..."
- Do not predict the outcome of this specific case.
- Keep response under 150 words.
- End with: "This is a statistical observation, not legal advice."
"""

# Model pinned to a versioned alias for stability.
# claude-sonnet-4-6 is the current recommended model as of 2026-04-05.
_MODEL = "claude-sonnet-4-6"


def get_case_strength_assessment(claim_summary: str) -> GuardrailResult:
    """
    Call Claude to produce a statistical case assessment, then run through AIGuardrail.
    Requires ANTHROPIC_API_KEY env var.

    IMPORTANT: This service is LAWYER_REVIEW_REQUIRED before production use.
    """
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        from app.services.ai_guardrail import GuardrailStatus
        from dataclasses import replace
        blocked = guardrail.process("")
        return blocked

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=_MODEL,
        max_tokens=400,
        system=_SYSTEM_PROMPT,
        messages=[
            {"role": "user", "content": claim_summary}
        ],
    )
    raw_text = response.content[0].text
    return guardrail.process(raw_text)
```

### Pattern 5: WeasyPrint PDF with Per-Page Disclaimer

**What:** Render the assessment summary as HTML using a dedicated PDF Jinja2 template, then convert to
PDF bytes using `flask_weasyprint.HTML`. The per-page disclaimer uses CSS `running()` / `element()`.

The CSS technique (supported since WeasyPrint 52.5, verified in 68.1):
```css
/* In the PDF template's <style> block */
@page {
    size: Letter;
    margin: 2.5cm 2cm 3.5cm 2cm;  /* extra bottom margin for disclaimer */

    @bottom-center {
        content: element(page-disclaimer);
        font-size: 8pt;
        color: #555;
    }
}

/* The disclaimer element: position: running() pulls it out of flow */
#page-disclaimer {
    position: running(page-disclaimer);
    text-align: center;
    font-size: 8pt;
    font-style: italic;
}
```

```html
<!-- In assessment_report.html — the running element must appear in <body> -->
<body>
  <div id="page-disclaimer">
    Legal Information, Not Legal Advice. This assessment describes statistical patterns in
    similar cases and does not constitute legal advice or predict your case outcome.
    Bryan and Bryan — {{ today }}.
  </div>

  <!-- Main content follows -->
  <h1>Case Assessment Summary</h1>
  ...
</body>
```

```python
# app/services/pdf_service.py
from __future__ import annotations

from flask import render_template
from flask_weasyprint import HTML as WeasyHTML


def render_assessment_pdf(claim) -> bytes:
    """
    Render the case assessment as a PDF.
    Must be called within a Flask request context (flask-weasyprint requirement).
    Returns PDF bytes.
    """
    html_string = render_template("assessment/pdf/assessment_report.html", claim=claim)
    pdf_bytes = WeasyHTML(string=html_string).write_pdf()
    return pdf_bytes
```

Route returning the PDF:
```python
@assessment_bp.route("/assess/<int:claim_id>/pdf")
@login_required
def download_pdf(claim_id):
    from flask import make_response
    from app.services.pdf_service import render_assessment_pdf

    claim = db.session.get(Claim, claim_id)
    if claim is None or claim.user_id != current_user.id:
        abort(404)
    pdf_bytes = render_assessment_pdf(claim)
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = (
        f'attachment; filename="assessment-{claim_id}.pdf"'
    )
    return response
```

### Pattern 6: Dispute Type Router (ASMT-01)

**What:** Step 1 of the wizard presents a dropdown/radio of claim types. Before advancing, validate
that the selected type is within Small Claims Court scope.

Excluded matters (source: Courts of Justice Act, O. Reg. 626/00; Ontario courts guidance):
- Title to land (real property ownership)
- Libel and slander — nuanced: defamation CAN proceed in Small Claims Court up to $50K, but the claim
  type router should flag it and require explicit acknowledgment because anti-SLAPP motions are not
  available in Small Claims Court and defamation claims are legally complex. **Lawyer review required
  before finalizing this logic.**
- Bankruptcy
- False imprisonment
- Malicious prosecution

The router should use a constant list in `ontario_constants.py`:
```python
# Add to ontario_constants.py
EXCLUDED_CLAIM_TYPES = [
    "title_to_land",
    "bankruptcy",
    "false_imprisonment",
    "malicious_prosecution",
]

# Claim types requiring explicit lawyer-acknowledgment before proceeding
COMPLEX_CLAIM_TYPES = [
    "defamation",  # Can proceed but no anti-SLAPP; lawyer review recommended
    "landlord_tenant",  # Separate Landlord and Tenant Board jurisdiction
]
```

### Anti-Patterns to Avoid

- **Storing wizard state in Flask session:** Session cookies have a 4KB limit. A multi-step assessment
  with evidence inventory data will exceed this. Use the `Claim` database model.
- **Using `timedelta(days=730)` for a 2-year period:** This gives wrong results around leap years. Use
  `python-dateutil`'s `relativedelta(years=2)` instead.
- **Calling WeasyPrint outside a Flask request context:** `flask_weasyprint.HTML` requires an active
  request context. If called from a background task (e.g., Celery), use plain `weasyprint.HTML` with
  an explicit `base_url`.
- **Returning full-page HTML to HTMX requests:** HTMX expects only the partial fragment for the swap
  target. Returning a full page causes the wizard container to render inside itself. Check
  `request.headers.get("HX-Request") == "true"` to verify before returning.
- **Not using `from __future__ import annotations` in model files:** Required on Python 3.14. All new
  model and service files must include this as their first import.
- **Mutating step_data without assignment:** `claim.step_data["key"] = val` is tracked by MutableDict,
  but `claim.step_data.update({...})` may not be. Prefer direct key assignment or reassign the whole
  dict: `claim.step_data = {**claim.step_data, "key": val}`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Custom HTML-to-PDF renderer | `weasyprint` + `flask-weasyprint` | CSS page margin boxes, running elements, proper font handling — months of work to replicate |
| Year arithmetic for limitation dates | `timedelta(days=730)` | `python-dateutil relativedelta(years=2)` | Leap year edge cases; Feb 29 birthday deadlines would be wrong |
| AI output sanitization | Custom regex pipeline | Extend existing `AIGuardrail` | Guardrail already exists and has LAWYER_REVIEW_REQUIRED patterns |
| HTMX request detection | Custom header-checking decorator | `request.headers.get("HX-Request")` | One-liner; no library needed |
| JSONB mutation tracking | Flag-based dirty tracking | `MutableDict.as_mutable(JSONB)` | Built into SQLAlchemy ORM extension |
| Multi-step form state | Browser `sessionStorage` | `Claim.step_data` (JSONB in DB) | Survives tab close, back navigation, session expiry |

**Key insight:** WeasyPrint's CSS running elements feature eliminates the need for any Python-level
page manipulation. Do not use the `PdfGenerator` class-based approach from older blog posts that
manipulates `_page_box` — that is a private API hack. The standard CSS approach is stable and supported.

---

## Common Pitfalls

### Pitfall 1: WeasyPrint Missing System Libraries in Docker

**What goes wrong:** The `python:3.12-slim` image has no Pango or HarfBuzz libraries. WeasyPrint
imports succeed but PDF rendering fails at runtime with `OSError: cannot load library 'libpango-1.0.so'`.
**Why it happens:** WeasyPrint uses Pango for text layout via CFFI. The slim base image omits it.
**How to avoid:** Add `RUN apt-get update && apt-get install -y libpango-1.0-0 libpangoft2-1.0-0
libharfbuzz-subset0` to the Dockerfile's runtime stage **before** the venv copy step.
**Warning signs:** Import succeeds in unit tests (Mac/Linux dev machine has Pango), fails only in CI
or Cloud Run deployment.

### Pitfall 2: JSONB step_data Mutations Not Saved

**What goes wrong:** Wizard step updates appear to work locally but values disappear on the next
request. SQLAlchemy emits no UPDATE statement.
**Why it happens:** Plain `JSONB` column type does not track in-place mutations. SQLAlchemy only sees
a change if the column-level object is replaced.
**How to avoid:** Declare as `MutableDict.as_mutable(JSONB)`. Verify with SQLAlchemy's echo mode:
`SQLALCHEMY_ECHO=True` should show an UPDATE after `claim.step_data["key"] = val; db.session.commit()`.
**Warning signs:** No UPDATE in the SQL log after modifying step_data fields.

### Pitfall 3: Limitation Period Off-By-One on Discovery Date

**What goes wrong:** Limitation calculator produces wrong deadline for users with Feb 29 birthdays or
claims discovered on Feb 29. The 2-year deadline falls on a non-existent date.
**Why it happens:** `timedelta(days=730)` does not account for leap years. Feb 29 + 2 years lands on
a day that doesn't exist.
**How to avoid:** Use `relativedelta(years=2)` from `python-dateutil`. It handles month-end roll-over
correctly (Feb 29 + 2 years = Feb 28).
**Warning signs:** Test with `discovery_date = date(2024, 2, 29)`.

### Pitfall 4: Full Page Returned to HTMX Swap Target

**What goes wrong:** The wizard step container shows an entire page rendered inside itself (double
nav bars, footer, etc.).
**Why it happens:** Route returns `render_template("assessment/wizard_shell.html", ...)` instead of
`render_template("assessment/steps/step_X.html", ...)` for HTMX requests.
**How to avoid:** Step partial templates must NOT extend `base.html`. Step routes should always return
the bare partial. The wizard shell is only loaded on the initial full-page GET.
**Warning signs:** Nested `<html>` tags visible in browser dev tools.

### Pitfall 5: AI Assessment Generated Before Lawyer Review Clears

**What goes wrong:** The AI case strength feature ships to users before the supervising lawyer has
reviewed the guardrail patterns and system prompt.
**Why it happens:** Development pressure; guardrail tests pass in CI so it "seems fine".
**How to avoid:** The `ASMT-06` plan task must include an explicit gate: `ANTHROPIC_API_KEY` env var
is not set in production Cloud Run until lawyer sign-off. Wrap the assessment route with a feature
flag check (`if not current_app.config.get("AI_ASSESSMENT_ENABLED"): abort(503)`).
**Warning signs:** AI assessment endpoint returns results without `LAWYER_REVIEW_REQUIRED` appearing
in the deployment review checklist.

### Pitfall 6: PDF Template Shares Base Template

**What goes wrong:** The PDF renders with the site navigation bar and footer HTML inside the document.
**Why it happens:** `assessment_report.html` extends `base.html` which includes `<nav>` and `<footer>`.
**How to avoid:** The PDF template must be standalone (`<!DOCTYPE html>` at root, no `{% extends %}`).
The disclaimer is embedded in the PDF template itself, not pulled from `base.html`.
**Warning signs:** PDF file contains "Log out" links or nav elements.

---

## Code Examples

### HTMX Wizard Step Detection in Flask Route

```python
# Source: htmx.org/attributes/hx-request + Flask docs
from flask import request

def is_htmx_request() -> bool:
    return request.headers.get("HX-Request") == "true"
```

### MutableDict JSONB Column Declaration (SQLAlchemy 2.0)

```python
# Source: https://docs.sqlalchemy.org/en/20/orm/extensions/mutable.html
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from sqlalchemy.orm import Mapped, mapped_column

step_data: Mapped[dict | None] = mapped_column(
    MutableDict.as_mutable(JSONB), nullable=True, default=dict
)
```

### Anthropic Messages API Call

```python
# Source: https://platform.claude.com/docs/en/api/python/messages/create
# Verified against PyPI anthropic==0.89.0 (2026-04-03)
import anthropic

client = anthropic.Anthropic(api_key="...")
response = client.messages.create(
    model="claude-sonnet-4-6",
    max_tokens=400,
    system="You are a ...",
    messages=[{"role": "user", "content": "..."}],
)
text = response.content[0].text
```

### Flask-WeasyPrint PDF Response

```python
# Source: https://doc.courtbouillon.org/flask-weasyprint/stable/first_steps.html
from flask_weasyprint import HTML as WeasyHTML
from flask import render_template, make_response

html_string = render_template("assessment/pdf/report.html", claim=claim)
pdf_bytes = WeasyHTML(string=html_string).write_pdf()
resp = make_response(pdf_bytes)
resp.headers["Content-Type"] = "application/pdf"
resp.headers["Content-Disposition"] = 'attachment; filename="report.pdf"'
```

### WeasyPrint Per-Page Disclaimer CSS

```css
/* Source: WeasyPrint CSS Generated Content for Paged Media (running elements)
   Supported since 52.5, current in 68.1 */
@page {
    size: Letter;
    margin: 2.5cm 2cm 3.5cm 2cm;

    @bottom-center {
        content: element(page-disclaimer);
    }
}

#page-disclaimer {
    position: running(page-disclaimer);
    font-size: 8pt;
    font-style: italic;
    text-align: center;
    color: #444;
}
```

### ontario_constants.py Additions

```python
# Dispute type router exclusions
EXCLUDED_CLAIM_TYPES: list[str] = [
    "title_to_land",
    "bankruptcy",
    "false_imprisonment",
    "malicious_prosecution",
]

# Types that can proceed but require explicit acknowledgment
COMPLEX_CLAIM_TYPES: list[str] = [
    "defamation",       # LAWYER_REVIEW_REQUIRED: anti-SLAPP not available in SCC
    "landlord_tenant",  # Typically LTB jurisdiction; exceptions exist
]
```

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Flask session for wizard state | DB-backed JSONB column | Standard since SQLAlchemy 1.4 JSONB support | Survives session expiry, scales beyond cookie size limit |
| timedelta(days=730) for 2-year limit | dateutil.relativedelta(years=2) | python-dateutil has been best practice for years | Correct leap year handling |
| WeasyPrint _page_box hack for headers | CSS running() / element() at-rule | WeasyPrint 52.5+ (current is 68.1) | Stable public API, no internal attribute dependency |
| flask-weasyprint 0.x | flask-weasyprint 1.2.0 | March 2025 | Requires Python 3.11+, WeasyPrint >=68.0, lazy loading |
| claude-3-haiku-20240307 | claude-haiku-4-5 | April 2026 | 3-haiku deprecated April 19, 2026 — do not use |

**Deprecated/outdated:**
- `flask-weasyprint 0.x`: Last pre-1.0 release incompatible with Flask 3.x. Use 1.2.0.
- `claude-3-haiku-20240307`: **Deprecated, EOL April 19, 2026** — 15 days from research date. Do not
  reference in any new code.
- `timedelta` for limitation periods: Functionally wrong for year calculations on leap years.

---

## Open Questions

1. **Defamation (libel/slander) exclusion rule**
   - What we know: Defamation CAN be brought in Ontario Small Claims Court up to $50K. But anti-SLAPP
     motions (CJA s.137.1) are not available in Small Claims Court.
   - What's unclear: Whether the dispute type router should EXCLUDE or FLAG-WITH-WARNING defamation
     claims. The existing requirement says "excludes libel/slander" but current Ontario law allows
     defamation in SCC. Sources conflict.
   - Recommendation: Flag with a prominent warning ("This is a complex claim type. Anti-SLAPP
     protections are not available in Small Claims Court. Strongly recommended: consult a lawyer before
     filing.") rather than hard-blocking. Supervising lawyer must confirm this decision before
     ASMT-01 ships.

2. **Minor tolling and the 15-year ultimate period**
   - What we know: s.15(4)(b) of the Limitations Act, 2002 suspends the ultimate period only if the
     claim ARISES while the claimant is a minor without a litigation guardian. The interaction between
     s.6 (basic period tolling) and s.15 is fact-specific.
   - What's unclear: Whether the calculator should attempt to model the s.15 suspension at all, or
     simply flag all minor-tolling scenarios for lawyer review.
   - Recommendation: The limitation calculator should compute the basic deadline with tolling applied
     but always set `status = REQUIRES_LAWYER_REVIEW` when `tolling_applied = True`. The phase blocker
     note already flags this: "Limitation period branching logic must be reviewed by supervising lawyer
     before launch."

3. **ANTHROPIC_API_KEY management in Cloud Run**
   - What we know: Cloud Run supports Secret Manager for env vars. The key cannot be committed.
   - What's unclear: Whether the AI feature should be a hard 503 or a graceful degradation (show
     assessment without AI insight) when key is absent.
   - Recommendation: Graceful degradation — if `ANTHROPIC_API_KEY` is absent, skip the AI indicator
     section in the assessment entirely and show a placeholder "AI assessment not available." This
     allows staging deploys without the key and makes the lawyer-review gate operational.

---

## Sources

### Primary (HIGH confidence)

- `https://platform.claude.com/docs/en/docs/about-claude/models/overview` — Current model IDs
  confirmed: `claude-sonnet-4-6`, `claude-opus-4-6`, `claude-haiku-4-5`. claude-3-haiku deprecation
  April 19, 2026 confirmed.
- `https://pypi.org/project/anthropic/` — SDK version 0.89.0 as of 2026-04-03. Python 3.9+.
- `https://github.com/Kozea/Flask-WeasyPrint/releases` — v1.2.0 released March 2025. Requires
  Python 3.11+, WeasyPrint >=68.0.
- `https://doc.courtbouillon.org/weasyprint/stable/first_steps.html` — Debian apt packages confirmed:
  `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz-subset0`.
- `https://docs.sqlalchemy.org/en/20/orm/extensions/mutable.html` — `MutableDict.as_mutable(JSONB)`
  pattern confirmed for SQLAlchemy 2.0.
- `https://platform.claude.com/docs/en/api/python/messages/create` — `messages.create()` signature
  including `system`, `model`, `max_tokens` confirmed.
- `https://htmx.org/attributes/hx-swap/` — `innerHTML` swap mode confirmed. Nine swap values listed.

### Secondary (MEDIUM confidence)

- `https://www.ontariocourts.ca/scj/small-claims-court/` — SCC hears civil disputes up to $50K.
  Excludes section not detailed; confirmed from search cross-reference.
- CSS `running()` / `element()` per-page footer technique — confirmed supported since WeasyPrint 52.5
  via multiple search results referencing v52.5 docs; current version is 68.1 so this is established.
- Ontario Limitations Act 2002 rules (s.4, s.6, s.7, s.15) — confirmed via
  `https://www.blg.com/en/insights/2023/06/limitations-act-2002-the-15-year-ultimate-limitation-period`
  and `https://achkarlitigation.com/insights/statute-of-limitations-in-ontario/`.

### Tertiary (LOW confidence)

- Defamation / libel-slander in SCC: Multiple sources conflict (some say excluded, some say allowed
  up to $50K). This needs supervising lawyer confirmation. Marked as open question.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all versions verified against official sources (PyPI, GitHub releases, Anthropic docs)
- Architecture: HIGH — patterns derived from official Flask, SQLAlchemy, HTMX, WeasyPrint docs
- Limitation logic: MEDIUM — statutory interpretation confirmed from legal blogs and BLG article; exact
  branching confirmed by ontario_constants.py already in codebase; final implementation needs lawyer review
- Dispute type exclusions: LOW-MEDIUM — defamation exclusion is conflicted; all others confirmed
- Pitfalls: HIGH — all verified against official documentation or existing codebase constraints

**Research date:** 2026-04-05
**Valid until:** 2026-05-05 (30 days — stable libraries; Anthropic model lineup could shift faster)
