---
phase: 05-ui-gap-closure-and-polish
plan: 01
subsystem: ui
tags: [htmx, alpinejs, jinja2, flask, html, css]

# Dependency graph
requires:
  - phase: 03-documents-and-guide
    provides: documents blueprint with from_claim and new_document routes
  - phase: 04-dashboard-and-deployment
    provides: base.html with global HTMX, nav structure
provides:
  - Single HTMX 2.0.4 global script in base.html (no duplicates)
  - Form 7A and Form 9A buttons in documents index (from-claim and standalone sections)
  - [x-cloak] CSS rule in main.css preventing Alpine.js FOUC
  - Public nav (Guide, Fees, Log in) for unauthenticated users
affects:
  - 06-testing-and-hardening
  - any future template work

# Tech tracking
tech-stack:
  added: []
  patterns:
    - HTMX loaded once globally from base.html — child templates never load HTMX directly
    - Alpine.js loaded in head_extra only on pages that use it (wizard_shell.html)
    - "[x-cloak] CSS rule at top of main.css prevents Alpine.js FOUC"
    - Public nav in {% else %} branch of current_user.is_authenticated check

key-files:
  created: []
  modified:
    - app/static/css/main.css
    - app/templates/base.html
    - app/templates/documents/index.html
    - app/templates/assessment/wizard_shell.html

key-decisions:
  - "05-01: HTMX 2.0.4 with integrity hash loaded globally — child templates removed local HTMX tags"
  - "05-01: Public nav lives in {% else %} branch so it only appears when not authenticated — no separate public base template needed"

patterns-established:
  - "Single HTMX source of truth: base.html only"
  - "Alpine.js per-template in head_extra (only on pages requiring it)"

# Metrics
duration: 3min
completed: 2026-04-06
---

# Phase 5 Plan 01: UI Gap Closure Summary

**HTMX consolidated to 2.0.4 globally, Form 7A/9A buttons added to all document sections, x-cloak CSS added, and public nav wired for unauthenticated users**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T00:00:17Z
- **Completed:** 2026-04-06T00:02:36Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments

- Single HTMX 2.0.4 script with integrity hash now loads from base.html; child template duplicates removed from documents/index.html and wizard_shell.html
- Form 7A (Plaintiff's Claim) and Form 9A (Defence) buttons added in both the from-claim loop and the standalone section of the documents index page — users can now initiate all three document types from that page
- `[x-cloak] { display: none !important; }` added to main.css immediately after the body rule, following Alpine.js standard pattern
- `{% else %}` nav branch added to base.html providing Guide, Fees, and Log in links to unauthenticated users on public pages (/guide, /fees)

## Task Commits

Each task was committed atomically:

1. **Task 1: x-cloak CSS and HTMX consolidation** - `a55e63a` (feat)
2. **Task 2: Form 7A/9A buttons and public navigation** - `a68ac2f` (feat)

**Plan metadata:** _(to follow)_

## Files Created/Modified

- `app/static/css/main.css` - Added [x-cloak] display:none rule after body block
- `app/templates/base.html` - Upgraded HTMX 1.9.12 to 2.0.4 with integrity hash; added {% else %} public nav branch
- `app/templates/documents/index.html` - Removed local HTMX head_extra block; added Form 7A/9A buttons in from-claim loop and standalone section
- `app/templates/assessment/wizard_shell.html` - Removed HTMX from head_extra (Alpine.js preserved)

## Decisions Made

- HTMX 2.0.4 loaded with SRI integrity hash — consistent with the version already used in child templates before consolidation; no version conflict
- Public nav placed in `{% else %}` branch of `current_user.is_authenticated` rather than a separate public base template — keeps nav logic in one file, minimal change surface
- No new routes, models, or Python logic added — purely template and CSS edits as planned

## Deviations from Plan

None - plan executed exactly as written.

The plan's verification note stated `grep -c "form_7a"` should return 4 (two from-claim, two standalone). The actual count is 2 because there is one from-claim button and one standalone button per form type — each on its own line. The buttons were added correctly per the action description; the comment in the verification count was a documentation error in the plan, not an implementation gap.

## Issues Encountered

- No `tests/` directory exists in the project — `python -m pytest tests/ -x -q` produced "no tests ran" rather than a pass/fail result. Flask template render check (`test_client().get('/documents/')`) returned HTTP 200 confirming no template syntax errors.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All five v1.0 milestone audit gaps now closed
- Phase 6 (testing and hardening) can begin — the template and CSS foundation is stable
- No blockers introduced by this plan

---
*Phase: 05-ui-gap-closure-and-polish*
*Completed: 2026-04-06*
