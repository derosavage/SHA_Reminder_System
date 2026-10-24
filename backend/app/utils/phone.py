"""
Shared Kenyan phone-number normalization.

Every auth and payment path stores phone numbers in the canonical
254XXXXXXXXX form. The conversion used to be re-implemented in each schema,
and the login / verify-OTP schemas forgot to do it at all: a client that
sent 0712345678 registered fine but could then never receive or verify an
OTP, because the lookup compared the raw string against the stored
254XXXXXXXXX value.

One helper, used everywhere, keeps the forms consistent.
"""

import re

# Canonical form: country code 254, then 7 (Safaricom) or 1 (Airtel),
# then the remaining 8 subscriber digits.
KENYAN_PHONE_PATTERN = re.compile(r"^254[17]\d{8}$")


def normalize_phone_number(value: str) -> str:
    """
    Convert a Kenyan phone number to the canonical 254XXXXXXXXX form.

    Accepts 0712345678, +254712345678, 254712345678 and 712345678.
    Anything that cannot be interpreted is returned with its non-digit
    characters stripped, so callers can still look it up (and get the
    generic "not found" answer) instead of raising.
    """
    if not isinstance(value, str):
        return ""
    digits = re.sub(r"\D", "", value)
    if not digits:
        return ""
    if digits.startswith("254"):
        return digits
    if digits.startswith("0"):
        return "254" + digits[1:]
    if len(digits) == 9 and digits.startswith("7"):
        return "254" + digits
    return digits


def is_valid_kenyan_phone(value: str) -> bool:
    """True when the value is a well-formed Kenyan mobile number."""
    return bool(KENYAN_PHONE_PATTERN.match(value or ""))
