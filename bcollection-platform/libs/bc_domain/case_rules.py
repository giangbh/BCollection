"""Pure lifecycle rules. Financial evidence must be verified by application services."""
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation


def vnd(value):
    try:
        amount = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("Invalid VND amount") from exc
    if not amount.is_finite() or amount < 0 or amount != amount.to_integral_value() or amount > 9_000_000_000_000_000:
        raise ValueError("VND must be a finite, nonnegative whole number within supported range")
    return int(amount)


def instant(value):
    result = value if isinstance(value, datetime) else datetime.fromisoformat(value)
    if result.tzinfo is None:
        raise ValueError("An explicit timezone is required")
    return result.astimezone(timezone.utc)


def lifecycle_after_balance(lifecycle, resolution, exposures):
    if not exposures or not all(e["balance_verified"] for e in exposures):
        return lifecycle, resolution
    cleared = all(e["overdue_vnd"] == 0 and e["dpd"] == 0 for e in exposures)
    if cleared:
        # A generic administrative/legal closure is not reclassified as a cure.
        if lifecycle == "CLOSED" and resolution != "CURED":
            return lifecycle, resolution
        return "CLOSED", "CURED"
    if lifecycle == "CLOSED" and resolution == "CURED":
        return "PROBATION", None
    return lifecycle, resolution


def obligation_status(exposure):
    if not exposure["balance_verified"]:
        return "UNVERIFIED"
    if exposure["overdue_vnd"] > 0 or exposure["dpd"] > 0:
        return "OVERDUE"
    if exposure["principal_vnd"] + exposure["interest_vnd"] == 0:
        return "SETTLED"
    return "CURRENT"
