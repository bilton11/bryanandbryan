# Regulatory Sign-Off Checklist

**This checklist must be completed by the supervising lawyer before the platform is
made available to external users.**

Product: Bryan and Bryan — Ontario Small Claims Court Self-Help Tool
Version: Phase 4 — Dashboard and Deployment
Date prepared: 2026-04-06
Prepared by: Bryan Ilton (technical lead)
Reviewing lawyer: ___________________
Review date: ___________________

---

## 1. Legal Information vs. Legal Advice Boundary

- [ ] Disclaimer appears on every page — hardcoded in `base.html` footer, outside all
  Jinja2 blocks so no child template can override it (implemented in Phase 1, plan 01-02).
- [ ] All user-facing copy uses "legal information" framing, not "legal advice" framing.
- [ ] The platform never tells a user what they should do — only what the rules are
  and what options exist.

## 2. AI Assessment Controls

- [ ] AI assessment uses statistical framing only:
  "cases with similar characteristics resulted in..." — never predicts the user's outcome.
- [ ] AI assessment feature flag (`AI_ASSESSMENT_ENABLED` env var) can be disabled
  without a code deploy (implemented in Phase 2, plan 02-03).
- [ ] AI prompt reviewed: `build_claim_summary()` strips PII (names, addresses, emails)
  before sending to Claude (Phase 2, plan 02-03).
- [ ] AI prompt guardrail patterns marked `LAWYER_REVIEW_REQUIRED` have been reviewed
  by supervising lawyer before any AI feature ships to external users (Phase 1, plan 01-02).

## 3. Document Templates

- [ ] No AI-generated content in any court document template:
  - Demand Letter (`demand_letter.html`)
  - Form 7A — Plaintiff's Claim (`form_7a.html`)
  - Form 9A — Defence (`form_9a.html`)
- [ ] Form 7A and 9A template versions pinned:
  - Form 7A: August 1, 2022 (verify still current at ontariocourts.ca)
  - Form 9A: August 1, 2022 (verify still current at ontariocourts.ca)
- [ ] Court form field mappings reviewed for accuracy (Phase 3, plan 03-02).

## 4. Limitation Period Logic

- [ ] General 2-year limitation period correctly implemented
  (Limitations Act, 2002, s. 4).
- [ ] Ultimate 15-year limitation period correctly implemented (s. 15).
- [ ] Discovery doctrine branching logic reviewed — discovery date triggers tested.
- [ ] Minor tolling logic reviewed — `minor_dob` field shifts limitation correctly.
- [ ] Incapacity tolling logic reviewed.
- [ ] Municipal notice requirement (10 days) correctly flagged and explained.
- [ ] `REQUIRES_LAWYER_REVIEW` flag set for all tolled/minor/incapacity cases — these
  cannot be automatically computed (Phase 2, plan 02-02).

## 5. Escalation Triggers

- [ ] Claim amount > $25,000 triggers lawyer escalation panel on dashboard.
- [ ] Corporate / business defendant triggers lawyer escalation panel.
- [ ] Limitation status `requires_lawyer_review`, `expired`, or `ultimate_expired`
  triggers escalation panel.
- [ ] Escalation panel copy reviewed — reasons list is accurate and not misleading.
- [ ] Escalation panel disclaimer reviewed:
  "This recommendation is based on general case characteristics and does not
  constitute legal advice."

## 6. Redirected Claim Types

- [ ] `REDIRECTED_CLAIM_TYPES` values reviewed:
  - `defamation`: redirect message explains anti-SLAPP risk and Superior Court forum.
  - `landlord_tenant`: redirect message points to Landlord and Tenant Board.
- [ ] `EXCLUDED_CLAIM_TYPES` values reviewed (title to land, bankruptcy, false
  imprisonment, malicious prosecution — outside SCC jurisdiction entirely).
- [ ] Both excluded and redirected types are hard stops — user cannot proceed
  past the dispute type step (Phase 2, plan 02-01).

## 7. Accessibility (WCAG / AODA)

- [ ] WCAG 2.0 Level AA fundamentals verified (Phase 4, plan 04-02):
  - Keyboard navigation: all interactive elements reachable via Tab.
  - Visible focus indicator: 3px gold outline on all interactive elements.
  - Contrast ratios: all text meets 4.5:1 minimum.
  - Skip navigation link: present and functional.
  - Semantic HTML: `<ol>` timeline, `<th scope="col">` table headers, `<label for>`.
  - Heading hierarchy: h1 > h2 > h3, no skipped levels.
  - `aria-current="page"` on active nav link.
  - Error identification: invalid date input triggers flash message (WCAG 3.3.1).
- [ ] AODA IASR (Integrated Accessibility Standards Regulation) compliance reviewed
  for public-facing tool: new and significantly refreshed web content must meet
  WCAG 2.0 Level AA by January 1, 2021.

## 8. Data and Privacy

- [ ] Data retention policy decided — what is the maximum retention period for user
  claims, documents, and session data? (Currently no automated deletion workflow.)
- [ ] Privacy policy drafted and linked from the platform.
- [ ] Terms of use drafted and linked from the platform.
- [ ] PIPEDA / Ontario PHIPA review: confirm no health information is collected.
- [ ] Data residency confirmed: Cloud SQL and Cloud Run both in `northamerica-northeast1`
  (Montreal) — Canadian data residency for Ontario users.

## 9. Deployment and Operations

- [ ] GitHub repository secrets configured before first deploy to main:
  `GCP_PROJECT_ID`, `WIF_PROVIDER`, `WIF_SERVICE_ACCOUNT`.
- [ ] Cloud Run secrets provisioned in Secret Manager:
  `claimpilot-db-url`, `anthropic-api-key`, `flask-secret-key`.
- [ ] Cloud Build trigger in GCP Console disabled (GitHub Actions is the deploy path).
- [ ] Incident response plan exists for production outages.
- [ ] Monitoring / alerting configured for error rates and latency.

---

## Sign-Off

By signing below, the supervising lawyer confirms they have reviewed each item
above and are satisfied the platform meets applicable legal and ethical standards
for a legal information tool serving Ontario self-represented litigants.

**Supervising Lawyer:** ___________________

**Signature:** ___________________

**Date:** ___________________

**Notes / Conditions:**

> (Any conditional approvals, outstanding items, or required follow-up actions)
