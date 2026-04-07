"""
PDF Generation Service — Bryan and Bryan

Renders a standalone assessment report PDF using WeasyPrint. The PDF template
uses CSS running()/element() to print the regulatory disclaimer on every page.
No site navigation, login/logout links, or other chrome is included in the PDF.
"""
from __future__ import annotations

import base64
from datetime import date
from pathlib import Path

from flask import current_app, render_template
from flask_weasyprint import HTML as WeasyHTML


# ---------------------------------------------------------------------------
# Brand letterhead — embed the B&B logo as a base64 data URI so PDFs stay
# self-contained. WeasyPrint receives HTML strings without a base_url, so
# relative <img src> paths cannot be resolved at render time. Encoding the
# logo inline keeps the "no external requests in PDF" guarantee.
# ---------------------------------------------------------------------------

_LOGO_RELATIVE_PATH = "img/logo.png"
_LOGO_DATA_URI_CACHE: str | None = None


def get_brand_logo_data_uri() -> str:
    """
    Return the B&B shield logo as a `data:image/png;base64,...` URI suitable
    for embedding in a PDF or HTML template. Returns an empty string when the
    file is missing so templates can render without a letterhead during
    development.
    """
    global _LOGO_DATA_URI_CACHE
    if _LOGO_DATA_URI_CACHE is not None:
        return _LOGO_DATA_URI_CACHE

    try:
        static_root = Path(current_app.static_folder)
    except RuntimeError:
        # Outside of an app context — treat as missing rather than crash
        return ""

    logo_path = static_root / _LOGO_RELATIVE_PATH
    if not logo_path.is_file():
        return ""

    encoded = base64.b64encode(logo_path.read_bytes()).decode("ascii")
    _LOGO_DATA_URI_CACHE = f"data:image/png;base64,{encoded}"
    return _LOGO_DATA_URI_CACHE


def render_assessment_pdf(claim) -> bytes:
    """
    Render a complete assessment report as a PDF and return raw bytes.

    Builds a context dict from all claim data needed for the report, renders the
    standalone PDF template, then converts the HTML to PDF via WeasyPrint.

    No PII (names, addresses, emails) is included in the context passed to the
    template — the template is designed to display only factual claim attributes.
    """
    from app.assessment.routes import EVIDENCE_TYPES, EVIDENCE_SCORE_LABELS, _score_evidence
    from app.ontario_constants import SMALL_CLAIMS_MONETARY_LIMIT, VALID_CLAIM_TYPES

    step_data = claim.step_data or {}

    # --- Claim type label ---
    dispute = step_data.get("dispute_type", {})
    claim_type_value = dispute.get("claim_type", "")
    claim_type_label = claim_type_value
    for ct in VALID_CLAIM_TYPES:
        if ct["value"] == claim_type_value:
            claim_type_label = ct["label"]
            break

    # --- Facts ---
    # Prefer the AI-polished narrative when present (set during finalize by
    # polish_facts_description). Falls back to the user's original wording.
    facts = step_data.get("facts", {})
    facts_description = facts.get("polished_description") or facts.get("description", "")
    facts_incident_date = facts.get("incident_date", "")
    facts_discovery_date = facts.get("discovery_date", "")

    # --- Amount ---
    amount_data = step_data.get("amount", {})
    amount_value = amount_data.get("amount", "")
    amount_certainty_map = {
        "exact": "exact amount",
        "estimated": "estimated",
        "tbd": "to be determined",
    }
    amount_certainty = amount_certainty_map.get(amount_data.get("amount_includes", ""), "")
    within_jurisdiction = False
    if amount_value:
        try:
            within_jurisdiction = int(amount_value) <= SMALL_CLAIMS_MONETARY_LIMIT
        except (ValueError, TypeError):
            pass

    # --- Opposing party type only ---
    party_data = step_data.get("opposing_party", {})
    party_type = party_data.get("party_type", "")

    # --- Limitation period ---
    limitation = step_data.get("limitation", {})
    limitation_status = limitation.get("status", "")
    limitation_deadline = limitation.get("basic_deadline", "")
    ultimate_deadline = limitation.get("ultimate_deadline", "")
    days_remaining = limitation.get("days_remaining")
    municipal_notice_required = limitation.get("municipal_notice_required", False)

    # --- Evidence inventory ---
    evidence_checked: list[str] = list(step_data.get("evidence", {}).get("checked", []))
    evidence_score_pct, evidence_score_label = _score_evidence(evidence_checked)

    # --- AI assessment ---
    ai_assessment_text = claim.ai_assessment or ""

    # --- Report date ---
    report_date = date.today().isoformat()

    context = dict(
        claim_type_label=claim_type_label,
        facts_description=facts_description,
        facts_incident_date=facts_incident_date,
        facts_discovery_date=facts_discovery_date,
        amount_value=amount_value,
        amount_certainty=amount_certainty,
        within_jurisdiction=within_jurisdiction,
        party_type=party_type,
        limitation_status=limitation_status,
        limitation_deadline=limitation_deadline,
        ultimate_deadline=ultimate_deadline,
        days_remaining=days_remaining,
        municipal_notice_required=municipal_notice_required,
        evidence_types=EVIDENCE_TYPES,
        evidence_checked=evidence_checked,
        evidence_score_pct=evidence_score_pct,
        evidence_score_label=evidence_score_label,
        ai_assessment_text=ai_assessment_text,
        report_date=report_date,
        brand_logo_data_uri=get_brand_logo_data_uri(),
    )

    html_string = render_template("assessment/pdf/assessment_report.html", **context)
    return WeasyHTML(string=html_string).write_pdf()
