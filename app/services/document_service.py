"""
Document Generation Service — Bryan and Bryan

Renders document templates to HTML and then to PDF via WeasyPrint. The pipeline
is: input_data dict -> Jinja2 template -> HTML string -> PDF bytes.

Per-page disclaimer is handled by CSS running()/element() in each PDF template.
"""
from __future__ import annotations

from datetime import date

from flask import render_template
from flask_weasyprint import HTML as WeasyHTML

from app.models.document import DocumentType


def _build_demand_letter_context(input_data: dict) -> dict:
    """Build template context dict for the Demand Letter template."""
    from app.ontario_constants import FILING_FEE_INFREQUENT_CLAIMANT, format_fee
    from app.services.pdf_service import get_brand_logo_data_uri

    return {
        "letter_date": date.today().strftime("%B %d, %Y"),
        "brand_logo_data_uri": get_brand_logo_data_uri(),
        "opposing_party_name": input_data.get("opposing_party_name", ""),
        "opposing_party_address_street": input_data.get("opposing_party_address_street", ""),
        "opposing_party_address_city": input_data.get("opposing_party_address_city", ""),
        "opposing_party_address_province": input_data.get("opposing_party_address_province", "ON"),
        "opposing_party_address_postal": input_data.get("opposing_party_address_postal", ""),
        "claim_type": input_data.get("claim_type", ""),
        "facts_description": input_data.get("facts_description", ""),
        "incident_date": input_data.get("incident_date", ""),
        "demand_amount": input_data.get("demand_amount", input_data.get("amount", "")),
        "deadline_days": input_data.get("demand_deadline_days", "30"),
        "payment_method": input_data.get("payment_method", ""),
        "sender_name": input_data.get("sender_name", ""),
        "sender_address_street": input_data.get("sender_address_street", ""),
        "sender_address_city": input_data.get("sender_address_city", ""),
        "sender_address_province": input_data.get("sender_address_province", "ON"),
        "sender_address_postal": input_data.get("sender_address_postal", ""),
        "sender_phone": input_data.get("sender_phone", ""),
        "sender_email": input_data.get("sender_email", ""),
        "filing_fee": format_fee(FILING_FEE_INFREQUENT_CLAIMANT),
    }


def _stitch_guided_narrative_7a(input_data: dict) -> str:
    """
    Stitch Form 7A guided sub-question answers into flowing prose.

    If narrative_mode is 'freeform', returns the freeform text directly.
    Otherwise, composes paragraphs from the four sub-questions.
    """
    if input_data.get("narrative_mode") == "freeform":
        return input_data.get("narrative_freeform", "")

    parts: list[str] = []

    what_happened = (input_data.get("narrative_what_happened") or "").strip()
    when_where = (input_data.get("narrative_when_where") or "").strip()
    damages = (input_data.get("narrative_damages") or "").strip()
    resolution = (input_data.get("narrative_resolution") or "").strip()

    if what_happened:
        parts.append(what_happened)
    if when_where:
        # Weave the date/location into a sentence if it looks like raw data
        if not when_where.lower().startswith("this") and not when_where.lower().startswith("the"):
            parts.append(f"This occurred on or about {when_where}.")
        else:
            parts.append(when_where)
    if damages:
        if not damages.lower().startswith("as"):
            parts.append(f"As a result of the foregoing, I suffered the following damages and losses: {damages}")
        else:
            parts.append(damages)
    if resolution:
        if not resolution.lower().startswith("i") and not resolution.lower().startswith("the"):
            parts.append(f"I seek the following resolution: {resolution}")
        else:
            parts.append(resolution)

    # Fall back to legacy facts_description if no guided answers provided
    if not parts:
        return input_data.get("facts_description", "")

    return "\n\n".join(parts)


def _stitch_guided_narrative_9a(input_data: dict) -> str:
    """
    Stitch Form 9A guided sub-question answers into flowing prose.

    If narrative_mode is 'freeform', returns the freeform text directly.
    """
    if input_data.get("narrative_mode") == "freeform":
        return input_data.get("narrative_freeform", "")

    parts: list[str] = []

    response = (input_data.get("narrative_response") or "").strip()
    supporting_facts = (input_data.get("narrative_supporting_facts") or "").strip()
    counterclaim = (input_data.get("narrative_counterclaim") or "").strip()

    if response:
        parts.append(response)
    if supporting_facts:
        if not supporting_facts.lower().startswith("the") and not supporting_facts.lower().startswith("i"):
            parts.append(f"The following facts support my position: {supporting_facts}")
        else:
            parts.append(supporting_facts)
    if counterclaim:
        parts.append(f"Counterclaim: {counterclaim}")

    if not parts:
        return input_data.get("facts_description", "")

    return "\n\n".join(parts)


def _build_form_7a_context(input_data: dict) -> dict:
    """Build template context dict for Form 7A (Plaintiff's Claim)."""
    from app.ontario_constants import FORM_7A_VERSION

    narrative_text = _stitch_guided_narrative_7a(input_data)

    return {
        "today": date.today().strftime("%B %d, %Y"),
        "form_version": FORM_7A_VERSION,
        "court_location": input_data.get("court_location", ""),
        "claim_number": input_data.get("claim_number", ""),
        # Plaintiff (sender / user filing the claim)
        "plaintiff_name": input_data.get("plaintiff_name", input_data.get("sender_name", "")),
        "sender_name": input_data.get("sender_name", ""),
        "sender_address_street": input_data.get("sender_address_street", ""),
        "sender_address_city": input_data.get("sender_address_city", ""),
        "sender_address_province": input_data.get("sender_address_province", "ON"),
        "sender_address_postal": input_data.get("sender_address_postal", ""),
        "sender_phone": input_data.get("sender_phone", ""),
        "sender_fax": input_data.get("sender_fax", ""),
        "sender_email": input_data.get("sender_email", ""),
        # Representative
        "representative_name": input_data.get("representative_name", ""),
        "representative_address": input_data.get("representative_address", ""),
        "lsuc_number": input_data.get("lsuc_number", ""),
        # Defendant (opposing party)
        "opposing_party_name": input_data.get("opposing_party_name", ""),
        "opposing_party_address_street": input_data.get("opposing_party_address_street", ""),
        "opposing_party_address_city": input_data.get("opposing_party_address_city", ""),
        "opposing_party_address_province": input_data.get("opposing_party_address_province", "ON"),
        "opposing_party_address_postal": input_data.get("opposing_party_address_postal", ""),
        "opposing_party_phone": input_data.get("opposing_party_phone", ""),
        "opposing_party_email": input_data.get("opposing_party_email", ""),
        # Claim amounts
        "claim_amount": input_data.get("claim_amount", input_data.get("demand_amount", input_data.get("amount", ""))),
        "interest_rate": input_data.get("interest_rate", ""),
        # Narrative
        "narrative_text": narrative_text,
    }


def _build_form_9a_context(input_data: dict) -> dict:
    """Build template context dict for Form 9A (Defence)."""
    from app.ontario_constants import FORM_9A_VERSION

    narrative_text = _stitch_guided_narrative_9a(input_data)

    return {
        "today": date.today().strftime("%B %d, %Y"),
        "form_version": FORM_9A_VERSION,
        "court_location": input_data.get("court_location", ""),
        "claim_number": input_data.get("claim_number", ""),
        # Plaintiff (the person who filed the original claim against the user)
        "plaintiff_name": input_data.get("plaintiff_name", input_data.get("opposing_party_name", "")),
        "plaintiff_address": input_data.get("plaintiff_address", ""),
        # Defendant (the user filing the defence)
        "defendant_name": input_data.get("defendant_name", input_data.get("sender_name", "")),
        "sender_name": input_data.get("sender_name", ""),
        "sender_address_street": input_data.get("sender_address_street", ""),
        "sender_address_city": input_data.get("sender_address_city", ""),
        "sender_address_province": input_data.get("sender_address_province", "ON"),
        "sender_address_postal": input_data.get("sender_address_postal", ""),
        "sender_phone": input_data.get("sender_phone", ""),
        "sender_email": input_data.get("sender_email", ""),
        # Representative
        "representative_name": input_data.get("representative_name", ""),
        "representative_address": input_data.get("representative_address", ""),
        "lsuc_number": input_data.get("lsuc_number", ""),
        # Defence response type
        "defence_response": input_data.get("defence_response", "dispute"),
        "admit_amount": input_data.get("admit_amount", ""),
        "admit_payment_start": input_data.get("admit_payment_start", ""),
        "partial_amount": input_data.get("partial_amount", ""),
        # Narrative
        "narrative_text": narrative_text,
    }


def render_document_html(document, input_data_override: dict | None = None) -> str:
    """
    Render a document to HTML string using the appropriate Jinja2 template.

    Dispatches based on document.doc_type. Returns rendered HTML.
    """
    input_data = input_data_override if input_data_override is not None else (document.input_data or {})

    if document.doc_type == DocumentType.DEMAND_LETTER:
        context = _build_demand_letter_context(input_data)
        return render_template("documents/pdf/demand_letter.html", **context)

    if document.doc_type == DocumentType.FORM_7A:
        context = _build_form_7a_context(input_data)
        return render_template("documents/pdf/form_7a.html", **context)

    if document.doc_type == DocumentType.FORM_9A:
        context = _build_form_9a_context(input_data)
        return render_template("documents/pdf/form_9a.html", **context)

    raise ValueError(f"Unknown doc_type: {document.doc_type!r}")


def render_document_pdf(document, input_data_override: dict | None = None) -> bytes:
    """
    Render a document to PDF bytes via WeasyPrint.

    Calls render_document_html to get the HTML string, then converts to PDF.
    Pass input_data_override to render from a version snapshot instead of
    document.input_data (used for historical version re-downloads).
    """
    html_string = render_document_html(document, input_data_override=input_data_override)
    return WeasyHTML(string=html_string).write_pdf()


def render_version_pdf(version) -> bytes:
    """
    Convenience wrapper that re-generates the PDF from a DocumentVersion's
    input_data_snapshot. Uses the parent document for doc_type routing.
    """
    return render_document_pdf(
        version.document,
        input_data_override=version.input_data_snapshot or {},
    )
