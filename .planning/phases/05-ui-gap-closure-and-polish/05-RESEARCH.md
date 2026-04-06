# Phase 5: UI Gap Closure and Polish — Research

**Researched:** 2026-04-06
**Domain:** Jinja2 templates, HTMX version consolidation, Alpine.js x-cloak, Flask public navigation
**Confidence:** HIGH — all five issues are fully scoped by direct codebase inspection; no third-party library guesswork needed for the core work.

---

## Summary

This phase closes five discrete issues identified in the v1.0 milestone audit. None requires new routes, models, or Flask logic — every fix is a targeted template or CSS edit. The research below maps each issue to the exact files and lines involved, documents the correct fix pattern, and flags the one ordering constraint that matters (HTMX consolidation).

The five issues are independent except that HTMX consolidation (issue 3) and the x-cloak CSS fix (issue 4) touch `base.html` and `main.css` respectively — those two edits set the baseline that the rest of the phase builds on.

**Primary recommendation:** Fix issues in dependency order: (4) x-cloak CSS → (3) HTMX consolidation → (1/2) Form 7A/9A buttons → (5) Public page nav. Each fix is a single-file edit except HTMX (two files).

---

## Standard Stack

No new libraries. All work uses what is already in the project.

### Core (already installed)
| Library | Version in use | Role |
|---------|---------------|------|
| Jinja2 | (Flask-bundled) | Template rendering — all fixes are template edits |
| HTMX | 1.9.12 (base.html) + 2.0.4 (wizard/docs) | Consolidate to 2.0.4 globally |
| Alpine.js | 3.14.9 (CDN, per-page where needed) | x-cloak directive support |

### Alternatives Considered
| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| Consolidate to HTMX 2.0.4 | Consolidate to 1.9.12 | 2.0.4 is what the wizard and documents pages already load via head_extra; keeping it means head_extra overrides are removed, not base.html changed |
| Inline [x-cloak] CSS per template | Global rule in main.css | Global is correct — x-cloak is used in 4+ templates and inline-per-template is the current inconsistency |

---

## Architecture Patterns

### Issue 1 + 2: Form 7A/9A buttons (documents/index.html)

**What's broken:** `documents/index.html` only has Demand Letter buttons. The two sections that need new buttons are:
1. "Generate from an Assessed Claim" — `{% for claim in assessed_claims %}` loop (lines 19-37): one `<a>` per claim for Demand Letter. Need to add Form 7A and Form 9A anchors beside it.
2. "Create Standalone Document" — lines 44-48: one `<a>` for Demand Letter. Need Form 7A and Form 9A anchors.

**Route signatures (verified from routes.py):**
```
documents.from_claim  → /documents/from-claim/<claim_id>/<doc_type>
documents.new_document → /documents/new/<doc_type>
```
Valid `doc_type` values: `demand_letter`, `form_7a`, `form_9a` (all from `DocumentType` enum).

**Exact Demand Letter button patterns to match:**

From-claim path (inside `{% for claim in assessed_claims %}`):
```html
<a href="{{ url_for('documents.from_claim', claim_id=claim.id, doc_type='demand_letter') }}"
   class="btn btn-primary" style="font-size: 0.875rem;">
  Demand Letter
</a>
```

Standalone path:
```html
<a href="{{ url_for('documents.new_document', doc_type='demand_letter') }}" class="btn btn-secondary">
  Demand Letter
</a>
```

**Fix:** Add two more anchors to each location using the same `btn btn-primary` / `btn btn-secondary` classes, with `doc_type='form_7a'` and `doc_type='form_9a'`. Button labels should use descriptive names, consistent with `DOC_TYPE_LABELS` in routes.py:
- `form_7a` → "Form 7A — Plaintiff's Claim"
- `form_9a` → "Form 9A — Defence"

**Guide links that drive this fix (confirmed in guide/index.html):**
- Line 193: `<a href="{{ url_for('documents.index') }}">Generate your Form 7A using our tool →</a>` — this lands on documents index, which must now show a Form 7A button.
- Line 284: `<a href="{{ url_for('documents.index') }}">generate your Form 9A using our tool →</a>` — same.

The guide links go to `documents.index` (not directly to new_document) — the fix is correctly in the index template, not the guide.

### Issue 3: HTMX dual-version load

**Current state (confirmed):**
- `base.html` line 8: `<script src="https://unpkg.com/htmx.org@1.9.12" defer></script>` — loads globally
- `documents/index.html` `{% block head_extra %}` line 6: loads `htmx.org@2.0.4`
- `assessment/wizard_shell.html` `{% block head_extra %}` line 4: loads `htmx.org@2.0.4`

Both child templates load 2.0.4 on top of 1.9.12 from base — result is two HTMX versions registered on the same page.

**Breaking changes between 1.9.12 → 2.0.4 relevant to this codebase:**

HTMX attributes used in this app: `hx-post`, `hx-get`, `hx-target`, `hx-swap="innerHTML"`, `hx-include`, `hx-indicator`, `htmx.trigger()`. All are unchanged between 1.9 and 2.0 (verified via Context7 docs for v2.0.4). The one breaking change that could matter — `hx-on` attribute syntax — is not used in this codebase. The `htmx.trigger(form, 'submit')` call in `evidence_checklist.html` is also unchanged in 2.0.

**Fix:** Replace the 1.9.12 script tag in `base.html` with 2.0.4. Remove the `{% block head_extra %}` HTMX script tags from `documents/index.html` and `wizard_shell.html` (their Alpine.js `<script defer>` tags in those blocks must be kept — only the HTMX tag is removed).

**Target state after fix:**
- `base.html`: loads `htmx.org@2.0.4` with integrity hash, globally, `defer`
- `documents/index.html` `head_extra`: empty (HTMX gone, no Alpine on this page)
- `wizard_shell.html` `head_extra`: Alpine.js only (HTMX tag removed)

**Integrity hash for htmx 2.0.4 (already in the codebase — copy from wizard_shell.html or documents/index.html):**
```
sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+
```

### Issue 4: Missing [x-cloak] CSS rule in main.css

**Current state (confirmed):**
- `app/static/css/main.css`: no `[x-cloak]` rule (grep confirmed zero matches)
- `documents/review.html` line 487: has `[x-cloak] { display: none !important; }` in an inline `<style>` tag
- `guide/index.html` line 1023: has `[x-cloak] { display: none !important; }` in its inline `<style>` block
- `assessment/steps/step_facts.html` line 75: uses `x-cloak` but has NO inline rule — the wizard_shell page that includes this partial has no `[x-cloak]` CSS either (only Alpine.js loaded via head_extra). This is the active flash bug (minor_dob field).

**Official Alpine.js pattern (verified via Context7):**
```css
[x-cloak] { display: none !important; }
```
Must be present before Alpine initializes. Global placement in `main.css` (which loads in `base.html` `<head>`) guarantees it fires before any Alpine script.

**Fix:** Add `[x-cloak] { display: none !important; }` to `main.css`. After this, the inline rules in `review.html` and `guide/index.html` become redundant but are harmless (identical rule, no conflict).

**Placement in main.css:** Add near top of file, after the Reset section and before component-specific rules. A "Utility" or "Alpine.js" comment block is appropriate.

### Issue 5: No navigation links on public pages (/guide and /fees)

**Current state (confirmed):**
- `base.html` nav block (lines 17-25): nav links are entirely inside `{% if current_user.is_authenticated %}`. For unauthenticated users, the nav renders only the `site-name` link — no other links.
- `/guide` and `/fees` are both public (`@login_required` absent on those routes). Unauthenticated users see a header with just the site name.
- `guide/index.html` has one cross-link: line 136 links to `documents.fees` from within a section body.
- `fees.html` has no links to guide or login.

**Fix:** Add an `{% else %}` branch to the nav's auth check in `base.html` showing links relevant to unauthenticated users:
- Guide (`main.guide`)
- Fees (`documents.fees`)
- Log in (`auth.login`)

**Exact auth route name confirmed:** `auth.login` (routes.py line 35: `@auth_bp.route("/login")`).

**Pattern (mirroring authenticated nav structure):**
```html
{% if current_user.is_authenticated %}
<div class="nav-links">
  ... existing authenticated links ...
</div>
{% else %}
<div class="nav-links">
  <a href="{{ url_for('main.guide') }}"{% if request.endpoint == 'main.guide' %} aria-current="page"{% endif %}>Guide</a>
  <a href="{{ url_for('documents.fees') }}"{% if request.endpoint == 'documents.fees' %} aria-current="page"{% endif %}>Fees</a>
  <a href="{{ url_for('auth.login') }}"{% if request.endpoint == 'auth.login' %} aria-current="page"{% endif %}>Log in</a>
</div>
{% endif %}
```

The `aria-current="page"` pattern is already used in the authenticated nav — carry it through consistently.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead |
|---------|-------------|-------------|
| x-cloak flash prevention | Per-template inline `<style>` (current inconsistent approach) | Single rule in main.css loaded globally |
| HTMX version management | Conditional loading or version detection JS | Simply load one version in base.html |
| Public nav | Separate base template for public pages | `{% else %}` branch in existing nav block |

---

## Common Pitfalls

### Pitfall 1: Removing HTMX from head_extra but forgetting Alpine.js
**What goes wrong:** `wizard_shell.html` head_extra loads both HTMX 2.0.4 AND Alpine.js 3.14.9. If the entire `head_extra` block is cleared, Alpine.js disappears from the wizard — all `x-data`, `x-show`, `x-cloak` in step_facts.html stop working.
**How to avoid:** Only remove the HTMX `<script>` tag from `wizard_shell.html` head_extra. Keep the Alpine.js `<script defer>` tag exactly as-is.

### Pitfall 2: Adding the wrong HTMX integrity hash to base.html
**What goes wrong:** Copying the 1.9.12 hash to the 2.0.4 URL causes a SubResource Integrity failure — HTMX silently fails to load.
**How to avoid:** Copy the 2.0.4 script tag exactly from `wizard_shell.html` or `documents/index.html` (both already have the correct 2.0.4 hash). The hash is `sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+`.

### Pitfall 3: documents/index.html head_extra has only HTMX (no Alpine)
**What goes wrong:** Unlike `wizard_shell.html`, `documents/index.html` head_extra contains ONLY the HTMX 2.0.4 script — no Alpine.js. So the entire `{% block head_extra %}` in that file can be deleted outright. No need to keep anything.
**How to avoid:** Confirm before editing: `documents/index.html` head_extra is lines 5-7 — just HTMX, nothing else.

### Pitfall 4: x-cloak rule placement causes specificity fight
**What goes wrong:** Adding `[x-cloak] { display: none; }` (without `!important`) after component rules that set `display: block` or similar can lose the cascade — element briefly shows.
**How to avoid:** Use `[x-cloak] { display: none !important; }` — exactly as Alpine.js official docs recommend. This matches the inline rules already in `review.html` and `guide/index.html`.

### Pitfall 5: From-claim buttons placed outside the `{% for claim in assessed_claims %}` loop
**What goes wrong:** The assessed claims section renders one row per claim. The Form 7A/9A buttons must be inside the loop, alongside the Demand Letter button, using `claim.id` for the `claim_id` parameter.
**How to avoid:** The button `<div>` at lines 29-34 of `documents/index.html` is the correct insertion point — the `<a>` tags go inside that div.

---

## Code Examples

### Form 7A/9A buttons — from-claim path
```html
{# Inside {% for claim in assessed_claims %} loop, in the button <div> #}
<a href="{{ url_for('documents.from_claim', claim_id=claim.id, doc_type='form_7a') }}"
   class="btn btn-primary" style="font-size: 0.875rem;">
  Form 7A — Plaintiff's Claim
</a>
<a href="{{ url_for('documents.from_claim', claim_id=claim.id, doc_type='form_9a') }}"
   class="btn btn-primary" style="font-size: 0.875rem;">
  Form 9A — Defence
</a>
```

### Form 7A/9A buttons — standalone path
```html
{# In "Create Standalone Document" section, alongside Demand Letter anchor #}
<a href="{{ url_for('documents.new_document', doc_type='form_7a') }}" class="btn btn-secondary">
  Form 7A — Plaintiff's Claim
</a>
<a href="{{ url_for('documents.new_document', doc_type='form_9a') }}" class="btn btn-secondary">
  Form 9A — Defence
</a>
```

### HTMX consolidation — base.html replacement tag
```html
{# Replace the 1.9.12 line in base.html with: #}
<script src="https://unpkg.com/htmx.org@2.0.4" integrity="sha384-HGfztofotfshcF7+8n44JQL2oJmowVChPTg48S+jvZoztPfvwD79OC/LTtG6dMp+" crossorigin="anonymous" defer></script>
```

### [x-cloak] rule — placement in main.css
```css
/* Alpine.js — prevent flash of unstyled content before initialization */
[x-cloak] { display: none !important; }
```
Source: Alpine.js official docs (verified via Context7 /alpinejs/alpine)

### Public page nav — base.html else branch
```html
{% else %}
<div class="nav-links">
  <a href="{{ url_for('main.guide') }}"{% if request.endpoint == 'main.guide' %} aria-current="page"{% endif %}>Guide</a>
  <a href="{{ url_for('documents.fees') }}"{% if request.endpoint == 'documents.fees' %} aria-current="page"{% endif %}>Fees</a>
  <a href="{{ url_for('auth.login') }}"{% if request.endpoint == 'auth.login' %} aria-current="page"{% endif %}>Log in</a>
</div>
{% endif %}
```

---

## File Map

| Issue | File(s) to edit | Change |
|-------|----------------|--------|
| 1+2: Form 7A/9A buttons | `app/templates/documents/index.html` | Add 4 `<a>` tags (2 per section) |
| 3: HTMX consolidation | `app/templates/base.html` | Replace 1.9.12 script with 2.0.4 |
| 3: HTMX consolidation | `app/templates/documents/index.html` | Delete entire `{% block head_extra %}` block |
| 3: HTMX consolidation | `app/templates/assessment/wizard_shell.html` | Remove HTMX script tag; keep Alpine.js tag |
| 4: x-cloak CSS | `app/static/css/main.css` | Add 1 CSS rule near top |
| 5: Public nav | `app/templates/base.html` | Add `{% else %}` branch to nav |

Note: Issues 1+2 and issue 3 both touch `documents/index.html`. Do them in the same edit to avoid conflicts. Issues 3 and 5 both touch `base.html` — same edit.

---

## State of the Art

| Old Approach | Current Approach | Impact |
|--------------|-----------------|--------|
| HTMX 1.x default behaviors | HTMX 2.x — `DELETE` uses URL params, cross-domain restricted | No impact: app uses only `hx-post`/`hx-get` with same-origin Flask routes |
| `hx-on="event: ..."` syntax | `hx-on:event-name="..."` syntax in 2.x | No impact: app does not use `hx-on` anywhere |
| Per-template x-cloak inline style | Global CSS rule | Correct approach — inline rules in review.html and guide/index.html become redundant but harmless |

---

## Open Questions

None. All five issues are fully diagnosed from codebase inspection with no ambiguity.

1. **Should inline `[x-cloak]` rules in review.html and guide/index.html be removed after main.css is updated?**
   - What we know: They are harmless duplicates after the global rule is added.
   - Recommendation: Leave them in place for Phase 5 (minimal diff). Phase 6 (codebase consistency cleanup) is the right time for that housekeeping.

2. **Should the HTMX 2.0.4 CDN tag use `defer` or no attribute?**
   - What we know: The existing 2.0.4 tags in wizard_shell.html and documents/index.html do NOT use `defer`. The 1.9.12 tag in base.html uses `defer`. HTMX 2.0 works with either.
   - Recommendation: Add `defer` to the global 2.0.4 tag in base.html (consistent with current global pattern, avoids render-blocking).

---

## Sources

### Primary (HIGH confidence)
- Codebase inspection (direct file reads) — all file paths, line numbers, route names, template patterns verified
- Context7 `/alpinejs/alpine` — `[x-cloak] { display: none !important; }` pattern confirmed
- Context7 `/bigskysoftware/htmx/v2.0.4` — `htmx.trigger()` unchanged in 2.0; `hx-indicator` unchanged

### Secondary (MEDIUM confidence)
- WebFetch `https://htmx.org/migration-guide-htmx-1/` — breaking changes between 1.x and 2.x: `hx-on` syntax, `DELETE` body behavior, cross-domain defaults — none affect this codebase's actual usage

---

## Metadata

**Confidence breakdown:**
- File map (which files to edit): HIGH — direct inspection
- Fix patterns (what to write): HIGH — copied from existing codebase patterns
- HTMX 1→2 compatibility: HIGH — confirmed via Context7 + official migration guide
- Alpine.js x-cloak pattern: HIGH — confirmed via Context7 official docs
- No impact on existing HTMX behavior: HIGH — app uses only hx-post/hx-get/hx-target/hx-swap/hx-include/hx-indicator/htmx.trigger(), all unchanged in 2.0

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable libraries, no fast-moving concerns)
