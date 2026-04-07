from __future__ import annotations

from datetime import date, datetime

from flask import abort, make_response, redirect, render_template, request, url_for
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
from app.services.limitation_service import LimitationResult, LimitationStatus, calculate_limitation

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
# Evidence inventory configuration
# ---------------------------------------------------------------------------

EVIDENCE_TYPES: list[dict] = [
    {"key": "written_contract", "label": "Written contract or agreement", "weight": 3},
    {"key": "receipts", "label": "Receipts or proof of payment", "weight": 2},
    {"key": "photos", "label": "Photos or videos of damage/issue", "weight": 2},
    {"key": "correspondence", "label": "Emails, texts, or letters with the other party", "weight": 2},
    {"key": "witness", "label": "Witness who can confirm your account", "weight": 2},
    {"key": "expert_report", "label": "Expert report or professional estimate", "weight": 1},
    {"key": "police_report", "label": "Police report (if applicable)", "weight": 1},
    {"key": "other_docs", "label": "Other supporting documents", "weight": 1},
]

EVIDENCE_SCORE_LABELS = [
    (70, "Strong evidence base"),
    (40, "Moderate — consider gathering more evidence"),
    (0, "Limited evidence — your case may be harder to prove"),
]

_EVIDENCE_TOTAL_WEIGHT = sum(e["weight"] for e in EVIDENCE_TYPES)


def _score_evidence(checked_keys: list[str]) -> tuple[int, str]:
    """Return (score_pct, label) for the given checked evidence keys."""
    checked_weight = sum(
        e["weight"] for e in EVIDENCE_TYPES if e["key"] in checked_keys
    )
    score_pct = round(checked_weight / _EVIDENCE_TOTAL_WEIGHT * 100) if _EVIDENCE_TOTAL_WEIGHT else 0
    label = next(lbl for threshold, lbl in EVIDENCE_SCORE_LABELS if score_pct >= threshold)
    return score_pct, label


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _calculate_and_store_limitation(claim: Claim) -> LimitationResult | None:
    """
    Extract facts data from claim, run the limitation calculator, and store
    the serialised result back into claim.step_data["limitation"].

    Returns the LimitationResult on success, or None if facts data is missing.
    The caller must call db.session.commit() after this to persist the update.
    """
    facts = (claim.step_data or {}).get("facts", {})
    if not facts:
        return None

    incident_date_str = facts.get("incident_date", "")
    if not incident_date_str:
        return None

    try:
        incident_date = date.fromisoformat(incident_date_str)
    except ValueError:
        return None

    # Discovery date — default to incident date if not provided (conservative)
    discovery_date_str = facts.get("discovery_date", "")
    discovery_date = (
        date.fromisoformat(discovery_date_str)
        if discovery_date_str
        else incident_date
    )

    is_minor = facts.get("is_minor") == "1"
    is_municipal_defendant = facts.get("is_municipal_defendant") == "1"

    minor_dob: date | None = None
    minor_dob_str = facts.get("minor_dob", "")
    if is_minor and minor_dob_str:
        try:
            minor_dob = date.fromisoformat(minor_dob_str)
        except ValueError:
            pass

    result = calculate_limitation(
        discovery_date=discovery_date,
        incident_date=incident_date,
        is_minor=is_minor,
        minor_dob=minor_dob,
        is_incapacitated=False,
        incapacity_end_date=None,
        is_municipal_defendant=is_municipal_defendant,
    )

    # Serialise for JSONB storage (dates → ISO strings)
    limitation_dict = {
        "status": result.status.value,
        "basic_deadline": result.basic_deadline.isoformat() if result.basic_deadline else None,
        "ultimate_deadline": result.ultimate_deadline.isoformat() if result.ultimate_deadline else None,
        "days_remaining": result.days_remaining,
        "warning_message": result.warning_message,
        "tolling_applied": result.tolling_applied,
        "municipal_notice_required": result.municipal_notice_required,
    }

    step_data = dict(claim.step_data or {})
    step_data["limitation"] = limitation_dict
    claim.step_data = step_data

    return result


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

    # Evidence score for summary step
    evidence_keys: list[str] = list((claim.step_data or {}).get("evidence", {}).get("checked", []))
    evidence_score_pct, evidence_score_label = _score_evidence(evidence_keys)

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
        # Evidence inventory
        evidence_types=EVIDENCE_TYPES,
        evidence_checked=evidence_keys,
        evidence_score_pct=evidence_score_pct,
        evidence_score_label=evidence_score_label,
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

        # Mutate via a fresh dict so SQLAlchemy's MutableDict tracking fires
        step_data = dict(claim.step_data)
        step_data[step_name] = form_data
        claim.step_data = step_data

        # After facts step: calculate limitation period and cache result
        if step_name == "facts":
            _calculate_and_store_limitation(claim)

        # Advance current_step to next (do not go backwards)
        next_step = _next_step(step_name)
        if next_step is not None:
            # Only advance if we are on the current or a previous step
            current_idx = WIZARD_STEPS.index(claim.current_step) if claim.current_step in WIZARD_STEPS else 0
            this_idx = WIZARD_STEPS.index(step_name)
            if this_idx >= current_idx:
                claim.current_step = next_step
        else:
            # Last step (summary) — keep as DRAFT, finalize route handles ASSESSED transition
            claim.current_step = "complete"

        db.session.commit()

        if next_step is None:
            # Summary step submitted — redirect to finalize to trigger AI assessment
            finalize_url = url_for("assessment.finalize")
            if is_htmx:
                resp = make_response()
                resp.headers["HX-Redirect"] = finalize_url
                return resp
            return redirect(finalize_url)

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


@assessment_bp.route("/assess/evidence", methods=["POST"])
@login_required
def save_evidence():
    """
    POST /assess/evidence — save evidence checklist selections and return updated partial.

    Called via HTMX from the evidence_checklist partial on the summary step.
    Accepts a multiselect of checked evidence keys, computes completeness score,
    persists to claim.step_data["evidence"], and returns the evidence_checklist partial.
    """
    claim = Claim.query.filter_by(
        user_id=current_user.id, status=ClaimStatus.DRAFT
    ).first()
    if claim is None:
        # Also check ASSESSED status — user may have just completed the wizard
        claim = Claim.query.filter_by(
            user_id=current_user.id, status=ClaimStatus.ASSESSED
        ).order_by(Claim.id.desc()).first()
    if claim is None:
        abort(404)

    # form.getlist returns all checked values for multi-checkbox fields
    checked_keys: list[str] = request.form.getlist("evidence_items")
    # Validate against known keys to prevent arbitrary data injection
    valid_keys = {e["key"] for e in EVIDENCE_TYPES}
    checked_keys = [k for k in checked_keys if k in valid_keys]

    score_pct, score_label = _score_evidence(checked_keys)

    step_data = dict(claim.step_data or {})
    step_data["evidence"] = {"checked": checked_keys}
    claim.step_data = step_data
    db.session.commit()

    return render_template(
        "assessment/partials/evidence_checklist.html",
        evidence_types=EVIDENCE_TYPES,
        evidence_checked=checked_keys,
        evidence_score_pct=score_pct,
        evidence_score_label=score_label,
    )


# ---------------------------------------------------------------------------
# Finalize, Results, and PDF Download Routes
# ---------------------------------------------------------------------------


@assessment_bp.route("/assess/finalize", methods=["GET", "POST"])
@login_required
def finalize():
    """
    GET|POST /assess/finalize — transition claim from DRAFT to ASSESSED and
    generate the AI case strength assessment.

    Called from the "Complete Assessment" button on the summary step.
    Accepts GET because HX-Redirect and 302 redirects both result in GET.
    Idempotent: if claim is already ASSESSED, skips AI call and redirects.
    """
    from app.services.assessment_service import get_case_strength_assessment

    # Check for already-assessed claim first (idempotent)
    assessed = Claim.query.filter_by(
        user_id=current_user.id, status=ClaimStatus.ASSESSED
    ).first()
    if assessed is not None:
        return redirect(url_for("assessment.results", claim_id=assessed.id))

    claim = Claim.query.filter_by(
        user_id=current_user.id, status=ClaimStatus.DRAFT
    ).first()
    if claim is None:
        return redirect(url_for("assessment.wizard_entry"))

    # Transition to ASSESSED
    claim.status = ClaimStatus.ASSESSED
    claim.current_step = "complete"
    db.session.commit()

    # 1. Polish the claimant's narrative into a clean factual statement.
    #    Stores result in claim.step_data["facts"]["polished_description"];
    #    falls back to the original on any failure.
    from app.services.assessment_service import polish_facts_description
    polish_facts_description(claim)

    # 2. Generate AI strength assessment (stores result in claim.ai_assessment).
    #    Gracefully degrades if API key absent or AI_ASSESSMENT_ENABLED=false.
    get_case_strength_assessment(claim)

    return redirect(url_for("assessment.results", claim_id=claim.id))


@assessment_bp.route("/assess/<int:claim_id>/results")
@login_required
def results(claim_id: int):
    """
    GET /assess/<claim_id>/results — display the completed assessment results.

    Shows all assessment data: claim summary, limitation period, evidence
    inventory, and AI case strength indicator. Provides a "Download PDF" link.
    """
    claim = Claim.query.get_or_404(claim_id)

    # Ownership check
    if claim.user_id != current_user.id:
        abort(404)

    # Status check — must be ASSESSED to view results
    if claim.status != ClaimStatus.ASSESSED:
        return redirect(url_for("assessment.wizard_entry"))

    step_data = claim.step_data or {}

    # Claim type label
    dispute = step_data.get("dispute_type", {})
    claim_type_value = dispute.get("claim_type", "")
    claim_type_label = claim_type_value
    for ct in VALID_CLAIM_TYPES:
        if ct["value"] == claim_type_value:
            claim_type_label = ct["label"]
            break

    # Evidence score
    evidence_keys: list[str] = list(step_data.get("evidence", {}).get("checked", []))
    evidence_score_pct, evidence_score_label = _score_evidence(evidence_keys)

    # Limitation result from cached step_data
    limitation = step_data.get("limitation", {})

    return render_template(
        "assessment/results.html",
        claim=claim,
        claim_type_label=claim_type_label,
        evidence_types=EVIDENCE_TYPES,
        evidence_checked=evidence_keys,
        evidence_score_pct=evidence_score_pct,
        evidence_score_label=evidence_score_label,
        limitation=limitation,
        valid_claim_types=VALID_CLAIM_TYPES,
        monetary_limit=SMALL_CLAIMS_MONETARY_LIMIT,
    )


@assessment_bp.route("/assess/<int:claim_id>/pdf")
@login_required
def download_pdf(claim_id: int):
    """
    GET /assess/<claim_id>/pdf — serve the assessment report as a PDF download.

    Ownership and status checks are applied before rendering. The PDF is
    generated on demand by WeasyPrint and returned as an attachment.
    """
    from app.services.pdf_service import render_assessment_pdf

    claim = Claim.query.get_or_404(claim_id)

    # Ownership check
    if claim.user_id != current_user.id:
        abort(404)

    # Status check — PDF only available for assessed claims
    if claim.status != ClaimStatus.ASSESSED:
        return redirect(url_for("assessment.wizard_entry"))

    pdf_bytes = render_assessment_pdf(claim)

    response = make_response(pdf_bytes)
    response.headers["Content-Type"] = "application/pdf"
    response.headers["Content-Disposition"] = f'attachment; filename="assessment-{claim_id}.pdf"'
    return response
