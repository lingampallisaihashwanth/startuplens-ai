from typing import Any, Dict, List, Optional
from pydantic import BaseModel, EmailStr, Field


class UserIdentity(BaseModel):
    id: str
    provider: str
    provider_user_id: str
    email: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: str


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    auth_provider: Optional[str] = None
    provider_user_id: Optional[str] = None
    avatar_url: Optional[str] = None
    created_at: str
    updated_at: str
    linked_providers: List[Dict[str, Any]] = Field(default_factory=list)
    identities: List[Dict[str, Any]] = Field(default_factory=list)


class SignupRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=8, max_length=128)
    confirm_password: Optional[str] = None


class LoginRequest(BaseModel):
    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1, max_length=128)


class AuthResponse(BaseModel):
    user: UserResponse
    token: str
    message: str = "Authenticated successfully"


class SessionStatusResponse(BaseModel):
    authenticated: bool
    user: Optional[UserResponse] = None
