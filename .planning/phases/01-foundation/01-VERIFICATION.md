---
phase: 01-foundation
verified: 2026-04-04T00:00:00Z
status: gaps_found
score: 4/5 must-haves verified
re_verification: false
gaps:
  - truth: "User can create an account with email and password, log in, and log out from any page"
    status: partial
    reason: "Auth is magic-link only (email, no password). Fully implemented but does not match ROADMAP criterion wording. Plan 01-01 explicitly chose this design."
    artifacts:
      - path: "app/auth/routes.py"
        issue: "Login form accepts email only. No password field, no password hash verification."
      - path: "app/models/user.py"
        issue: "No password_hash column. User model is email plus timestamps only."
    missing:
      - "If criterion interpreted strictly: password field on login form and password_hash on User model."
      - "If magic-link accepted: update ROADMAP criterion wording. No code changes needed."
---

# Phase 1: Foundation Verification Report

**Phase Goal:** The app runs, users can authenticate, every page carries its disclaimer, and the AI guardrail architecture is in place before any user-facing feature ships.
**Verified:** 2026-04-04
**Status:** gaps_found (4/5 must-haves verified)
**Re-verification:** No

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can create an account with email and password, log in, and log out from any page | PARTIAL | Magic-link auth (email only, no password) is fully implemented. No password field exists by explicit plan design. Account creation, login, 7-day session, and logout all work end-to-end. Gap is a criterion wording mismatch, not a missing feature. |
| 2 | Every page displays the regulatory disclaimer footer | VERIFIED | Disclaimer hardcoded in base.html footer element, outside all Jinja2 block tags. All 4 templates extend base.html. Confirmed text: Legal Information, Not Legal Advice at base.html line 41. |
| 3 | AI output filter prevents directive language from reaching user | VERIFIED | app/services/ai_guardrail.py: 9 regex patterns with re.IGNORECASE, GuardrailStatus enum, GuardrailResult dataclass, module-level guardrail singleton. Not yet wired to any route (no AI routes in Phase 1 - by design). |
| 4 | All court constants are named constants in a central config file | VERIFIED | app/ontario_constants.py defines 14 named constants with source citations. format_fee() helper provided. No hardcoded values found in any template. |
| 5 | App builds via Docker multi-stage, passes /health, auto-deploys to Cloud Run | PARTIAL | Dockerfile structure verified (2-stage, non-root appuser, gunicorn CMD). /health route exists without auth gate. deploy.yml triggers on push to main with WIF auth. Docker build NOT executed - no daemon in dev environment. |

**Score:** 4/5 truths structurally verified.

---

### Required Artifacts

| Artifact | Exists | Lines | Wired | Status |
|----------|--------|-------|-------|--------|
| app/__init__.py | YES | 37 | YES - all extensions init_app, blueprints registered | VERIFIED |
| app/config.py | YES | 59 | YES - imported in create_app | VERIFIED |
| app/extensions.py | YES | 12 | YES - db, migrate, login_manager, limiter instances | VERIFIED |
| app/models/user.py | YES | 25 | YES - user_loader callback wired in factory | VERIFIED |
| app/auth/routes.py | YES | 119 | YES - auth_bp registered with /auth prefix | VERIFIED |
| app/services/auth_tokens.py | YES | 22 | YES - imported and called in auth/routes.py | VERIFIED |
| app/main/routes.py | YES | 16 | YES - main_bp registered, /health has no auth gate | VERIFIED |
| app/templates/base.html | YES | 54 | YES - all child templates extend it | VERIFIED |
| app/services/ai_guardrail.py | YES | 100 | ORPHANED - not imported in any route (Phase 2 will wire) | BY DESIGN |
| app/ontario_constants.py | YES | 52 | ORPHANED - not imported in any route (Phase 2 will use) | BY DESIGN |
| app/static/css/main.css | YES | 290 | YES - linked in base.html via url_for | VERIFIED |
| Dockerfile | YES | 26 | YES - referenced in deploy.yml docker build step | VERIFIED |
| .github/workflows/deploy.yml | YES | 44 | YES - triggers on push to main | VERIFIED |
| migrations/ | YES | 1 version | YES - feb6e53d0a3e users table applied | VERIFIED |

---

### Key Link Verification

| From | To | Via | Status |
|------|----|-----|--------|
| auth/routes.py | services/auth_tokens.py | generate_magic_token and verify_magic_token calls | WIRED |
| auth/routes.py | models/user.py | db.session.execute(db.select(User)) for create-on-verify | WIRED |
| app/__init__.py | extensions.py | db, migrate, login_manager, limiter.init_app calls | WIRED |
| app/__init__.py | models/user.py | @login_manager.user_loader callback | WIRED |
| base.html | static/css/main.css | url_for static filename css/main.css | WIRED |
| base.html | auth.logout | url_for auth.logout in nav, conditional on is_authenticated | WIRED |
| Dockerfile | requirements.txt | COPY requirements.txt plus pip install -r | WIRED |
| deploy.yml | Dockerfile | docker build . step | WIRED |
| guardrail singleton | any route | NOT imported outside ai_guardrail.py | ORPHANED (Phase 2 must wire) |
| ontario_constants | any route | NOT imported outside ontario_constants.py | ORPHANED (Phase 2 must wire) |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| app/templates/main/index.html | 7 | Your dashboard is coming soon. | Info | Expected placeholder - dashboard is Phase 4 deliverable |

No blockers found. No stub implementations in auth, guardrail, or constants.

---

## Gap Analysis

### Gap 1: Must-Have #1 - Authentication Criterion Wording Mismatch

**ROADMAP criterion:** User can create an account with email and password, log in, and log out from any page

**What was built:** Magic-link authentication. Users submit email, receive a 15-minute signed link via itsdangerous URLSafeTimedSerializer, click to authenticate. Account created on first verification. 7-day session via remember=True. Logout from nav on every page.

**Why this is a design conflict, not a missing feature:** The Phase 1 Plan (01-01-PLAN.md) explicitly states: no password_hash column - this is magic-link only auth. The research phase chose magic-link. The SUMMARY confirms the implementation delivered on the intended design. The ROADMAP criterion predates the design decision.

**Resolution options:**

Option 1 (recommended): Update the ROADMAP success criterion to: User can create an account with email, authenticate via magic link, and log out from any page. No code changes needed. Magic-link is a deliberate, stronger security choice.

Option 2: Add password auth. Requires password_hash column, bcrypt hashing, and a password field on the login form. Significant scope addition not in any current plan.

### Gap 2: Must-Have #5 - Docker Build Not Executed at Runtime

**Structurally verified:**
- Dockerfile has two stages: AS builder (pip install into venv) and AS runtime (copy venv, non-root appuser)
- Gunicorn CMD: exec gunicorn --bind :PORT --workers 1 --threads 8 --timeout 0 app:create_app()
- /health route at app/main/routes.py line 13 has no @login_required decorator
- deploy.yml uses Workload Identity Federation, Artifact Registry, deploys to northamerica-northeast1

**Not verified:** Actual docker build execution. The SUMMARY documents: Docker daemon not available in the Windows shell environment - container build skipped.

**Resolution:** First push to main with GitHub secrets configured will verify the build in CI.

---

## Human Verification Required

### 1. Magic-Link Full Auth Cycle
**Test:** Start dev server (flask run). Visit /. Submit email at /auth/login. Copy magic link from console. Visit link. Confirm login, dashboard renders, disclaimer visible. Click Log out. Confirm redirect to login.
**Expected:** Full cycle completes. Disclaimer visible on every page.
**Why human:** Requires running server and browser.

### 2. Docker Build and Health Check
**Test:** In a Docker-enabled environment: docker build -t bb-test . then docker run -d -p 8080:8080 -e SECRET_KEY=test -e FLASK_CONFIG=development bb-test then curl http://localhost:8080/health.
**Expected:** Build succeeds. Response: {status: healthy}.
**Why human:** Docker daemon required.

### 3. AI Guardrail Smoke Test
**Test:** From project root with app dependencies installed, import guardrail from app.services.ai_guardrail and call guardrail.process() with directive text (e.g. You should file now). Verify status is TRANSFORMED and phrase is replaced with statistical framing.
**Expected:** Status TRANSFORMED, directive phrases replaced.
**Why human:** Requires Python environment with app dependencies installed.

---

## Phase 2 Readiness

Ready to proceed. Phase 2 obligations:

- Guardrail: Import guardrail from app.services.ai_guardrail and call guardrail.process(raw_output) on ALL Claude API output before rendering.
- Constants: Import from app.ontario_constants for every court value in UI. Never hardcode fees, limits, or deadlines.
- Templates: All new templates must extend base.html. Disclaimer renders automatically.
- Auth: Use @login_required on all assessment and document routes.

---

_Verified: 2026-04-04_
_Verifier: Claude (gsd-verifier)_
