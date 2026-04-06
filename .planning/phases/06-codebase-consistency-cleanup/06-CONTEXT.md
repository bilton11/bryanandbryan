# Phase 6: Codebase Consistency Cleanup - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Resolve 4 specific tech debt items identified in v1.0-MILESTONE-AUDIT.md: model export inconsistency, documentation staleness (REQUIREMENTS.md and ROADMAP.md), and CI safety gap. No new features, no new capabilities — strictly cleanup.

</domain>

<decisions>
## Implementation Decisions

### Model exports
- Add Document and DocumentVersion to `app/models/__init__.py` — match existing export pattern for all other models

### Documentation staleness
- Update REQUIREMENTS.md traceability table: flip Phase 2, 3, and 4 requirement statuses from Pending to Complete
- Fix ROADMAP Phase 1 success criterion 1: change "email/password" to "magic-link auth" to match actual implementation

### CI safety
- Remove `|| true` from pytest step in deploy.yml so test failures block deployment

### Claude's Discretion
- All implementation details — these are mechanical fixes with no ambiguity

</decisions>

<specifics>
## Specific Ideas

No specific requirements — all 4 items are precisely defined by the milestone audit.

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 06-codebase-consistency-cleanup*
*Context gathered: 2026-04-06*
