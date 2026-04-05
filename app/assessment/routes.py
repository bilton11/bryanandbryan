from __future__ import annotations

from datetime import date, datetime

from flask import abort, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from app.assessment import assessment_bp
from app.extensions import db
from app.models.claim import Claim, ClaimStatus
from app.ontario_constants import (
    EXCLUDED_CLAIM_TYPES,
    REDIRECTED_CLAIM_TYPES,
    SMALL_CLAIMS_MONETARY_LIMIT,
    VALID_CLAIM_TYPES,
)

# ---------------------------------------------------------------------------
# Wizard configuration
# ---------------------------------------------------------------------------

WIZARD_STEPS: list[str] = [
    "dispute_type",
    "facts",
    "amount",
    "opposing_party",
    "summary",
]

STEP_LABELS: dict[str, str] = {
    "dispute_type": "Dispute Type",
    "facts": "Facts",
    "amount": "Amount",
    "opposing_party": "Opposing Party",
    "summary": "Summary",
}

_STEP_TEMPLATE: dict[str, str] = {
    "dispute_type": "assessment/steps/step_dispute_type.html",
    "facts": "assessment/steps/step_facts.html",
    "amount": "assessment/steps/step_amount.html",
    "opposing_party": "assessment/steps/step_opposing_party.html",
    "summary": "assessment/steps/step_summary.html",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_or_create_draft(user_id: int) -> Claim:
    """Return the user's existing DRAFT claim or create a new one."""
    claim = Claim.query.filter_by(user_id=user_id, status=ClaimStatus.DRAFT).first()
    if claim is None:
        claim = Claim(user_id=user_id, step_data={})
        db.session.add(claim)
        db.session.commit()
    return claim


def _next_step(current: str) -> str | None:
    """Return the step that follows current, or None if current is last."""
    idx = WIZARD_STEPS.index(current)
    if idx + 1 < len(WIZARD_STEPS):
        return WIZARD_STEPS[idx + 1]
    return None


def _prev_step(current: str) -> str | None:
    """Return the step before current, or None if current is first."""
    idx = WIZARD_STEPS.index(current)
    if idx > 0:
        return WIZARD_STEPS[idx - 1]
    return None


def _render_step(
    step_name: str,
    claim: Claim,
    errors: dict | None = None,
    is_htmx: bool = False,
) -> str:
    """Render a step partial template with common context."""
    template = _STEP_TEMPLATE[step_name]
    ctx = dict(
        claim=claim,
        step_name=step_name,
        wizard_steps=WIZARD_STEPS,
        step_labels=STEP_LABELS,
        errors=errors or {},
        valid_claim_types=VALID_CLAIM_TYPES,
        monetary_limit=SMALL_CLAIMS_MONETARY_LIMIT,
        excluded_claim_types=EXCLUDED_CLAIM_TYPES,
        redirected_claim_types=REDIRECTED_CLAIM_TYPES,
        today=date.today().isoformat(),
    )
    if is_htmx:
        return render_template(template, **ctx)
    # Non-HTMX: wrap in shell
    return render_template(
        "assessment/wizard_shell.html",
        initial_step_template=template,
        **ctx,
    )


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------


def _validate_dispute_type(form_data: dict) -> dict:
    """Return error dict (empty = valid). Both excluded and redirected are hard stops."""
    errors: dict[str, str] = {}
    valid_values = [v["value"] for v in VALID_CLAIM_TYPES]
    claim_type = form_data.get("claim_type", "").strip()

    if not claim_type:
        errors["claim_type"] = "Please select a claim type to continue."
        return errors

    if claim_type not in valid_values:
        errors["claim_type"] = "Please select a valid claim type."
        return errors

    if claim_type in EXCLUDED_CLAIM_TYPES:
        errors["claim_type"] = (
            "This type of claim cannot be filed in Ontario Small Claims Court. "
            "Small Claims Court handles civil disputes for money or personal property "
            "up to $50,000. Please select a different claim type or consult a lawyer."
        )
        errors["excluded"] = "true"
        return errors

    if claim_type in REDIRECTED_CLAIM_TYPES:
        errors["claim_type"] = REDIRECTED_CLAIM_TYPES[claim_type]
        errors["redirected"] = "true"
        return errors

    return errors


def _validate_facts(form_data: dict) -> dict:
    errors: dict[str, str] = {}

    description = form_data.get("description", "").strip()
    if not description:
        errors["description"] = "Please describe what happened."
    elif len(description) < 20:
        errors["description"] = "Please provide a more detailed description (at least 20 characters)."

    incident_date_str = form_data.get("incident_date", "").strip()
    if not incident_date_str:
        errors["incident_date"] = "Please enter the date the incident occurred."
    else:
        try:
            incident_date = date.fromisoformat(incident_date_str)
            if incident_date > date.today():
                errors["incident_date"] = "The incident date cannot be in the future."
        except ValueError:
            errors["incident_date"] = "Please enter a valid date (YYYY-MM-DD)."

    return errors


def _validate_amount(form_data: dict) -> dict:
    errors: dict[str, str] = {}

    amount_str = form_data.get("amount", "").strip()
    if not amount_str:
        errors["amount"] = "Please enter the amount you are claiming."
        return errors

    try:
        amount = int(amount_str)
    except ValueError:
        errors["amount"] = "Please enter a whole dollar amount (no decimals)."
        return errors

    if amount <= 0:
        errors["amount"] = "The claim amount must be greater than zero."
    elif amount > SMALL_CLAIMS_MONETARY_LIMIT:
        errors["amount"] = (
            f"Ontario Small Claims Court can only hear claims up to "
            f"${SMALL_CLAIMS_MONETARY_LIMIT:,}. Your amount of ${amount:,} exceeds "
            f"this limit. You may need to file in the Superior Court of Justice."
        )
        errors["jurisdiction_exceeded"] = "true"

    return errors


def _validate_opposing_party(form_data: dict) -> dict:
    errors: dict[str, str] = {}

    party_name = form_data.get("party_name", "").strip()
    if not party_name:
        errors["party_name"] = "Please enter the opposing party's name."
    elif len(party_name) < 2:
        errors["party_name"] = "Please enter the full name of the opposing party."

    party_type = form_data.get("party_type", "").strip()
    if not party_type:
        errors["party_type"] = "Please select whether the opposing party is an individual or business."
    elif party_type not in ("individual", "business"):
        errors["party_type"] = "Please select a valid party type."

    return errors


_VALIDATORS = {
    "dispute_type": _validate_dispute_type,
    "facts": _validate_facts,
    "amount": _validate_amount,
    "opposing_party": _validate_opposing_party,
    "summary": lambda _: {},  # read-only — no validation
}


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@assessment_bp.route("/assess")
@login_required
def wizard_entry():
    """GET /assess — entry point; get or create draft, render wizard at current step."""
    claim = _get_or_create_draft(current_user.id)
    # Ensure current_step is valid
    if claim.current_step not in WIZARD_STEPS:
        claim.current_step = WIZARD_STEPS[0]
        db.session.commit()
    return _render_step(claim.current_step, claim, is_htmx=False)


@assessment_bp.route("/assess/step/<step_name>", methods=["GET", "POST"])
@login_required
def wizard_step(step_name: str):
    """GET+POST /assess/step/<step_name> — render or advance a wizard step."""
    if step_name not in WIZARD_STEPS:
        abort(404)

    claim = Claim.query.filter_by(
        user_id=current_user.id, status=ClaimStatus.DRAFT
    ).first()
    if claim is None:
        # No draft exists — redirect to entry to create one
        return redirect(url_for("assessment.wizard_entry"))

    is_htmx = request.headers.get("HX-Request") == "true"

    if request.method == "POST":
        form_data = request.form.to_dict()
        errors = _VALIDATORS[step_name](form_data)

        if errors:
            # Re-render the current step with errors
            return _render_step(step_name, claim, errors=errors, is_htmx=is_htmx)

        # Persist step data
        if claim.step_data is None:
            claim.step_data = {}
        claim.step_data[step_name] = form_data

        # Advance current_step to next (do not go backwards)
        next_step = _next_step(step_name)
        if next_step is not None:
            # Only advance if we are on the current or a previous step
            current_idx = WIZARD_STEPS.index(claim.current_step) if claim.current_step in WIZARD_STEPS else 0
            this_idx = WIZARD_STEPS.index(step_name)
            if this_idx >= current_idx:
                claim.current_step = next_step
        else:
            # Last step (summary) — mark assessed
            claim.status = ClaimStatus.ASSESSED
            claim.current_step = "complete"

        db.session.commit()

        if next_step is None:
            # Assessment complete — redirect to a completion page (plan 02-02)
            if is_htmx:
                from flask import make_response
                resp = make_response()
                resp.headers["HX-Redirect"] = url_for("assessment.wizard_entry")
                return resp
            return redirect(url_for("assessment.wizard_entry"))

        return _render_step(next_step, claim, is_htmx=is_htmx)

    # GET
    return _render_step(step_name, claim, is_htmx=is_htmx)


@assessment_bp.route("/assess/back/<step_name>", methods=["POST"])
@login_required
def wizard_back(step_name: str):
    """POST /assess/back/<step_name> — navigate back to previous step."""
    if step_name not in WIZARD_STEPS:
        abort(404)

    claim = Claim.query.filter_by(
        user_id=current_user.id, status=ClaimStatus.DRAFT
    ).first()
    if claim is None:
        return redirect(url_for("assessment.wizard_entry"))

    prev = _prev_step(step_name)
    if prev is None:
        prev = WIZARD_STEPS[0]

    claim.current_step = prev
    db.session.commit()

    is_htmx = request.headers.get("HX-Request") == "true"
    return _render_step(prev, claim, is_htmx=is_htmx)
