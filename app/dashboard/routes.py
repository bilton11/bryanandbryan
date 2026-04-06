from __future__ import annotations

from datetime import date

from flask import abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required
from sqlalchemy.orm import selectinload

from app.dashboard import dashboard_bp
from app.extensions import db
from app.models.claim import Claim
from app.models.document import Document
from app.services.deadline_service import build_claim_deadlines
from app.services.escalation_service import get_escalation_reasons, is_escalation_required


@dashboard_bp.route("/")
@login_required
def index():
    """GET / — user dashboard showing all claims, documents, and deadlines."""
    claims = db.session.execute(
        db.select(Claim)
        .where(Claim.user_id == current_user.id)
        .options(selectinload(Claim.documents))
        .order_by(Claim.updated_at.desc())
    ).scalars().all()

    documents = db.session.execute(
        db.select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.updated_at.desc())
    ).scalars().all()

    claim_deadlines = {c.id: build_claim_deadlines(c) for c in claims}

    has_overdue = any(
        bool(dl.overdue_items) for dl in claim_deadlines.values()
    )

    claim_escalations = {
        c.id: {
            "required": is_escalation_required(c),
            "reasons": get_escalation_reasons(c),
        }
        for c in claims
    }

    return render_template(
        "dashboard/index.html",
        claims=claims,
        documents=documents,
        claim_deadlines=claim_deadlines,
        has_overdue=has_overdue,
        today=date.today(),
        claim_escalations=claim_escalations,
    )


@dashboard_bp.route("/dashboard/dates/<int:claim_id>", methods=["POST"])
@login_required
def save_dates(claim_id: int):
    """POST /dashboard/dates/<claim_id> — save user-entered service and settlement dates."""
    claim = db.session.get(Claim, claim_id)
    if claim is None or claim.user_id != current_user.id:
        abort(404)

    claim_dates: dict[str, str] = {}

    date_parse_error = False

    raw_service = request.form.get("service_date", "").strip()
    if raw_service:
        try:
            date.fromisoformat(raw_service)
            claim_dates["service_date"] = raw_service
        except ValueError:
            date_parse_error = True

    raw_settlement = request.form.get("settlement_conference_date", "").strip()
    if raw_settlement:
        try:
            date.fromisoformat(raw_settlement)
            claim_dates["settlement_conference_date"] = raw_settlement
        except ValueError:
            date_parse_error = True

    if date_parse_error:
        # WCAG 3.3.1 Error Identification — inform the user what went wrong
        flash("One or more dates were not in a valid format. Please use the date picker or YYYY-MM-DD format.", "error")

    # CRITICAL: full reassignment — MutableDict only tracks top-level key changes
    step_data = dict(claim.step_data or {})
    step_data["claim_dates"] = claim_dates
    claim.step_data = step_data

    db.session.commit()

    deadlines = build_claim_deadlines(claim)
    today = date.today()

    is_htmx = request.headers.get("HX-Request") == "true"
    if is_htmx:
        return render_template(
            "dashboard/partials/deadline_timeline.html",
            deadlines=deadlines,
            claim=claim,
            today=today,
        )

    return redirect(url_for("dashboard.index"))
