from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from dateutil.relativedelta import relativedelta

from app.ontario_constants import DEFENCE_DEADLINE_DAYS, TRIAL_REQUEST_DEADLINE_DAYS


@dataclass
class ClaimDeadlines:
    """All computed court deadlines for a single claim.

    Fields that are None indicate the underlying date has not been entered by the
    user yet (e.g. service_date not recorded) or the relevant step_data key is
    missing. Callers must handle None gracefully.
    """

    limitation_deadline: date | None = None
    defence_deadline: date | None = None
    settlement_conf_date: date | None = None
    trial_request_deadline: date | None = None
    overdue_items: list[str] = field(default_factory=list)


def build_claim_deadlines(claim, today: date | None = None) -> ClaimDeadlines:
    """Compute all four court deadlines from a Claim's step_data.

    Pure function — reads claim.step_data, performs date arithmetic, returns
    a ClaimDeadlines dataclass. Does not write to the database.

    Parameters
    ----------
    claim:
        A Claim ORM instance. Reads claim.step_data["limitation"]["basic_deadline"]
        and claim.step_data["claim_dates"]["service_date"] /
        "settlement_conference_date".
    today:
        Date to treat as today. Defaults to date.today(). Pass explicitly in tests.
    """
    if today is None:
        today = date.today()

    step_data = claim.step_data or {}
    overdue: list[str] = []

    # --- Limitation deadline (from limitation service output) ---
    limitation_deadline: date | None = None
    limitation_section = step_data.get("limitation", {})
    if limitation_section:
        raw = limitation_section.get("basic_deadline")
        if raw:
            try:
                limitation_deadline = date.fromisoformat(raw)
            except (ValueError, TypeError):
                limitation_deadline = None

    # --- Dates entered by the user on the dashboard ---
    claim_dates = step_data.get("claim_dates", {})

    # Defence deadline = service_date + DEFENCE_DEADLINE_DAYS
    defence_deadline: date | None = None
    raw_service = claim_dates.get("service_date")
    if raw_service:
        try:
            service_date = date.fromisoformat(raw_service)
            defence_deadline = service_date + relativedelta(days=DEFENCE_DEADLINE_DAYS)
        except (ValueError, TypeError):
            defence_deadline = None

    # Settlement conference date (user-entered, no arithmetic needed)
    settlement_conf_date: date | None = None
    raw_settlement = claim_dates.get("settlement_conference_date")
    if raw_settlement:
        try:
            settlement_conf_date = date.fromisoformat(raw_settlement)
        except (ValueError, TypeError):
            settlement_conf_date = None

    # Trial request deadline = settlement_conference_date + TRIAL_REQUEST_DEADLINE_DAYS
    trial_request_deadline: date | None = None
    if settlement_conf_date is not None:
        trial_request_deadline = settlement_conf_date + relativedelta(
            days=TRIAL_REQUEST_DEADLINE_DAYS
        )

    # --- Overdue items ---
    if limitation_deadline is not None and limitation_deadline < today:
        overdue.append("Limitation Period Expiry")
    if defence_deadline is not None and defence_deadline < today:
        overdue.append("Defence Filing Deadline")
    if settlement_conf_date is not None and settlement_conf_date < today:
        overdue.append("Settlement Conference")
    if trial_request_deadline is not None and trial_request_deadline < today:
        overdue.append("Trial Request Deadline")

    return ClaimDeadlines(
        limitation_deadline=limitation_deadline,
        defence_deadline=defence_deadline,
        settlement_conf_date=settlement_conf_date,
        trial_request_deadline=trial_request_deadline,
        overdue_items=overdue,
    )
