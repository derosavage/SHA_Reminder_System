"""
Pydantic schemas for User authentication and profile management.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional
from datetime import datetime
import re


class UserCreate(BaseModel):
    """Schema for user registration."""
    national_id: str = Field(..., description="Kenyan National ID number")
    phone_number: str = Field(..., description="Phone number in 254 format")
    full_name: Optional[str] = Field(None, max_length=200)
    email: Optional[str] = None
    preferred_language: str = Field("sw", pattern="^(sw|en)$")

    @validator("phone_number")
    def validate_phone(cls, v):
        # Remove any non-digit characters
        v = re.sub(r"\D", "", v)
        if v.startswith("0"):
            v = "254" + v[1:]
        elif v.startswith("7"):
            v = "254" + v
        elif v.startswith("+254"):
            v = v[1:]
        if not v.startswith("254") or len(v) != 12:
            raise ValueError(
                "Phone must be a valid Kenyan number (e.g., 0712345678)"
            )
        return v

    @validator("national_id")
    def validate_national_id(cls, v):
        v = v.strip()
        if not v.isdigit() or len(v) < 5 or len(v) > 10:
            raise ValueError("National ID must be a valid Kenyan ID number")
        return v


class UserLogin(BaseModel):
    """Schema for user login."""
    phone_number: str
    password: Optional[str] = None
    otp_code: Optional[str] = None


class VerifyOTP(BaseModel):
    """Schema for OTP verification."""
    phone_number: str
    otp_code: str = Field(..., min_length=4, max_length=6)


class UserUpdate(BaseModel):
    """Schema for updating user profile."""
    full_name: Optional[str] = None
    email: Optional[str] = None
    preferred_language: Optional[str] = Field(None, pattern="^(sw|en)$")
    sms_notifications: Optional[bool] = None
    reminder_day: Optional[int] = Field(None, ge=1, le=28)


class UserResponse(BaseModel):
    """Schema for user API response."""
    id: str
    national_id: str
    phone_number: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    status: str
    is_verified: bool
    eligibility_status: str
    contribution_amount: float
    preferred_language: str
    sms_notifications: bool
    reminder_day: int
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True


class UserProfile(BaseModel):
    """Schema for user profile response (includes sensitive fields)."""
    id: str
    national_id: str
    phone_number: str
    full_name: Optional[str]
    email: Optional[str]
    role: str
    status: str
    sha_number: Optional[str]
    is_verified: bool
    eligibility_status: str
    contribution_amount: float
    last_contribution_date: Optional[datetime]
    preferred_language: str
    sms_notifications: bool
    push_notifications: bool
    reminder_day: int
    created_at: datetime
    last_login_at: Optional[datetime]

    class Config:
        from_attributes = True