---
phase: 03-documents-and-guide
verified: 2026-04-06T01:27:35Z
status: passed
score: 5/5 must-haves verified
---

# Phase 3: Documents and Guide Verification Report

**Phase Goal:** A user can generate a Demand Letter, Plaintiff's Claim (Form 7A), or Defence (Form 9A) as a court-ready PDF, see the current filing fees, and read through the full plain-language process guide.
**Verified:** 2026-04-06T01:27:35Z
**Status:** passed
**Re-verification:** No - initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | User can generate a Demand Letter PDF from structured inputs, template-based with no AI content | VERIFIED | demand_letter.html (287 lines): Jinja2 template with static prose slots; _build_demand_letter_context() assembles from input_data dict only, no LLM call in the pipeline |
| 2 | User can generate a Form 7A PDF matching the August 1, 2022 Ontario court form | VERIFIED | form_7a.html (396 lines): FORM_7A_VERSION stamped in header as "August 1, 2022"; bilingual EN/FR labels; Ontario header, Plaintiff No. 1, Defendant No. 1, Reasons for Claim, monetary claim table, signature block, notice box; Ont. Reg. No. 258/98 present |
| 3 | User can generate a Form 9A Defence PDF under the same template pipeline | VERIFIED | form_9a.html (363 lines): same WeasyPrint table-based pipeline; three checkbox response options (dispute / admit with payment terms / admit-part) rendered conditionally; _build_form_9a_context() and _stitch_guided_narrative_9a() fully implemented; NotImplementedError stubs removed |
| 4 | Filing fee calculator displays current fees ($108 claim, $77 defence) with Ontario.ca citations, fees read from named constants not hardcoded | VERIFIED | ontario_constants.py: FILING_FEE_INFREQUENT_CLAIMANT = 108_00, DEFENCE_FILING_FEE = 77_00 (cents). fees() route calls format_fee(CONSTANT), zero hardcoded dollar strings. "O. Reg. 432/93, Table" citation per row; ontario.ca link; FEES_LAST_VERIFIED passed through |
| 5 | User can read the full Small Claims Court lifecycle guide via accordion sections, searchable with Alpine.js | VERIFIED | guide/index.html (1025 lines): 8 accordion sections; Alpine.js 3.14.9 CDN; guideApp() implements filterSections() with data-keywords search, goToStage() with smooth scroll and auto-open; Settlement Conference sub-guide present; TMC notes "New as of June 2025: Rule 16.1.01"; /guide route passes all constants |

**Score:** 5/5 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| app/models/document.py | Document + DocumentVersion models | VERIFIED | 113 lines; DocumentType enum (DEMAND_LETTER, FORM_7A, FORM_9A); JSONB-with-SQLite-fallback; UniqueConstraint on version snapshot |
| app/documents/__init__.py | Blueprint definition | VERIFIED | 5 lines; documents_bp = Blueprint("documents", ...) |
| app/documents/routes.py | 9 routes for document pipeline | VERIFIED | 382 lines; all 9 routes present; all authenticated except /fees |
| app/services/document_service.py | PDF render pipeline dispatching all 3 doc types | VERIFIED | 242 lines; render_document_html() dispatches by DocumentType; render_document_pdf() calls WeasyHTML.write_pdf(); no NotImplementedError stubs |
| app/templates/documents/pdf/demand_letter.html | Demand Letter PDF template | VERIFIED | 287 lines; standalone HTML; table-based layout; per-page CSS running disclaimer |
| app/templates/documents/pdf/form_7a.html | Form 7A Plaintiff's Claim PDF template | VERIFIED | 396 lines; court-faithful bilingual layout; form_version from constant; all required sections |
| app/templates/documents/pdf/form_9a.html | Form 9A Defence PDF template | VERIFIED | 363 lines; three conditional checkboxes; bilingual labels; same pipeline |
| app/templates/documents/fees.html | Filing fee page | VERIFIED | 82 lines; renders fee_table from route context; Ontario.ca link; fees_last_verified from constant |
| app/templates/guide/index.html | 8-stage accordion process guide | VERIFIED | 1025 lines; all 8 stages with data-keywords; full guideApp() Alpine.js component; Settlement Conference sub-guide; TMC June 2025 reform |
| app/ontario_constants.py | Named constants for fees and form versions | VERIFIED | 123 lines; FILING_FEE_INFREQUENT_CLAIMANT = 108_00; DEFENCE_FILING_FEE = 77_00; FORM_7A_VERSION = "August 1, 2022"; FORM_9A_VERSION = "August 1, 2022"; GUIDE_STAGES with 8 dicts |
| migrations/versions/3812ca30ab60_...py | Alembic migration for Document + DocumentVersion | VERIFIED | File exists; applied to dev SQLite DB |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| documents_bp | app/__init__.py | app.register_blueprint(documents_bp) | WIRED | Line 46 of __init__.py, no URL prefix |
| fees() route | ontario_constants.py | 8 named constant imports + format_fee() | WIRED | All fee values pass through format_fee(CONSTANT), zero hardcoded strings |
| /guide route | ontario_constants.py | GUIDE_STAGES, SMALL_CLAIMS_MONETARY_LIMIT, 3 fee constants | WIRED | main/routes.py passes all values as template context |
| render_document_html() | form_7a.html / form_9a.html | DocumentType dispatch | WIRED | if document.doc_type == DocumentType.FORM_7A branches to correct template |
| review.html | guided narrative prompts | doc_type.value in ('form_7a', 'form_9a') | WIRED | Section visible only for court forms; Alpine.js narrativeMode toggle |
| form submit | document_service.py | POST to /review merges form data, redirect to preview | WIRED | Preview calls render_document_html(doc) |
| PDF download | WeasyHTML.write_pdf() | render_document_pdf() + make_response() with Content-Disposition: attachment | WIRED | Plain anchor tag (not HTMX) triggers binary download |
| form_7a.html | FORM_7A_VERSION constant | form_version context variable | WIRED | _build_form_7a_context() imports and passes FORM_7A_VERSION |

---

### Requirements Coverage

| Requirement | Status | Notes |
|-------------|--------|-------|
| DOCS-01: Demand Letter PDF generation | SATISFIED | Template pipeline proven end-to-end; structured input only, no AI content |
| DOCS-02: Form 7A Plaintiff's Claim PDF | SATISFIED | August 1, 2022 version stamped; bilingual labels; court-faithful layout |
| DOCS-03: Form 9A Defence PDF | SATISFIED | Same pipeline; three-option response section; guided narrative stitcher |
| DOCS-04: Version history snapshot | SATISFIED | DocumentVersion.input_data_snapshot taken at download time; UniqueConstraint on (document_id, version_number) |
| GUID-01: Filing fee page with source citations | SATISFIED | All fees from named constants; O. Reg. 432/93 citation per row; Ontario.ca link |
| GUID-02: Process guide, full lifecycle | SATISFIED | 8 stages from before filing through enforcement at /guide (public, no login) |
| GUID-03: Process guide, Settlement Conference prep | SATISFIED | Full sub-guide in Stage 5: what to expect, what to bring checklist, dos/don'ts table |
| GUID-04: Process guide, post-June 2025 TMC reform | SATISFIED | Stage 6 explicitly notes "New as of June 2025: Rule 16.1.01" with TMC purpose and consequences |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| guide/index.html | 58 | placeholder="Search topics..." | Info | HTML input placeholder attribute, not a code stub; expected UX pattern |

No blockers or warnings found.

---

### Human Verification Required

#### 1. Form 7A Visual Inspection Against Ontario Courts Public Portal

**Test:** Generate a Form 7A PDF and compare it against the current Form 7A from https://ontariocourts.ca/scr/en/forms/forms-instructions.htm
**Expected:** Field positions, bilingual labels, form identifier (Form/Formule 7A, Ont. Reg. 258/98), and section order match the August 1, 2022 version visually
**Why human:** PDF rendering artifacts (column alignment, page breaks, font substitution) can only be assessed by visual inspection

#### 2. Form 9A Visual Inspection, Three-Checkbox Response

**Test:** Generate a Form 9A PDF with each of the three defence response options (dispute, admit, admit-part) selected in turn
**Expected:** Only the selected option shows a filled checkbox; conditional payment fields render for admit and admit-part
**Why human:** Checkbox symbol rendering in WeasyPrint requires visual confirmation

#### 3. Guide Alpine.js Keyword Search

**Test:** Navigate to /guide, type "garnishment" in the search box
**Expected:** Only Stage 8 (After Judgment / Enforcement) remains visible; all other 7 stages are hidden; clearing the search restores all 8
**Why human:** JavaScript execution and DOM filtering cannot be verified by static code analysis

#### 4. Navigator Accordion Auto-Open

**Test:** Click a stage pill button (e.g. "Settlement Conference")
**Expected:** Page smooth-scrolls to Stage 5, accordion opens automatically if closed, "What's next: Trial Management Conference" appears below the nav
**Why human:** JavaScript DOM interaction and scroll behavior require browser verification

---

## Gaps Summary

No gaps. All five observable truths pass all three verification levels (exists, substantive, wired).

The phase delivers the complete document generation pipeline for all three document types, a filing fee page sourced entirely from named constants with regulatory citations, and a 1,025-line accordion process guide covering all 8 lifecycle stages including the post-June 2025 TMC reform. Human verification is recommended for visual form inspection and JavaScript behavior, but no automated-verifiable gaps exist.

---

_Verified: 2026-04-06T01:27:35Z_
_Verifier: Claude (gsd-verifier)_
