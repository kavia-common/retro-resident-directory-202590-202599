from __future__ import annotations

from datetime import date, datetime
from typing import Literal, Optional

from pydantic import BaseModel, EmailStr, Field


class ErrorEnvelope(BaseModel):
    """Consistent error response envelope."""

    error: dict = Field(..., description="Structured error information.")


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1, max_length=64, description="Username.")
    password: str = Field(..., min_length=1, max_length=128, description="Password.")


class LoginResponse(BaseModel):
    token: str = Field(..., description="Bearer token to send in Authorization header.")
    token_type: Literal["bearer"] = Field("bearer", description="Token type.")
    expires_at: int = Field(..., description="Expiry time as epoch seconds.")
    username: str = Field(..., description="Authenticated username.")
    is_admin: bool = Field(..., description="Whether the user has admin privileges.")


class CurrentUserResponse(BaseModel):
    username: str = Field(..., description="Authenticated username.")
    is_admin: bool = Field(..., description="Whether the user has admin privileges.")


class ResidentBase(BaseModel):
    full_name: str = Field(..., min_length=1, max_length=120, description="Resident full name.")
    unit: Optional[str] = Field(None, max_length=32, description="Apartment/unit identifier.")
    phone: Optional[str] = Field(None, max_length=32, description="Phone number.")
    email: Optional[EmailStr] = Field(None, description="Email address.")
    status: Literal["active", "inactive"] = Field("active", description="Resident status.")
    notes: Optional[str] = Field(None, max_length=2000, description="Admin notes about the resident.")
    move_in_date: Optional[date] = Field(None, description="Move-in date.")
    tags: list[str] = Field(default_factory=list, description="Tags for filtering/searching.")
    created_at: Optional[datetime] = Field(None, description="Creation timestamp (server-set).")
    updated_at: Optional[datetime] = Field(None, description="Update timestamp (server-set).")


class ResidentCreate(ResidentBase):
    """Payload for creating a resident."""

    created_at: None = Field(None, description="Ignored; server sets this field.")
    updated_at: None = Field(None, description="Ignored; server sets this field.")


class ResidentUpdate(BaseModel):
    """Payload for updating a resident (all fields optional)."""

    full_name: Optional[str] = Field(None, min_length=1, max_length=120, description="Resident full name.")
    unit: Optional[str] = Field(None, max_length=32, description="Apartment/unit identifier.")
    phone: Optional[str] = Field(None, max_length=32, description="Phone number.")
    email: Optional[EmailStr] = Field(None, description="Email address.")
    status: Optional[Literal["active", "inactive"]] = Field(None, description="Resident status.")
    notes: Optional[str] = Field(None, max_length=2000, description="Admin notes about the resident.")
    move_in_date: Optional[date] = Field(None, description="Move-in date.")
    tags: Optional[list[str]] = Field(None, description="Tags for filtering/searching.")


class ResidentOut(ResidentBase):
    id: int = Field(..., description="Resident ID.")


class ResidentListResponse(BaseModel):
    total: int = Field(..., description="Total number of matching residents.")
    items: list[ResidentOut] = Field(..., description="Residents list items.")
