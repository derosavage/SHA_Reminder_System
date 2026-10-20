"""Time helpers."""

from datetime import datetime, timedelta, timezone

# Kenya is UTC+3 year round (no daylight saving), so a fixed offset is enough
# and avoids depending on the tzdata package being installed on Windows.
EAT = timezone(timedelta(hours=3), name="EAT")


def utcnow() -> datetime:
    """Naive UTC 'now' (matches our naive DateTime columns).

    Replacement for the deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)


def eat_now() -> datetime:
    """Aware 'now' in East Africa Time.

    Daraja builds its request Password from the same Timestamp string it sends,
    and its docs are written in EAT. Sending UTC produced timestamps three hours
    behind what Safaricom expects.
    """
    return datetime.now(EAT)

