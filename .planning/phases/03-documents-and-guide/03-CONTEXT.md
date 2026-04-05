# Phase 3: Documents and Guide - Context

**Gathered:** 2026-04-05
**Status:** Ready for planning

<domain>
## Phase Boundary

Generate court-ready PDF documents (Demand Letter, Plaintiff's Claim Form 7A, Defence Form 9A) from structured inputs, display current filing fees with Ontario.ca citations, and provide a plain-language Small Claims Court process guide covering filing through enforcement. Document generation is template-based (no AI content). Dashboard and deadline tracking are separate phases.

</domain>

<decisions>
## Implementation Decisions

### Document input flow
- Pre-populate document fields from the completed case assessment — user reviews before generating
- One standard professional format for Demand Letter — no tone/style variations
- User sees an HTML preview of the final document before downloading the PDF
- Additional fields not in assessment (address for service, representative info, etc.): Claude's discretion on collection approach

### Court form fidelity
- Pixel-perfect replica of official Ontario court forms (Form 7A, Form 9A) — same boxes, fonts, spacing as the paper form
- Version-aware with config flag pinned to August 1, 2022 version — makes future form updates easier to track
- Narrative sections (Reasons for Claim / Defence): guided sub-question prompts by default, with a "write your own" toggle for experienced users
- Auto-pagination for overflow narratives: Claude's discretion

### Process guide structure
- Full chronological lifecycle guide (filing -> service -> defence -> settlement conference -> trial -> enforcement) in accordion sections
- "Where am I?" navigator that jumps to the relevant stage + shows what's next
- Alpine.js search for the guide: Claude's discretion on heading filter vs full-text
- TMC reform presentation: Claude's discretion
- Section depth: Claude's discretion
- Stage checklists: Claude's discretion

### Document management
- Documents default to being linked to an assessment but can also be created standalone for edge cases (e.g., defence without prior assessment)
- Regeneration keeps versions — each generation saved as a new version, user can access older versions
- PDF storage approach: Claude's discretion (given versioning requirement)
- Filing fee calculator: standalone /fees page with full schedule AND fees shown contextually during document generation
- Fee schedule cites Ontario.ca source, reads from named constants (existing pattern from Phase 1)

### Claude's Discretion
- How to collect additional fields not in assessment (inline review page vs follow-up wizard)
- Auto-pagination for overflow narrative sections
- TMC reform presentation (seamless vs flagged as recent change)
- Guide section depth (essentials only vs expandable detail)
- Stage checklists (include or prose-only)
- Alpine.js search implementation (heading filter vs full-text)
- PDF storage strategy (stored files vs on-the-fly, given versioning)

</decisions>

<specifics>
## Specific Ideas

- Court forms must pass visual inspection against the Ontario Courts Public Portal format — pixel-perfect is the bar
- Guided prompts for narrative sections break it into sub-questions (What happened? When? What damages?) and stitch answers into the form section
- "Where am I?" navigator is a UX shortcut layered on top of the full guide, not a replacement
- Versioned documents give SRLs an audit trail of what they submitted vs. what they revised

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-documents-and-guide*
*Context gathered: 2026-04-05*
