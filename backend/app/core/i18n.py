"""
Internationalization (i18n) Module
Bilingual message catalogue for the sha-pay API.

Kiswahili (sw) is the default language, English (en) is the secondary one.
Messages are plain dicts keyed by message key, with one entry per supported
language. Placeholders use the ``{name}`` style and are filled in with
``str.format(**kwargs)``.
"""

from typing import Any, Dict, Optional, Tuple

DEFAULT_LANGUAGE = "sw"
SUPPORTED_LANGUAGES: Tuple[str, ...] = ("sw", "en")

MESSAGES: Dict[str, Dict[str, str]] = {
    # --- Authentication / OTP -------------------------------------------------
    "registration_success": {
        "sw": "Usajili umefanikiwa. Angalia SMS kwa msimbo wa OTP.",
        "en": "Registration successful. Check SMS for OTP.",
    },
    "user_already_exists": {
        "sw": "Mtumiaji mwenye namba hii ya simu au kitambulisho tayari kuna.",
        "en": (
            "A user with this phone number or national ID already exists."
        ),
    },
    "invalid_otp": {
        "sw": "Msimbo wa OTP si sahihi",
        "en": "Invalid OTP code",
    },
    "account_locked": {
        "sw": (
            "Majaribio mengi yameshindwa. Jaribu tena baada ya dakika chache."
        ),
        "en": "Too many failed attempts. Try again in a few minutes.",
    },
    "no_active_otp": {
        "sw": "Hakuna msimbo wa OTP unaotumika. Tafuta msimbo mpya.",
        "en": "No active OTP. Please request a new one.",
    },
    "otp_expired": {
        "sw": "Msimbo wa OTP umeisha muda. Tafuta msimbo mpya.",
        "en": "OTP has expired. Please request a new one.",
    },
    "phone_verified": {
        "sw": "Namba ya simu imethibitishwa kwa mafanikio.",
        "en": "Phone verified successfully.",
    },
    # Generic wording: identical for registered and unregistered numbers so
    # the endpoints cannot be used to discover who has an account.
    "otp_resent": {
        "sw": "Kama namba imeandikishwa, msimbo mpya wa OTP umetumwa.",
        "en": "If the number is registered, a new OTP has been sent.",
    },
    "otp_sent_for_login": {
        "sw": "Kama namba imeandikishwa, msimbo wa OTP umetumwa.",
        "en": "If the number is registered, an OTP has been sent.",
    },
    "phone_required": {
        "sw": "Namba ya simu inahitajika",
        "en": "Phone number is required",
    },
    "otp_send_failed": {
        "sw": "Hawewe kutuma msimbo wa OTP",
        "en": "Could not send OTP",
    },
    "login_failed": {
        "sw": "Kuingia kimefaili",
        "en": "Login failed",
    },
    # Request validation (UserCreate / VerifyOTP).
    "invalid_phone_number": {
        "sw": (
            "Namba ya simu lazima iwe namba halali ya Kenya "
            "(kwa mfano, 0712345678)"
        ),
        "en": "Phone must be a valid Kenyan number (e.g., 0712345678)",
    },
    "invalid_national_id": {
        "sw": (
            "Namba ya kitambulisho lazima iwe namba halali ya "
            "kitambulisho cha Kenya"
        ),
        "en": "National ID must be a valid Kenyan ID number",
    },
    # --- SMS ------------------------------------------------------------------
    "otp_sms": {
        "sw": (
            "Msimbo wako wa sha-pay ni: {otp}. "
            "Unatumika kwa dakika {minutes}. "
            "Usishiriki msimbo huu na mtu yeyote."
        ),
        "en": (
            "Your sha-pay OTP is: {otp}. "
            "Valid for {minutes} minutes. "
            "Do not share this code."
        ),
    },
    "payment_reminder_sms": {
        "sw": (
            "Mpendwa {name}, malipo yako ya SHA ya KES {amount} "
            "yanatarajiwa tarehe {due_date}. Lipa kwa M-Pesa "
            "Paybill 200222, Namba {account_ref}. "
            "Ili kuepuka adhabu ya 2%/mwezi, lipa kabla ya tarehe 9."
        ),
        "en": (
            "Dear {name}, your SHA payment of KES {amount} "
            "is due on {due_date}. Pay via M-Pesa Paybill 200222, "
            "Account {account_ref}. "
            "Avoid 2%/month penalty - pay before the 9th."
        ),
    },
    # --- Users ----------------------------------------------------------------
    "user_not_found": {
        "sw": "Mtumiaji hakupatikana",
        "en": "User not found",
    },
    "profile_updated": {
        "sw": "Wasifu umesasishwa kwa mafanikio.",
        "en": "Profile updated successfully.",
    },
    "account_deleted": {
        "sw": (
            "Akaunti imefutwa kwa mafanikio. Data yako imewekwa bila majina."
        ),
        "en": (
            "Account deleted successfully. Your data has been anonymized."
        ),
    },
    # --- Payments -------------------------------------------------------------
    "payment_request_sent": {
        "sw": (
            "Ombi la malipo la M-Pesa limetumwa. Angalia simu yako "
            "kwa ujumbe wa STK Push."
        ),
        "en": (
            "M-Pesa payment request sent. "
            "Check your phone for STK Push prompt."
        ),
    },
    "payment_login_required": {
        "sw": "Tafuta kuingia tena.",
        "en": "Please log in again.",
    },
    "payment_own_phone_only": {
        "sw": (
            "Unaweza kulipa tu kwa namba yako mwenyewe ya simu "
            "iliyoandikishwa."
        ),
        "en": "You can only pay from your own registered phone number.",
    },
    "payment_phone_format": {
        "sw": "Namba ya simu lazima iwe katika muundo wa 254XXXXXXXXX.",
        "en": "Phone number must be in 254XXXXXXXXX format.",
    },
    "payment_failed": {
        "sw": "Imeshindwa kuanza malipo ya M-Pesa. Tafuta tena.",
        "en": "Failed to initiate M-Pesa payment. Please try again.",
    },
    "forbidden": {
        "sw": "Imepunguzwa",
        "en": "Forbidden",
    },
    # --- Reminders ------------------------------------------------------------
    "reminder_sent": {
        "sw": "Kikumbusho kimetumwa kwa mafanikio.",
        "en": "Reminder sent successfully.",
    },
    "reminder_failed": {
        "sw": "Imeshindwa kutuma kikumbusho",
        "en": "Failed to send reminder",
    },
    # --- Penalties ------------------------------------------------------------
    "penalty_calculated": {
        "sw": "Adhabu imekokotwa kwa mafanikio.",
        "en": "Penalty calculated successfully.",
    },
    "penalty_history_retrieved": {
        "sw": "Historia ya adhabu imepatikana.",
        "en": "Penalty history retrieved.",
    },
    "penalty_formula": {
        "sw": "Fomula ya adhabu na viwango rasmi.",
        "en": "Penalty formula and official rates.",
    },
}


def coerce_language(value: Any, fallback: str = DEFAULT_LANGUAGE) -> str:
    """
    Coerce any input into a supported language code.

    Accepts values such as "EN", "en-KE" or "sw_KE" and returns the matching
    supported code ("en", "sw"). Anything unsupported returns `fallback`.
    """
    if not isinstance(value, str):
        return fallback
    normalized = value.strip().lower().replace("_", "-")
    if not normalized:
        return fallback
    base = normalized.split("-")[0]
    if base in SUPPORTED_LANGUAGES:
        return base
    return fallback


def parse_accept_language(accept_language: Optional[str]) -> Optional[str]:
    """
    Return the best supported language for an Accept-Language header.

    Honours q-values, so "en-KE,en;q=0.9,sw;q=0.8" resolves to "en".
    Returns None when the header is missing or names no supported language.
    """
    if not accept_language:
        return None

    candidates = []
    for index, part in enumerate(accept_language.split(",")):
        part = part.strip()
        if not part:
            continue
        pieces = part.split(";")
        tag = pieces[0].strip().lower()
        quality = 1.0
        for param in pieces[1:]:
            param = param.strip()
            if param.lower().startswith("q="):
                try:
                    quality = float(param[2:].strip())
                except ValueError:
                    quality = 0.0
        candidates.append((-quality, index, tag))

    candidates.sort()
    for _, _, tag in candidates:
        base = tag.split("-")[0]
        if base in SUPPORTED_LANGUAGES:
            return base
    return None


def resolve_language(
    accept_language: Optional[str],
    fallback: str = DEFAULT_LANGUAGE,
) -> str:
    """
    Resolve the language to use from an Accept-Language header.

    Returns the best supported language named by the header, or `fallback`
    when the header is absent or names no supported language.
    """
    match = parse_accept_language(accept_language)
    if match:
        return match
    return coerce_language(fallback)


def translate(
    key: str,
    language: str = DEFAULT_LANGUAGE,
    **kwargs: Any,
) -> str:
    """
    Translate a message key into the requested language.

    Falls back to the default language and finally to the key itself, so it
    never raises: a missing key returns the key, a missing placeholder
    returns the raw template.
    """
    entry = MESSAGES.get(key)
    if not entry:
        return key

    text = entry.get(coerce_language(language))
    if text is None:
        text = entry.get(DEFAULT_LANGUAGE)
    if text is None:
        return key

    if not kwargs:
        return text
    try:
        return text.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return text
