# Phase 3: Documents and Guide - Research

**Researched:** 2026-04-05
**Domain:** PDF document generation (WeasyPrint/Jinja2), court form replication, Flask document versioning, Alpine.js accordion/search
**Confidence:** HIGH for stack and WeasyPrint patterns; MEDIUM for form field inventory (sourced from official descriptions + instructional sites, not pixel-by-pixel PDF inspection); HIGH for Ontario process/TMC content

---

## Summary

Phase 3 builds on the WeasyPrint + Jinja2 + Flask pattern already established in Phase 2. The existing `pdf_service.py` and standalone PDF template approach is the correct foundation — extend it, don't redesign it. Three document types (Demand Letter, Form 7A, Form 9A) require three new Jinja2 templates rendered via WeasyPrint. The court forms must be pixel-perfect against the August 1, 2022 Ontario forms — the right approach is HTML tables with `border-collapse` and fixed pt/mm dimensions, not CSS Grid or Flexbox (both have WeasyPrint limitations). Document versioning should use a new `DocumentVersion` model in Postgres (metadata + regeneration timestamp), with PDFs generated on-the-fly from stored input data rather than storing binary blobs — this aligns with the app's existing pattern and avoids binary storage complexity.

The Ontario process guide is a standard Alpine.js accordion with a simple `x-show` filter on section headings — no full-text search plugin needed. The TMC reform (June 2025, Rule 16.1.01) is a real addition that must appear in the guide as a discrete step after the settlement conference. The Trial Management Conference is now a mandatory post-settlement-conference checkpoint before trial.

The additional fields not in the assessment (address for service, representative info) should be collected on an inline review/supplement page that pre-populates from `claim.step_data` and adds a short extra-fields form before generation — one page, not a multi-step wizard. This keeps the flow: assessment → review + supplement → preview → download.

**Primary recommendation:** Extend the existing WeasyPrint/Jinja2 pipeline. Add a `Document` model (metadata, version chain) with on-the-fly PDF generation. Use HTML tables for form replication. Guide = Alpine.js accordion with heading-text filter.

---

## Standard Stack

### Core (already in requirements.txt — no new installs needed)

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| weasyprint | >=68.0,<69 | HTML→PDF rendering | Already used in Phase 2; supports CSS Paged Media, running elements, tables |
| flask-weasyprint | >=1.2.0,<2 | Flask integration for WeasyPrint | Already used; provides `HTML` wrapper with Flask context |
| Jinja2 | (via Flask) | Template rendering | Already standard; standalone templates established in Phase 2 |
| Alpine.js | (CDN, via base.html or local) | Accordion + search filter for guide | Already used in Phase 2 wizard |
| HTMX | (CDN, via base.html) | Preview + download interactions | Already used throughout app |

### Supporting (no new installs needed)

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| SQLAlchemy / flask-sqlalchemy | (existing) | Document + version models | New `Document` and `DocumentVersion` tables |
| flask-migrate / Alembic | (existing) | DB migrations for new models | Adding new tables |
| python-dateutil | (existing) | Date formatting in templates | Already available |

### New Dependency Needed

**None.** The full stack is already installed. No new pip packages required.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| WeasyPrint tables for form layout | CSS Grid | Grid has known WeasyPrint limitations (no subgrid, no auto-fill); tables are safer for fixed-layout forms |
| On-the-fly PDF generation | Store PDF bytes in DB/GCS | Stored blobs require binary storage, migrations, versioned blobs; on-the-fly is simpler and re-generates from structured data always |
| Alpine.js heading filter | Full-text search plugin (Fuse.js) | Fuse.js adds a dependency; heading-title filter is sufficient for a ~10-section guide and keeps the stack pure |

---

## Architecture Patterns

### Recommended Project Structure

```
app/
├── documents/                    # New blueprint
│   ├── __init__.py               # Blueprint definition
│   └── routes.py                 # Document CRUD, preview, download, version history
├── models/
│   ├── document.py               # Document + DocumentVersion models (NEW)
│   └── __init__.py               # Add Document import
├── services/
│   └── document_service.py       # Render logic per doc type (NEW)
├── ontario_constants.py          # Add FORM_7A_VERSION, FORM_9A_VERSION constants
└── templates/
    ├── documents/                # New template folder
    │   ├── index.html            # Document selection / list page
    │   ├── review.html           # Pre-populate + supplement fields (HTMX)
    │   ├── preview.html          # HTML preview before PDF download
    │   └── versions.html         # Version history list
    └── documents/pdf/            # Standalone PDF templates (no extends base.html)
        ├── demand_letter.html
        ├── form_7a.html
        └── form_9a.html
    └── guide/
        └── index.html            # Process guide accordion page
```

### Pattern 1: Standalone PDF Templates (Established in Phase 2)

**What:** Templates that do NOT extend `base.html`. No nav, no footer chrome. System fonts only. Per-page disclaimer via CSS `running()` / `element()`.

**When to use:** All three document PDF templates.

**Key CSS for court forms:**
```css
/* Source: Phase 2 pdf_service.py pattern + WeasyPrint docs */
@page {
  size: Letter;
  margin: 1.5cm 1.5cm 3cm 1.5cm;  /* court forms use tight margins */
  @bottom-center {
    content: element(page-disclaimer);
    font-size: 7pt;
    color: #555;
  }
}

/* Use tables, not flexbox/grid, for form field boxes */
table.form-grid {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}
table.form-grid td {
  border: 1pt solid #000;
  padding: 3pt 4pt;
  vertical-align: top;
  font-size: 9pt;
}

/* Label + value cell pattern for form fields */
.field-label {
  font-size: 7pt;
  font-weight: bold;
  text-transform: uppercase;
  color: #333;
  display: block;
  margin-bottom: 2pt;
}
.field-value {
  font-size: 9.5pt;
  min-height: 14pt;
}
```

**Critical:** WeasyPrint does NOT render `<input>` or `<textarea>` elements visually by default. All form "fields" in the PDF must be rendered as `<div>` or `<td>` elements containing the data value (or a blank underline). For the HTML preview (not the PDF), normal inputs can be shown.

### Pattern 2: Document + DocumentVersion Data Model

**What:** Two new models — `Document` (master record with type, linked claim, current version pointer) and `DocumentVersion` (immutable snapshot of input data + metadata for each generation).

**Why:** The CONTEXT.md decision is "regeneration keeps versions — each generation saved as a new version." Input data is stored as JSON, PDF is re-generated on-the-fly from that data. No binary blob storage.

```python
# Source: Established SQLAlchemy 2.0 pattern from existing app
class Document(db.Model):
    __tablename__ = "documents"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    claim_id: Mapped[Optional[int]] = mapped_column(ForeignKey("claims.id"), nullable=True)
    doc_type: Mapped[str] = mapped_column(String(50))  # "demand_letter", "form_7a", "form_9a"
    form_version: Mapped[str] = mapped_column(String(20))  # e.g. "2022-08-01"
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), ...)
    versions: Mapped[list["DocumentVersion"]] = relationship("DocumentVersion", back_populates="document", order_by="DocumentVersion.created_at")

class DocumentVersion(db.Model):
    __tablename__ = "document_versions"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_id: Mapped[int] = mapped_column(ForeignKey("documents.id", ondelete="CASCADE"))
    version_number: Mapped[int] = mapped_column()  # 1, 2, 3...
    input_data: Mapped[dict] = mapped_column(_JSONB_OR_JSON)  # All field values
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), ...)
    document: Mapped["Document"] = relationship("Document", back_populates="versions")
```

**PDF generation:** `document_service.py` takes a `DocumentVersion` and renders its `input_data` through the appropriate Jinja2 template via WeasyPrint. No PDF bytes stored in DB.

### Pattern 3: Preview → Download Flow (HTMX)

**What:** Two-step user flow. Step 1: server renders HTML preview (same template logic, different CSS — no @page rules). Step 2: user clicks "Download PDF" → HTMX request → server re-renders with PDF CSS → WeasyPrint → bytes → `application/pdf` response.

```python
# Preview route — returns HTML fragment for HTMX swap
@documents_bp.route("/preview/<int:version_id>")
@login_required
def preview(version_id):
    version = _get_version_or_404(version_id)
    html = render_template(f"documents/{version.document.doc_type}_preview.html",
                           **version.input_data)
    return html  # HTMX swaps into preview container

# Download route — returns PDF bytes
@documents_bp.route("/download/<int:version_id>.pdf")
@login_required
def download_pdf(version_id):
    version = _get_version_or_404(version_id)
    pdf_bytes = document_service.render_pdf(version)
    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f"attachment; filename={version.document.doc_type}_{version_id}.pdf"
    return response
```

**Note on HTMX + PDF download:** HTMX cannot trigger a binary file download. The download link must be a plain `<a href="...">` tag (not hx-get), pointing to the PDF route. This is the established pattern — confirmed in the existing Phase 2 PDF download route.

### Pattern 4: Supplemental Fields Collection (Inline Review Page)

**What:** A single review + supplement page, not a multi-step wizard. Pre-populate all fields from `claim.step_data`. Show a compact form for additional fields not in assessment (address for service, representative info, interest rate). User reviews, edits, submits → generates Document + DocumentVersion.

**Rationale for Claude's Discretion choice:** The wizard already collected the substance. Adding a second wizard is over-engineering. An inline review page is: (a) faster to build, (b) less disorienting for users who just finished an assessment, (c) consistent with how legal forms actually work — you review a pre-filled draft.

**Implementation:** Standard Flask form POST. Pre-populate with `{{ claim.step_data.get('...', '') }}`. Additional fields as labeled `<input>` elements. On submit, create `Document` + `DocumentVersion`, redirect to preview.

### Pattern 5: Alpine.js Searchable Accordion (Process Guide)

**What:** Sections stored as Jinja2 blocks or a data structure. Alpine.js `x-data` holds `search` string. Each section has a `data-title` attribute. `x-show` on each section evaluates `search === '' || $el.dataset.title.toLowerCase().includes(search.toLowerCase())`.

```html
<!-- Source: Alpine.js docs + Context7 /alpinejs/alpine search filter pattern -->
<div x-data="{ search: '', openSection: null }">
  <input x-model="search" type="search" placeholder="Search guide...">

  <template x-for="section in sections" :key="section.id">
    <div x-show="search === '' || section.title.toLowerCase().includes(search.toLowerCase())">
      <button @click="openSection = openSection === section.id ? null : section.id"
              :aria-expanded="openSection === section.id">
        <span x-text="section.title"></span>
      </button>
      <div x-show="openSection === section.id || search !== ''" x-collapse>
        <!-- content -->
      </div>
    </div>
  </template>
</div>
```

**Recommendation for Claude's Discretion:** Use **heading filter** (title text match), not full-text search. Full-text would require scanning inner HTML content, which is complex and error-prone. Heading filter gives 90% of the utility. When search is active, auto-expand all matching sections (`search !== ''` in the x-show on the collapsible content).

**x-collapse plugin:** Required for smooth animation. Already available via CDN (Alpine.js collapse plugin). Check if it's already loaded in base.html or needs adding.

### Pattern 6: Version-Aware Form Constants

```python
# ontario_constants.py additions
FORM_7A_VERSION = "2022-08-01"   # August 1, 2022 — pin this
FORM_9A_VERSION = "2022-08-01"   # August 1, 2022
FORM_7A_EFFECTIVE = "2023-01-30" # "Effective from" date
FORM_9A_EFFECTIVE = "2023-01-30"
```

Store `form_version` on the `Document` model. When generating PDF, stamp the version in the footer. If forms change, update constant + template together — one config flag controls both.

### Anti-Patterns to Avoid

- **Using CSS Flexbox/Grid for court form boxes:** WeasyPrint's flex support is "not deeply tested" and Grid has known subgrid/auto limitations. Use `<table>` with `border-collapse: collapse` instead.
- **Storing PDF bytes in the database:** Binary blobs make migrations painful, inflate DB size, and break the versioning model. Store `input_data` as JSONB; regenerate on-the-fly.
- **Using `<input>` elements in PDF templates:** WeasyPrint does not render form inputs. Use styled `<div>` or `<td>` blocks with data values instead.
- **Inheriting from base.html in PDF templates:** Established pattern from Phase 2: standalone templates only. Nav, flash messages, footer chrome don't belong in court documents.
- **Hardcoding form version strings:** Already decided — use ontario_constants.py named constants.
- **Full-text search for guide:** Scanning inner HTML content is brittle. Heading filter is sufficient.
- **New wizard for supplemental fields:** One review/supplement page is enough. Don't spawn a second wizard.

---

## Form Field Inventories

### Form 7A — Plaintiff's Claim (August 1, 2022)

**Source: Ontario Court Services / RunSensible / official form description (MEDIUM confidence — derived from instructional sources, not direct PDF parsing)**

```
HEADER: "Ontario" / "Superior Court of Justice" / "Small Claims Court"
         Claim No. [blank — clerk fills] | Court address | Phone

PLAINTIFF SECTION:
  [ ] Additional plaintiffs (Form 1A attached)
  [ ] Plaintiff is under 18 years of age
  Last name or company name | First name | Second name
  Also known as
  Street address | City/Town | Province | Postal code
  Phone | Email
  Representative (if any):
    Last name | First name | Law Society of Ontario #
    Address | City | Province | Postal code | Phone | Email

DEFENDANT SECTION (mirrors Plaintiff):
  [ ] Additional defendants (Form 1A attached)
  [ ] Defendant is under 18 years of age
  Last name or company name | First name | Second name
  Also known as
  Street address | City/Town | Province | Postal code
  Phone | Email
  Representative (if any): [same sub-fields as plaintiff rep]

CLAIM DETAILS SECTION:
  "Reasons for Claim and Details"
  Narrative text area (large): explain what happened, where, when;
    explain amount claimed or goods to be returned;
    note attached documents; note if documents unavailable

MONETARY CLAIM:
  Principal amount: $________
  Pre-judgment interest from: [date] under [ ] Courts of Justice Act
    [ ] Agreement at ___% per year
  Post-judgment interest and court costs also claimed
  [ ] Additional pages attached (if narrative overflows)

SIGNATURE BLOCK:
  Prepared on: [date]
  Plaintiff/representative signature
  --------------------------------
  Issued on: [date — clerk fills]
  Clerk of the court / Deputy Judge
```

### Form 9A — Defence (August 1, 2022)

**Source: Ontario Court Services / RunSensible / official form description (MEDIUM confidence)**

```
HEADER: Same as 7A header structure
  Claim No. [same as 7A] | Court address | Phone

PLAINTIFF SECTION (read-only — copied from claim):
  Same fields as 7A plaintiff section
  [ ] Additional plaintiffs, [ ] Under 18

DEFENDANT SECTION (defendant filing the defence):
  Same fields as 7A defendant section
  [ ] Additional defendants, [ ] Under 18

RESPONSE TO CLAIM:
  The defendant [name(s)] states:
  [ ] I dispute the claim
  [ ] I admit the full claim and propose to pay:
        $______ on [date] / by [weekly/monthly] payments of $______ starting [date]
  [ ] I admit part of the claim: $______
        and propose to pay: $______ on [date] / by payments of $______ starting [date]

DEFENCE DETAILS SECTION:
  "Reasons for Disputing the Claim"
  Narrative text area (large): explain what happened, where, when;
    explain why you disagree with claim; attach supporting documents
  [ ] Additional pages attached

SIGNATURE BLOCK:
  Date | Defendant/representative signature
  Note: if address for service changes, notify court within 7 days
```

### Demand Letter

**No official form — custom template. Standard Ontario demand letter structure:**

```
[Letterhead: Bryan and Bryan / Date / Reference number]

To: [Defendant name and address]

Re: Demand for Payment — [Brief claim description]

Dear [Defendant name],

[Opening: relationship, transaction, what happened]
[Amount owed breakdown: principal, interest if applicable]
[Deadline: pay within [14/30] days of this letter]
[Consequences: will commence Small Claims Court proceedings without further notice]
[Contact information for response]

Yours truly,
[Plaintiff name]
[Address for service]
[Date]

[Disclaimer footer on every page]
```

---

## Ontario Small Claims Court Process (Guide Content)

**Source: Ontario.ca official guides, ontariocourts.ca, Steps to Justice, Merovitz Potechin (MEDIUM-HIGH confidence)**

Full lifecycle for guide sections:

### Stage 1: Before You File
- Confirm jurisdiction: amount ≤ $50,000 (as of Oct 2025), proper claim type
- Send demand letter (strongly recommended, often required by settlement conference judge)
- Gather evidence: contracts, receipts, photos, correspondence
- Name defendants correctly (individual full given name; company legal name)
- Identify correct court office (where defendant lives/does business, or where cause arose)

### Stage 2: Filing the Claim
- Complete Form 7A (Plaintiff's Claim)
- Pay filing fee: $108 (infrequent claimant, claims ≤ $25,000); $249 (frequent claimant, 10+/year)
- Can file online (Small Claims Court Submissions Online portal; Toronto region: Ontario Courts Public Portal as of Oct 14, 2025), by mail, or in person
- Court issues claim, assigns Claim No.

### Stage 3: Serving the Defendant
- Serve Plaintiff's Claim on each defendant within **6 months** of issuance
- Personal service or alternatives (mail, courier, leaving with adult at address)
- File Affidavit of Service (Form 8A) or Lawyer/Paralegal's Certificate (Form 8B) with court

### Stage 4: Defendant's Response
- Defendant has **20 days** after service to file Defence (Form 9A) with proof of service
- If no defence filed: plaintiff may note defendant in default → seek Default Judgment (Form 11B)
- Defendant may also file a Defendant's Claim (Form 10A) within 20 days of filing defence

### Stage 5: Settlement Conference (Mandatory)
- Automatically scheduled for every defended action (within ~90 days of first defence)
- **At least 14 days before:** serve and file Form 13A (List of Proposed Witnesses) + key documents
- Informal, confidential meeting with judicial officer (often by Zoom/telephone)
- Judicial officer may offer opinion on likely outcome; can impose costs for non-attendance/inadequate prep
- If settled: record in Form 14D (Terms of Settlement) or court endorsement
- If not settled: action set for trial (file Request to Clerk + pay $145 trial fee)

### Stage 6: Trial Management Conference (NEW — June 2025, Rule 16.1.01)
- Court may schedule TMC after action is set for trial
- Purpose: confirm trial readiness, narrow issues, schedule trial date
- **Different from settlement conference:** TMC is procedural (are you ready?), not substantive (will you settle?)
- Attendance mandatory unless court orders otherwise
- Stricter adjournment rules apply at this stage (Rule 17.02 — compensation may be ordered for wasted trial prep)

### Stage 7: Trial
- Each party presents evidence and witnesses
- Judge makes decision (judgment or dismissal)
- Costs may be awarded (up to 15% of claim for representation costs; higher if conduct warrants)
- Self-represented litigants: up to $1,500 compensation for inconvenience (increased under June 2025 reforms)
- 2-year automatic dismissal if no steps taken

### Stage 8: After Judgment / Enforcement
- **Voluntary payment:** contact debtor directly first
- **Examination of Debtor:** Notice of Examination (Form 20H) + Financial Information Form (Form 20I) — learn debtor's assets/income
- **Garnishment:** wages, bank accounts (Form 20E Notice of Garnishment; restrictions apply — EI, social assistance, pension exempt)
- **Writ of Seizure and Sale of Personal Property:** sheriff seizes and sells goods (Form 20C)
- **Writ of Seizure and Sale of Land:** registers on title as lien (Forms 20D/20N; complex, rarely proceeds to auction)
- **Writ of Delivery:** return of specific property (Form 20B)
- Writs expire; renewal possible before expiry
- Creditor's responsibility to notify court when paid in full

### Settlement Conference Prep Sub-Guide (GUID-02)
- Complete Form 13A and serve 14+ days before
- Organize evidence into logical binder: contracts, invoices, correspondence, photos
- Prepare brief written summary (1-2 pages): facts, position, what you'll accept to settle
- Know your bottom line before arriving
- Bring certified cheque or ability to pay if settlement is reached
- Be prepared to summarize what witnesses would say (don't bring witnesses)
- Approach: be realistic, not emotional; judicial officer's opinion is informed and worth heeding

---

## Filing Fee Schedule (for /fees page and DOCS-04)

All fees already in `ontario_constants.py` — cite them from named constants:

| Fee | Constant | Amount | Applies To |
|-----|----------|--------|------------|
| Claim filing (infrequent) | `FILING_FEE_INFREQUENT_CLAIMANT` | $108 | Claimants filing < 10/year; claims ≤ $25,000 |
| Claim filing (frequent) | `FILING_FEE_FREQUENT_CLAIMANT` | $249 | 10+ claims/year regardless of amount |
| Defence filing | `DEFENCE_FILING_FEE` | $77 | All defendants |
| Motion (infrequent) | `MOTION_FEE_INFREQUENT` | $89 | |
| Motion (frequent) | `MOTION_FEE_FREQUENT` | $189 | |
| Certificate of Judgment | `CERTIFICATE_OF_JUDGMENT_FEE` | $22 | After judgment |
| Writ of Delivery | `WRIT_OF_DELIVERY_FEE` | $55 | Enforcement |
| Writ of Seizure | `WRIT_OF_SEIZURE_FEE` | $55 | Enforcement |

**Source citation for /fees page:** O. Reg. 432/93, Table (Small Claims Court — Fees). URL: `https://www.ontario.ca/laws/regulation/930432`

**Note on infrequent claimant threshold:** The $25,000 threshold (`INFREQUENT_CLAIMANT_LIMIT`) determines which filing fee applies. Claims above $25,000 but within $50,000 jurisdiction may face different fee schedule — verify in constants. The fee page should explain the infrequent vs frequent claimant distinction clearly.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| PDF generation | Custom PDF library | WeasyPrint (already installed) | CSS-native, handles paged media, running elements |
| Form input rendering in PDF | `<input>` elements | Styled `<div>`/`<td>` blocks | WeasyPrint doesn't render inputs natively |
| Document versioning | Custom diff/delta logic | Simple `version_number` incrementing + JSONB `input_data` snapshots | No need for diffs — store full input per version |
| Accordion UI | Custom JS toggle | Alpine.js x-show + x-collapse (already loaded) | Already in stack, minimal code |
| Full-text guide search | Fuse.js or similar | Alpine.js heading filter (title text only) | Sufficient for ~10 sections, no extra dependency |
| Demand letter content | AI generation | Jinja2 template with structured variables | Regulatory requirement — no AI in documents |
| Binary PDF storage | File system or GCS blobs | On-the-fly generation from JSONB | Simpler, no binary storage, consistent with Phase 2 pattern |

---

## Common Pitfalls

### Pitfall 1: WeasyPrint Can't Render HTML Form Inputs
**What goes wrong:** Developer uses `<input type="text" value="{{ field }}">` in PDF template. WeasyPrint renders a blank box or nothing at all.
**Why it happens:** WeasyPrint doesn't implement browser-style form widget rendering.
**How to avoid:** PDF templates use `<td>{{ field or '&nbsp;' }}</td>` or `<div class="field-value">{{ field }}</div>`. For checkboxes, use Unicode characters: `✓` (U+2713) or `☐` (U+2610) in `<span>` elements.
**Warning signs:** Any `<input>`, `<select>`, or `<textarea>` in a PDF template.

### Pitfall 2: CSS Flexbox/Grid Instability in WeasyPrint
**What goes wrong:** Court form layout breaks — cells misalign, overflow, or disappear.
**Why it happens:** WeasyPrint's flex is "not deeply tested"; Grid has no subgrid, no auto-fill.
**How to avoid:** Use `<table border-collapse: collapse>` for all form grid layouts. Pt-based widths and heights.
**Warning signs:** `display: flex` or `display: grid` in PDF-only CSS.

### Pitfall 3: HTMX Can't Trigger Binary Downloads
**What goes wrong:** Developer uses `hx-get="/download/1.pdf"` and gets a broken HTMX swap instead of a file download.
**Why it happens:** HTMX swaps response content into the DOM; it can't trigger browser file download dialog for binary responses.
**How to avoid:** Download link is a plain `<a href="/documents/download/1.pdf" target="_blank">` tag, NOT an HTMX request. This is consistent with the Phase 2 PDF download pattern.
**Warning signs:** `hx-get` on any PDF download endpoint.

### Pitfall 4: Form Version Mismatch Between Template and Stored Data
**What goes wrong:** The form template is updated but old DocumentVersion records render incorrectly.
**Why it happens:** Templates are re-rendered from stored `input_data`, but templates change.
**How to avoid:** Store `form_version` on `Document`. In the future, when forms change: create a new template version and version-guard the renderer. For now (pinned to 2022-08-01), this is forward-protection.

### Pitfall 5: Narrative Overflow in Court Forms
**What goes wrong:** Long "Reasons for Claim" text overflows the form box and bleeds outside the border.
**Why it happens:** Court form boxes have fixed visual dimensions; PDF doesn't know text is long until render time.
**How to avoid:** Use `min-height` not `height` on narrative cells (allows expansion). Use `break-inside: avoid` where appropriate. Consider CSS `overflow: auto` in WeasyPrint (supported). For the requirement "auto-pagination for overflow narratives" (Claude's Discretion): add a continuation page logic in the Jinja2 template — if narrative > X chars, render an overflow continuation page with same header/form number. Keep it simple: a conditional block `{% if narrative|length > 800 %}...{% endif %}`.

### Pitfall 6: Alpine.js x-collapse Not Loaded
**What goes wrong:** Accordion content collapses instantly without animation; or worse, stays visible.
**Why it happens:** Alpine collapse is a separate plugin (`@alpinejs/collapse`) that must be loaded before Alpine initializes.
**How to avoid:** Check if `x-collapse` is already in `base.html`. If not, add `<script defer src="...collapse..."></script>` before the main Alpine script. Order matters: plugins before core.

### Pitfall 7: Address for Service vs Mailing Address Confusion
**What goes wrong:** The form's "address for service" is pre-populated with the user's account address, but the legal concept is where they can be served (may differ from home address).
**Why it happens:** Assessment only collected claim facts, not legal procedural details.
**How to avoid:** On the review/supplement page, label the field clearly: "Address for Service (where legal documents can be delivered to you)" with a brief plain-language note. Pre-populate from assessment data as a starting point but allow edit.

---

## Code Examples

### Standalone PDF Template Structure (from Phase 2 — verified working)

```html
<!-- Source: app/templates/assessment/pdf/assessment_report.html -->
<!DOCTYPE html>
<html lang="en">
<head>
  <style>
    @page {
      size: Letter;
      margin: 2.5cm 2cm 3.5cm 2cm;
      @bottom-center {
        content: element(page-disclaimer);
        font-size: 8pt;
      }
    }
    #page-disclaimer { position: running(page-disclaimer); font-size: 8pt; font-style: italic; }
    body { font-family: Georgia, "Times New Roman", Times, serif; font-size: 10pt; }
  </style>
</head>
<body>
  <div id="page-disclaimer">Legal Information, Not Legal Advice — Bryan and Bryan — {{ date }}</div>
  <!-- form content -->
</body>
</html>
```

### Form Cell Pattern for Court Forms (Table-Based)

```html
<!-- Use this pattern for Form 7A/9A field boxes -->
<table class="form-grid">
  <tr>
    <td style="width: 50%;">
      <span class="field-label">Last name or company name</span>
      <div class="field-value">{{ plaintiff_last_name or '' }}</div>
    </td>
    <td style="width: 25%;">
      <span class="field-label">First name</span>
      <div class="field-value">{{ plaintiff_first_name or '' }}</div>
    </td>
    <td style="width: 25%;">
      <span class="field-label">Second name</span>
      <div class="field-value">{{ plaintiff_second_name or '' }}</div>
    </td>
  </tr>
</table>
```

### Checkbox Rendering Without `<input>` (WeasyPrint-safe)

```html
<!-- Source: WeasyPrint workaround — use Unicode, not <input> -->
<span class="checkbox">
  {% if condition %}&#x2713;{% else %}&#x25A1;{% endif %}
</span> Label text
```

### Alpine.js Searchable Accordion Pattern

```html
<!-- Source: Context7 /alpinejs/alpine + project conventions -->
<div x-data="{ search: '', open: null }">
  <input x-model="search" type="search" placeholder="Search guide sections...">

  <div class="guide-sections">
    {% for section in sections %}
    <div x-show="search === '' || '{{ section.title }}'.toLowerCase().includes(search.toLowerCase())"
         class="guide-section">
      <button @click="open = open === '{{ section.id }}' ? null : '{{ section.id }}'"
              :aria-expanded="open === '{{ section.id }}'">
        {{ section.title }}
      </button>
      <div x-show="open === '{{ section.id }}' || search !== ''" x-collapse>
        {{ section.content | safe }}
      </div>
    </div>
    {% endfor %}
  </div>
</div>
```

### Document Service Render Function

```python
# Source: Pattern from app/services/pdf_service.py — extended for multiple doc types
from flask import render_template
from flask_weasyprint import HTML as WeasyHTML

DOC_TEMPLATES = {
    "demand_letter": "documents/pdf/demand_letter.html",
    "form_7a": "documents/pdf/form_7a.html",
    "form_9a": "documents/pdf/form_9a.html",
}

def render_document_pdf(version: "DocumentVersion") -> bytes:
    template = DOC_TEMPLATES[version.document.doc_type]
    html_string = render_template(template, **version.input_data,
                                  form_version=version.document.form_version)
    return WeasyHTML(string=html_string).write_pdf()
```

---

## TMC Reform — Implementation Note for Guide

The Trial Management Conference is a **real, confirmed addition** (Rule 16.1.01, effective June 1, 2025). It is NOT a replacement for the settlement conference — it is a new mandatory step that occurs **after the settlement conference, when an action is set for trial**.

**Presentation recommendation (Claude's Discretion):** Present TMC as a discrete numbered stage in the guide (Stage 6 in the lifecycle above). No need to "flag as recent change" with warning banners — just describe it accurately as part of the current process. A brief parenthetical "(Rule 16.1.01, in effect June 2025)" is sufficient to anchor users who've read older guides.

The June 2025 reforms also introduced:
- Stricter adjournment rules with compensation for wasted trial prep (Rule 17.02)
- Increased self-represented litigant inconvenience compensation (up to $1,500)
- Formal recognition of hybrid/remote hearings

---

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Settlement conference only before trial | Settlement conference + TMC | June 1, 2025 | Guide must include TMC as discrete stage |
| $35,000 claim limit | $50,000 claim limit | October 1, 2025 | Constants already updated; guide must reflect |
| Toronto online filings via SCCO portal | Toronto region: Ontario Courts Public Portal | October 14, 2025 | Mention in filing stage of guide |
| 5-step SCC lifecycle in older guides | 8-step lifecycle including TMC and enforcement detail | 2025 | Guide is the current authoritative resource |
| WeasyPrint no PDF forms | WeasyPrint supports PDF form inputs via `--pdf-forms` / `appearance: auto` | v58+ | Opt-in only — not needed here since we serve our own data, not editable PDFs |

---

## Open Questions

1. **Form 7A exact pixel dimensions and font specifications**
   - What we know: Layout structure confirmed from instructional sources; August 1, 2022 version; uses Helvetica/Arial equivalent
   - What's unclear: Exact font size for form body (appears to be 9-10pt); exact box heights; whether the header uses a specific government font
   - Recommendation: Download the official Word version (`scr-7a-aug22-en-fil.docx`) during implementation and measure. The planner should make one implementation task that explicitly includes inspecting the official form document before writing template CSS.

2. **Alpine.js collapse plugin already loaded?**
   - What we know: Alpine.js is used in the Phase 2 wizard but the base.html snippet shown doesn't include `@alpinejs/collapse`
   - What's unclear: Whether collapse was added to the template during Phase 2 wizard implementation
   - Recommendation: Check `base.html` and the wizard shell template for `x-collapse` usage or CDN link during implementation.

3. **Infrequent claimant fee above $25K**
   - What we know: `INFREQUENT_CLAIMANT_LIMIT = 25_000` and `FILING_FEE_INFREQUENT_CLAIMANT = 108_00` exist. Jurisdiction now extends to $50,000.
   - What's unclear: Is there a different fee schedule for infrequent claimants filing $25,001–$50,000 claims?
   - Recommendation: Verify against O. Reg. 432/93 Table during implementation before displaying fee calculator. The constants may need an additional entry.

4. **"Where am I?" navigator for guide**
   - What we know: CONTEXT.md describes it as "a UX shortcut layered on top of the full guide" — jumps to relevant stage + shows what's next
   - What's unclear: What data drives it (claim stage from DB? user selection?)
   - Recommendation: Simplest approach — a dropdown or button set at the top of the guide page: "I am at stage: [Filing / Service / Defence / Settlement Conf / Trial / Enforcement]". Alpine `@click` scrolls to section and opens it. No DB integration needed.

---

## Sources

### Primary (HIGH confidence)
- `/kozea/weasyprint` (Context7) — CSS support, page model, running elements, tables
- `app/services/pdf_service.py` (existing codebase) — standalone template pattern
- `app/templates/assessment/pdf/assessment_report.html` (existing codebase) — @page CSS, running disclaimer
- `app/ontario_constants.py` (existing codebase) — fee constants, procedural constants
- `https://ontariocourtforms.on.ca/en/rules-of-the-small-claims-court-forms/` — form version dates confirmed

### Secondary (MEDIUM confidence)
- `https://www.runsensible.com/legal-forms/ontario-court-legal-case-plaintiffs-claim-form-7a/` — Form 7A field inventory (instructional, not official form spec)
- `https://www.runsensible.com/legal-forms/ontario-court-legal-case-defence-form-9a/` — Form 9A field inventory
- `https://www.ontariocourts.ca/scj/areas-of-law/small-claims-court/settlement-conference-trial-management-conferences/` — TMC confirmed
- `https://www.pallettvalo.com/whats-trending/notable-reforms-to-ontarios-rules-of-small-claims-court-in-effect-june-2025/` — TMC Rule 16.1.01 detail
- `https://www.ontario.ca/document/guide-procedures-small-claims-court/making-claim` — Process steps
- `https://doc.courtbouillon.org/weasyprint/stable/api_reference.html` — CSS feature support

### Tertiary (LOW confidence — flag for validation)
- WebSearch results re: infrequent claimant fee above $25K — not verified against regulation text
- Form pixel dimensions — not inspected directly; Word document should be reviewed during implementation

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Phase 2 codebase confirms exact versions; no new dependencies
- Architecture patterns: HIGH — established from Phase 2 PDF service + official WeasyPrint docs
- Form field inventories: MEDIUM — official instructional sources, not direct form inspection
- Process guide content: HIGH — verified from Ontario.ca + ontariocourts.ca official sources
- TMC reform: HIGH — confirmed from legal news sites citing Rule 16.1.01
- Pitfalls: HIGH — WeasyPrint limitations confirmed from official docs + GitHub issues

**Research date:** 2026-04-05
**Valid until:** 2026-06-05 (stable stack; court rules change infrequently but verify fee schedule if > 30 days)
