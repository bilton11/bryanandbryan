"""
AI Case Strength Assessment Service — Bryan and Bryan

Generates a statistical framing of Ontario Small Claims Court case strength
using Claude (Anthropic API). All Claude output is passed through AIGuardrail
before storage or display.

LAWYER_REVIEW_REQUIRED: This module is a user-facing AI feature. The system
prompt, graceful-degradation messages, and guardrail integration must be
reviewed by the supervising lawyer before any production deployment.
"""
from __future__ import annotations

import os

from flask import current_app

from app.extensions import db
from app.services.ai_guardrail import GuardrailResult, GuardrailStatus, guardrail

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_MODEL = "claude-sonnet-4-6"

_SYSTEM_PROMPT = """You are a legal information assistant describing statistical patterns in Ontario Small Claims Court cases.

Rules you MUST follow:
- ONLY describe statistical patterns. Never give legal advice.
- NEVER say "you should", "you must", "I recommend", "you will win", "you will lose".
- Frame ALL observations as: "Cases with similar characteristics in Ontario..."
- Do not predict the outcome of this specific case.
- Keep response under 150 words.
- End with: "This is a statistical observation, not legal advice."
"""

# LAWYER_REVIEW_REQUIRED: This system prompt produces user-facing prose that
# will appear on the assessment PDF in place of the user's raw description.
# The supervising lawyer must approve the wording rules below before launch.
_FACTS_POLISH_SYSTEM_PROMPT = """You are a paralegal assistant rewriting a self-represented litigant's narrative of an incident into a clear, complete factual statement suitable for an Ontario Small Claims Court assessment summary.

Rules you MUST follow:
- Stay strictly within the facts the claimant provided. NEVER invent details, parties, dates, dollar amounts, or events that were not in the original.
- Do NOT add legal conclusions ("the defendant was negligent", "this constitutes conversion", "the contract was breached"). State only what happened, not what it legally means.
- Do NOT recommend a course of action, predict an outcome, or characterise the strength of the case.
- Use the first person ("I", "my") — this is the claimant's own statement.
- Use plain, formal English. Avoid slang. Avoid Latin maxims. Avoid pejorative language about the other party.
- Preserve every concrete fact: who, what, when, where, dollar amounts, dates.
- If the original is too sparse to write a coherent paragraph, return the original sentence essentially unchanged rather than padding with invented context.
- Return ONLY the rewritten narrative. No preamble, no headings, no quotation marks, no commentary.
- Keep the rewrite under 200 words.
"""

_FACTS_POLISH_DEGRADED = GuardrailResult(
    status=GuardrailStatus.BLOCKED,
    text="",
    original="",
)

_DEGRADED_RESULT = GuardrailResult(
    status=GuardrailStatus.BLOCKED,
    text=(
        "AI assessment is not currently available. "
        "Complete your assessment without it, or try again later."
    ),
    original="",
)

_ERROR_RESULT = GuardrailResult(
    status=GuardrailStatus.BLOCKED,
    text="AI assessment temporarily unavailable.",
    original="",
)


# ---------------------------------------------------------------------------
# Claim summary builder (no PII in the prompt sent to Claude)
# ---------------------------------------------------------------------------


def build_claim_summary(claim) -> str:
    """
    Build a structured text summary of the claim for submission to Claude.

    Deliberately excludes personally identifying information (names, addresses,
    emails) — only factual attributes that describe the nature of the dispute
    are sent to the API.
    """
    from app.ontario_constants import VALID_CLAIM_TYPES

    step_data = claim.step_data or {}

    # Claim type
    dispute = step_data.get("dispute_type", {})
    claim_type_value = dispute.get("claim_type", "")
    claim_type_label = claim_type_value
    for ct in VALID_CLAIM_TYPES:
        if ct["value"] == claim_type_value:
            claim_type_label = ct["label"]
            break

    # Facts
    facts = step_data.get("facts", {})
    description = facts.get("description", "")
    incident_date = facts.get("incident_date", "")
    discovery_date = facts.get("discovery_date", "")
    is_minor = facts.get("is_minor") == "1"
    is_municipal = facts.get("is_municipal_defendant") == "1"

    # Amount
    amount_data = step_data.get("amount", {})
    amount = amount_data.get("amount", "")
    amount_certainty = amount_data.get("amount_includes", "")

    # Opposing party type only (not name, address, or email)
    party_data = step_data.get("opposing_party", {})
    party_type = party_data.get("party_type", "")

    # Limitation result
    limitation = step_data.get("limitation", {})
    limitation_status = limitation.get("status", "")
    limitation_deadline = limitation.get("basic_deadline", "")
    days_remaining = limitation.get("days_remaining")
    tolling_applied = limitation.get("tolling_applied", False)

    # Evidence
    evidence = step_data.get("evidence", {})
    checked_keys = evidence.get("checked", [])
    evidence_count = len(checked_keys)

    lines = [
        "Ontario Small Claims Court Case Profile",
        "=" * 40,
        f"Claim type: {claim_type_label}",
        f"Description of dispute: {description}",
        f"Incident date: {incident_date}",
    ]
    if discovery_date and discovery_date != incident_date:
        lines.append(f"Date discovered: {discovery_date}")
    if amount:
        lines.append(f"Claim amount: ${amount}")
    if amount_certainty:
        lines.append(f"Amount certainty: {amount_certainty}")
    lines.append(f"Opposing party type: {party_type or 'not specified'}")
    if is_minor:
        lines.append("Note: Claimant was a minor at time of incident (tolling may apply)")
    if is_municipal:
        lines.append("Note: Defendant is a municipal entity (pre-filing notice required)")
    if tolling_applied:
        lines.append("Note: Limitation period tolling was applied")
    lines.append(f"Limitation status: {limitation_status}")
    if limitation_deadline:
        lines.append(f"Filing deadline: {limitation_deadline}")
    if days_remaining is not None:
        lines.append(f"Days remaining: {days_remaining}")
    lines.append(f"Evidence items available: {evidence_count} of 8")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main assessment function
# ---------------------------------------------------------------------------


def get_case_strength_assessment(claim) -> GuardrailResult:
    """
    Generate an AI case strength assessment for the given claim.

    1. Returns a BLOCKED GuardrailResult (graceful degradation) when:
       - ANTHROPIC_API_KEY env var is absent
       - AI_ASSESSMENT_ENABLED config flag is False
       - Any Anthropic API error occurs

    2. On success: stores the guardrailed text in claim.ai_assessment and
       commits to the database, then returns the GuardrailResult.

    LAWYER_REVIEW_REQUIRED: This function is a user-facing AI call. The
    system prompt and all downstream display must be reviewed before launch.
    """
    # Feature flag — allows disabling AI without a code deploy (lawyer review gate)
    if not current_app.config.get("AI_ASSESSMENT_ENABLED", True):
        return _DEGRADED_RESULT

    # API key gate — graceful degradation when key absent
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return _DEGRADED_RESULT

    claim_summary = build_claim_summary(claim)

    try:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model=_MODEL,
            max_tokens=300,
            system=_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": claim_summary,
                }
            ],
        )
        raw_text = message.content[0].text if message.content else ""
    except Exception:
        return _ERROR_RESULT

    # Pass all Claude output through AIGuardrail before storage or display
    result = guardrail.process(raw_text)

    # Persist the guardrailed text (even TRANSFORMED is safe to store)
    if result.status != GuardrailStatus.BLOCKED:
        claim.ai_assessment = result.text
        db.session.commit()

    return result


# ---------------------------------------------------------------------------
# Facts polishing — rewrites the claimant's narrative into a clean factual
# statement suitable for the assessment summary PDF. Strictly bounded by the
# original facts (no fabrication, no legal conclusions, no recommendations).
# ---------------------------------------------------------------------------


def polish_facts_description(claim) -> str:
    """
    Use Claude to rewrite the claimant's free-text description into a clear,
    complete factual statement in plain formal English. Stores the result in
    claim.step_data['facts']['polished_description'] and returns it.

    Returns the original description unchanged on any failure (graceful
    degradation): missing API key, disabled feature flag, API error, or
    guardrail block. The PDF template falls back to the original.

    LAWYER_REVIEW_REQUIRED: Output appears verbatim on the assessment PDF.
    """
    step_data = claim.step_data or {}
    facts = step_data.get("facts", {}) or {}
    original = (facts.get("description") or "").strip()

    if not original:
        return ""

    # Feature flag and API key gates — same pattern as the strength assessment
    if not current_app.config.get("AI_ASSESSMENT_ENABLED", True):
        return original
    if not os.environ.get("ANTHROPIC_API_KEY"):
        return original

    try:
        import anthropic

        client = anthropic.Anthropic()
        message = client.messages.create(
            model=_MODEL,
            max_tokens=400,
            system=_FACTS_POLISH_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Rewrite the following narrative into a clear, complete factual "
                        "statement following the rules in the system prompt:\n\n"
                        f"{original}"
                    ),
                }
            ],
        )
        raw_text = (message.content[0].text if message.content else "").strip()
    except Exception:
        return original

    if not raw_text:
        return original

    # Pass through the same guardrail used for the strength assessment so any
    # advice-shaped phrasing slipped past the system prompt is caught.
    result = guardrail.process(raw_text)
    polished = result.text if result.status != GuardrailStatus.BLOCKED else original

    # Persist alongside the original — never overwrite the user's own words
    new_step_data = dict(step_data)
    new_facts = dict(facts)
    new_facts["polished_description"] = polished
    new_step_data["facts"] = new_facts
    claim.step_data = new_step_data
    db.session.commit()

    return polished
