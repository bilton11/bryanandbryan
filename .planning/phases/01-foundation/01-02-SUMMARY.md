---
phase: 01-foundation
plan: 02
subsystem: infra
tags: [flask, jinja2, css, docker, github-actions, cloud-run, wcag, ai-guardrail, ontario-law]

# Dependency graph
requires:
  - phase: 01-01
    provides: Flask app factory, flask-login, magic-link auth, base.html skeleton, static/css placeholder
provides:
  - Mandatory non-overridable regulatory disclaimer footer on every page
  - AIGuardrail class that transforms directive language to statistical framing
  - Ontario Small Claims Court named constants with source citations
  - Mobile-first CSS with WCAG 2.1 AA fundamentals (navy/gold palette)
  - Docker multi-stage build (python:3.12-slim, non-root appuser)
  - GitHub Actions CI/CD workflow for Cloud Run (northamerica-northeast1)
affects:
  - All future phases — every template extends base.html with disclaimer
  - Phase 2+ AI features — must pass output through ai_guardrail.guardrail.process()
  - Phase 3 document generation — use ontario_constants.py for all fees and limits
  - Deployment — Dockerfile and deploy.yml define production build and release

# Tech tracking
tech-stack:
  added: [gunicorn]
  patterns:
    - Statistical framing via regex substitution (not LLM post-processing)
    - Fees stored in cents as integers (avoids floating-point errors)
    - CSS custom properties (design tokens) at :root
    - Mobile-first CSS with min-width breakpoints only

key-files:
  created:
    - app/services/ai_guardrail.py
    - app/ontario_constants.py
    - app/static/css/main.css
    - Dockerfile
    - .dockerignore
    - .github/workflows/deploy.yml
  modified:
    - app/templates/base.html
    - app/templates/auth/login.html
    - app/templates/auth/check_email.html
    - app/templates/auth/link_expired.html

key-decisions:
  - "Disclaimer hardcoded in footer (not in a Jinja2 block) — no child template can override it"
  - "Fees stored in cents as integers — format_fee() helper for display"
  - "AIGuardrail patterns marked LAWYER_REVIEW_REQUIRED — mandatory review gate"
  - "Docker runtime stage uses non-root appuser for security"
  - "Workload Identity Federation (not service account key) for GitHub Actions auth"

patterns-established:
  - "Guardrail pattern: all AI output passes through guardrail.process() before display"
  - "Constants pattern: all Ontario court values come from ontario_constants.py with source citations"
  - "Template pattern: all pages extend base.html — disclaimer always renders"
  - "CSS token pattern: colors/spacing defined as :root custom properties, never hardcoded"

# Metrics
duration: 3min
completed: 2026-04-05
---

# Phase 1 Plan 2: Regulatory Infrastructure Summary

**Non-overridable disclaimer footer, regex-based AI guardrail (9 directive patterns with LAWYER_REVIEW_REQUIRED markers), Ontario court constants in cents, mobile-first WCAG CSS, and Docker/GitHub Actions CI/CD pipeline for Cloud Run**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-05T00:51:28Z
- **Completed:** 2026-04-05T00:54:30Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments

- Hardcoded disclaimer footer in base.html outside all Jinja2 blocks — no child template can remove or override it
- AIGuardrail class with 9 regex patterns converting directive language ("you should", "you must", "I recommend", etc.) to statistical framing; marked LAWYER_REVIEW_REQUIRED throughout
- `ontario_constants.py` with 15 named constants for fees (in cents), monetary limits, and procedural deadlines, each citing the source statute or regulation
- Mobile-first CSS: navy/gold design tokens, WCAG focus styles (3px outline), 44px touch targets, skip-nav, reduced-motion media query, auth-card component
- Docker multi-stage build with python:3.12-slim, non-root `appuser`, gunicorn runtime
- GitHub Actions workflow using Workload Identity Federation to deploy to Cloud Run in `northamerica-northeast1`

## Task Commits

1. **Task 1: Regulatory layer — disclaimer, AI guardrail, Ontario constants** - `06fd5fc` (feat)
2. **Task 2: Mobile-first CSS, Docker build, and CI/CD pipeline** - `a1dd8b6` (feat)

**Plan metadata:** (docs commit follows)

## Files Created/Modified

- `app/templates/base.html` - Full base template with skip-nav, ARIA landmarks, non-overridable disclaimer footer
- `app/services/ai_guardrail.py` - AIGuardrail class, GuardrailStatus enum, GuardrailResult dataclass, singleton
- `app/ontario_constants.py` - 15 named constants with source citations, format_fee() helper
- `app/static/css/main.css` - 250-line mobile-first stylesheet with design tokens and WCAG compliance
- `app/templates/auth/login.html` - Updated to use .auth-card wrapper
- `app/templates/auth/check_email.html` - Updated to use .auth-card wrapper
- `app/templates/auth/link_expired.html` - Updated to use .auth-card, .btn-primary link
- `Dockerfile` - python:3.12-slim multi-stage build, non-root appuser, gunicorn
- `.dockerignore` - Excludes git, planning, pyc, venv, env files
- `.github/workflows/deploy.yml` - Cloud Run CI/CD via Workload Identity Federation

## Decisions Made

- **Disclaimer not in a block:** The footer disclaimer is hardcoded HTML — no `{% block %}` wrapper. This is the only mechanism in Jinja2's template inheritance that prevents child templates from overriding it. This is a regulatory requirement.
- **Fees in cents:** All filing fees stored as integers in cents (`FILING_FEE_INFREQUENT_CLAIMANT = 108_00`). The `format_fee()` helper divides by 100 for display. Avoids floating-point rounding errors in fee calculations.
- **LAWYER_REVIEW_REQUIRED markers:** Every directive-to-statistical pattern in `ai_guardrail.py` carries an inline comment `# LAWYER_REVIEW_REQUIRED`. These substitutions define the legal boundary between information and advice — supervising lawyer must review before any AI feature ships.
- **Workload Identity Federation:** The deploy workflow uses `google-github-actions/auth@v3` with WIF provider/service account secrets rather than a long-lived service account key. Better security posture for CI/CD.

## Deviations from Plan

None — plan executed exactly as written.

Note: Docker build could not be verified in the execution environment (Docker daemon not available in shell). Dockerfile structure is correct and matches the specified multi-stage pattern exactly. Build verification is a pre-deploy step in the GitHub Actions workflow.

## Issues Encountered

- Docker daemon not available in the Windows shell environment — container build and `/health` endpoint test skipped. The Dockerfile is structurally correct (AS builder stage, non-root user, gunicorn CMD). Verification will occur on first CI push.

## User Setup Required

None — no external service configuration required for this plan. CI/CD deployment requires GitHub repository secrets (`GCP_PROJECT_ID`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`) to be set before the first push to `main` triggers a deploy.

## Next Phase Readiness

- Phase 1 foundation complete — app factory, auth, regulatory layer, and deployment pipeline are all in place
- Phase 2 can begin: all AI assessment output must pass through `guardrail.process()` before rendering
- Ontario constants are the single source of truth — import from `app.ontario_constants`, never hardcode fees or limits in UI strings
- Supervising lawyer review of `ai_guardrail.py` patterns is a hard gate before any AI feature is user-facing

---
*Phase: 01-foundation*
*Completed: 2026-04-05*
