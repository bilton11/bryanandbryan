---
phase: 03
plan: 02
subsystem: documents-and-guide
tags: [form-7a, form-9a, pdf, weasyprint, guided-narrative, process-guide, alpine-js, accordion, search]
depends_on: ["03-01"]
provides:
  - Form 7A Plaintiff's Claim PDF template (court-form-faithful)
  - Form 9A Defence PDF template (court-form-faithful)
  - Guided narrative prompts on review page with freeform toggle
  - Full Small Claims Court process guide at /guide (8 stages)
  - Settlement Conference preparation sub-guide
  - Alpine.js accordion search and "Where am I?" navigator
affects:
  - 04-polish (all document types now fully operational)
tech-stack:
  added: []
  patterns:
    - Guided narrative stitching — sub-question answers assembled into prose paragraphs
    - WeasyPrint table-based CSS — no Flexbox/Grid in PDF templates
    - Alpine.js keyword-filter search — data-keywords attribute on accordion sections
    - CSS running()/element() per-page disclaimer — consistent with assessment_report.html pattern
key-files:
  created:
    - app/templates/documents/pdf/form_7a.html
    - app/templates/documents/pdf/form_9a.html
    - app/templates/guide/index.html
  modified:
    - app/services/document_service.py
    - app/templates/documents/review.html
    - app/main/routes.py
    - app/ontario_constants.py
decisions:
  - "Form 7A and 9A use table-based CSS layout exclusively — no Flexbox or Grid for WeasyPrint compatibility"
  - "Narrative stitching falls back to facts_description if no guided answers provided — backwards compatible with Demand Letter flow"
  - "monetary_limit_formatted passed as pre-formatted string from route — avoids need for custom Jinja2 filter"
  - "Guide accordion search filters on data-keywords attribute + section title — heading-filter approach per RESEARCH.md"
  - "GUIDE_STAGES constant in ontario_constants.py — all stage metadata in single source of truth"
metrics:
  duration: "12 minutes"
  completed: "2026-04-06"
---

# Phase 3 Plan 02: Form 7A, Form 9A, and Process Guide Summary

**One-liner:** Table-based WeasyPrint PDF templates for Form 7A/9A with guided narrative stitching and an 8-stage accordion process guide with Alpine.js search at /guide.

## What Was Built

### Task 1: Form 7A and Form 9A PDF Templates + Review Page Updates

**Form 7A (Plaintiff's Claim):**
- Standalone HTML template (no base.html inheritance) rendered by WeasyPrint
- Letter-size, 15mm margins with 25mm bottom for running footer disclaimer
- Table-based CSS grid — no Flexbox or Grid (WeasyPrint reliability)
- All sections: Ontario header with form identifier, plaintiff section, defendant section, narrative area (min-height: 200mm, allows pagination), monetary claim table, signature block, notice box
- Bilingual field labels (English/French) matching the August 1, 2022 official form
- Per-page disclaimer via CSS `running(page-disclaimer)` / `element()` pattern

**Form 9A (Defence):**
- Same structural approach as Form 7A
- Response-to-claim section with three checkboxes (dispute / admit with payment terms / admit-part) — only the selected option shows a checkmark
- Defendant as the "sender" (user), plaintiff pre-populated from opposing party data

**document_service.py updates:**
- Removed `NotImplementedError` stubs for FORM_7A and FORM_9A
- Added `_build_form_7a_context()` and `_build_form_9a_context()` context builders
- Added `_stitch_guided_narrative_7a()` — assembles 4 sub-question answers (what/when/damages/resolution) into paragraphs
- Added `_stitch_guided_narrative_9a()` — assembles 3 sub-question answers (response/facts/counterclaim) into paragraphs
- Both stitchers fall back to `facts_description` if no guided answers are present (backwards compatible)
- Narrative mode `freeform` bypasses stitching and uses raw `narrative_freeform` text

**review.html updates:**
- Guided narrative prompts section for FORM_7A (4 prompts) and FORM_9A (3 prompts) — hidden for demand_letter
- Alpine.js `narrativeMode` toggle between guided and freeform
- Defence response section for FORM_9A: radio buttons for dispute/admit/admit-part with Alpine.js conditional fields
- Claim amount + interest rate + claim number fields for FORM_7A
- Plaintiff info section for FORM_9A (person who sued you)
- facts_description textarea hidden for court forms (handled by guided narrative system)

### Task 2: Process Guide at /guide

**Guide route:**
- `GET /guide` in `app/main/routes.py` — no `@login_required` (public information)
- Passes all fee amounts from `ontario_constants` (no hardcoded values in template)
- Passes `monetary_limit_formatted` as `"$50,000"` string

**ontario_constants.py:**
- Added `GUIDE_STAGES` list of 8 dicts with id/title/icon for all lifecycle stages

**guide/index.html:**
- 8 accordion sections covering the full Small Claims Court lifecycle
- Stage 1: Before You File — eligibility, do you have a case, limitation period, evidence, costs, alternatives, checklist
- Stage 2: Filing the Claim — court location, Form 7A, filing methods, fees
- Stage 3: Serving the Defendant — what is service, methods, who can serve, timing, Affidavit of Service
- Stage 4: Defendant's Response — 20-day deadline, options (dispute/admit/do nothing), default judgment
- Stage 5: Settlement Conference — what it is, when, who attends, what happens, outcomes, plus full **Settlement Conference Preparation Sub-Guide** (what to expect, what to bring checklist, how to present, dos/don'ts table, after the conference)
- Stage 6: Trial Management Conference — June 2025 Rule 16.1.01 change noted, purpose, what to bring
- Stage 7: Trial — proceedings order, evidence, witnesses, judgment, costs, appeal (30 days to Divisional Court)
- Stage 8: After Judgment / Enforcement — garnishment, writ of seizure, writ of delivery, examination of debtor, 6-year enforcement window
- "Where am I?" navigator: 8 clickable pill buttons, active highlighting, "What's next" teaser
- Alpine.js heading-filter search with `data-keywords` attribute on each section
- `guideApp()` Alpine.js component handles: stage navigation, smooth scroll, accordion open-on-navigate, keyword filtering, visible section count

## Decisions Made

| Decision | Rationale |
|----------|-----------|
| Table-based CSS for PDF templates | WeasyPrint renders `<table>` reliably; Flexbox/Grid produce layout artifacts in some WeasyPrint versions |
| Guided narrative falls back to facts_description | Ensures demand letters and assessments pre-populated before guided fields exist still render correctly |
| monetary_limit_formatted as string from route | Avoids adding a custom Jinja2 filter; keeps formatting logic in Python where it belongs |
| data-keywords on accordion sections | Simpler and faster than full-text search; heading-filter approach recommended in RESEARCH.md |
| GUIDE_STAGES in ontario_constants.py | Consistent with "single source of truth" for all court data |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Added monetary_limit_formatted context variable**

- **Found during:** Task 2, guide template uses Jinja2 filter `format_number` which did not exist
- **Issue:** `{{ monetary_limit | int | format_number }}` would fail at render time — no `format_number` filter registered
- **Fix:** Changed template to use `{{ monetary_limit_formatted }}` and passed pre-formatted `"$50,000"` string from route
- **Files modified:** app/templates/guide/index.html, app/main/routes.py
- **Commit:** 08ae3ae

## Authentication Gates

None — all work was local template and Python file creation.

## Next Phase Readiness

Phase 3 is now complete. All three document types (Demand Letter, Form 7A, Form 9A) produce PDFs via WeasyPrint. The process guide covers the full lifecycle at /guide.

Phase 4 (Polish) can proceed. Items to address in Phase 4:
- WCAG/AODA audit (identified as pre-launch blocker)
- Navigation links to /guide from main navigation and relevant pages
- Mobile responsiveness review
- Error page polish (404, 500)
- Link from guide Stage 2 and 3 sections into document generation flow (already linked, verify UX)
