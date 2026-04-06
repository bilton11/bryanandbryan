# Roadmap: Bryan and Bryan

## Overview

A licensed Ontario lawyer + tech builder POC that lets self-represented litigants assess their Small Claims Court claim, generate court-ready documents, and understand the process — all firmly on the "legal information" side of the LSO line. The build starts with regulatory guardrails baked into the architecture (they cannot be retrofitted), moves through the case assessment wizard and AI integration, then delivers document generation and the process guide, and closes with the user dashboard that ties everything together.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: Foundation** - App skeleton, auth, regulatory guardrails, and infrastructure plumbing
- [x] **Phase 2: Case Assessment** - Multi-step wizard, limitation calculator, jurisdiction check, AI strength indicator
- [x] **Phase 3: Documents and Guide** - PDF document generators (Demand Letter, Form 7A, Form 9A) and plain-language process guide
- [x] **Phase 4: Dashboard and Deployment** - User dashboard, deadline tracker, timeline visualization, lawyer escalation, and production deploy
- [x] **Phase 5: UI Gap Closure and Polish** - Form 7A/9A document buttons, HTMX consolidation, x-cloak CSS, public page navigation

## Phase Details

### Phase 1: Foundation
**Goal**: The app runs, users can authenticate, every page carries its disclaimer, and the AI guardrail architecture is in place before any user-facing feature ships.
**Depends on**: Nothing (first phase)
**Requirements**: AUTH-01, AUTH-02, AUTH-03, REGL-01, REGL-02, REGL-03, INFRA-01, INFRA-02, INFRA-03, INFRA-04
**Success Criteria** (what must be TRUE):
  1. User can create an account with email, authenticate via magic link, and log out from any page
  2. Every page in the app displays the "legal information, not legal advice" regulatory disclaimer footer
  3. A structural AI output filter is in place — no directive language ("you should", "I recommend") can reach the user regardless of what Claude returns
  4. All court fees, monetary limits, and procedural constants are defined as named constants in a central config file — zero hardcoded values in UI strings
  5. The app builds via Docker multi-stage, passes the /health endpoint check, and auto-deploys to Cloud Run on push to main
**Plans**: 2 plans

Plans:
- [x] 01-01-PLAN.md — App factory, User model, magic-link auth, Alembic migrations, health check
- [x] 01-02-PLAN.md — Regulatory disclaimer footer, AI guardrail wrapper, Ontario constants, mobile-first CSS, Docker build, CI/CD pipeline

### Phase 2: Case Assessment
**Goal**: A user can walk through the full guided case assessment — from dispute type routing through limitation check, jurisdiction validation, evidence inventory, and AI case strength indicator — and download a PDF summary.
**Depends on**: Phase 1
**Requirements**: ASMT-01, ASMT-02, ASMT-03, ASMT-04, ASMT-05, ASMT-06, ASMT-07
**Success Criteria** (what must be TRUE):
  1. User attempting to file a libel/slander or landlord-tenant claim is stopped at the router with a plain-language explanation of the correct forum
  2. User can complete the multi-step guided interview (claim type, facts, amount, opposing party) with progress persisted to the database between sessions
  3. The limitation period calculator produces the correct deadline using discovery date, handles minor tolling and municipal notice rules, and surfaces a clear warning when a claim may be time-barred
  4. The jurisdiction check prevents a user from proceeding if their claim amount exceeds $50,000 or the matter is outside Small Claims Court scope
  5. The AI case strength indicator displays statistical framing only ("cases with similar characteristics in Ontario...") — no directive language, no win probability percentage
  6. User can download a PDF case assessment summary with the regulatory disclaimer printed on every page
**Plans**: 3 plans

Plans:
- [x] 02-01-PLAN.md — Claim model, assessment blueprint, HTMX wizard skeleton, dispute type router
- [x] 02-02-PLAN.md — Limitation period calculator, jurisdiction check, evidence inventory checklist
- [x] 02-03-PLAN.md — AI case strength indicator and PDF assessment summary download

### Phase 3: Documents and Guide
**Goal**: A user can generate a Demand Letter, Plaintiff's Claim (Form 7A), or Defence (Form 9A) as a court-ready PDF, see the current filing fees, and read through the full plain-language process guide.
**Depends on**: Phase 2
**Requirements**: DOCS-01, DOCS-02, DOCS-03, DOCS-04, GUID-01, GUID-02, GUID-03, GUID-04
**Success Criteria** (what must be TRUE):
  1. User can generate a Demand Letter PDF from structured inputs — output is template-based with no AI-generated content
  2. User can generate a Plaintiff's Claim (Form 7A) PDF that matches the current Ontario court form version (August 1, 2022) and passes visual inspection against the Ontario Courts Public Portal format
  3. User can generate a Defence (Form 9A) PDF under the same template pipeline
  4. The filing fee calculator displays current fees ($108 claim, $77 defence) with citations to the Ontario.ca source — fees are read from named constants, not hardcoded
  5. User can read the full Small Claims Court lifecycle guide (filing through enforcement, including post-June 2025 Trial Management Conference reforms) via accordion-style sections, searchable with Alpine.js
**Plans**: 2 plans

Plans:
- [x] 03-01-PLAN.md — Document pipeline (Document/DocumentVersion models, documents blueprint, document service, Demand Letter PDF, filing fee page)
- [x] 03-02-PLAN.md — Form 7A and Form 9A pixel-perfect court forms, guided narrative prompts, plain-language process guide (8-stage accordion, Alpine.js search, settlement conference prep)

### Phase 4: Dashboard and Deployment
**Goal**: A logged-in user sees all their claims, generated documents, and upcoming deadlines in one place; the lawyer escalation pathway is live; and the platform is fully deployed to production on Cloud Run.
**Depends on**: Phase 3
**Requirements**: DASH-01, DASH-02, DASH-03, DASH-04
**Success Criteria** (what must be TRUE):
  1. User dashboard shows all their claims with status, all generated documents with download links, and upcoming deadline warnings
  2. The deadline tracker calculates and displays key dates (limitation period expiry, 20-day defence deadline after service, settlement conference window, trial request deadline) from user-entered key dates
  3. Timeline visualization renders calculated deadlines in chronological order
  4. User with a complex case (claim > $25K, corporate defendant, or flagged complexity) sees a clear escalation pathway to the partner lawyer
**Plans**: 2 plans

Plans:
- [x] 04-01-PLAN.md — Dashboard blueprint, deadline tracker service, claims/documents lists, CSS timeline visualization, navigation update
- [x] 04-02-PLAN.md — Lawyer escalation pathway, GitHub Actions deployment hardening, WCAG audit, regulatory sign-off checklist

### Phase 5: UI Gap Closure and Polish
**Goal**: Close the Form 7A/9A UI entry point gap identified in milestone audit, consolidate HTMX versions, and fix cosmetic/UX issues on public pages.
**Depends on**: Phase 4
**Requirements**: (gap closure — no new requirements)
**Gap Closure**: Closes integration gap (Form 7A/9A buttons) and broken E2E flow (Guide → Form 7A generation) from v1.0-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. User can create Form 7A and Form 9A documents from the documents index page — both standalone and from-claim paths, matching existing Demand Letter button pattern
  2. The Guide → Generate Form 7A flow completes end-to-end without hitting a dead end
  3. A single HTMX version loads across the entire app — no dual-version script tags
  4. The `[x-cloak]` CSS rule is present so Alpine.js-controlled elements do not flash before initialization
  5. Unauthenticated users on public pages (/guide, /fees) see navigation links to other public pages and login
**Plans**: 1 plan

Plans:
- [x] 05-01-PLAN.md — x-cloak CSS, HTMX 2.0.4 consolidation, Form 7A/9A document buttons, public page navigation

### Phase 6: Codebase Consistency Cleanup
**Goal**: Resolve documentation staleness, model export inconsistency, and CI safety gap identified in milestone audit tech debt.
**Depends on**: Phase 5
**Requirements**: (gap closure — no new requirements)
**Gap Closure**: Closes tech debt items from v1.0-MILESTONE-AUDIT.md
**Success Criteria** (what must be TRUE):
  1. Document and DocumentVersion models are exported from `app/models/__init__.py` consistent with all other models
  2. REQUIREMENTS.md traceability table shows correct status for all Phase 2, 3, and 4 requirements (Complete, not Pending)
  3. ROADMAP Phase 1 success criterion 1 matches actual implementation (magic-link auth, not email/password)
  4. `pytest` step in deploy.yml fails the pipeline on test failure — no `|| true` bypass
**Plans**: 0 plans

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5 → 6

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. Foundation | 2/2 | Complete | 2026-04-05 |
| 2. Case Assessment | 3/3 | Complete | 2026-04-05 |
| 3. Documents and Guide | 2/2 | Complete | 2026-04-06 |
| 4. Dashboard and Deployment | 2/2 | Complete | 2026-04-06 |
| 5. UI Gap Closure and Polish | 1/1 | Complete | 2026-04-06 |
| 6. Codebase Consistency Cleanup | 0/1 | Planned | — |
