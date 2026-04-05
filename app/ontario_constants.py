"""
Ontario Small Claims Court — Named Constants
Single source of truth for all court fees, monetary limits, and procedural values.
All values must be updated here when rules change — never hardcode in UI strings.

Last verified: 2026-04-04
Source: Ontario Courts website, Courts of Justice Act, Rules of the Small Claims Court
"""
from __future__ import annotations

# --- Monetary Limits ---
SMALL_CLAIMS_MONETARY_LIMIT = 50_000  # Maximum claim amount, effective Oct 2024
# Source: Courts of Justice Act, s. 23(1), O. Reg. 291/24

INFREQUENT_CLAIMANT_LIMIT = 25_000  # Threshold for infrequent claimant fee schedule
# Source: Small Claims Court — Fees, Ontario.ca

# --- Filing Fees ---
FILING_FEE_FREQUENT_CLAIMANT = 249_00  # in cents — frequent claimant (10+ claims/year)
FILING_FEE_INFREQUENT_CLAIMANT = 108_00  # in cents — infrequent claimant
DEFENCE_FILING_FEE = 77_00  # in cents
# Source: O. Reg. 432/93, Table (Small Claims Court — Fees)

# --- Service and Enforcement Fees ---
MOTION_FEE_INFREQUENT = 89_00  # in cents
MOTION_FEE_FREQUENT = 189_00  # in cents
CERTIFICATE_OF_JUDGMENT_FEE = 22_00  # in cents
WRIT_OF_DELIVERY_FEE = 55_00  # in cents
WRIT_OF_SEIZURE_FEE = 55_00  # in cents
# Source: O. Reg. 432/93, Table

# --- Procedural Constants ---
LIMITATION_PERIOD_YEARS = 2  # General limitation period
# Source: Limitations Act, 2002, S.O. 2002, c. 24, Sched. B, s. 4

ULTIMATE_LIMITATION_YEARS = 15  # Ultimate limitation period
# Source: Limitations Act, 2002, s. 15

DEFENCE_DEADLINE_DAYS = 20  # Days to file defence after service
# Source: Rules of the Small Claims Court, Rule 9.01(1)

TRIAL_REQUEST_DEADLINE_DAYS = 30  # Days after unsuccessful settlement conference
# Source: Rules of the Small Claims Court, Rule 13.05(2)

MUNICIPAL_NOTICE_DAYS = 10  # Days written notice before action against municipality
# Source: Municipal Act, 2001, s. 44(12)


# --- Dispute Type Router ---

# Hard-stop excluded types: NOT within SCC jurisdiction at all
EXCLUDED_CLAIM_TYPES: list[str] = [
    "title_to_land",
    "bankruptcy",
    "false_imprisonment",
    "malicious_prosecution",
]

# Hard-stop redirected types: technically possible in SCC but should be
# routed elsewhere by default. Each entry has a plain-language redirect
# message explaining the correct forum. Marked LAWYER_REVIEW_REQUIRED
# because exceptions exist (e.g. defamation CAN be brought in SCC, but
# anti-SLAPP motions are not available there).
REDIRECTED_CLAIM_TYPES: dict[str, str] = {
    "defamation": (
        "Defamation claims (libel and slander) involve complex procedural "
        "rules including anti-SLAPP motions that are not available in Small "
        "Claims Court. These claims are typically filed in the Superior Court "
        "of Justice. We strongly recommend consulting a lawyer before proceeding. "
        "LAWYER_REVIEW_REQUIRED"
    ),
    "landlord_tenant": (
        "Most landlord-tenant disputes in Ontario must be filed with the "
        "Landlord and Tenant Board (LTB), not Small Claims Court. The LTB "
        "handles evictions, rent arrears, maintenance issues, and deposit "
        "disputes. Visit tribunalsontario.ca/ltb to file your application. "
        "LAWYER_REVIEW_REQUIRED"
    ),
}

# All valid claim types for the dispute type step dropdown
VALID_CLAIM_TYPES: list[dict[str, str]] = [
    {"value": "unpaid_debt", "label": "Unpaid debt or loan"},
    {"value": "property_damage", "label": "Property damage"},
    {"value": "breach_of_contract", "label": "Breach of contract"},
    {"value": "consumer_complaint", "label": "Consumer complaint (goods or services)"},
    {"value": "personal_injury", "label": "Personal injury (up to $50,000)"},
    {"value": "return_of_property", "label": "Return of personal property"},
    {"value": "defamation", "label": "Defamation (libel or slander)"},
    {"value": "landlord_tenant", "label": "Landlord/tenant dispute"},
    {"value": "title_to_land", "label": "Title to land or real property"},
    {"value": "bankruptcy", "label": "Bankruptcy matter"},
    {"value": "false_imprisonment", "label": "False imprisonment"},
    {"value": "malicious_prosecution", "label": "Malicious prosecution"},
]


# --- Display Helpers ---
def format_fee(cents: int) -> str:
    """Format a fee in cents to a display string like '$108.00'."""
    return f"${cents / 100:.2f}"
