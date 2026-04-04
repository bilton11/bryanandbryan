# Bryan and Bryan

## What This Is

A tech-enhanced Ontario Small Claims Court platform that provides guided self-service tools for self-represented litigants (SRLs). Built as a hybrid legal tech product: self-service assessment, document generation, and process guidance layered on top of a licensed lawyer's practice. The POC proves that an SRL can assess their claim, generate court-ready documents, and understand the process — without the platform crossing into legal advice.

## Core Value

An SRL can walk through a guided case assessment, get a clear picture of their situation, and produce court-ready documents — all framed as legal information, never legal advice.

## Requirements

### Validated

(None yet — ship to validate)

### Active

- [ ] Case assessment wizard with multi-step guided interview (claim type, facts, limitation check, jurisdiction, evidence inventory, AI strength indicator)
- [ ] AI-powered case strength indicator using Anthropic API with strict regulatory guardrails (legal information only, never directive language)
- [ ] PDF case assessment summary generation with disclaimer on every page
- [ ] Document generator for Plaintiff's Claim (Form 7A), Defence (Form 9A), and Demand Letter — deterministic templates, no AI
- [ ] Filing fee calculator ($108 claim, $77 defence, etc.)
- [ ] Plain-language process guide covering the full Small Claims Court lifecycle (filing through enforcement)
- [ ] Deadline tracker with deterministic calculation from key dates (limitation period, defence deadline, settlement conference, trial request)
- [ ] Timeline visualization for calculated deadlines
- [ ] Professional landing page with clear value props and pricing placeholder
- [ ] User authentication (basic, for POC)
- [ ] User dashboard showing claims, documents, and deadlines
- [ ] Mobile-responsive design (most SRLs access on phones)
- [ ] WCAG 2.1 AA accessibility
- [ ] Regulatory disclaimer on every page
- [ ] Health check endpoint
- [ ] CI/CD pipeline: GitHub Actions → Cloud Run auto-deploy on push to main
- [ ] Docker multi-stage build with gunicorn

### Out of Scope

- Stripe payment integration — stub only for POC, no real transactions
- AI-generated document content — deterministic templates only for safest regulatory position
- CanLII API integration — stub only for POC
- Email reminders for deadlines — stub for future implementation
- OAuth/social login — email/password sufficient for POC
- Multi-province support — Ontario only
- Real-time chat or messaging — not needed for POC
- Paralegal matching/referral system — future feature

## Context

- **Partnership**: Tech builder + Ontario-licensed lawyer. Lawyer handles regulatory oversight and content accuracy. Tech side handles platform development.
- **Regulatory environment**: LSO (Law Society of Ontario) regulates legal services. Platform must stay firmly on the "legal information" side — never "legal advice." All AI outputs must avoid directive language ("you should", "I recommend"). Every page carries disclaimer.
- **Target users**: Self-represented litigants in Ontario Small Claims Court. Many access on mobile. Many have no legal background. Tone must be professional, approachable, empowering — never condescending or legalese-heavy.
- **Ontario Small Claims Court**: Monetary limit $50,000 (as of Oct 2025). Cannot hear libel/slander, title to land, etc. General 2-year limitation period under Limitations Act with exceptions.
- **POC audience**: Internal — the two partners evaluating whether the concept works and the regulatory positioning holds.

## Constraints

- **Tech stack**: Flask 3.x, PostgreSQL 15 (SQLAlchemy 2.0 + Alembic), Jinja2 + HTMX + Alpine.js, Tailwind CSS (CDN), Anthropic API (Claude Sonnet), Docker, GitHub Actions → Cloud Run — non-negotiable, matches existing workflow
- **Data residency**: All infrastructure in `northamerica-northeast1` (Montreal) — Canadian data residency matters for legal tech
- **Infrastructure**: GCP Cloud Run, new Cloud SQL PostgreSQL 15 instance, Artifact Registry, Secret Manager
- **Regulatory**: No directive language in AI outputs. Disclaimer on every page. Document generation is template-only (no AI). Assessment framed as "factors a court would typically consider," never predictions or recommendations.
- **Branding**: Navy (#1e3a5f) + teal (#0d9488) + warm gray (#f5f5f4). Product name: Bryan and Bryan. Tagline: "Navigate Ontario Small Claims Court with confidence."

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| No AI for document generation | Safest regulatory position — pure template formatting, zero hallucination risk | — Pending |
| Statistical framing for AI assessment | "Cases with similar characteristics..." not "you should..." — stays on legal info side | — Pending |
| Flask over Django | Matches existing workflow, lighter for POC scope | — Pending |
| HTMX + Alpine.js over SPA | Server-rendered with progressive enhancement, simpler architecture | — Pending |
| New Cloud SQL instance | Clean separation from other projects | — Pending |
| Montreal region | Canadian data residency for legal tech | — Pending |
| Partner is a lawyer (not paralegal) | Broader regulatory scope than paralegal license | — Pending |

---
*Last updated: 2026-04-04 after initialization*
