# Project Research Summary

**Project:** Bryan and Bryan — Ontario Small Claims Court Self-Service Platform
**Domain:** Legal tech / document generation / AI-assisted case assessment (Ontario SRLs)
**Researched:** 2026-04-04
**Confidence:** HIGH

---

## Executive Summary

This is a hybrid legal information platform serving self-represented litigants (SRLs) in Ontario Small Claims Court. The defining product characteristic is a licensed Ontario lawyer as a partner — the platform delivers legal information and document generation while the lawyer handles legal advice via an escalation pathway. This hybrid model is the primary competitive gap in the market: free tools like Steps to Justice and Courtready.ca are well-built but have no escalation path. The product differentiates by combining Ontario-specific guidance, dispute-type-aware document generation, and a warm handoff to the partner lawyer when cases exceed the platform's scope.

The recommended stack is Flask 3.1.x + HTMX + PostgreSQL deployed to GCP Cloud Run — a deliberate lightweight choice that matches the partners' existing workflow and avoids the overhead of a full SPA or Django scaffolding for a two-person POC. The multi-step wizard is the core UX pattern: server-side state persisted to the database, HTMX handling step transitions, jinja2-fragments enabling partial renders without duplicating templates. WeasyPrint handles PDF generation from Jinja2 templates, which is the right fit for fixed-layout Ontario court forms. Claude Sonnet 4.6 handles case assessment with hard-coded statistical framing constraints.

The single most important risk on this project is not technical — it is regulatory. The AI component must be architected with structural guardrails against directive language before any user-facing feature ships. The Nippon Life v. OpenAI (March 2026) ruling established that terms-of-service disclaimers are not a defense against AI producing outputs that constitute legal advice. The supervising lawyer must review all AI prompt configurations, response templates, and output filtering logic before launch. This constraint, along with limitation period calculation complexity and court form version currency, must be treated as architecture-level decisions in Phase 1, not polish items for later phases.

---

## Key Findings

### Recommended Stack

The stack is fully verified against PyPI as of 2026-04-04. Flask 3.1.3 + SQLAlchemy 2.0.48 is the core, with Flask-SQLAlchemy 3.1.1 as the bridge. The Python minimum is 3.12 (driven by WeasyPrint 68.1's Python >= 3.10 requirement — use 3.12 for best performance). The frontend is HTMX 2.0.8 + Alpine.js 3.15.9 + Tailwind CSS v3 CDN, which eliminates a JS build step for the POC. The Tailwind CDN constraint must be revisited before real user traffic. Gunicorn 25.3.0 is the production server; Flask dev server is explicitly prohibited.

**Core technologies:**
- **Flask 3.1.3**: Web framework — lightweight, matches existing workflow, no unnecessary scaffolding
- **HTMX 2.0.8 + jinja2-fragments 1.11.0**: Multi-step wizard pattern — server-rendered partials, no client state management
- **WeasyPrint 68.1**: PDF generation — CSS-first workflow matches fixed-layout court forms; requires Debian-based Docker image (not Alpine)
- **SQLAlchemy 2.0.48 (Mapped column style)**: ORM — type-safe models, Alembic migrations via Flask-Migrate 4.1.0
- **anthropic 0.89.0 / claude-sonnet-4-6**: AI assessment — synchronous SDK, statistical framing only, $3/MTok input
- **GCP Cloud Run + Cloud SQL PostgreSQL 15**: Infrastructure — scales to zero, Montreal region for Canadian data residency
- **Flask-WTF 1.2.2**: CSRF protection — critical for HTMX requests which bypass CSRF unless explicitly configured

See `/planning/research/STACK.md` for full version matrix and Docker system dependency requirements.

### Expected Features

The feature set is governed by the legal information / legal advice boundary. Every feature must be designed to provide information and process guidance; the partner lawyer provides advice. The Dispute Type Router is the entry gate for the entire platform — it prevents users from pursuing claims in the wrong forum, which is harm rather than help.

**Must have (table stakes — v1 POC):**
- Dispute Type Router — forum check before anything else (LTB vs. Small Claims vs. Superior Court)
- Limitation Period Checker — most time-sensitive user need; missed deadline is irreversible; requires multi-branch logic (not naive date + 2 years)
- Process walkthrough / procedural guide — post-June 2025 reforms (Trial Management Conference is new)
- Evidence Checklist — dispute-type-specific, low complexity, high value
- Court Fee Display — flat display of current fees (infrequent claimant: $108 filing, $308 trial date)
- Demand Letter Generator — pre-litigation, high settlement rate, lower regulatory complexity than Form 7A
- Lawyer Escalation Pathway — the business model; must validate the hybrid proposition at v1

**Should have (competitive differentiators — v1.x after validation):**
- Plaintiff's Claim Form 7A generation — high value but high compliance complexity; requires verified form currency
- Jurisdiction Validation — formalizes what the router approximates
- Dispute-Type-Specific Guided Interview — start with contractor and unpaid invoice
- Deadline Tracker — add when users have active cases on the platform
- Settlement Conference Prep Tool — add when v1 users reach that stage

**Defer to v2+:**
- Case Strength Assessment (AI-powered) — requires Ontario Small Claims outcome data corpus, AI Citation Verification layer, significant regulatory sensitivity
- Post-Judgment Enforcement Guide — only relevant after judgment; defer until users reach this stage
- Ontario Limitation Period Full Database (40+ statutes) — high research investment
- AI Citation Verification (standalone) — prerequisite for Case Strength Assessment; build together

**Anti-features (never build):**
- "You should sue" / win probability meters / percentage-based outcome predictions
- Automated court filing on behalf of users
- Freeform AI legal advice chatbot
- Representing users at hearings

See `/planning/research/FEATURES.md` for competitor analysis and full dependency graph.

### Architecture Approach

The architecture follows a standard Flask blueprint structure with a strict service layer separation: routes handle HTTP mechanics only, services own all business logic, models are data containers. This layering is critical for testability — services must be callable without HTTP context. The Claim model is the central aggregate; it doubles as wizard state storage, preventing the 4KB session cookie limit problem.

**Major components:**
1. **`assess` blueprint + `assessment_service`** — Multi-step wizard, HTMX partial renders per step, server-side DB-backed wizard state
2. **`ai_service`** — Thin Anthropic SDK facade; the only file that imports `anthropic`; owns all prompt construction and response parsing
3. **`document_service` + `documents` blueprint** — Jinja2 → WeasyPrint → PDF pipeline; ownership check (claim.user_id == current_user.id) before generation
4. **`deadline_service`** — Pure Python date logic; limitation period calculations and procedural deadline tracking
5. **User / Claim / Document models** — SQLAlchemy 2.0 Mapped column style; Claim owns wizard state via `wizard_step` column

**Build order (hard dependencies):**
App factory → User/auth → Claim model → Base template/HTMX setup → Assess wizard skeleton → AI service → Assessment service → Deadline service → Documents blueprint/PDF → Dashboard → Guide (static) → Deployment config

See `/planning/research/ARCHITECTURE.md` for full component diagram, anti-patterns, and data flow diagrams.

### Critical Pitfalls

1. **AI produces directive legal advice** — Structural guardrails (not just system prompts) must prevent "you should file," "you will win," or any tailored legal conclusion. Nippon Life v. OpenAI (March 2026) frames this as a product-liability design defect. The supervising lawyer must review all prompt configurations before any user-facing AI feature ships. Statistical framing only: "In cases with similar characteristics, X% resulted in Y outcome."

2. **Limitation period calculator gives dangerously wrong dates** — The Limitations Act 2002 runs from the discovery date, not the incident date. Minors, incapacity, discoverability delay, municipality 10-day notice requirements, and the 15-year ultimate period all break naive "incident date + 2 years" logic. Multi-branch qualifier flow is mandatory from day one.

3. **Court forms generated with wrong or outdated version** — Form versions change via Ontario Regulation amendments without announcement. The current Form 7A version is dated August 1, 2022; monetary limit updated October 1, 2025 ($50K). Generated PDFs must be tested through the Ontario Courts Public Portal, not just visually inspected. Form version dates must be stored in the codebase with a quarterly review process.

4. **Stale content after court rule changes** — All dollar figures, fees, and procedural deadlines must be named constants in a central configuration file, never hardcoded in UI strings. The supervising lawyer is the content owner; quarterly review checklist is a pre-launch deliverable.

5. **Privacy breach of sensitive legal dispute information** — Claim content is PIPEDA high-risk (legal strategy, party names, financial details). Field-level encryption at rest, no logging of claim facts, no third-party analytics on input pages, and a PIPEDA breach notification workflow are required before launch.

See `/planning/research/PITFALLS.md` for full recovery strategies and "Looks Done But Isn't" checklist.

---

## Implications for Roadmap

### Phase 1: Foundation and Guardrails

**Rationale:** The regulatory constraints (AI framing, privacy, content architecture) cannot be retrofitted. Trying to add structural guardrails after the fact requires schema changes, rewritten prompts, and legal re-review of all outputs. This phase is the non-negotiable prerequisite for everything else. It also establishes the app factory pattern and database models that all downstream phases depend on.

**Delivers:**
- App factory, config, extensions (Flask app skeleton)
- User model + Flask-Login authentication
- Claim model (central aggregate + wizard state)
- Database migrations setup (Flask-Migrate + Alembic)
- Base Jinja2 template with HTMX/Alpine/Tailwind CDN wired up
- Central content configuration file (all fees, limits, deadlines as named constants — never in UI strings)
- AI service wrapper skeleton with statistical framing constraints hardcoded
- Privacy architecture: encryption-at-rest plan, no-logging policy for claim content
- Supervising lawyer sign-off on AI prompt constraints

**Addresses (from FEATURES.md):** Prerequisite infrastructure; no user-facing features yet
**Avoids (from PITFALLS.md):** Pitfalls 1 (AI advice), 4 (stale content), 5 (privacy breach)
**Research flag:** Standard patterns — Flask app factory and SQLAlchemy 2.0 are well-documented

---

### Phase 2: Core Information and Routing

**Rationale:** The Dispute Type Router is the entry gate for the entire platform — every downstream feature assumes the user is in the right forum. The Limitation Period Checker is the most time-sensitive user need (a missed deadline is irreversible) and needs multi-branch logic built correctly from the start, not added later. Process walkthrough and court fee display are low-complexity, high-value, and validate that the content architecture (named constants) works in practice.

**Delivers:**
- Dispute Type Router (LTB / Small Claims / Superior Court / HRTO routing)
- Limitation Period Checker with multi-branch logic (minor tolling, incapacity, municipality notice, discoverability caveat, 15-year ultimate period)
- Process walkthrough / procedural guide (Ontario-specific, post-June 2025 reforms including Trial Management Conference)
- Court fee display (infrequent and frequent claimant rates)
- Evidence checklist (dispute-type-aware)
- Basic FAQ / glossary

**Addresses (from FEATURES.md):** All P1 features except Demand Letter and Lawyer Escalation
**Avoids (from PITFALLS.md):** Pitfall 2 (limitation period miscalculation), Pitfall 4 (stale content)
**Research flag:** Limitation period branching logic may need deeper legal research during planning (40+ statutes, discoverability doctrine is heavily litigated). The supervising lawyer should validate all branching paths before launch.

---

### Phase 3: Document Generation and Lawyer Escalation

**Rationale:** Document generation is the core deliverable that distinguishes this platform from a guide site. The Demand Letter is lower regulatory complexity than Form 7A and validates the full document pipeline (Jinja2 → WeasyPrint → PDF) before tackling the court-certified form. Lawyer Escalation must ship in this phase because it is the business model — without it, the platform is just a free guide with no monetization path.

**Delivers:**
- Demand Letter Generator (Jinja2 template, WeasyPrint PDF output)
- Lawyer Escalation Pathway (trigger detection: claim > $25K, counterclaim, corporate defendant, complexity flags)
- Full document generation pipeline verified (WeasyPrint Docker config, PDF compliance testing against Ontario Courts Public Portal)
- Disclaimer-on-every-page CSS (`@page { @bottom-center { content: "..."; } }`)

**Uses (from STACK.md):** WeasyPrint 68.1, jinja2-fragments, Debian-based Docker base image
**Avoids (from PITFALLS.md):** Pitfall 3 (wrong form version), PDF compliance rejection
**Research flag:** WeasyPrint Docker system dependencies are well-documented. PDF compliance testing against the Ontario Courts Public Portal may surface edge cases — allocate time for iterative testing.

---

### Phase 4: Wizard and Case Assessment Flow

**Rationale:** The multi-step wizard is the most complex UX component (HTMX partial renders, server-side DB state, step validation, AI integration) and deserves its own phase after the document pipeline is verified. Building the wizard on top of an already-tested Claim model and document service reduces integration risk.

**Delivers:**
- Multi-step case assessment wizard (`assess` blueprint + assessment_service)
- HTMX wizard pattern fully implemented: full-page vs. fragment detection, jinja2-fragments render_block(), server-side state via Claim.wizard_step
- Jurisdiction validation integrated into wizard entry
- Dispute-Type-Specific Guided Interview (contractor and unpaid invoice pathways as initial set)

**Implements (from ARCHITECTURE.md):** Pattern 1 (full vs. partial render), Pattern 2 (service layer), Pattern 5 (DB-backed wizard state)
**Avoids (from PITFALLS.md):** Anti-Pattern 3 (wizard state in session cookie), Anti-Pattern 4 (Alpine owning navigation)
**Research flag:** HTMX multi-step wizard pattern is well-documented. The CSRF + HTMX header configuration requires explicit wiring (meta tag + JS event listener) — document this during planning.

---

### Phase 5: Plaintiff's Claim (Form 7A) and Dashboard

**Rationale:** Form 7A generation is deferred until the wizard and document pipeline are both proven in production. Form compliance requirements (version currency, portal testing, PDF spec) make this the highest-stakes document on the platform. The Dashboard ships here because it requires active claims to be meaningful.

**Delivers:**
- Plaintiff's Claim Form 7A generation (Jinja2 template matched to current August 1, 2022 version)
- Form version tracking in codebase with quarterly review process documented
- Dashboard: user claims list, status display, deadline warnings
- Deadline Tracker (limitation period warning + procedural deadlines)
- Settlement Conference Prep Tool

**Avoids (from PITFALLS.md):** Pitfall 3 (wrong form version), PDF portal rejection
**Research flag:** Form 7A template compliance needs pre-launch verification against ontariocourtforms.on.ca. Assign the supervising lawyer to confirm version currency. Portal testing is required (not optional visual inspection).

---

### Phase 6: AI Case Assessment (v2)

**Rationale:** Deferred because it requires the AI Citation Verification layer, a source of Ontario Small Claims outcome data, and the most intensive lawyer review of any feature. Shipping this without those prerequisites creates regulatory exposure. This phase also represents the most significant incremental monetization opportunity.

**Delivers:**
- Case Strength Assessment with statistical framing (AI-powered)
- AI Citation Verification wrapper (hallucination guard for any case law references)
- Audit log of all AI outputs (prompt/response pairs stored for lawyer review)
- Ontario-specific limitation period lookup expanded to high-frequency cause-of-action types

**Avoids (from PITFALLS.md):** Pitfall 1 (AI legal advice) — requires most rigorous guardrail verification of any phase
**Research flag:** NEEDS deeper research during planning. The source of Ontario Small Claims outcome data for calibrating statistical framing is an open question. CanLII integration for citation verification has no current implementation details. This phase should trigger a `/gsd:research-phase` before planning begins.

---

### Phase Ordering Rationale

- **Foundation before features** is non-negotiable: privacy architecture and content configuration (named constants) cannot be added after feature development without schema migrations and rework.
- **Router and limitations before document generation**: A user in the wrong forum or with a time-barred claim who receives a generated document is worse off than a user who never started.
- **Demand Letter before Form 7A**: Tests the full PDF pipeline at lower regulatory stakes before tackling the court-certified form.
- **Wizard after document pipeline**: Integrating an untested HTMX wizard with an untested PDF pipeline simultaneously multiplies debugging surface area.
- **AI assessment last**: All other features can ship safely without it. AI assessment has the highest regulatory sensitivity and should only ship when the rest of the platform is stable and the guardrail architecture is fully proven.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 2 (Limitation Period):** The discoverability doctrine and exception branches are complex enough that the supervising lawyer should review the branching logic before the phase planning begins. Not a `/gsd:research-phase` trigger, but requires legal subject-matter input.
- **Phase 6 (AI Assessment):** Source of Ontario Small Claims outcome data is unresolved. CanLII integration patterns have no implementation detail in the current research. This phase should trigger `/gsd:research-phase`.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (Foundation):** Flask app factory, SQLAlchemy 2.0, Docker setup — well-documented, established patterns
- **Phase 3 (Document Generation):** WeasyPrint + Flask pipeline is well-documented and specific to this stack
- **Phase 4 (Wizard):** HTMX multi-step wizard pattern is well-documented with Flask-specific examples
- **Phase 5 (Form 7A + Dashboard):** Standard Flask patterns; main work is content/compliance, not architecture research

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All versions verified against PyPI as of 2026-04-04; WeasyPrint Docker deps verified against official docs; model name verified against Anthropic official docs |
| Features | MEDIUM-HIGH | P1 features and anti-features are HIGH confidence (official government sources, regulatory analysis). Competitor internals (Courtready.ca, Steps to Justice) are MEDIUM — full feature lists from search results, not direct inspection |
| Architecture | HIGH | Flask/HTMX/SQLAlchemy patterns from official docs and high-confidence technical sources; legal-specific flows are inferred from the domain |
| Pitfalls | HIGH | Regulatory pitfalls from official sources (Ontario statutes, Stanford Law, Osler). Technical pitfalls from well-established Flask community patterns |

**Overall confidence: HIGH**

### Gaps to Address

- **Ontario Small Claims outcome data source (Phase 6):** No current answer for what dataset would calibrate the statistical framing in the AI case assessment. CanLII has decision text but no structured outcome metadata. This must be resolved before Phase 6 planning.
- **Gunicorn worker/thread configuration:** The `--workers 1 --threads 8` recommendation for Cloud Run is based on Google official docs + community sources, not empirical testing on this workload. Load test under realistic concurrency before finalizing.
- **AI prompt guardrail design:** The research establishes the constraint (statistical framing, no directive language) but the actual prompt architecture (system prompt structure, output post-processing filter) requires the supervising lawyer's input during Phase 1 planning. This is the highest-risk design decision on the project.
- **AODA/WCAG compliance scope:** Research identifies AODA as mandatory (fines up to $100K/day) and WCAG 2.0 AA as the minimum. The actual audit process and remediation effort are not scoped. This should be planned as a pre-launch deliverable, not an afterthought.
- **Data retention policy:** The research specifies privacy requirements (encrypted at rest, PIPEDA breach notification) but the specific retention periods and deletion workflows require a decision by the partners before schema design in Phase 1.

---

## Sources

### Primary (HIGH confidence)
- Ontario.ca — Fees for Small Claims Court (official government source, fees confirmed)
- Ontario.ca — Suing Someone in Small Claims Court (official process guidance)
- Ontario Limitations Act 2002 — Full statute text
- Anthropic Models Overview — claude-sonnet-4-6 confirmed as current recommended model
- WeasyPrint 68.1 official docs — system dependency requirements
- Flask, SQLAlchemy, HTMX, Alpine.js — all PyPI/GitHub official release pages
- Stanford Law / CodeX — Nippon Life v. OpenAI analysis (March 2026)
- Osler — Using Generative AI to Provide Legal Services in Canada
- Pallett Valo Lawyers — Ontario Small Claims Court June 2025 reforms
- Rudner Law — $50K monetary limit increase (October 2025)
- Office of the Privacy Commissioner — PIPEDA breach notification
- WCAG/AODA — Ontario digital accessibility requirements
- Ontario Court Services — Rules of the Small Claims Court Forms (form versions)

### Secondary (MEDIUM confidence)
- Lexaltico — Ontario Small Claims Court Reform 2025 (law firm summary)
- Steps to Justice — Small Claims Court Guided Pathways (JS-rendered, content from search)
- Courtready.ca — feature list from search results + attempted direct fetch
- CLEO — New Guided Pathway: Responding to Small Claims Court
- NSRLP — Representing Yourself Canada (national SRL advocacy org)
- BLG — Limitations Act 2002 ultimate limitation period
- Various Flask architecture and HTMX pattern sources (dev.to, Medium, hackersandslackers)

### Tertiary (LOW confidence)
- PettyLawsuit press release (March 2026) — self-reported company claims, US-only product

---
*Research completed: 2026-04-04*
*Ready for roadmap: yes*
