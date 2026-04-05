---
phase: "02-case-assessment"
plan: "02-02"
subsystem: "case-assessment"
tags: ["limitation-period", "jurisdiction-check", "evidence-inventory", "htmx", "ontario-law"]

dependency_graph:
  requires: ["02-01"]
  provides:
    - "Pure-Python limitation period calculator with Ontario Limitations Act logic"
    - "Limitation result display partial with status-appropriate styling"
    - "Evidence inventory checklist with weighted completeness scoring"
    - "POST /assess/evidence HTMX route for live score updates"
    - "Jurisdiction enforcement hard stop at $50K on amount step (from 02-01)"
  affects: ["02-03"]

tech_stack:
  added:
    - "python-dateutil (relativedelta for accurate year arithmetic)"
  patterns:
    - "Pure-Python service layer with no ORM imports for testability"
    - "Serialize LimitationResult to dict (dates as ISO strings) for JSONB storage"
    - "HTMX partial swap pattern: hx-post returns updated partial HTML fragment"
    - "Alpine.js x-show for conditional form field (minor_dob revealed when is_minor checked)"
    - "Post-step hook: limitation calculated and cached after facts step POST"

key_files:
  created:
    - "app/services/limitation_service.py"
    - "app/templates/assessment/partials/limitation_result.html"
    - "app/templates/assessment/partials/evidence_checklist.html"
  modified:
    - "app/assessment/routes.py"
    - "app/templates/assessment/steps/step_facts.html"
    - "app/templates/assessment/steps/step_summary.html"

decisions:
  - id: "02-02-A"
    decision: "Limitation result cached to step_data['limitation'] after facts step POST"
    rationale: "Avoids recalculating on every summary render; keeps summary step read-only"
    alternatives_considered: "Recalculate on each summary GET"
  - id: "02-02-B"
    decision: "Evidence score stored as checked key list in step_data['evidence']['checked']"
    rationale: "Simple list is portable; score recalculated from EVIDENCE_TYPES weights on each request"
    alternatives_considered: "Store score integer directly"
  - id: "02-02-C"
    decision: "REQUIRES_LAWYER_REVIEW always set when tolling_applied=True, regardless of days remaining"
    rationale: "Tolling calculations are fact-specific; any automated deadline is potentially wrong"
    alternatives_considered: "Show calculated deadline with disclaimer"
  - id: "02-02-D"
    decision: "minor_dob field added to step_facts (deviation)"
    rationale: "Without DOB, minor tolling cannot shift basic_start date — field is required for correct calculation"
    alternatives_considered: "Omit minor_dob and always flag REQUIRES_LAWYER_REVIEW for minors without calculating"

metrics:
  duration: "4 minutes 30 seconds"
  completed: "2026-04-05"
  tasks_completed: 2
  tasks_total: 2
  deviations: 1
---

# Phase 2 Plan 2: Limitation Calculator, Jurisdiction Check, and Evidence Inventory Summary

**One-liner:** Pure-Python Ontario Limitations Act calculator with minor/incapacity tolling, municipal notice flag, and HTMX-wired 8-item weighted evidence checklist.

## What Was Built

### Task 1: Limitation Period Calculator Service

`app/services/limitation_service.py` — no ORM imports, testable in isolation.

- `LimitationStatus` enum: WITHIN_PERIOD, WARNING (< 90 days), EXPIRED, ULTIMATE_EXPIRED, REQUIRES_LAWYER_REVIEW
- `LimitationResult` dataclass: basic_deadline, ultimate_deadline, days_remaining, warning_message, tolling_applied, municipal_notice_required
- `calculate_limitation()`: uses `relativedelta(years=LIMITATION_PERIOD_YEARS)` for 2-year basic period, `relativedelta(years=ULTIMATE_LIMITATION_YEARS)` for 15-year ultimate period — both from ontario_constants
- Basic period starts from discovery_date (not incident_date) — Ontario discovery rule
- Minor tolling: shifts basic_start to minor_dob + 18 years if that date is later; sets REQUIRES_LAWYER_REVIEW
- Incapacity tolling: shifts basic_start to incapacity_end_date if later; sets REQUIRES_LAWYER_REVIEW
- Municipal defendant: sets municipal_notice_required=True, appends 10-day notice warning to message
- All 4 verification tests pass

### Task 2: Integration, Templates, and Evidence Inventory

**routes.py additions:**
- `EVIDENCE_TYPES` list (8 items with weights totalling 14)
- `_score_evidence()` helper: sum weights of checked items / 14 × 100
- `_calculate_and_store_limitation()`: extracts facts, runs calculator, stores serialised dict to step_data["limitation"]
- Called automatically after successful facts step POST
- `save_evidence` route at POST /assess/evidence: validates checked keys, stores to step_data["evidence"], returns evidence_checklist partial

**limitation_result.html** — bare partial:
- Green (WITHIN_PERIOD), amber (WARNING), red (EXPIRED), dark red (ULTIMATE_EXPIRED), blue/purple (REQUIRES_LAWYER_REVIEW)
- Separate yellow box for municipal notice when required
- Falls back gracefully when limitation data not yet calculated

**evidence_checklist.html** — bare partial:
- 8 checkboxes, hx-post to /assess/evidence, hx-target="#evidence-checklist-inner"
- Inline script triggers form submit on checkbox change (no extra button needed)
- Score progress bar: green >= 70%, amber 40-69%, red < 40%
- "Strong evidence base" / "Moderate — consider gathering more evidence" / "Limited evidence — your case may be harder to prove"

**step_summary.html** — two new sections added above the Complete Assessment button:
- "Limitation Period" section with intro text + limitation_result partial
- "Evidence Inventory" section with intro text + evidence_checklist partial

**step_facts.html** — minor_dob conditional field:
- Alpine.js `x-data="{ isMinor: ... }"` on the is_minor checkbox container
- `x-show="isMinor"` reveals date-of-birth input only when checkbox is checked
- Required attribute set conditionally via `:required="isMinor"`

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added minor_dob date field to step_facts.html**

- **Found during:** Task 2 — wiring `_calculate_and_store_limitation()` to the facts form data
- **Issue:** The facts step had an `is_minor` checkbox but no DOB field. Without a DOB, `calculate_limitation(minor_dob=None)` cannot calculate `age_18 = minor_dob + relativedelta(years=18)`, so tolling is flagged but the shifted deadline cannot be computed.
- **Fix:** Added Alpine.js conditional `minor_dob` date input to step_facts.html, shown only when `is_minor` is checked. The field persists via `saved.get("minor_dob", "")` and the routes.py helper extracts it when present.
- **Files modified:** `app/templates/assessment/steps/step_facts.html`
- **Commit:** c7e7ea9

## Verification Status

Manual verification requires a running dev server (plan 02-02 has no automated server startup). The following checks should be performed:

- Navigate to /assess, complete dispute type and facts steps with discovery_date 1 year ago → summary shows green "within period" limitation result
- Check is_minor, enter DOB making claimant 17 → summary shows REQUIRES_LAWYER_REVIEW
- Enter amount 60000 → blocked at amount step with jurisdiction error
- Enter amount 5000 → advances to opposing_party
- On summary: evidence checklist shows 8 items; checking items updates score via HTMX
- `python -c "from app.services.limitation_service import calculate_limitation; print('import OK')"` — verified passing

## Next Phase Readiness

- Plan 02-03 can build on the ASSESSED claim status and step_data structure
- step_data["limitation"] contains status, deadlines, and warnings for display in completion/results page
- step_data["evidence"] contains checked list for display in results
- Blocker remains: limitation branching logic must be reviewed by supervising lawyer before launch
