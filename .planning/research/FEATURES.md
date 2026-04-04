# Feature Research

**Domain:** Ontario Small Claims Court self-service platform for self-represented litigants (SRLs)
**Researched:** 2026-04-04
**Confidence:** MEDIUM-HIGH (core features HIGH; AI framing patterns MEDIUM; competitor internals LOW)

---

## Context and Regulatory Frame

This platform operates under a hard constraint: it must stay on the **legal information** side of the legal information / legal advice boundary. This is not aesthetic — it is regulatory.

**The boundary in Canadian law:**
- Law societies regulate "legal advice" — the application of law to a specific person's specific facts with a recommendation.
- "Legal information" — general explanations of law and process — can be provided by anyone.
- The Moffatt v Air Canada (BC Small Claims) decision confirmed AI chatbots can be liable for negligent misrepresentation if outputs are inaccurate. Ontario is the only province with a legislated requirement (Dec 2024 Rules of Civil Procedure amendments) for AI certification.
- In 2026, Nippon Life sued OpenAI over ChatGPT allegedly crossing the UPL line by encouraging a pro se litigant to fire her attorney.

**The hybrid model here is the differentiator:** an Ontario-licensed lawyer is a partner. The platform handles information; the lawyer handles advice. That pairing is the product.

**AI output framing rule (non-negotiable):**
> Outputs use statistical framing: "In cases with similar characteristics, X% resulted in Y outcome." Never directive: "You should do X."

---

## Feature Landscape

### Table Stakes (Users Expect These)

Features that define minimum viability. An SRL landing on this platform expects these to exist. Missing any one of them causes abandonment.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| **Process walkthrough / procedural guide** | SRLs primary need is "what do I do next?" — without this, there's no product | MEDIUM | Must cover: pre-filing, claim filing, service, settlement conference, trial management conference (new June 2025), trial. Steps to Justice's Guided Pathways does this for free; must add value over it. |
| **Plain-language explanation of Small Claims Court** | Users arrive confused about what the court is, what it costs, who can use it | LOW | Scope ($50K limit as of Oct 2025), types of cases, who can appear (SRL, paralegal, lawyer), what you can recover |
| **Limitation period checker** | A 2-year clock that most users don't know about — missing it destroys the case | MEDIUM | Ontario basic limitation: 2 years from discovery. Over 40 statutes impose different periods. Must prominently warn; cannot calculate authoritatively (legal advice risk). Courtready.ca has a limitation period calculator. Output must be framed as "check this date, confirm with a lawyer." |
| **Court fee display / calculator** | Users want to know what this costs before they start | LOW | Infrequent claimant: $108 to file, $308 to set trial date, $94 default judgment. Frequent claimant (10+ claims/year): $228 to file, $403 trial date. Display, don't calculate dynamically — fees are flat, not amount-based. Source: Ontario Regulation 332/16. |
| **Document generation: Plaintiff's Claim (Form 7A)** | The core deliverable — the actual filing document | HIGH | Steps to Justice's Guided Pathways already generates this via guided interview. The question is: what's better/different about our version? Must output an Ontario Courts-compliant Form 7A. |
| **Document generation: basic demand letter** | Industry standard pre-litigation step; many disputes settle here | MEDIUM | Must be framed as a document the user sends, not legal advice. Factual narrative + claim amount + response deadline. PettyLawsuit's core loop starts here. |
| **Jurisdiction validation** | Users may not know which court to file in or whether they're eligible | MEDIUM | Three checks: (1) monetary limit ($50K per plaintiff), (2) cause of action type (money/personal property, not injunctions), (3) venue (defendant's address or where transaction occurred) |
| **Evidence checklist** | Users don't know what to gather or that they need 3 copies | LOW | Contracts, receipts, photos, emails/texts, expert estimates, invoices. Must serve originals 30 days before trial. Specific to dispute type (contractor dispute vs. unpaid debt vs. property damage). |
| **Basic FAQ / glossary** | Legal jargon is a barrier; SRLs are frequently lost in terminology | LOW | Terms: Plaintiff, Defendant, Service, Default Judgment, Settlement Conference, Trial Management Conference, Defendant's Claim, Garnishment, Writ of Seizure |

### Differentiators (Competitive Advantage)

Features that create value over and above the free public tools (Steps to Justice, ontario.ca, Courtready.ca).

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Case strength assessment (statistical framing)** | Helps SRLs understand their realistic position before investing time and money — no equivalent in free tools | HIGH | AI analyzes: dispute type, claim amount, available evidence, defendant type. Output: "Cases with these characteristics have a [range]% favorable outcome rate in Ontario Small Claims Court." Must never say "you will win" or "you should sue." Requires a corpus of Ontario Small Claims decisions or analog to train/calibrate framing. |
| **Dispute-type-specific guided interview** | Free tools are generic; specific dispute types (contractor, landlord, unpaid invoice, consumer product) have different legal elements, different evidence, different forms | HIGH | Contractor dispute interview differs from landlord-tenant (note: LTB handles most residential tenancy — must route-check), unpaid invoice, car accident, consumer product. Each pathway surfaces the relevant cause of action elements. |
| **Deadline tracker / case timeline** | Procedural deadlines are numerous and missing one is catastrophic; no free tool tracks them dynamically | MEDIUM | Tracks: limitation period warning, service deadline (within reasonable time after filing), defence deadline (20 days for defendant after service), settlement conference date, trial management conference date (new June 2025 rule), trial date, 30-day evidence service deadline before trial. |
| **Settlement conference prep tool** | Most cases resolve at settlement conference; SRLs are unprepared for this stage | MEDIUM | What to bring, how to present, what a judge-mediated settlement looks like, how to negotiate a number. Framed as information + preparation, not strategy advice. |
| **Post-judgment enforcement guide** | Getting a judgment is only half the battle; collecting is where SRLs fail | MEDIUM | Enforcement options: garnishment of wages/bank account, writ of seizure and sale, debtor examination (Examination in Aid of Execution). Courtready.ca has a debtor exam guide; we can integrate/expand. Each step has forms and fees. |
| **Lawyer escalation pathway** | The hybrid model: when the platform can't help further, warm handoff to the partner lawyer | LOW (integration) HIGH (trust design) | This is the business model. Platform identifies triggers: claim > $25K, complex fact pattern, counterclaim, defendant is a corporation with counsel. Framing: "Based on the complexity indicators in your case, this may benefit from a consultation with a licensed lawyer." Must not say "you need a lawyer" (that's legal advice). |
| **AI citation verification (hallucination guard)** | Cited cases that don't exist are a documented problem in Canadian courts (Courtready's CaseCheck addresses this) | MEDIUM | Any AI-generated document that references case law must be checked against CanLII or a verified database before display. Non-optional for any document going to court. |
| **Ontario-specific limitation period lookup by cause of action** | The standard 2-year period has 40+ exceptions — a generic calculator is insufficient | HIGH | Breach of contract, negligence, consumer protection, Construction Act liens (45 days), Employment Standards Act complaints, etc. Must present options with clear "verify with lawyer" framing. Courtready.ca has a special limitation periods tool; our version should be more integrated with the case flow. |
| **Dispute type router (LTB vs. Small Claims vs. ONCA)** | SRLs frequently try to bring cases in the wrong forum — residential tenancy goes to LTB, not Small Claims; some disputes need Superior Court | MEDIUM | Intake question set that determines: Is this a residential tenancy? (LTB) Is the claim over $50K? (Superior Court) Is this a human rights complaint? (HRTO) Routes with explanations, not just a hard stop. |

### Anti-Features (Commonly Requested, Often Problematic)

Features that seem desirable but create regulatory, liability, or scope problems.

| Feature | Why Requested | Why Problematic | Alternative |
|---------|---------------|-----------------|-------------|
| **"You should sue" / "you have a strong case" verdict** | Users want validation and a clear answer | Directive language = legal advice = UPL exposure. The Nippon Life v. OpenAI case (March 2026) is exactly this. | Statistical framing: "Cases with these evidence characteristics had favorable outcomes X% of the time in Ontario." Let users draw their own conclusions. |
| **Specific legal strategy recommendations** | Users want to know how to win, what arguments to make | This is what lawyers do. Providing it without a licence is UPL. Even with a licensed lawyer partner, the platform itself cannot give strategy. | The lawyer escalation pathway handles this. Platform provides information about legal elements and what courts have considered relevant; lawyer provides strategy. |
| **Win probability as a percentage claim** | Feels useful, data-driven | An exact percentage implies precision the data cannot support and creates an expectation. If a user sues relying on "73% win rate" and loses, liability exposure is real. | Ranges and framing: "In cases with similar characteristics, outcomes were mixed — approximately half resulted in judgment for the plaintiff." Qualitative bucketing over false precision. |
| **Automated court filing / e-filing integration** | Users want the platform to file for them | Ontario's e-filing portal (Ontario Courts Public Portal for Toronto; Justice Services Online for elsewhere) requires the filer to have an account and accept terms. Filing on behalf of someone without authorization may constitute legal services. The platform is not a paralegal. | Generate the completed form; walk the user through filing it themselves. Include direct links and step-by-step guidance for each portal. |
| **Legal advice chatbot ("ask our AI lawyer anything")** | Broad AI chat interface seems valuable | Without tight scope controls, users will ask for advice, and the AI will tend to give it. This is the Nippon Life scenario. | Scoped AI interactions only: the AI answers specific questions within a defined information framework, never freeform. "I can explain what courts have considered in cases like this. I can't tell you what to do." |
| **Comprehensive case management for multiple parties** | Seems like a natural extension | Scope creep. Multi-party cases with cross-claims, third-party claims, and corporate defendants are complex enough to require counsel. Building this invites users to use the platform for cases it can't adequately serve. | Hard cap: platform serves plaintiffs in individual, simple claims. Flags complexity indicators and escalates. |
| **Representing users at hearings (paralegal-equivalent service)** | Some users want full representation | This requires a paralegal licence in Ontario. Neither the platform nor an unlicensed person can provide it. | Clarify scope on landing page. Partner lawyer can provide representation as a paid service through the practice, not through the platform. |

---

## Feature Dependencies

```
[Dispute Type Router]
    └──required before──> [Case Strength Assessment]
    └──required before──> [Dispute-Type-Specific Guided Interview]
                              └──required before──> [Document Generation: Plaintiff's Claim]
                              └──required before──> [Evidence Checklist]
                              └──feeds into──> [Demand Letter Generator]

[Jurisdiction Validation]
    └──required before──> [Document Generation: Plaintiff's Claim]
    └──required before──> [Court Fee Display]

[Limitation Period Checker]
    └──standalone but integrates with──> [Case Strength Assessment]
    └──informs──> [Deadline Tracker]

[Document Generation: Plaintiff's Claim]
    └──feeds into──> [Deadline Tracker]
    └──precedes──> [Settlement Conference Prep Tool]
    └──precedes──> [Post-Judgment Enforcement Guide]

[AI Citation Verification]
    └──required wrapper around──> [Case Strength Assessment]
    └──required wrapper around──> [Any AI-generated document referencing case law]

[Case Strength Assessment]
    └──triggers conditionally──> [Lawyer Escalation Pathway]

[Deadline Tracker]
    └──enhances──> [Settlement Conference Prep Tool]
```

### Dependency Notes

- **Dispute Type Router is the entry gate:** Everything downstream assumes the user is in the right forum. A user who should be at the LTB getting a Plaintiff's Claim generated is a harm, not a help.
- **Jurisdiction Validation must precede Document Generation:** Generating a claim for a case outside Small Claims jurisdiction (>$50K, wrong cause of action type) is worse than generating nothing.
- **Limitation Period Checker is standalone but critical:** It can be used early (pre-qualification) or late (panic check). It must be prominent and reachable at any stage.
- **AI Citation Verification wraps all AI outputs:** Any feature that uses AI to generate text that might include case names requires hallucination checking. This is a non-optional safety layer.
- **Lawyer Escalation must be reachable from every feature:** Not just the end of a flow. If a user hits a complexity flag anywhere, they can route to the lawyer without losing their work.

---

## MVP Definition

### Launch With (v1)

Minimum viable POC — validates that the hybrid model works for real SRLs.

- [ ] **Dispute Type Router** — gates everything; prevents misuse from the start
- [ ] **Limitation Period Checker** — the most time-sensitive user need; a missed limitation period is irreversible harm
- [ ] **Process walkthrough / procedural guide** — plain language, Ontario-specific, covers the full Small Claims lifecycle post-June 2025 reforms
- [ ] **Evidence Checklist** — low complexity, high value, dispute-type-aware
- [ ] **Court Fee Display** — simple, static, accurate; answers the first question most users have
- [ ] **Document Generation: Demand Letter** — pre-litigation step with high settlement rate; lower legal complexity than the court form
- [ ] **Lawyer Escalation Pathway** — the business model; must be present at v1 to validate the hybrid proposition

### Add After Validation (v1.x)

Add once core loop is validated with real users.

- [ ] **Document Generation: Plaintiff's Claim (Form 7A)** — high value but higher complexity; requires verified form compliance with Ontario Courts rules
- [ ] **Jurisdiction Validation** — formalizes what the Dispute Type Router approximates; needed before Form 7A generation
- [ ] **Dispute-Type-Specific Guided Interview** — generalizing to multiple dispute types; start with most common (contractor, unpaid invoice)
- [ ] **Deadline Tracker** — needs real case data (filing date, service confirmation) to be useful; add when users have active cases on the platform
- [ ] **Settlement Conference Prep Tool** — add when v1 users start reaching the settlement conference stage

### Future Consideration (v2+)

Defer until product-market fit is established.

- [ ] **Case Strength Assessment (AI-powered)** — requires careful AI framing design, a source of Ontario Small Claims outcome data, and the AI Citation Verification layer; significant build and regulatory sensitivity
- [ ] **Post-Judgment Enforcement Guide** — valuable but only relevant after judgment; defer until users reach this stage
- [ ] **Ontario-Specific Limitation Period Lookup by Cause of Action** — full 40+ statute coverage; high research investment, useful for complex cases that may be out of scope anyway
- [ ] **AI Citation Verification tool** — standalone tool; needed as a wrapper when Case Strength Assessment ships

---

## Feature Prioritization Matrix

| Feature | User Value | Implementation Cost | Priority |
|---------|------------|---------------------|----------|
| Dispute Type Router | HIGH | LOW | P1 |
| Limitation Period Checker | HIGH | MEDIUM | P1 |
| Process Walkthrough | HIGH | MEDIUM | P1 |
| Court Fee Display | MEDIUM | LOW | P1 |
| Evidence Checklist | HIGH | LOW | P1 |
| Demand Letter Generator | HIGH | MEDIUM | P1 |
| Lawyer Escalation Pathway | HIGH | LOW | P1 |
| Plaintiff's Claim (Form 7A) | HIGH | HIGH | P2 |
| Jurisdiction Validation | HIGH | MEDIUM | P2 |
| Dispute-Type-Specific Interview | HIGH | HIGH | P2 |
| Deadline Tracker | MEDIUM | MEDIUM | P2 |
| Settlement Conference Prep | MEDIUM | MEDIUM | P2 |
| Case Strength Assessment | HIGH | HIGH | P3 |
| Post-Judgment Enforcement | MEDIUM | MEDIUM | P3 |
| AI Citation Verification | HIGH (safety) | MEDIUM | P3 (when AI ships) |
| Ontario Limitation Period Full DB | MEDIUM | HIGH | P3 |

**Priority key:**
- P1: Must have for POC launch
- P2: Add after core loop is validated
- P3: Future consideration; ship with later phases

---

## Competitor Feature Analysis

| Feature | Steps to Justice (CLEO) | Courtready.ca | PettyLawsuit (US) | Our Approach |
|---------|------------------------|---------------|-------------------|--------------|
| Process guide | Yes, comprehensive | Partial (Academy) | Yes (US-focused) | Yes — Ontario-specific, post-2025 reforms |
| Form 7A generation | Yes (guided pathway) | No | Not applicable (US) | Yes — with dispute-type-specific interview |
| Demand letter | No | No | Yes (core feature) | Yes — as pre-litigation step |
| Limitation period check | No | Yes (calculator) | No | Yes — with cause-of-action context |
| Court fee display | Basic (links out) | No | No | Yes — flat fee display, not dynamic calc |
| Evidence checklist | Partial (general tips) | No | Partial | Yes — dispute-type-specific |
| Case strength assessment | No | No | Claims 85% win rate (unverified) | Yes (v2+) — statistical framing only |
| Deadline tracker | No | Yes (deadlines calculator) | No | Yes (v1.x) — case-specific |
| Lawyer escalation | No (links to Law Society) | No | No | Yes — core hybrid proposition |
| Jurisdiction check | No | No | Yes (US-focused) | Yes — Ontario forum routing |
| Citation verification | No | Yes (CaseCheck tool) | No | Yes (when AI ships, as safety layer) |
| AI framing guardrails | N/A | N/A | Absent (concern) | Yes — statistical framing, non-directive |
| Ontario-specific | Yes | Yes | No | Yes — our primary advantage |

**Key gap in the market:** No existing tool combines Ontario-specific content + dispute-type-specific guidance + lawyer escalation + AI-guardrailed case assessment. The free tools (Steps to Justice, Courtready.ca) are excellent but have no escalation path. PettyLawsuit is US-only and has no legal advice boundary. The hybrid model is the gap.

---

## Sources

- [Steps to Justice — Small Claims Court Guided Pathways](https://stepstojustice.ca/guided-pathways/small-claims-court/) — MEDIUM confidence (page rendered as JS, content from search summary)
- [Ontario.ca — Fees for Small Claims Court](https://www.ontario.ca/page/fees-small-claims-court) — HIGH confidence (official government source, fetched directly)
- [Lexaltico — Ontario Small Claims Court Reform 2025](https://www.lexaltico.com/small-claims-court-reform-ontario/) — MEDIUM confidence (law firm summary)
- [Courtready.ca](https://courtready.ca/) — MEDIUM confidence (search results + attempted fetch; full feature list from search)
- [CLEO — New Guided Pathway: Responding to Small Claims Court](https://www.cleo.on.ca/en/whats-new/new-guided-pathway-responding-to-small-claims-court-cases) — MEDIUM confidence
- [PettyLawsuit press release, March 2026](https://news.marketersmedia.com/legal-tech-startup-pettylawsuit-introduces-ai-legal-services-to-rebuild-small-claims-court-expanding-access-to-justice-for-users/89185139) — LOW confidence (self-reported by company, US-only product)
- [Stanford CodeX — Nippon Life v. OpenAI (March 2026)](https://law.stanford.edu/2026/03/07/designed-to-cross-why-nippon-life-v-openai-is-a-product-liability-case/) — HIGH confidence (Stanford law analysis of active case)
- [Osler — Using Generative AI to Provide Legal Services in Canada](https://www.osler.com/en/insights/reports/ai-in-canada/using-generative-ai-to-provide-legal-services/) — HIGH confidence (major Canadian law firm)
- [ABA Journal — Re-Regulating UPL in the Age of AI (2025)](https://www.americanbar.org/groups/law_practice/resources/law-practice-magazine/2025/march-april-2025/re-regulating-upl-in-the-age-of-ai/) — MEDIUM confidence (US-focused, but instructive for principles)
- [Ontario.ca — Suing Someone in Small Claims Court](https://www.ontario.ca/page/suing-someone-small-claims-court) — HIGH confidence (official government source)
- [Steps to Justice — Get Your Evidence](https://stepstojustice.ca/steps/tribunals-and-courts/2-get-your-evidence/) — MEDIUM confidence
- [NSRLP — Representing Yourself Canada](https://representingyourselfcanada.com/) — MEDIUM confidence (national SRL advocacy org, research-backed)

---
*Feature research for: Ontario Small Claims Court self-service platform (Bryan and Bryan POC)*
*Researched: 2026-04-04*
