"""
Authentication API Routes
Handles user registration, OTP verification, and token management.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from app.core.database import get_db
from app.core.config import settings
from app.core.i18n import coerce_language, resolve_language, translate
from app.schemas.user import UserCreate, UserResponse, VerifyOTP, UserLogin
from app.services.auth_service import AuthService
from app.services.sms_service import SMSService
from app.utils.dependencies import get_client_info, get_request_language
from app.utils.rate_limit import rate_limit, check_rate_limit

# AuthService raises plain English ValueError messages; map them to message
# keys so the API can answer in the caller's language.
_SERVICE_ERROR_KEYS = (
    ("already exists", "user_already_exists"),
    ("Too many failed attempts", "account_locked"),
    ("No active OTP", "no_active_otp"),
    ("OTP has expired", "otp_expired"),
    ("Invalid OTP", "invalid_otp"),
)

# Pydantic validation messages raised by the UserCreate / VerifyOTP schemas.
_VALIDATION_MESSAGE_KEYS = (
    ("Phone must be a valid Kenyan number", "invalid_phone_number"),
    ("National ID must be a valid Kenyan ID number", "invalid_national_id"),
)


def _localized_service_error(exc: Exception, language: str) -> str:
    """Translate a service error message, keeping the original if unknown."""
    text = str(exc)
    for needle, key in _SERVICE_ERROR_KEYS:
        if needle in text:
            return translate(key, language)
    return text


def _translate_validation_message(message: str, language: str) -> str:
    """Translate a pydantic validation message when we have a translation."""
    for needle, key in _VALIDATION_MESSAGE_KEYS:
        if needle in message:
            return translate(key, language)
    return message


def _language_for_request(request: Request) -> str:
    """
    Language for a request that failed before the dependencies ran.

    Mirrors get_request_language() minus the user preference: there is no
    authenticated user to read a preference from yet.
    """
    explicit = coerce_language(request.query_params.get("lang"), fallback="")
    if explicit:
        return explicit
    return resolve_language(request.headers.get("accept-language"))


def _localized_validation_error(
    exc: RequestValidationError,
    request: Request,
) -> HTTPException:
    """Re-raise a validation error with a translated message."""
    language = _language_for_request(request)
    errors = []
    for error in exc.errors():
        item = dict(error)
        item["msg"] = _translate_validation_message(
            str(item.get("msg", "")), language
        )
        errors.append(item)
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=jsonable_encoder(errors),
    )


class LocalizedValidationRoute(APIRoute):
    """Route class that answers validation errors in the caller's language."""

    def get_route_handler(self):
        original_route_handler = super().get_route_handler()

        async def custom_route_handler(request: Request):
            try:
                return await original_route_handler(request)
            except RequestValidationError as exc:
                raise _localized_validation_error(exc, request)

        return custom_route_handler


router = APIRouter(
    dependencies=[Depends(rate_limit("auth", 10))],
    route_class=LocalizedValidationRoute,
)


async def _user_language(
    db: AsyncSession,
    phone_number: str,
    fallback: str,
) -> str:
    """Language stored for a registered user, or the request language."""
    user = await AuthService.get_user_by_phone(db, phone_number)
    if user is None:
        return fallback
    return coerce_language(user.preferred_language, fallback=fallback)


@router.post("/register", response_model=dict)
async def register(
    user_data: UserCreate,
    db: AsyncSession = Depends(get_db),
    client_info: dict = Depends(get_client_info),
    language: str = Depends(get_request_language),
    lang: Optional[str] = Query(
        None, description="Explicit language override (sw or en)"
    ),
):
    """Register a new user with phone number and National ID."""
    # The payload's preferred_language wins over the request default; an
    # explicit ?lang= parameter overrides both.
    explicit = coerce_language(lang, fallback="")
    if explicit:
        resolved = explicit
    elif "preferred_language" in user_data.model_fields_set:
        resolved = coerce_language(user_data.preferred_language, fallback=language)
    else:
        resolved = language

    try:
        user, otp = await AuthService.register_user(db, user_data)

        # Send OTP via SMS (in production, actually send), in the language the
        # user registered with.
        sms_sent = await SMSService.send_otp(
            user.phone_number,
            otp,
            language=coerce_language(user.preferred_language, fallback=resolved),
        )

        logger.info(f"User registered: {user.phone_number}")
        response = {
            "success": True,
            "message": translate("registration_success", resolved),
            "language": resolved,
            "data": {
                "user_id": str(user.id),
                "phone_number": user.phone_number,
                "otp_sent": sms_sent,
            },
        }
        # DEVELOPMENT ONLY: expose the OTP when no SMS provider is configured
        # so local testing stays possible. Gated on DEBUG, not on
        # ALLOW_INSECURE_DEFAULTS: a deployed instance runs with DEBUG=false, so
        # an OTP can never be handed back over the wire in production. Returning
        # it would let anyone who knows a registered phone number sign in as that
        # user, since login is phone + OTP only.
        if settings.DEBUG and not sms_sent:
            response["data"]["debug_otp"] = otp
        return response
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_localized_service_error(e, resolved),
        )


@router.post("/verify-otp", response_model=dict)
async def verify_otp(
    verification: VerifyOTP,
    db: AsyncSession = Depends(get_db),
    language: str = Depends(get_request_language),
):
    """Verify phone number with OTP code."""
    try:
        user = await AuthService.verify_otp(
            db, verification.phone_number, verification.otp_code
        )
        token = AuthService.create_access_token(
            user_id=str(user.id), role=user.role.value
        )
        return {
            "success": True,
            "message": translate("phone_verified", language),
            "language": language,
            "data": {
                "access_token": token,
                "token_type": "bearer",
                "user_id": str(user.id),
                "role": user.role.value,
            },
        }
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=_localized_service_error(e, language),
        )


@router.post("/resend-otp", response_model=dict)
async def resend_otp(
    phone_data: dict,
    db: AsyncSession = Depends(get_db),
    language: str = Depends(get_request_language),
):
    """Resend OTP verification code."""
    phone_number = phone_data.get("phone_number")
    if not phone_number:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=translate("phone_required", language),
        )

    check_rate_limit(f"otp:{phone_number}", 3, 600)
    try:
        otp = await AuthService.request_new_otp(db, phone_number)
        # Identical response whether or not the number is registered, so the
        # endpoint can't be used to discover registered users.
        response = {
            "success": True,
            "message": translate("otp_resent", language),
            "language": language,
        }
        if otp:
            sms_language = await _user_language(db, phone_number, language)
            sms_sent = await SMSService.send_otp(
                phone_number, otp, language=sms_language
            )
            # DEVELOPMENT ONLY: see the note in register().
            if settings.DEBUG and not sms_sent:
                response["debug_otp"] = otp
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Resend OTP error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=translate("otp_send_failed", language),
        )


@router.post("/login", response_model=dict)
async def login(
    login_data: UserLogin,
    db: AsyncSession = Depends(get_db),
    language: str = Depends(get_request_language),
):
    """Login with phone number (sends OTP)."""
    check_rate_limit(f"otp:{login_data.phone_number}", 3, 600)
    try:
        # Identical response whether or not the number is registered, so the
        # endpoint can't be used to discover registered users.
        response = {
            "success": True,
            "message": translate("otp_sent_for_login", language),
            "language": language,
            "data": {},
        }
        otp = await AuthService.request_new_otp(db, login_data.phone_number)
        if otp:
            sms_language = await _user_language(
                db, login_data.phone_number, language
            )
            sms_sent = await SMSService.send_otp(
                login_data.phone_number, otp, language=sms_language
            )
            # DEVELOPMENT ONLY: see the note in register().
            if settings.DEBUG and not sms_sent:
                response["data"]["debug_otp"] = otp
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=translate("login_failed", language),
        )
