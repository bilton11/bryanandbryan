# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-04-04)

**Core value:** An SRL can walk through a guided case assessment, get a clear picture of their situation, and produce court-ready documents — all framed as legal information, never legal advice.
**Current focus:** Milestone v1.0 complete

## Current Position

Phase: 5 of 6 (UI Gap Closure and Polish) — PLANNED
Plan: 0 of 1 in current phase — Not yet planned
Status: Gap closure phases added from milestone audit
Last activity: 2026-04-06 — Added gap closure phases 5-6 from v1.0 audit

Progress: [████████░░] 80% (4/6 phases complete)

## Performance Metrics

**Velocity:**
- Total plans completed: 9
- Average duration: 6 minutes
- Total execution time: 56 minutes

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-foundation | 2/2 completed | 8 min | 4 min |
| 02-case-assessment | 3/3 completed | 20 min | 7 min |
| 03-documents-and-guide | 2/2 completed | 18 min | 9 min |
| 04-dashboard-and-deployment | 2/2 completed | 12 min | 6 min |

**Recent Trend:**
- Last 5 plans: 03-01 (6 min), 03-02 (12 min), 04-01 (4 min), 04-02 (8 min)
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
- 03-01: documents blueprint registered without URL prefix — routes define /documents/ paths directly
- 03-01: DocumentVersion.input_data_snapshot taken at download time — review is free-edit until download triggers versioning
- 03-01: PDF download uses plain anchor tag (not HTMX) — HTMX cannot trigger binary file downloads
- 03-02: Form 7A/9A use table-based CSS layout exclusively — no Flexbox/Grid for WeasyPrint compatibility
- 03-02: Narrative stitching falls back to facts_description — backwards compatible with Demand Letter flow
- 03-02: monetary_limit_formatted passed as pre-formatted string from route — avoids custom Jinja2 filter
- 03-02: Guide accordion search uses data-keywords attribute — heading-filter approach, not full-text
- 03-02: GUIDE_STAGES constant added to ontario_constants.py — single source of truth for stage metadata
- 04-01: Timeline partial serves double duty — initial Jinja2 include and HTMX swap target (#timeline-{claim_id})
- 04-01: settlement_conf_date stored as user-entered date; trial_request_deadline = settlement_conf_date + 30 days
- 04-02: Dashboard route at /dashboard (not /) — avoids redirect loop with main.index
- 04-02: Claim labels use type + opposing party + amount instead of DB IDs
- 04-02: HTMX script loaded globally from base.html

### Pending Todos

None.

### Blockers/Concerns

- Phase 1: AI prompt guardrail architecture requires supervising lawyer sign-off before any user-facing AI feature ships (Nippon Life v. OpenAI March 2026 precedent)
- Phase 1: Data retention policy (specific retention periods and deletion workflows) must be decided by partners before schema design
- Phase 2: Limitation period branching logic must be reviewed by supervising lawyer before launch — discovery doctrine branches are legally sensitive
- Phase 4: pytest step in deploy.yml uses `|| true` — remove before external launch so test failures block deployment
- All phases: Python 3.14 is in use — verify any new SQLAlchemy model files have `from __future__ import annotations`
- CI/CD: GitHub repository secrets (GCP_PROJECT_ID, WIF_PROVIDER, WIF_SERVICE_ACCOUNT) must be configured before first deploy to main

## Session Continuity

Last session: 2026-04-06
Stopped at: Gap closure phases 5-6 created from milestone audit — ready to plan Phase 5
Resume file: None
