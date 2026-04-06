---
phase: 06-codebase-consistency-cleanup
plan: 01
subsystem: infra
tags: [pytest, flask, sqlalchemy, ci, github-actions]

# Dependency graph
requires:
  - phase: 05-ui-gap-closure-and-polish
    provides: v1.0 UI polish — all functional gaps closed before tech debt cleanup
provides:
  - Document and DocumentVersion exported from app.models (consistent with User/Claim)
  - CI test gate enforced — test failures now block deployment
  - Smoke test suite (3 passing) covering app factory, model imports, health endpoint
  - REQUIREMENTS.md traceability table accurate — all 29 v1 requirements show Complete
  - ROADMAP.md Phase 1 criterion 1 confirmed matching actual magic-link implementation
affects: []

# Tech tracking
tech-stack:
  added: [pytest (tests/)]
  patterns: [smoke test fixture pattern with in-memory SQLite for CI]

key-files:
  created:
    - tests/__init__.py
    - tests/conftest.py
    - tests/test_smoke.py
  modified:
    - app/models/__init__.py
    - .github/workflows/deploy.yml
    - .planning/REQUIREMENTS.md

key-decisions:
  - "06-01: tests/ directory created with smoke tests to satisfy CI test gate (exit code 4 without tests/ would have blocked CI same as a failure)"
  - "06-01: conftest.py uses in-memory SQLite with TESTING=True override — no DATABASE_URL env var required in CI"
  - "06-01: ROADMAP.md Phase 1 criterion 1 was already correct ('magic link') — confirmed no-op"

patterns-established:
  - "Smoke test pattern: conftest.py session-scoped app fixture + in-memory SQLite for test isolation"

# Metrics
duration: 2min
completed: 2026-04-06
---

# Phase 6 Plan 01: Codebase Consistency Cleanup Summary

**Four v1.0 tech debt items resolved: Document/DocumentVersion model exports, CI test gate with passing smoke suite, 15 Pending requirements corrected to Complete, ROADMAP magic-link wording confirmed**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-06T16:17:15Z
- **Completed:** 2026-04-06T16:19:22Z
- **Tasks:** 2
- **Files modified:** 6 (including 3 new)

## Accomplishments

- Document and DocumentVersion are now importable from app.models alongside User and Claim
- CI/CD pipeline pytest step enforces test gate — `|| true` bypass removed, 3 smoke tests passing green
- All 29 v1 requirements show Complete in REQUIREMENTS.md traceability table (was 14 Pending across Phases 2-3)
- ROADMAP.md Phase 1 success criterion 1 confirmed already says "authenticate via magic link" — accurate

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix model exports and CI test gate** - `0a6d300` (feat)
2. **Task 2: Fix REQUIREMENTS.md traceability and verify ROADMAP wording** - `062715b` (docs)

**Plan metadata:** (this commit)

## Files Created/Modified

- `app/models/__init__.py` - Added `from app.models.document import Document, DocumentVersion`
- `.github/workflows/deploy.yml` - Removed `|| true` from pytest step (test failures now block CI)
- `tests/__init__.py` - Created (makes tests/ a Python package)
- `tests/conftest.py` - Session-scoped Flask app fixture with in-memory SQLite
- `tests/test_smoke.py` - 3 smoke tests: model imports, app factory, /health endpoint
- `.planning/REQUIREMENTS.md` - ASMT-01–07, DOCS-01–04, GUID-01–04 changed from Pending to Complete; Last updated line updated

## Decisions Made

- Created `tests/` directory with smoke tests (Rule 3 deviation): without a `tests/` directory, `python -m pytest tests/` exits with code 4 (no tests found) — non-zero exit blocks CI identically to a test failure. Smoke tests are the minimal correct fix.
- Used in-memory SQLite (`sqlite:///:memory:`) in conftest.py so tests pass in CI without any database environment variable configuration.
- ROADMAP.md edit was a confirmed no-op — "authenticate via magic link" was already present on Phase 1 success criterion 1.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created tests/ directory with smoke tests**

- **Found during:** Task 1 (Fix model exports and CI test gate)
- **Issue:** No `tests/` directory existed. Running `python -m pytest tests/ -v --tb=short` (the newly un-bypassed command) exits with code 4 ("file or directory not found") — this non-zero exit code would fail the CI step the same way a test failure would, preventing any deployment
- **Fix:** Created `tests/__init__.py`, `tests/conftest.py` (session-scoped in-memory SQLite fixture), and `tests/test_smoke.py` (3 tests: model imports, app factory, /health endpoint). All 3 pass.
- **Files modified:** tests/__init__.py, tests/conftest.py, tests/test_smoke.py
- **Verification:** `python -m pytest tests/ -v --tb=short` exits 0 with "3 passed"
- **Committed in:** 0a6d300 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Auto-fix was necessary for the CI test gate to work as intended. The intent of removing `|| true` is to block deploys on test failure — without a tests/ directory that intent could not be realized.

## Issues Encountered

None — all planned work completed without unexpected problems once the missing tests/ directory was addressed.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

Phase 6 is the final phase. With plan 01 complete:

- All four tech debt items from v1.0-MILESTONE-AUDIT.md are resolved
- v1.0 milestone is complete — all 29 requirements marked Complete, all audit items closed
- No blockers remain for the CI/CD pipeline tech debt concern (previously listed in STATE.md Blockers)
- Remaining blockers (lawyer sign-off, data retention policy, GitHub secrets) are pre-launch operational items, not build items

---
*Phase: 06-codebase-consistency-cleanup*
*Completed: 2026-04-06*
