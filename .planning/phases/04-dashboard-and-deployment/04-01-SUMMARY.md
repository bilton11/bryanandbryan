---
phase: "04"
plan: "01"
name: dashboard-deadline-tracker
subsystem: frontend
tags: [flask, jinja2, htmx, css-grid, timeline, deadline-service, dashboard]

dependency-graph:
  requires:
    - "01-01"  # Flask app, SQLAlchemy models, extensions
    - "02-01"  # Claim model, step_data JSONB, ClaimStatus
    - "02-02"  # limitation step_data["limitation"]["basic_deadline"]
    - "03-01"  # Document model, download route (plain anchor)
  provides:
    - "Dashboard blueprint (GET /, POST /dashboard/dates/<claim_id>)"
    - "ClaimDeadlines dataclass and build_claim_deadlines() pure function"
    - "CSS timeline visualization with severity dots and overdue detection"
    - "Full navigation bar (Dashboard, New Assessment, Documents, Guide, Log out)"
  affects:
    - "04-02"  # Deployment — no changes expected

tech-stack:
  added: []
  patterns:
    - "Blueprint pattern (same as assessment, documents)"
    - "SQLAlchemy 2.0 db.select() style queries with selectinload"
    - "JSONB full-reassignment mutation pattern (step_data = dict(...))"
    - "HTMX partial update for timeline on date POST"
    - "Plain anchor for PDF downloads (not HTMX)"
    - "CSS custom timeline with ::before pseudo-elements for dots and line"

key-files:
  created:
    - app/dashboard/__init__.py
    - app/dashboard/routes.py
    - app/services/deadline_service.py
    - app/templates/dashboard/index.html
    - app/templates/dashboard/partials/claims_list.html
    - app/templates/dashboard/partials/documents_list.html
    - app/templates/dashboard/partials/deadline_timeline.html
  modified:
    - app/__init__.py  # register dashboard_bp
    - app/main/routes.py  # redirect index() to dashboard.index
    - app/templates/main/index.html  # redirect notice
    - app/templates/base.html  # full navigation links
    - app/static/css/main.css  # Dashboard Phase 4 CSS section appended

decisions:
  - id: D-04-01-A
    description: "dashboard_bp registered without url_prefix — routes define / and /dashboard/dates/<claim_id> directly"
    rationale: "Consistent with assessment and documents blueprints; keeps /  as the dashboard home"
  - id: D-04-01-B
    description: "Deadline timeline partial used for both initial include and HTMX re-render target"
    rationale: "Single template source of truth; HTMX swaps innerHTML of #timeline-{claim_id} div"
  - id: D-04-01-C
    description: "settlement_conf_date stored as-is (user-entered); trial_request_deadline computed as settlement_conf_date + 30 days"
    rationale: "Settlement conference is a real calendar date the user knows; trial request deadline is procedurally derived"

metrics:
  duration: "4 minutes"
  completed: "2026-04-06"
  tasks-completed: 2
  tasks-total: 2
  deviations: 1
---

# Phase 4 Plan 01: Dashboard and Deadline Tracker Summary

**One-liner:** Dashboard blueprint with ClaimDeadlines dataclass, HTMX timeline partial, and CSS timeline showing 4 court deadlines sorted chronologically with overdue red-dot highlighting.

## Tasks Completed

| # | Name | Commit | Key Files |
|---|------|--------|-----------|
| 1 | Dashboard blueprint, deadline service, and routes | dd07dd3 | dashboard/__init__.py, routes.py, deadline_service.py, app/__init__.py, main/routes.py, deadline_timeline.html |
| 2 | Dashboard templates, timeline CSS, and navigation | 934617e | dashboard/index.html, claims_list.html, documents_list.html, main.css, base.html |

## Decisions Made

| ID | Decision | Rationale |
|----|----------|-----------|
| D-04-01-A | dashboard_bp registered without url_prefix | Consistent with other blueprints; `/` is the dashboard home |
| D-04-01-B | Timeline partial used for both include and HTMX swap target | Single source of truth; no duplication |
| D-04-01-C | settlement_conf_date stored as user-entered; trial request = +30 days | Settlement date is known; trial deadline is procedurally derived |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] deadline_timeline.html created in Task 1 to unblock route verification**

- **Found during:** Task 1 verification
- **Issue:** The `save_dates` route imports and renders `dashboard/partials/deadline_timeline.html`. Without the file, the route verification import would fail if the template was loaded. Pre-creating it as part of Task 1 avoided a blocking gap.
- **Fix:** Created the full deadline_timeline.html partial during Task 1 (not Task 2 as planned). No functionality changed — just ordering.
- **Files modified:** app/templates/dashboard/partials/deadline_timeline.html
- **Commit:** dd07dd3

**2. [Rule 1 - Bug] assessment.wizard_entry takes no claim_id argument**

- **Found during:** Task 2 (claims_list.html authoring)
- **Issue:** The plan specified linking draft claims to the assessment wizard with `claim_id`. Route inspection showed `/assess` takes no URL arguments.
- **Fix:** `claims_list.html` links to `url_for('assessment.wizard_entry')` without `claim_id` for DRAFT claims.
- **Files modified:** app/templates/dashboard/partials/claims_list.html

## Next Phase Readiness

Plan 04-02 (Deployment) can proceed. No blockers introduced by this plan.

- All dashboard routes registered and verified
- Deadline service is pure (no DB writes), easy to test
- HTMX patterns consistent with prior phases
- CSS timeline fully self-contained in main.css Dashboard section
