"""Time helpers."""

from datetime import datetime, timezone


def utcnow() -> datetime:
    """Naive UTC 'now' (matches our naive DateTime columns).

    Replacement for the deprecated datetime.utcnow().
    """
    return datetime.now(timezone.utc).replace(tzinfo=None)
