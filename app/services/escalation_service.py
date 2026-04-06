from __future__ import annotations

from app.ontario_constants import INFREQUENT_CLAIMANT_LIMIT


def is_escalation_required(claim) -> bool:
    """Return True if the claim has characteristics that warrant lawyer involvement.

    Three triggers (any one is sufficient):
    1. Claim amount exceeds INFREQUENT_CLAIMANT_LIMIT ($25,000)
    2. The opposing party is a business / corporate defendant
    3. The limitation period status requires legal review or has expired
    """
    step_data: dict = claim.step_data or {}

    # --- Trigger 1: claim amount > $25,000 ---
    raw_amount = step_data.get("amount", {}).get("amount", 0)
    try:
        claim_amount = int(raw_amount)
    except (TypeError, ValueError):
        claim_amount = 0

    if claim_amount > INFREQUENT_CLAIMANT_LIMIT:
        return True

    # --- Trigger 2: corporate / business defendant ---
    party_type = step_data.get("opposing_party", {}).get("party_type", "")
    if party_type == "business":
        return True

    # --- Trigger 3: limitation period requires review or has expired ---
    limitation_status = step_data.get("limitation", {}).get("status", "")
    if limitation_status in ("requires_lawyer_review", "expired", "ultimate_expired"):
        return True

    return False


def get_escalation_reasons(claim) -> list[str]:
    """Return human-readable reasons explaining why escalation is recommended.

    Only includes reasons that actually apply to this claim.
    Returns an empty list when no escalation triggers are present.
    """
    step_data: dict = claim.step_data or {}
    reasons: list[str] = []

    # --- Trigger 1: claim amount ---
    raw_amount = step_data.get("amount", {}).get("amount", 0)
    try:
        claim_amount = int(raw_amount)
    except (TypeError, ValueError):
        claim_amount = 0

    if claim_amount > INFREQUENT_CLAIMANT_LIMIT:
        reasons.append(
            f"Your claim exceeds ${INFREQUENT_CLAIMANT_LIMIT:,} — cases at this level"
            " benefit from legal guidance on procedure and evidence."
        )

    # --- Trigger 2: corporate defendant ---
    party_type = step_data.get("opposing_party", {}).get("party_type", "")
    if party_type == "business":
        reasons.append(
            "Your claim involves a corporate defendant, who may be represented by"
            " legal counsel."
        )

    # --- Trigger 3: limitation period ---
    limitation_status = step_data.get("limitation", {}).get("status", "")
    if limitation_status == "requires_lawyer_review":
        reasons.append(
            "Your limitation period involves special circumstances (tolling, minors,"
            " or municipal notice) that require legal review."
        )
    elif limitation_status == "expired":
        reasons.append(
            "Your limitation period may have expired — a lawyer can advise whether"
            " any exceptions apply."
        )
    elif limitation_status == "ultimate_expired":
        reasons.append(
            "Your ultimate limitation period has expired. Legal advice is strongly"
            " recommended before proceeding."
        )

    return reasons
