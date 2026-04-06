from __future__ import annotations

from datetime import date, datetime, timezone

from flask import abort, make_response, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.documents import documents_bp
from app.extensions import db
from app.models.claim import Claim, ClaimStatus
from app.models.document import Document, DocumentType, DocumentVersion
from app.ontario_constants import (
    CERTIFICATE_OF_JUDGMENT_FEE,
    DEFENCE_FILING_FEE,
    FEES_LAST_VERIFIED,
    FILING_FEE_FREQUENT_CLAIMANT,
    FILING_FEE_INFREQUENT_CLAIMANT,
    MOTION_FEE_FREQUENT,
    MOTION_FEE_INFREQUENT,
    WRIT_OF_DELIVERY_FEE,
    WRIT_OF_SEIZURE_FEE,
    format_fee,
)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

DOC_TYPE_LABELS: dict[str, str] = {
    DocumentType.DEMAND_LETTER.value: "Demand Letter",
    DocumentType.FORM_7A.value: "Form 7A — Plaintiff's Claim",
    DocumentType.FORM_9A.value: "Form 9A — Defence",
}

ONTARIO_COURT_LOCATIONS: list[str] = [
    "Toronto",
    "Ottawa",
    "Brampton",
    "Hamilton",
    "London",
    "Mississauga",
    "Newmarket",
    "Oshawa",
    "Barrie",
    "Windsor",
    "Kitchener",
    "St. Catharines",
    "Sudbury",
    "Kingston",
    "Thunder Bay",
    "Sault Ste. Marie",
    "Chatham",
    "Brantford",
    "Peterborough",
    "Belleville",
]

REPRESENTATIVE_TYPES: list[dict[str, str]] = [
    {"value": "self", "label": "Self (no representative)"},
    {"value": "lawyer", "label": "Lawyer"},
    {"value": "paralegal", "label": "Paralegal"},
    {"value": "agent", "label": "Agent"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _verify_document_ownership(doc_id: int) -> Document:
    """Return the document if it belongs to current_user, else abort(404)."""
    doc = db.session.get(Document, doc_id)
    if doc is None or doc.user_id != current_user.id:
        abort(404)
    return doc


def _auto_title(doc_type: DocumentType) -> str:
    """Generate a human-readable default title for a new document."""
    today = date.today().strftime("%Y-%m-%d")
    label = DOC_TYPE_LABELS.get(doc_type.value, doc_type.value)
    return f"{label} — {today}"


def _prepopulate_from_claim(claim: Claim, doc_type: str) -> dict:
    """
    Extract relevant fields from a claim's step_data to pre-populate input_data
    for the given document type. Returns a flat dict.
    """
    step_data = claim.step_data or {}
    facts = step_data.get("facts", {})
    amount_data = step_data.get("amount", {})
    dispute_data = step_data.get("dispute_type", {})
    opposing = step_data.get("opposing_party", {})

    base: dict = {
        "claim_type": dispute_data.get("claim_type", ""),
        "facts_description": facts.get("description", ""),
        "incident_date": facts.get("incident_date", ""),
        "amount": amount_data.get("amount", ""),
        "demand_amount": amount_data.get("amount", ""),
        "opposing_party_name": opposing.get("party_name", ""),
        "opposing_party_type": opposing.get("party_type", ""),
    }

    if doc_type == DocumentType.FORM_7A.value:
        # Also pull evidence data
        evidence = step_data.get("evidence", {})
        base["evidence_checked"] = evidence.get("checked", [])

    elif doc_type == DocumentType.FORM_9A.value:
        # In a defence context, the "opposing party" from the original assessment
        # becomes the plaintiff — swap perspective
        base["plaintiff_name"] = opposing.get("party_name", "")
        base["plaintiff_type"] = opposing.get("party_type", "")

    return base


def _next_version_number(document: Document) -> int:
    """Return the next version number for a document (max existing + 1, min 1)."""
    existing = [v.version_number for v in document.versions]
    return max(existing, default=0) + 1


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@documents_bp.route("/documents/")
@login_required
def index():
    """GET /documents/ — list all user's documents with latest version info."""
    documents = (
        Document.query.filter_by(user_id=current_user.id)
        .order_by(Document.updated_at.desc())
        .all()
    )

    # Fetch ASSESSED claims for the "generate from claim" section
    assessed_claims = (
        Claim.query.filter_by(user_id=current_user.id, status=ClaimStatus.ASSESSED)
        .order_by(Claim.updated_at.desc())
        .all()
    )

    return render_template(
        "documents/index.html",
        documents=documents,
        assessed_claims=assessed_claims,
        doc_type_labels=DOC_TYPE_LABELS,
        DocumentType=DocumentType,
    )


@documents_bp.route("/documents/new/<doc_type>")
@login_required
def new_document(doc_type: str):
    """GET /documents/new/<doc_type> — start a standalone document (no claim)."""
    # Validate doc_type
    valid_types = [dt.value for dt in DocumentType]
    if doc_type not in valid_types:
        abort(404)

    dt = DocumentType(doc_type)
    doc = Document(
        user_id=current_user.id,
        claim_id=None,
        doc_type=dt,
        title=_auto_title(dt),
        input_data={},
    )
    db.session.add(doc)
    db.session.commit()

    return redirect(url_for("documents.review", doc_id=doc.id))


@documents_bp.route("/documents/from-claim/<int:claim_id>/<doc_type>")
@login_required
def from_claim(claim_id: int, doc_type: str):
    """GET /documents/from-claim/<claim_id>/<doc_type> — start doc from assessed claim."""
    claim = db.session.get(Claim, claim_id)
    if claim is None or claim.user_id != current_user.id:
        abort(404)

    if claim.status != ClaimStatus.ASSESSED:
        # Not assessed yet — redirect to assessment wizard
        return redirect(url_for("assessment.wizard_entry"))

    valid_types = [dt.value for dt in DocumentType]
    if doc_type not in valid_types:
        abort(404)

    dt = DocumentType(doc_type)
    input_data = _prepopulate_from_claim(claim, doc_type)

    doc = Document(
        user_id=current_user.id,
        claim_id=claim_id,
        doc_type=dt,
        title=_auto_title(dt),
        input_data=input_data,
    )
    db.session.add(doc)
    db.session.commit()

    return redirect(url_for("documents.review", doc_id=doc.id))


@documents_bp.route("/documents/<int:doc_id>/review", methods=["GET", "POST"])
@login_required
def review(doc_id: int):
    """GET/POST /documents/<doc_id>/review — review and supplement document fields."""
    doc = _verify_document_ownership(doc_id)

    if request.method == "POST":
        form_data = request.form.to_dict()
        # Merge form data into existing input_data (preserving any pre-populated keys
        # not present in the form, e.g. evidence_checked from claim)
        merged = dict(doc.input_data or {})
        merged.update(form_data)
        doc.input_data = merged
        doc.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        return redirect(url_for("documents.preview", doc_id=doc.id))

    # GET — render the review form
    input_data = doc.input_data or {}
    return render_template(
        "documents/review.html",
        document=doc,
        input_data=input_data,
        court_locations=ONTARIO_COURT_LOCATIONS,
        representative_types=REPRESENTATIVE_TYPES,
        doc_type_labels=DOC_TYPE_LABELS,
        DocumentType=DocumentType,
    )


@documents_bp.route("/documents/<int:doc_id>/preview")
@login_required
def preview(doc_id: int):
    """GET /documents/<doc_id>/preview — HTML preview of the rendered document."""
    from app.services.document_service import render_document_html

    doc = _verify_document_ownership(doc_id)

    html_content = render_document_html(doc)

    return render_template(
        "documents/preview.html",
        document=doc,
        html_content=html_content,
        doc_type_labels=DOC_TYPE_LABELS,
    )


@documents_bp.route("/documents/<int:doc_id>/download")
@login_required
def download(doc_id: int):
    """GET /documents/<doc_id>/download — generate PDF, create version, return as download."""
    from app.services.document_service import render_document_pdf

    doc = _verify_document_ownership(doc_id)

    # Create new version snapshot before generating PDF
    version_number = _next_version_number(doc)
    version = DocumentVersion(
        document_id=doc.id,
        version_number=version_number,
        input_data_snapshot=dict(doc.input_data or {}),
        generated_at=datetime.now(timezone.utc),
    )
    db.session.add(version)
    doc.updated_at = datetime.now(timezone.utc)
    db.session.commit()

    pdf_bytes = render_document_pdf(doc)

    safe_title = doc.doc_type.value.replace("_", "-")
    filename = f"{safe_title}-v{version_number}.pdf"

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@documents_bp.route("/documents/<int:doc_id>/versions")
@login_required
def versions(doc_id: int):
    """GET /documents/<doc_id>/versions — list all versions of a document."""
    doc = _verify_document_ownership(doc_id)

    # Versions are ordered by version_number desc via relationship config
    all_versions = doc.versions

    return render_template(
        "documents/versions.html",
        document=doc,
        versions=all_versions,
        doc_type_labels=DOC_TYPE_LABELS,
    )


@documents_bp.route("/documents/<int:doc_id>/versions/<int:version_id>/download")
@login_required
def download_version(doc_id: int, version_id: int):
    """GET /documents/<doc_id>/versions/<version_id>/download — re-generate PDF from snapshot."""
    from app.services.document_service import render_version_pdf

    doc = _verify_document_ownership(doc_id)

    version = db.session.get(DocumentVersion, version_id)
    if version is None or version.document_id != doc.id:
        abort(404)

    pdf_bytes = render_version_pdf(version)

    safe_title = doc.doc_type.value.replace("_", "-")
    filename = f"{safe_title}-v{version.version_number}.pdf"

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


@documents_bp.route("/fees")
def fees():
    """GET /fees — standalone filing fee page. No login required."""
    fee_table = [
        {
            "label": "Filing a Claim (infrequent claimant — fewer than 10 claims/year)",
            "amount": format_fee(FILING_FEE_INFREQUENT_CLAIMANT),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Filing a Claim (frequent claimant — 10 or more claims/year)",
            "amount": format_fee(FILING_FEE_FREQUENT_CLAIMANT),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Filing a Defence",
            "amount": format_fee(DEFENCE_FILING_FEE),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Filing a Motion (infrequent claimant)",
            "amount": format_fee(MOTION_FEE_INFREQUENT),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Filing a Motion (frequent claimant)",
            "amount": format_fee(MOTION_FEE_FREQUENT),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Certificate of Judgment",
            "amount": format_fee(CERTIFICATE_OF_JUDGMENT_FEE),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Writ of Delivery",
            "amount": format_fee(WRIT_OF_DELIVERY_FEE),
            "source": "O. Reg. 432/93, Table",
        },
        {
            "label": "Writ of Seizure and Sale",
            "amount": format_fee(WRIT_OF_SEIZURE_FEE),
            "source": "O. Reg. 432/93, Table",
        },
    ]

    return render_template(
        "documents/fees.html",
        fee_table=fee_table,
        fees_last_verified=FEES_LAST_VERIFIED,
    )
