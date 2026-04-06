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

    return {
        "letter_date": date.today().strftime("%B %d, %Y"),
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


def render_document_html(document, input_data_override: dict | None = None) -> str:
    """
    Render a document to HTML string using the appropriate Jinja2 template.

    Dispatches based on document.doc_type. Returns rendered HTML.
    FORM_7A and FORM_9A are not yet implemented (plan 03-02).
    """
    input_data = input_data_override if input_data_override is not None else (document.input_data or {})

    if document.doc_type == DocumentType.DEMAND_LETTER:
        context = _build_demand_letter_context(input_data)
        return render_template("documents/pdf/demand_letter.html", **context)

    if document.doc_type == DocumentType.FORM_7A:
        raise NotImplementedError("Form 7A template not yet implemented — coming in plan 03-02.")

    if document.doc_type == DocumentType.FORM_9A:
        raise NotImplementedError("Form 9A template not yet implemented — coming in plan 03-02.")

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
