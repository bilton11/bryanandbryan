from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from enum import Enum

from dateutil.relativedelta import relativedelta

from app.ontario_constants import (
    LIMITATION_PERIOD_YEARS,
    MUNICIPAL_NOTICE_DAYS,
    ULTIMATE_LIMITATION_YEARS,
)


class LimitationStatus(Enum):
    WITHIN_PERIOD = "within_period"
    WARNING = "warning"
    EXPIRED = "expired"
    ULTIMATE_EXPIRED = "ultimate_expired"
    REQUIRES_LAWYER_REVIEW = "requires_lawyer_review"


@dataclass
class LimitationResult:
    status: LimitationStatus
    basic_deadline: date | None
    ultimate_deadline: date | None
    days_remaining: int | None
    warning_message: str | None
    tolling_applied: bool = False
    municipal_notice_required: bool = False


def calculate_limitation(
    discovery_date: date,
    incident_date: date,
    is_minor: bool,
    minor_dob: date | None,
    is_incapacitated: bool,
    incapacity_end_date: date | None,
    is_municipal_defendant: bool,
    today: date | None = None,
) -> LimitationResult:
    """
    Calculate the Ontario Limitations Act limitation period for a claim.

    The basic period starts from the discovery date (when the claimant knew or
    ought to have known they had a claim) — not the incident date. The 15-year
    ultimate period always runs from the incident date.

    Tolling applies for minors and incapacitated persons, shifting the start
    of the basic period forward. When tolling applies, a lawyer should review
    because the exact calculation depends on specific circumstances.

    Parameters
    ----------
    discovery_date : date
        Date the claimant discovered (or ought to have discovered) the claim.
    incident_date : date
        Date the underlying event occurred (used for ultimate period).
    is_minor : bool
        True if the claimant was under 18 at the time of the incident.
    minor_dob : date | None
        Claimant's date of birth (required when is_minor=True for tolling calc).
    is_incapacitated : bool
        True if the claimant was legally incapacitated during any part of the period.
    incapacity_end_date : date | None
        Date incapacity ended (required when is_incapacitated=True).
    is_municipal_defendant : bool
        True if the defendant is a municipality or municipal body.
    today : date | None
        Date to use as "today" — defaults to date.today(). Pass explicitly in tests.
    """
    if today is None:
        today = date.today()

    tolling_applied = False

    # --- Basic limitation period ---
    # Starts from discovery date; may be tolled forward for minors/incapacity
    basic_start = discovery_date

    # Tolling for minors: period does not run until the claimant turns 18
    if is_minor and minor_dob is not None:
        age_18 = minor_dob + relativedelta(years=18)
        if age_18 > basic_start:
            basic_start = age_18
            tolling_applied = True

    # Tolling for incapacity: period does not run during incapacity
    if is_incapacitated and incapacity_end_date is not None:
        if incapacity_end_date > basic_start:
            basic_start = incapacity_end_date
            tolling_applied = True

    basic_deadline = basic_start + relativedelta(years=LIMITATION_PERIOD_YEARS)

    # --- Ultimate limitation period ---
    # Always runs from the incident date regardless of tolling
    ultimate_deadline = incident_date + relativedelta(years=ULTIMATE_LIMITATION_YEARS)

    # --- Days remaining ---
    days_remaining: int | None = (basic_deadline - today).days

    # --- Municipal notice ---
    municipal_notice_required = is_municipal_defendant
    municipal_warning: str | None = None
    if municipal_notice_required:
        municipal_warning = (
            f"Because the other party is a municipality, you must give {MUNICIPAL_NOTICE_DAYS} days "
            "written notice before filing your claim. This notice must be served on the municipality "
            "before your claim is filed with the court."
        )

    # --- Determine status ---
    warning_message: str | None = None

    if tolling_applied:
        # Tolling makes the calculation fact-specific — always flag for lawyer review
        status = LimitationStatus.REQUIRES_LAWYER_REVIEW
        warning_message = (
            "Your situation may involve a special rule that pauses or extends the "
            "usual 2-year deadline. A lawyer should review your specific circumstances "
            "to confirm the correct deadline."
        )
    elif today > ultimate_deadline:
        status = LimitationStatus.ULTIMATE_EXPIRED
        warning_message = (
            f"The 15-year absolute deadline appears to have passed (it expired on "
            f"{ultimate_deadline.isoformat()}). In almost all cases this means the claim "
            "cannot be brought. You should consult a lawyer to confirm."
        )
        days_remaining = None
    elif today > basic_deadline:
        status = LimitationStatus.EXPIRED
        warning_message = (
            f"The 2-year limitation period appears to have expired (it expired on "
            f"{basic_deadline.isoformat()}). You may no longer be able to file this claim. "
            "Consult a lawyer as soon as possible."
        )
        days_remaining = None
    elif days_remaining is not None and days_remaining < 90:
        status = LimitationStatus.WARNING
        warning_message = (
            f"Act promptly — you have approximately {days_remaining} days remaining "
            f"to file your claim (deadline: {basic_deadline.isoformat()}). "
            "Once the deadline passes, you may lose your right to sue."
        )
    else:
        status = LimitationStatus.WITHIN_PERIOD
        warning_message = (
            f"Your claim appears to be within the limitation period. "
            f"You have until {basic_deadline.isoformat()} to file "
            f"({days_remaining} days from today)."
        )

    # Append municipal notice warning to existing message if both apply
    if municipal_warning:
        if warning_message:
            warning_message = warning_message + " " + municipal_warning
        else:
            warning_message = municipal_warning

    return LimitationResult(
        status=status,
        basic_deadline=basic_deadline,
        ultimate_deadline=ultimate_deadline,
        days_remaining=days_remaining,
        warning_message=warning_message,
        tolling_applied=tolling_applied,
        municipal_notice_required=municipal_notice_required,
    )
