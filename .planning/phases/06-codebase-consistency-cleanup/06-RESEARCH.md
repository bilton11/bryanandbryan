# Phase 6: Codebase Consistency Cleanup - Research

**Researched:** 2026-04-06
**Domain:** Internal codebase — model exports, documentation files, GitHub Actions YAML
**Confidence:** HIGH

## Summary

This phase resolves four specific tech debt items identified in v1.0-MILESTONE-AUDIT.md. Every change is a direct surgical edit to an existing file with a known current state and a known target state. There are no libraries to install, no architectural decisions to make, and no runtime behaviour changes. The research task is therefore to document the exact current state of each file and verify the precise edit required.

All four items were verified by reading the actual files in the repository. Confidence is HIGH throughout because findings come from direct file inspection, not inference.

**Primary recommendation:** Plan as a single task that makes all four edits atomically — they are independent, all fit in one commit, and together they close the audit cleanly.

---

## Standard Stack

No new libraries. All changes operate on files already in the repository.

| File | Type | Change |
|------|------|--------|
| `app/models/__init__.py` | Python | Add two model exports |
| `.planning/REQUIREMENTS.md` | Markdown | Update 19 status cells |
| `.planning/ROADMAP.md` | Markdown | Edit one sentence |
| `.github/workflows/deploy.yml` | YAML | Remove ` || true` from one line |

---

## Architecture Patterns

### Pattern 1: Model `__init__.py` Re-Export

**What:** `app/models/__init__.py` is the canonical re-export surface for all SQLAlchemy models. Currently exports `User` and `Claim`. `Document` and `DocumentVersion` both live in `app/models/document.py` but are absent from `__init__.py`.

**Current state (verified):**
```python
# app/models/__init__.py — current
from app.models.user import User
from app.models.claim import Claim
```

**Target state:**
```python
# app/models/__init__.py — after fix
from app.models.user import User
from app.models.claim import Claim
from app.models.document import Document, DocumentVersion
```

**Important context:** Consumers currently import `Document` and `DocumentVersion` directly from the submodule (`from app.models.document import ...`). Adding them to `__init__.py` does not break any existing import — it only makes the centralised re-export pattern consistent. No consumer needs to change.

**Python 3.14 note:** `app/models/document.py` already carries `from __future__ import annotations` at line 1. No change needed there.

### Pattern 2: REQUIREMENTS.md Traceability Table Update

**What:** The traceability table in `.planning/REQUIREMENTS.md` has 19 rows that show `Pending` for Phase 2, 3, and 4 requirements. Phases 2, 3, and 4 are all Complete (verified by ROADMAP.md progress table and v1.0-MILESTONE-AUDIT.md).

**Current state (verified — lines 99–118 of `.planning/REQUIREMENTS.md`):**
```
| ASMT-01 | Phase 2 | Pending |   ← and 6 more ASMT rows
| DOCS-01 | Phase 3 | Pending |   ← and 3 more DOCS rows
| GUID-01 | Phase 3 | Pending |   ← and 3 more GUID rows
| DASH-01 | Phase 4 | Complete |  ← already correct (4 rows)
```

**Rows requiring update — exact list:**

Phase 2 (7 rows): ASMT-01, ASMT-02, ASMT-03, ASMT-04, ASMT-05, ASMT-06, ASMT-07 — change `Pending` to `Complete`

Phase 3 (8 rows): DOCS-01, DOCS-02, DOCS-03, DOCS-04, GUID-01, GUID-02, GUID-03, GUID-04 — change `Pending` to `Complete`

Phase 4 (4 rows): DASH-01, DASH-02, DASH-03, DASH-04 — already `Complete`, no change needed

**Total edits:** 15 cells changed from `Pending` to `Complete` (7 + 8; DASH rows already correct).

Note: The audit report says "Phase 2 and 3 requirements still show Pending" — Phase 4 rows are already `Complete` in the file. The CONTEXT.md says "Phase 2, 3, and 4" but on inspection Phase 4 is already correct. Plan should update Phase 2 and Phase 3 rows only.

### Pattern 3: ROADMAP Phase 1 Success Criterion 1 Wording Fix

**What:** Phase 1 success criterion 1 in `.planning/ROADMAP.md` currently reads "email and password" but the actual implementation uses magic-link auth. The audit flagged this as a wording mismatch.

**Current state (verified — line 28 of `.planning/ROADMAP.md`):**
```
  1. User can create an account with email, authenticate via magic link, and log out from any page
```

Wait — the file already says "authenticate via magic link." Re-reading the audit: the audit item says "ROADMAP success criterion says 'email and password' but implementation is magic-link by design." But the actual file content at line 28 reads "authenticate via magic link."

This means the ROADMAP has already been partially corrected, or the audit was flagging something slightly different. Let me reconcile: the CONTEXT.md decision says "Fix ROADMAP Phase 1 success criterion 1: change 'email/password' to 'magic-link auth' to match actual implementation." The file at line 28 already contains "authenticate via magic link."

**Resolution:** The wording in Phase 1 success criterion 1 already matches the magic-link implementation. The edit may already be done. The planner should verify line 28 of ROADMAP.md against the criterion text before making any edit. If it already reads "authenticate via magic link" or similar, this item is already resolved and should be noted as such rather than making a redundant edit.

### Pattern 4: CI Pipeline — Remove `|| true` from pytest Step

**What:** The pytest step in `.github/workflows/deploy.yml` uses `|| true` which means test failures are silently swallowed and deployment proceeds even when tests fail.

**Current state (verified — line 36 of `.github/workflows/deploy.yml`):**
```yaml
      - name: Run tests
        run: python -m pytest tests/ -v --tb=short || true
```

**Target state:**
```yaml
      - name: Run tests
        run: python -m pytest tests/ -v --tb=short
```

**Behaviour change:** After this edit, a non-zero pytest exit code will cause the `test` job to fail. The `deploy` job has `needs: [test]`, so deploy will be blocked. This is the intended behaviour.

**Risk assessment:** If the tests/ directory has any currently failing tests, removing `|| true` will immediately block the next deployment. Planner should note that running tests locally before merging this change is prudent.

---

## Don't Hand-Roll

Not applicable — this phase makes no architectural choices and builds no new abstractions.

---

## Common Pitfalls

### Pitfall 1: ROADMAP Criterion Already Fixed

**What goes wrong:** A planner or implementer edits ROADMAP line 28 to add "magic-link" language — but that language is already present, resulting in a double-edit or mangled text.

**Why it happens:** The audit was written from memory or static analysis; the file may have been updated after the audit was written.

**How to avoid:** Read `.planning/ROADMAP.md` line 28 before editing. If it already says "magic-link" or "authenticate via magic link," mark this item as already complete and skip the edit.

**Warning signs:** If the diff for this file is empty or changes something already correct.

### Pitfall 2: Forgetting the `DocumentType` Enum

**What goes wrong:** Adding `Document` and `DocumentVersion` to `__init__.py` but omitting `DocumentType`, leaving it importable only from the submodule.

**Why it happens:** The decision text says "Add Document and DocumentVersion" — `DocumentType` is a sibling class in the same file and should follow the same export decision.

**How to avoid:** The decision is locked to `Document` and `DocumentVersion` only — those are what the tests and consumers reference via `app.models`. `DocumentType` is currently imported directly from `app.models.document` in all consumers (`documents/routes.py` and `document_service.py`) and that pattern works fine. Do not add `DocumentType` to `__init__.py` unless the planner explicitly decides to.

### Pitfall 3: Counting the Wrong REQUIREMENTS.md Rows

**What goes wrong:** Updating only Phase 2 rows (7) and missing Phase 3 rows (8), or mistakenly editing Phase 4 rows that are already `Complete`.

**Why it happens:** The CONTEXT.md says "Phase 2, 3, and 4" but Phase 4 rows are already `Complete` — 15 edits needed, not 19.

**How to avoid:** The plan task should enumerate the 15 specific requirement IDs: ASMT-01 through ASMT-07, DOCS-01 through DOCS-04, GUID-01 through GUID-04.

### Pitfall 4: Removing `|| true` Breaks an Active Pipeline

**What goes wrong:** Removing `|| true` while there are currently-failing tests causes the very next push to `main` to fail at the test stage and block deployment.

**Why it happens:** `|| true` was there to permit deployment despite test failures — removing it enforces the gate that was previously bypassed.

**How to avoid:** The plan should include a step: run `python -m pytest tests/ -v` locally before committing deploy.yml. If tests pass, the removal is safe. If tests fail, fix the tests first (or note what is failing and accept the gate).

---

## Code Examples

### Model Export Pattern (from existing `__init__.py`)

```python
# Source: direct file read — app/models/__init__.py
# Current (2 exports):
from app.models.user import User
from app.models.claim import Claim

# After fix (4 exports — same pattern, two additions):
from app.models.user import User
from app.models.claim import Claim
from app.models.document import Document, DocumentVersion
```

### REQUIREMENTS.md Row Pattern

```markdown
# Source: direct file read — .planning/REQUIREMENTS.md lines 99-118
# Current (example stale rows):
| ASMT-01 | Phase 2 | Pending |
| DOCS-01 | Phase 3 | Pending |

# After fix:
| ASMT-01 | Phase 2 | Complete |
| DOCS-01 | Phase 3 | Complete |
```

### Deploy YAML Pytest Step

```yaml
# Source: direct file read — .github/workflows/deploy.yml line 36
# Current:
      - name: Run tests
        run: python -m pytest tests/ -v --tb=short || true

# After fix:
      - name: Run tests
        run: python -m pytest tests/ -v --tb=short
```

---

## State of the Art

| Item | Current State | Target State | Impact |
|------|--------------|--------------|--------|
| `app/models/__init__.py` | Exports `User`, `Claim` only | Exports `User`, `Claim`, `Document`, `DocumentVersion` | Consistent re-export surface |
| REQUIREMENTS.md Phase 2 rows | `Pending` (7 rows) | `Complete` | Accurate traceability |
| REQUIREMENTS.md Phase 3 rows | `Pending` (8 rows) | `Complete` | Accurate traceability |
| ROADMAP.md Phase 1 SC 1 | Likely already correct — verify | No change if already correct | Documentation accuracy |
| deploy.yml pytest step | `... || true` | No `|| true` | Test failures block deploy |

---

## Open Questions

1. **ROADMAP Phase 1 criterion wording**
   - What we know: Line 28 of `.planning/ROADMAP.md` currently reads "User can create an account with email, authenticate via magic link, and log out from any page" — this already says "magic link"
   - What's unclear: Whether the audit was flagging this exact line or a different part of the success criteria block
   - Recommendation: Planner should read lines 27–32 of ROADMAP.md to confirm the full criterion text. If it already matches "magic-link auth," mark this sub-item as already resolved and document that in the commit message.

2. **Test suite health before removing `|| true`**
   - What we know: `|| true` was added in Phase 4 implying tests may have been failing or fragile at that time
   - What's unclear: Current state of tests/ — whether they all pass
   - Recommendation: Plan should include a verification step to run tests locally. If any fail, they must be fixed before or alongside removing `|| true`.

---

## Sources

### Primary (HIGH confidence)

Direct file reads — no external sources required for this phase:

- `app/models/__init__.py` — verified current content (2 exports: User, Claim)
- `app/models/document.py` — verified Document and DocumentVersion class definitions, `from __future__ import annotations` present
- `.github/workflows/deploy.yml` — verified `|| true` at line 36
- `.planning/REQUIREMENTS.md` — verified traceability table rows 99–118
- `.planning/ROADMAP.md` — verified Phase 1 success criterion at line 28
- `.planning/v1.0-MILESTONE-AUDIT.md` — verified source of all four tech debt items

No external library research required. No WebSearch conducted — not applicable to this domain.

---

## Metadata

**Confidence breakdown:**
- Model export fix: HIGH — verified by direct file read
- REQUIREMENTS.md update: HIGH — verified row-by-row; exact IDs enumerated
- ROADMAP wording fix: HIGH (finding: may already be done) — verified by direct file read
- CI `|| true` removal: HIGH — verified exact line in deploy.yml; behaviour change understood

**Research date:** 2026-04-06
**Valid until:** Until any of the four target files is modified — these are point-in-time observations
