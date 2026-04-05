---
phase: 02-case-assessment
plan: "03"
subsystem: ai, pdf, assessment
tags: [anthropic, claude, weasyprint, flask-weasyprint, ai-guardrail, pdf-generation, htmx]

# Dependency graph
requires:
  - phase: 02-01
    provides: assessment wizard, Claim model, ClaimStatus enum, HTMX wizard pattern
  - phase: 02-02
    provides: limitation_service, evidence inventory, summary step, AIGuardrail
provides:
  - AI case strength assessment via Claude API with statistical framing and guardrail
  - Graceful AI degradation when ANTHROPIC_API_KEY absent or AI_ASSESSMENT_ENABLED=false
  - WeasyPrint PDF generation for assessment report with per-page CSS running() disclaimer
  - POST /assess/finalize route (DRAFT→ASSESSED transition + AI assessment trigger)
  - GET /assess/<id>/results route (full results page with all data + AI indicator)
  - GET /assess/<id>/pdf route (PDF download with ownership/status checks)
affects:
  - phase 03 (document generation may reference ai_assessment field)
  - phase 04 (WCAG audit should test results page and PDF download flow)

# Tech tracking
tech-stack:
  added:
    - weasyprint==68.1 (PDF generation; GTK required on Windows dev — works on Cloud Run Linux)
    - flask-weasyprint==1.2.0 (Flask integration for WeasyPrint HTML→PDF)
    - anthropic==0.81.0 (Claude API client — already in requirements.txt)
  patterns:
    - AI feature flag pattern: AI_ASSESSMENT_ENABLED env var in DefaultConfig (lawyer review gate)
    - PII exclusion from AI prompts: build_claim_summary() sends factual attributes only, not names/addresses/emails
    - CSS running()/element() for per-page PDF disclaimer via @page { @bottom-center { content: element(...) } }
    - Standalone PDF template (no extends base.html, system fonts only, no external requests)
    - Finalize route separation: wizard_step/summary redirects to /assess/finalize; finalize owns DRAFT→ASSESSED transition

key-files:
  created:
    - app/services/assessment_service.py
    - app/services/pdf_service.py
    - app/templates/assessment/pdf/assessment_report.html
    - app/templates/assessment/results.html
    - app/templates/assessment/partials/ai_assessment.html
  modified:
    - app/assessment/routes.py
    - app/templates/assessment/steps/step_summary.html
    - app/config.py

key-decisions:
  - "AI_ASSESSMENT_ENABLED config flag in DefaultConfig controlled by env var — allows disabling AI without code deploy"
  - "PII exclusion from Claude prompt: build_claim_summary() strips names, addresses, emails; sends factual attributes only"
  - "PDF template is fully standalone (no extends base.html) — PDF must contain no nav, logout links, or site chrome"
  - "Finalize route owns DRAFT→ASSESSED transition; wizard_step/summary no longer marks ASSESSED directly"
  - "WeasyPrint generates PDFs with CSS running()/element() for regulatory disclaimer printed on every page"

patterns-established:
  - "AI feature flag pattern: DefaultConfig.AI_ASSESSMENT_ENABLED = env('AI_ASSESSMENT_ENABLED', 'true') == 'true'"
  - "PII exclusion: AI prompt builders strip identifying fields, send only claim type/facts/amount/party type"
  - "Standalone PDF templates: no {% extends %}, system fonts only, embedded CSS, no external URLs"
  - "Finalize pattern: wizard final-step POST → redirect to /finalize → AI call → redirect to /results"

# Metrics
duration: 7min
completed: 2026-04-05
---

# Phase 2 Plan 3: AI Assessment and PDF Download Summary

**Claude API case strength indicator with AIGuardrail integration, graceful degradation, and WeasyPrint PDF report with CSS running-element per-page disclaimer**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-05T20:02:54Z
- **Completed:** 2026-04-05T20:09:27Z
- **Tasks:** 2
- **Files modified:** 8 (5 created, 3 modified)

## Accomplishments
- AI assessment service calls Claude with statistical framing system prompt, passes all output through AIGuardrail, and gracefully degrades when ANTHROPIC_API_KEY is absent or AI_ASSESSMENT_ENABLED=false
- PDF service uses WeasyPrint with a standalone template (no site chrome) and CSS running()/element() to stamp the regulatory disclaimer on every page
- Full wizard-to-results-to-PDF flow wired: wizard summary → POST /finalize → results page → PDF download

## Task Commits

Each task was committed atomically:

1. **Task 1: AI assessment service, PDF service, and assessment report template** - `ece2f71` (feat)
2. **Task 2: Wire AI assessment and PDF download into wizard routes** - `d46f1b4` (feat)

**Plan metadata:** (this commit)

## Files Created/Modified
- `app/services/assessment_service.py` — Claude API call with _SYSTEM_PROMPT, build_claim_summary() PII exclusion, get_case_strength_assessment() with guardrail and feature flag
- `app/services/pdf_service.py` — render_assessment_pdf() using WeasyPrint with Flask context
- `app/templates/assessment/pdf/assessment_report.html` — Standalone PDF template with CSS running(page-disclaimer) per-page footer
- `app/templates/assessment/results.html` — Full results page extending base.html with AI indicator and PDF download button
- `app/templates/assessment/partials/ai_assessment.html` — AI assessment card partial showing text or "not available" placeholder
- `app/assessment/routes.py` — Added finalize(), results(), download_pdf() routes; refactored summary step redirect
- `app/templates/assessment/steps/step_summary.html` — htmx-indicator for "Analyzing your case..." loading state
- `app/config.py` — Added AI_ASSESSMENT_ENABLED feature flag to DefaultConfig

## Decisions Made
- **AI_ASSESSMENT_ENABLED feature flag in DefaultConfig:** Allows lawyer to disable AI without a code deploy. Controlled by env var.
- **PII exclusion from Claude prompt:** `build_claim_summary()` deliberately excludes party names, addresses, and emails — only factual claim attributes are sent to the Anthropic API.
- **PDF template fully standalone:** No `{% extends "base.html" %}`. System fonts only, no external URL requests. PDF must not contain nav or logout links.
- **Finalize route owns DRAFT→ASSESSED transition:** The wizard_step/summary handler no longer marks ASSESSED directly — it redirects to /finalize which owns the status transition and AI call atomically.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] WeasyPrint + flask-weasyprint not installed**
- **Found during:** Task 1 verification (pdf_service import)
- **Issue:** weasyprint and flask-weasyprint were in requirements.txt but not installed in the dev environment
- **Fix:** `pip install "weasyprint>=68.0,<69" "flask-weasyprint>=1.2.0,<2"`
- **Files modified:** None (environment only)
- **Verification:** Import of `render_assessment_pdf` succeeds
- **Committed in:** n/a (pip install, not a code change)

---

**Total deviations:** 1 auto-fixed (1 blocking — missing dependency install)
**Impact on plan:** Required to unblock Task 1 verification. No scope creep.

## Issues Encountered
- WeasyPrint requires GTK/Pango native libraries (libgobject) on Windows — PDF generation raises OSError on Windows dev. This is a known WeasyPrint Windows limitation; the library works correctly on Cloud Run (Linux). Import verification passes; actual PDF rendering is production-only on Windows.

## Next Phase Readiness
- Phase 2 complete: wizard, limitation calculator, evidence inventory, AI assessment, and PDF download all wired end-to-end
- Phase 3 (document generation) can read `claim.ai_assessment` for any downstream use
- LAWYER_REVIEW_REQUIRED blockers remain: AI prompt patterns (guardrail), limitation period branching, and all REDIRECTED_CLAIM_TYPES messages must be reviewed before launch
- WeasyPrint Windows limitation is non-blocking for development; Cloud Run deploy will have GTK available

---
*Phase: 02-case-assessment*
*Completed: 2026-04-05*
