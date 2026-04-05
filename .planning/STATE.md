# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** An SRL can walk through a guided case assessment, get a clear picture of their situation, and produce court-ready documents — all framed as legal information, never legal advice.
**Current focus:** Phase 3 — Documents and Guide

## Current Position

Phase: 3 of 4 (Documents and Guide)
Plan: 0 of 2 in current phase
Status: Ready to plan
Last activity: 2026-04-05 — Phase 2 complete, verified, approved

Progress: [█████░░░░░] 50%

## Performance Metrics

**Velocity:**
- Total plans completed: 4
- Average duration: 6 minutes
- Total execution time: 20 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2/2 completed | 8 min | 4 min |
| 02-case-assessment | 3/3 completed | 20 min | 7 min |

**Recent Trend:**
- Last 5 plans: 01-02 (3 min), 02-01 (8 min), 02-02 (5 min), 02-03 (7 min)
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
- 02-01: JSONB with SQLite fallback via JSONB().with_variant(JSON(), "sqlite") — all JSONB columns should use this pattern
- 02-01: Both EXCLUDED and REDIRECTED claim types are hard stops — no acknowledgment checkbox, user must pick different type
- 02-01: REDIRECTED_CLAIM_TYPES values contain LAWYER_REVIEW_REQUIRED marker — supervising lawyer must review before launch
- 02-01: Assessment blueprint registered without URL prefix — routes define /assess/ paths directly
- 02-02: Limitation result serialised to step_data["limitation"] dict (dates as ISO strings) after facts step POST
- 02-02: REQUIRES_LAWYER_REVIEW always set when tolling_applied — automated deadline cannot be trusted for minor/incapacity cases
- 02-02: minor_dob field added to step_facts (Alpine.js conditional) — required for minor tolling to compute shifted deadline
- 02-03: AI_ASSESSMENT_ENABLED config flag in DefaultConfig — env var lawyer gate, disables AI without code deploy
- 02-03: PII exclusion from Claude prompt — build_claim_summary() strips names/addresses/emails, sends factual attributes only
- 02-03: PDF template fully standalone (no extends base.html) — system fonts only, no nav/logout, per-page disclaimer via CSS running()/element()
- 02-03: Finalize route owns DRAFT→ASSESSED transition — wizard_step/summary redirects to /finalize which calls AI and commits

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
Stopped at: Phase 2 complete — ready to plan Phase 3
Resume file: None
