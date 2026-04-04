# Phase 1: Foundation - Context

**Gathered:** 2026-04-04
**Status:** Ready for planning

<domain>
## Phase Boundary

The app runs, users can authenticate, every page carries its regulatory disclaimer, and the AI guardrail architecture is in place before any user-facing feature ships. This phase delivers the skeleton that all subsequent phases build on.

</domain>

<decisions>
## Implementation Decisions

### Auth experience
- Magic link (email-based) authentication — no passwords
- User enters email, receives a login link, clicks to authenticate
- Session duration: 7 days before re-authentication required
- Unauthenticated users redirected to login page, then returned to original destination after auth
- Entire app is gated behind login — no public pages, landing page is the login page

### Claude's Discretion
- Disclaimer presentation — styling, placement, and wording of the regulatory footer
- Visual foundation — color palette, typography, overall tone
- AI guardrail UX — how filtered output is handled (transparent vs visible)
- Magic link expiry duration
- Rate limiting on magic link requests
- Login page layout and copy

</decisions>

<specifics>
## Specific Ideas

No specific requirements — open to standard approaches

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 01-foundation*
*Context gathered: 2026-04-04*
