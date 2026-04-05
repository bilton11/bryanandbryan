# Requirements: Bryan and Bryan

**Defined:** 2026-04-04
**Core Value:** An SRL can walk through a guided case assessment, get a clear picture of their situation, and produce court-ready documents — all framed as legal information, never legal advice.

## v1 Requirements

### Foundation

- [x] **AUTH-01**: User can create account with email and authenticate via magic link
- [x] **AUTH-02**: User can log in and stay logged in across sessions
- [x] **AUTH-03**: User can log out from any page
- [x] **REGL-01**: Every page displays regulatory disclaimer footer ("legal information, not legal advice")
- [x] **REGL-02**: AI outputs structurally enforce statistical framing — no directive language ("you should", "I recommend") can reach the user
- [x] **REGL-03**: Court fees, monetary limits, and procedural constants stored as named constants (single source of truth, easy to update when rules change)
- [x] **INFRA-01**: Docker multi-stage build with gunicorn on python:3.12-slim
- [x] **INFRA-02**: CI/CD pipeline via GitHub Actions → Cloud Run, auto-deploy on push to main
- [x] **INFRA-03**: Health check endpoint at /health
- [x] **INFRA-04**: Mobile-first responsive design, WCAG 2.1 AA compliance

### Case Assessment

- [x] **ASMT-01**: Dispute type router validates claim type and prevents filing in wrong forum (e.g., excludes libel/slander, title to land)
- [x] **ASMT-02**: Multi-step guided interview collecting claim type, basic facts, amount, opposing party details
- [x] **ASMT-03**: Limitation period calculator with branching logic (discovery date, not incident date; tolling for minors/incapacitated; municipal notice obligations)
- [x] **ASMT-04**: Jurisdiction check confirming amount ≤ $50,000 and matter is within Small Claims Court scope
- [x] **ASMT-05**: Evidence inventory checklist with completeness scoring (contracts, receipts, photos, correspondence, witnesses)
- [x] **ASMT-06**: AI-powered case strength indicator using Claude Sonnet with statistical framing ("cases with similar characteristics in Ontario...")
- [x] **ASMT-07**: Downloadable PDF case assessment summary with disclaimer on every page

### Documents

- [ ] **DOCS-01**: Demand letter generator — template-based, structured inputs, no AI content generation
- [ ] **DOCS-02**: Plaintiff's Claim (Form 7A) generator — template-based, court-formatted, matching Ontario court requirements
- [ ] **DOCS-03**: Defence (Form 9A) generator — template-based, court-formatted
- [ ] **DOCS-04**: Filing fee calculator ($108 claim, $77 defence, etc.) with source citations

### Guide

- [ ] **GUID-01**: Plain-language process guide covering full Small Claims Court lifecycle (filing → service → defence → settlement conference → trial → enforcement)
- [ ] **GUID-02**: Settlement conference preparation guide (what to expect, what to bring, how to present)
- [ ] **GUID-03**: Searchable, accordion-style sections using Alpine.js
- [ ] **GUID-04**: Court fees schedule with citations to Ontario.ca and court rules

### Dashboard

- [ ] **DASH-01**: User dashboard showing all claims, generated documents, and upcoming deadlines
- [ ] **DASH-02**: Deadline tracker calculating from key dates (limitation period expiry, defence deadline 20 days after service, settlement conference window, trial request deadline)
- [ ] **DASH-03**: Timeline visualization for calculated deadlines
- [ ] **DASH-04**: Lawyer escalation pathway — clear handoff point to partner lawyer for complex cases

## v2 Requirements

### Payments

- **PAY-01**: Stripe integration for document generation tier ($99)
- **PAY-02**: Pricing page with functional payment flow

### Integrations

- **INTG-01**: CanLII API integration for case law references
- **INTG-02**: Email reminders for approaching deadlines

### Authentication

- **AUTH-04**: OAuth login (Google)
- **AUTH-05**: Password reset via email link

### Expansion

- **EXPN-01**: Multi-province support (beyond Ontario)
- **EXPN-02**: AI-generated document content (with lawyer review workflow)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Automated court filing | Requires direct integration with Ontario Courts portal — regulatory and technical complexity too high for POC |
| Freeform AI legal chatbot | Impossible to guarantee outputs stay on "legal information" side — highest regulatory risk |
| Win probability as precise percentage | Implies prediction of specific outcome — crosses into legal advice territory |
| Real-time chat/messaging | Not needed for POC; adds significant complexity |
| Paralegal matching/referral | Future feature — partner lawyer handles escalation directly for now |
| AI-generated document content | Template-only is safest regulatory position for POC — zero hallucination risk |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| AUTH-01 | Phase 1 | Complete |
| AUTH-02 | Phase 1 | Complete |
| AUTH-03 | Phase 1 | Complete |
| REGL-01 | Phase 1 | Complete |
| REGL-02 | Phase 1 | Complete |
| REGL-03 | Phase 1 | Complete |
| INFRA-01 | Phase 1 | Complete |
| INFRA-02 | Phase 1 | Complete |
| INFRA-03 | Phase 1 | Complete |
| INFRA-04 | Phase 1 | Complete |
| ASMT-01 | Phase 2 | Pending |
| ASMT-02 | Phase 2 | Pending |
| ASMT-03 | Phase 2 | Pending |
| ASMT-04 | Phase 2 | Pending |
| ASMT-05 | Phase 2 | Pending |
| ASMT-06 | Phase 2 | Pending |
| ASMT-07 | Phase 2 | Pending |
| DOCS-01 | Phase 3 | Pending |
| DOCS-02 | Phase 3 | Pending |
| DOCS-03 | Phase 3 | Pending |
| DOCS-04 | Phase 3 | Pending |
| GUID-01 | Phase 3 | Pending |
| GUID-02 | Phase 3 | Pending |
| GUID-03 | Phase 3 | Pending |
| GUID-04 | Phase 3 | Pending |
| DASH-01 | Phase 4 | Pending |
| DASH-02 | Phase 4 | Pending |
| DASH-03 | Phase 4 | Pending |
| DASH-04 | Phase 4 | Pending |

**Coverage:**
- v1 requirements: 29 total
- Mapped to phases: 29
- Unmapped: 0 ✓

---
*Requirements defined: 2026-04-04*
*Last updated: 2026-04-04 after roadmap creation*
