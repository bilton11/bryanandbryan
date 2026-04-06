from flask import jsonify, render_template
from flask_login import login_required

from app.main import main_bp


@main_bp.route("/")
@login_required
def index():
    return render_template("main/index.html")


@main_bp.route("/health")
def health():
    return jsonify({"status": "healthy"}), 200


@main_bp.route("/guide")
def guide():
    """GET /guide — plain-language Small Claims Court process guide. No login required."""
    from app.ontario_constants import (
        DEFENCE_DEADLINE_DAYS,
        DEFENCE_FILING_FEE,
        FILING_FEE_FREQUENT_CLAIMANT,
        FILING_FEE_INFREQUENT_CLAIMANT,
        GUIDE_STAGES,
        SMALL_CLAIMS_MONETARY_LIMIT,
        format_fee,
    )

    return render_template(
        "guide/index.html",
        guide_stages=GUIDE_STAGES,
        monetary_limit=SMALL_CLAIMS_MONETARY_LIMIT,
        monetary_limit_formatted=f"${SMALL_CLAIMS_MONETARY_LIMIT:,}",
        filing_fee_infrequent=format_fee(FILING_FEE_INFREQUENT_CLAIMANT),
        filing_fee_frequent=format_fee(FILING_FEE_FREQUENT_CLAIMANT),
        defence_filing_fee=format_fee(DEFENCE_FILING_FEE),
        defence_deadline_days=DEFENCE_DEADLINE_DAYS,
    )
