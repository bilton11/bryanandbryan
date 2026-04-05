---
phase: 02-case-assessment
plan: 01
subsystem: ui
tags: [htmx, sqlalchemy, jsonb, wizard, flask, ontario, small-claims]

requires:
  - phase: 01-foundation
    provides: User model, Flask app factory, SQLAlchemy extensions, auth blueprint, base.html, main.css

provides:
  - Claim model (JSONB step_data, ClaimStatus enum, dialect-adaptive JSONB/JSON)
  - Assessment blueprint with HTMX wizard at /assess
  - 5-step wizard: dispute_type, facts, amount, opposing_party, summary
  - Hard-stop dispute type validation (EXCLUDED and REDIRECTED types)
  - ontario_constants: EXCLUDED_CLAIM_TYPES, REDIRECTED_CLAIM_TYPES, VALID_CLAIM_TYPES
  - Wizard CSS classes (progress bar, error/warning/excluded boxes, nav row)

affects:
  - 02-02 (limitation period, assessment report — uses Claim model and step_data)
  - 02-03 (AI assessment — uses Claim.ai_assessment column and step_data)
  - 03-documents (PDF generation — reads Claim data)

tech-stack:
  added:
    - htmx 2.0.4 (CDN, no npm install needed)
    - python-dateutil>=2.9 (added to requirements.txt for plan 02-02)
    - weasyprint>=68.0 (added to requirements.txt for plan 02-03/03)
    - flask-weasyprint>=1.2.0 (added to requirements.txt)
    - anthropic>=0.89.0 (added to requirements.txt for plan 02-03)
  patterns:
    - HTMX partial swap pattern: HX-Request header detection, hx-target="#wizard-step-container", hx-swap="innerHTML"
    - Dialect-adaptive SQLAlchemy type: JSONB().with_variant(JSON(), "sqlite") wrapped in MutableDict.as_mutable()
    - Per-step validation functions (_validate_*) returning error dicts (empty = valid)
    - _render_step() helper: HTMX returns partial, non-HTMX wraps in wizard_shell

key-files:
  created:
    - app/models/claim.py
    - app/assessment/__init__.py
    - app/assessment/routes.py
    - app/templates/assessment/wizard_shell.html
    - app/templates/assessment/steps/step_dispute_type.html
    - app/templates/assessment/steps/step_facts.html
    - app/templates/assessment/steps/step_amount.html
    - app/templates/assessment/steps/step_opposing_party.html
    - app/templates/assessment/steps/step_summary.html
  modified:
    - app/models/user.py (added claims relationship)
    - app/models/__init__.py (added Claim import)
    - app/__init__.py (registered assessment_bp)
    - app/ontario_constants.py (added EXCLUDED_CLAIM_TYPES, REDIRECTED_CLAIM_TYPES, VALID_CLAIM_TYPES)
    - requirements.txt (added Phase 2 deps)
    - Dockerfile (added WeasyPrint system libs)
    - app/static/css/main.css (wizard CSS section)

key-decisions:
  - "JSONB falls back to JSON on SQLite via JSONB().with_variant(JSON(), 'sqlite') — dev works without PostgreSQL"
  - "Both EXCLUDED and REDIRECTED claim types are hard stops using .wizard-excluded red box — no acknowledgment checkbox allowed"
  - "REDIRECTED_CLAIM_TYPES values contain LAWYER_REVIEW_REQUIRED marker for supervising lawyer audit"
  - "Assessment blueprint registered without URL prefix — routes define their own /assess/ paths"
  - "All Phase 2 Python deps (dateutil, weasyprint, flask-weasyprint, anthropic) added in this plan to avoid multiple requirements.txt edits"

patterns-established:
  - "Dialect-adaptive JSON: MutableDict.as_mutable(JSONB().with_variant(JSON(), 'sqlite')) — use for all JSONB columns"
  - "Wizard step rendering: _render_step() checks HX-Request header; HTMX gets bare partial, direct URL gets wizard_shell wrapper"
  - "Step validation: pure functions _validate_*(form_data) returning dict; empty dict = valid"
  - "HTMX forms: hx-post to wizard_step, hx-target='#wizard-step-container', hx-swap='innerHTML'"

duration: 8min
completed: 2026-04-05
---

# Phase 2 Plan 01: Case Assessment Wizard Summary

**5-step HTMX wizard with DB-backed JSONB state, hard-stop dispute type validation (excluded + redirected claim types), and progress-bar UI**

## Performance

- **Duration:** 8 min
- **Started:** 2026-04-05T00:29:17Z
- **Completed:** 2026-04-05T00:37:40Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments

- Claim model with dialect-adaptive JSONB (PostgreSQL prod) / JSON (SQLite dev) step_data, ClaimStatus enum (DRAFT/ASSESSED/FILED), and user relationship
- Full 5-step wizard (dispute_type → facts → amount → opposing_party → summary) with HTMX partial swaps — no full page reloads
- Dispute type step hard-stops: 4 EXCLUDED types (title_to_land, bankruptcy, false_imprisonment, malicious_prosecution) and 2 REDIRECTED types (defamation → Superior Court, landlord_tenant → LTB) all blocked with forum-specific plain-language messages
- Session persistence: GET /assess resumes at claim.current_step; step data survives browser close
- All Phase 2 Python dependencies added to requirements.txt; WeasyPrint system libs added to Dockerfile

## Task Commits

1. **Task 1: Claim model, assessment blueprint, ontario_constants additions, dependency updates** — `1099485` (feat)
2. **Task 2: HTMX wizard routes, step templates, progress bar, and dispute type validation** — `db45b6d` (feat)

**Plan metadata:** _(committed after this SUMMARY and STATE.md update)_

## Files Created/Modified

- `app/models/claim.py` — Claim model with dialect-adaptive JSONB step_data and ClaimStatus enum
- `app/models/user.py` — Added claims relationship (lazy=dynamic)
- `app/models/__init__.py` — Added Claim import
- `app/assessment/__init__.py` — Assessment blueprint definition
- `app/assessment/routes.py` — Wizard entry, wizard_step, wizard_back routes; all validation helpers
- `app/__init__.py` — assessment_bp blueprint registration
- `app/ontario_constants.py` — EXCLUDED_CLAIM_TYPES (4), REDIRECTED_CLAIM_TYPES (2), VALID_CLAIM_TYPES (12)
- `requirements.txt` — Phase 2 deps: dateutil, weasyprint, flask-weasyprint, anthropic
- `Dockerfile` — WeasyPrint system libraries (libpango, libharfbuzz)
- `app/templates/assessment/wizard_shell.html` — Full-page wizard with progress bar and wizard-step-container
- `app/templates/assessment/steps/step_dispute_type.html` — Radio buttons, .wizard-excluded hard-stop display
- `app/templates/assessment/steps/step_facts.html` — Description, incident/discovery dates, minor/municipal checkboxes
- `app/templates/assessment/steps/step_amount.html` — Dollar input with prefix, amount_includes select, warning at >$25k
- `app/templates/assessment/steps/step_opposing_party.html` — party_name, party_type radio, address/email
- `app/templates/assessment/steps/step_summary.html` — Read-only review with Edit links and Complete Assessment button
- `app/static/css/main.css` — Wizard CSS section: progress bar, form, fields, error/warning/excluded boxes, nav, summary

## Decisions Made

- **JSONB with SQLite fallback:** `JSONB().with_variant(JSON(), "sqlite")` wrapped in `MutableDict.as_mutable()` — dev works on SQLite without PostgreSQL, production uses native JSONB with indexing support
- **No acknowledgment checkbox for redirected types:** Both EXCLUDED and REDIRECTED are hard stops. User must select a different claim type — no opt-out path
- **REDIRECTED_CLAIM_TYPES values contain `LAWYER_REVIEW_REQUIRED` marker** to signal the supervising lawyer audit requirement from the AIGuardrail decision in 01-02
- **Blueprint registered without URL prefix:** assessment routes define `/assess/...` paths directly, keeping them clean without a double prefix
- **All Phase 2 deps added upfront:** dateutil, weasyprint, flask-weasyprint, anthropic added to requirements.txt in this plan to avoid three separate requirements edits across plans 02-01, 02-02, 02-03

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] JSONB not supported by SQLite dev database**
- **Found during:** Task 1 verification (`db.create_all()`)
- **Issue:** `sqlalchemy.exc.UnsupportedCompilationError: Compiler SQLiteTypeCompiler can't render element of type JSONB`
- **Fix:** Replaced `MutableDict.as_mutable(JSONB)` with `MutableDict.as_mutable(JSONB().with_variant(JSON(), "sqlite"))` — JSONB on PostgreSQL, JSON on SQLite
- **Files modified:** `app/models/claim.py`
- **Verification:** `db.create_all()` succeeds on SQLite; JSONB column DDL will be used on PostgreSQL
- **Committed in:** `1099485` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for dev environment. Production PostgreSQL is unaffected — JSONB is still used there. No scope creep.

## Issues Encountered

- Flask-Login session setup in test client required adding a temporary `/test_login/<uid>` route to call `login_user()` within a request context. Flask-Login's `_id` session fingerprint (user-agent + remote-addr hash) cannot be easily spoofed via `session_transaction()` alone. Used this pattern for all functional verification tests.

## Next Phase Readiness

- Plan 02-02 (limitation period calculator, assessment report) can begin immediately — Claim model with step_data is ready, ontario_constants has all needed values
- Plan 02-03 (AI assessment) can begin — Claim.ai_assessment column exists, anthropic dependency added
- Supervising lawyer must review REDIRECTED_CLAIM_TYPES messages (defamation and landlord_tenant) before launch — both marked LAWYER_REVIEW_REQUIRED

---
*Phase: 02-case-assessment*
*Completed: 2026-04-05*
