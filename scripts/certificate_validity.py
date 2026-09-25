"""Validate requested TAK client certificate expiry in Taiwan local time."""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone


TAIPEI = timezone(timedelta(hours=8))
MIN_VALIDITY = timedelta(minutes=5)
MAX_VALIDITY = timedelta(days=730)
ISSUER_MARGIN = timedelta(days=1)
LOCAL_EXPIRY = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}\Z")


def requested_expiry(value: str | None, *, now: datetime | None = None,
                     issuer_not_after: datetime | None = None) -> datetime:
    """Return an aware UTC expiry; an empty selection keeps the two-year default."""
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError("Current time must include a timezone")
    now = now.astimezone(timezone.utc)
    if value is None or value == "":
        expiry = (now + MAX_VALIDITY).replace(second=0, microsecond=0)
    elif isinstance(value, str) and LOCAL_EXPIRY.fullmatch(value):
        try:
            expiry = datetime.strptime(value, "%Y-%m-%dT%H:%M").replace(
                tzinfo=TAIPEI).astimezone(timezone.utc)
        except ValueError as exc:
            raise ValueError("Invalid certificate expiry date or time") from exc
    else:
        raise ValueError("Certificate expiry must be a Taiwan date and time")
    duration = expiry - now
    if duration < MIN_VALIDITY or duration > MAX_VALIDITY:
        raise ValueError("Certificate validity must be between 5 minutes and 730 days")
    if issuer_not_after is not None and expiry + ISSUER_MARGIN > issuer_not_after.astimezone(timezone.utc):
        raise ValueError("Issuing CA expires before the requested certificate expiry")
    return expiry


def local_expiry(value: str | None, *, now: datetime | None = None) -> str:
    """Normalize a form selection to a stable datetime-local value."""
    return requested_expiry(value, now=now).astimezone(TAIPEI).strftime("%Y-%m-%dT%H:%M")
