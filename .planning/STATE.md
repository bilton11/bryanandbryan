# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** An SRL can walk through a guided case assessment, get a clear picture of their situation, and produce court-ready documents — all framed as legal information, never legal advice.
**Current focus:** Phase 2 — Case Assessment

## Current Position

Phase: 2 of 4 (Case Assessment)
Plan: 0 of 3 in current phase
Status: Ready to plan
Last activity: 2026-04-05 — Phase 1 complete, verified, approved

Progress: [██░░░░░░░░] 25%

## Performance Metrics

**Velocity:**
- Total plans completed: 2
- Average duration: 4 minutes
- Total execution time: 8 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2/2 completed | 8 min | 4 min |

**Recent Trend:**
- Last 5 plans: 01-01 (5 min), 01-02 (3 min)
- Trend: stable

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Pre-start: No AI for document generation — template-only for safest regulatory position
- Pre-start: Statistical framing for AI assessment — "cases with similar characteristics..." not "you should..."
- Pre-start: Flask + HTMX + Alpine.js (no SPA, server-rendered partials)
- Pre-start: GCP Cloud Run + Cloud SQL, Montreal region (northamerica-northeast1) for Canadian data residency
- 01-01: flask-login pin is `>=0.6` (0.7 was never released on PyPI)
- 01-01: sqlalchemy pin is `>=2.0.49` (Python 3.14 compatibility fix for Optional[T] Mapped columns)
- 01-01: `from __future__ import annotations` required in all model files on Python 3.14
- 01-02: Disclaimer hardcoded in footer outside Jinja2 blocks — no child template can override (regulatory requirement)
- 01-02: Fees stored in cents as integers; format_fee() for display (avoids float errors)
- 01-02: AIGuardrail patterns marked LAWYER_REVIEW_REQUIRED — supervising lawyer must review before any AI feature ships
- 01-02: Workload Identity Federation (not service account key) for GitHub Actions → Cloud Run auth

### Pending Todos

None yet.

### Blockers/Concerns

- Phase 1: AI prompt guardrail architecture requires supervising lawyer sign-off before any user-facing AI feature ships (Nippon Life v. OpenAI March 2026 precedent)
- Phase 1: Data retention policy (specific retention periods and deletion workflows) must be decided by partners before schema design
- Phase 2: Limitation period branching logic must be reviewed by supervising lawyer before launch — discovery doctrine branches are legally sensitive
- Phase 4: WCAG/AODA audit must be treated as a pre-launch deliverable, not an afterthought (fines up to $100K/day)
- All phases: Python 3.14 is in use — verify any new SQLAlchemy model files have `from __future__ import annotations`
- CI/CD: GitHub repository secrets (GCP_PROJECT_ID, WIF_PROVIDER, WIF_SERVICE_ACCOUNT) must be configured before first deploy to main

## Session Continuity

Last session: 2026-04-05
Stopped at: Phase 1 complete — ready to plan Phase 2
Resume file: None
