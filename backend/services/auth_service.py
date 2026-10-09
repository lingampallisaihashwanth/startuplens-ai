"""
StartupLens AI — Authentication and Social OAuth Service
Handles:
- Password hashing (PBKDF2-HMAC-SHA256 with cryptographically secure salts)
- JWT creation and verification (HS256)
- Session persistence and revocation in SQLite
- OAuth CSRF state protection
- Google OAuth 2.0 / OpenID Connect
- GitHub Web Application Flow (minimal read scopes)
- LinkedIn OpenID Connect (openid, profile, email)
- Safe Account Linking based on verified email
"""

import base64
import hashlib
import hmac
import json
import logging
import secrets
import urllib.parse
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx

from backend.config import settings
from backend.database.db import db

logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Base authentication exception."""
    pass


class InvalidCredentialsError(AuthError):
    pass


class OAuthError(AuthError):
    pass


class AuthService:
    """Authentication and identity service for StartupLens AI."""

    # ── Password Hashing ──────────────────────────────────────────────────────

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash password with PBKDF2-HMAC-SHA256 using 100,000 iterations and 16-byte salt."""
        salt = secrets.token_bytes(16)
        key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
        return f"pbkdf2:sha256:100000${salt.hex()}${key.hex()}"

    @staticmethod
    def verify_password(password: str, password_hash: Optional[str]) -> bool:
        """Verify plain password against stored hash."""
        if not password_hash or not password_hash.startswith("pbkdf2:sha256:"):
            return False
        try:
            parts = password_hash.split("$")
            if len(parts) != 3:
                return False
            _, salt_hex, key_hex = parts
            salt = bytes.fromhex(salt_hex)
            expected_key = bytes.fromhex(key_hex)
            computed_key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)
            return hmac.compare_digest(computed_key, expected_key)
        except Exception as e:
            logger.warning(f"Error verifying password hash: {e}")
            return False

    # ── JWT Encoding & Decoding (HS256) ───────────────────────────────────────

    @staticmethod
    def _b64url_encode(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")

    @staticmethod
    def _b64url_decode(data: str) -> bytes:
        rem = len(data) % 4
        if rem > 0:
            data += "=" * (4 - rem)
        return base64.urlsafe_b64decode(data.encode("utf-8"))

    def create_jwt_token(self, payload: Dict[str, Any], expires_in_seconds: Optional[int] = None) -> str:
        """Generate a cryptographically signed HS256 JWT."""
        exp_sec = expires_in_seconds or settings.SESSION_EXPIRE_SECONDS
        now = datetime.now(timezone.utc)
        claims = dict(payload)
        claims["iat"] = int(now.timestamp())
        claims["exp"] = int((now + timedelta(seconds=exp_sec)).timestamp())
        claims["jti"] = secrets.token_hex(16)

        header = {"alg": "HS256", "typ": "JWT"}
        header_b64 = self._b64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
        payload_b64 = self._b64url_encode(json.dumps(claims, separators=(",", ":")).encode("utf-8"))

        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
        secret_bytes = (settings.JWT_SECRET or "startuplens-secret-key").encode("utf-8")
        signature = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
        sig_b64 = self._b64url_encode(signature)

        return f"{header_b64}.{payload_b64}.{sig_b64}"

    def verify_jwt_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Verify JWT signature and expiration. Returns claims dict or None."""
        try:
            parts = token.split(".")
            if len(parts) != 3:
                return None
            header_b64, payload_b64, sig_b64 = parts

            signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")
            secret_bytes = (settings.JWT_SECRET or "startuplens-secret-key").encode("utf-8")
            expected_sig = hmac.new(secret_bytes, signing_input, hashlib.sha256).digest()
            actual_sig = self._b64url_decode(sig_b64)

            if not hmac.compare_digest(expected_sig, actual_sig):
                return None

            payload_json = self._b64url_decode(payload_b64).decode("utf-8")
            claims = json.loads(payload_json)

            now_ts = int(datetime.now(timezone.utc).timestamp())
            if claims.get("exp", 0) < now_ts:
                return None

            return claims
        except Exception as e:
            logger.debug(f"JWT verification failed: {e}")
            return None

    @staticmethod
    def hash_token(token: str) -> str:
        """Hash token for persistent session lookup."""
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    # ── Session Management ────────────────────────────────────────────────────

    def create_session_for_user(self, user: Dict[str, Any]) -> Tuple[str, str]:
        """Create a signed JWT and persist session in SQLite. Returns (token, expires_at_iso)."""
        payload = {
            "sub": user["id"],
            "email": user["email"],
            "name": user["name"],
        }
        token = self.create_jwt_token(payload)
        token_hash = self.hash_token(token)
        exp_iso = (datetime.now(timezone.utc) + timedelta(seconds=settings.SESSION_EXPIRE_SECONDS)).isoformat()
        db.create_auth_session(user_id=user["id"], token_hash=token_hash, expires_at=exp_iso)
        return token, exp_iso

    def get_user_from_token(self, token: str) -> Optional[Dict[str, Any]]:
        """Resolve authenticated user from JWT token or session table, verifying active session."""
        token_hash = self.hash_token(token)
        session = db.get_auth_session(token_hash)
        if not session:
            return None

        claims = self.verify_jwt_token(token)
        user_id = None
        if claims and "sub" in claims:
            user_id = claims["sub"]
        else:
            user_id = session.get("user_id")

        if not user_id:
            return None

        return db.get_user_by_id(user_id)

    def revoke_session(self, token: str) -> bool:
        """Revoke active session token."""
        token_hash = self.hash_token(token)
        return db.delete_auth_session(token_hash)

    # ── OAuth State CSRF Nonce ────────────────────────────────────────────────

    def create_oauth_state(self, provider: str, redirect_to: Optional[str] = None) -> str:
        """Generate cryptographically secure random state and persist it."""
        state = secrets.token_urlsafe(32)
        db.save_oauth_state(state=state, provider=provider, redirect_to=redirect_to)
        return state

    def verify_oauth_state(self, state: str, provider: str) -> Optional[Dict[str, Any]]:
        """Validate state against CSRF attack and consume it."""
        if not state or len(state) < 16:
            return None
        return db.verify_and_consume_oauth_state(state=state, provider=provider)

    # ── Google OAuth / OIDC ───────────────────────────────────────────────────

    def get_google_auth_url(self, state: str) -> str:
        """Generate Google OAuth 2.0 authorization URL with openid profile email scopes."""
        if not settings.GOOGLE_CLIENT_ID:
            raise OAuthError("Google OAuth is not configured. Missing GOOGLE_CLIENT_ID.")

        params = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid email profile",
            "state": state,
            "access_type": "online",
            "prompt": "select_account",
        }
        return f"https://accounts.google.com/o/oauth2/v2/auth?{urllib.parse.urlencode(params)}"

    async def handle_google_callback(self, code: str) -> Dict[str, Any]:
        """Exchange Google authorization code and fetch verified profile."""
        token_url = "https://oauth2.googleapis.com/token"
        data = {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "code": code,
            "grant_type": "authorization_code",
            "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(token_url, data=data)
            if token_res.status_code != 200:
                logger.error(f"Google token exchange failed: {token_res.status_code} {token_res.text}")
                raise OAuthError("Google sign-in could not be completed.")

            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise OAuthError("Google sign-in could not be completed.")

            # Fetch user info via OIDC endpoint
            userinfo_url = "https://openidconnect.googleapis.com/v1/userinfo"
            userinfo_res = await client.get(
                userinfo_url,
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_res.status_code != 200:
                logger.error(f"Google userinfo request failed: {userinfo_res.status_code}")
                raise OAuthError("Google sign-in could not be completed.")

            info = userinfo_res.json()

        email = info.get("email")
        if not email:
            raise OAuthError("Google account did not provide an email address.")

        email_verified = bool(info.get("email_verified", False))
        return {
            "provider": "google",
            "provider_user_id": str(info.get("sub")),
            "email": email,
            "email_verified": email_verified,
            "name": info.get("name") or email.split("@")[0],
            "avatar_url": info.get("picture"),
        }

    # ── GitHub OAuth ──────────────────────────────────────────────────────────

    def get_github_auth_url(self, state: str) -> str:
        """Generate GitHub authorization URL with read:user and user:email scopes (no repo write)."""
        if not settings.GITHUB_CLIENT_ID:
            raise OAuthError("GitHub OAuth is not configured. Missing GITHUB_CLIENT_ID.")

        params = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
            "scope": "read:user user:email",
            "state": state,
        }
        return f"https://github.com/login/oauth/authorize?{urllib.parse.urlencode(params)}"

    async def handle_github_callback(self, code: str) -> Dict[str, Any]:
        """Exchange GitHub authorization code and fetch primary verified profile."""
        token_url = "https://github.com/login/oauth/access_token"
        headers = {"Accept": "application/json"}
        data = {
            "client_id": settings.GITHUB_CLIENT_ID,
            "client_secret": settings.GITHUB_CLIENT_SECRET,
            "code": code,
            "redirect_uri": settings.GITHUB_REDIRECT_URI,
        }

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(token_url, headers=headers, data=data)
            if token_res.status_code != 200:
                logger.error(f"GitHub token exchange failed: {token_res.status_code}")
                raise OAuthError("GitHub sign-in could not be completed.")

            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                logger.error(f"GitHub response missing access token: {token_data}")
                raise OAuthError("GitHub sign-in could not be completed.")

            # Fetch user profile
            user_headers = {
                "Authorization": f"Bearer {access_token}",
                "User-Agent": "StartupLens-AI",
                "Accept": "application/json",
            }
            user_res = await client.get("https://api.github.com/user", headers=user_headers)
            if user_res.status_code != 200:
                logger.error(f"GitHub user profile fetch failed: {user_res.status_code}")
                raise OAuthError("GitHub sign-in could not be completed.")

            user_data = user_res.json()

            # Ensure we get a verified email (check /user/emails if public email is not set or unverified)
            email = user_data.get("email")
            email_verified = False

            emails_res = await client.get("https://api.github.com/user/emails", headers=user_headers)
            if emails_res.status_code == 200:
                emails_list = emails_res.json()
                # Find primary verified email
                primary = next((e for e in emails_list if e.get("primary") and e.get("verified")), None)
                if primary:
                    email = primary.get("email")
                    email_verified = True
                elif emails_list:
                    verified = next((e for e in emails_list if e.get("verified")), None)
                    if verified:
                        email = verified.get("email")
                        email_verified = True
                    else:
                        email = emails_list[0].get("email")
            elif email:
                email_verified = True

        if not email:
            raise OAuthError("GitHub account has no accessible email address.")

        name = user_data.get("name") or user_data.get("login") or email.split("@")[0]

        return {
            "provider": "github",
            "provider_user_id": str(user_data.get("id")),
            "email": email,
            "email_verified": email_verified,
            "name": name,
            "avatar_url": user_data.get("avatar_url"),
        }

    # ── LinkedIn OAuth / OIDC ─────────────────────────────────────────────────

    def get_linkedin_auth_url(self, state: str) -> str:
        """Generate LinkedIn OIDC authorization URL with openid profile email scopes."""
        if not settings.LINKEDIN_CLIENT_ID:
            raise OAuthError("LinkedIn OAuth is not configured. Missing LINKEDIN_CLIENT_ID.")

        params = {
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
            "response_type": "code",
            "scope": "openid profile email",
            "state": state,
        }
        return f"https://www.linkedin.com/oauth/v2/authorization?{urllib.parse.urlencode(params)}"

    async def handle_linkedin_callback(self, code: str) -> Dict[str, Any]:
        """Exchange LinkedIn authorization code and fetch OIDC userinfo."""
        token_url = "https://www.linkedin.com/oauth/v2/accessToken"
        data = {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": settings.LINKEDIN_CLIENT_ID,
            "client_secret": settings.LINKEDIN_CLIENT_SECRET,
            "redirect_uri": settings.LINKEDIN_REDIRECT_URI,
        }
        headers = {"Content-Type": "application/x-www-form-urlencoded"}

        async with httpx.AsyncClient(timeout=15.0) as client:
            token_res = await client.post(token_url, data=data, headers=headers)
            if token_res.status_code != 200:
                logger.error(f"LinkedIn token exchange failed: {token_res.status_code}")
                raise OAuthError("LinkedIn sign-in could not be completed.")

            token_data = token_res.json()
            access_token = token_data.get("access_token")
            if not access_token:
                raise OAuthError("LinkedIn sign-in could not be completed.")

            # Official LinkedIn OpenID Connect userinfo endpoint
            userinfo_res = await client.get(
                "https://api.linkedin.com/v2/userinfo",
                headers={"Authorization": f"Bearer {access_token}"},
            )
            if userinfo_res.status_code != 200:
                logger.error(f"LinkedIn userinfo fetch failed: {userinfo_res.status_code}")
                raise OAuthError("LinkedIn sign-in could not be completed.")

            info = userinfo_res.json()

        email = info.get("email")
        if not email:
            raise OAuthError("LinkedIn account did not provide an email address.")

        email_verified = bool(info.get("email_verified", True))
        return {
            "provider": "linkedin",
            "provider_user_id": str(info.get("sub")),
            "email": email,
            "email_verified": email_verified,
            "name": info.get("name") or f"{info.get('given_name', '')} {info.get('family_name', '')}".strip() or email.split("@")[0],
            "avatar_url": info.get("picture"),
        }

    # ── Social User Authentication & Safe Account Linking ─────────────────────

    def authenticate_or_link_social_user(self, profile: Dict[str, Any]) -> Dict[str, Any]:
        """
        Safely map a verified social identity to a StartupLens account.
        Rules:
        1. If identity (auth_provider, provider_user_id) exists -> authenticate user.
        2. If verified email matches an existing account -> link provider identity.
        3. If email is unverified and account exists -> reject merging to prevent account takeover.
        4. If new user -> create new account with provider identity.
        """
        provider = profile["provider"]
        provider_user_id = str(profile["provider_user_id"])
        email = profile["email"].strip().lower()
        name = profile.get("name") or email.split("@")[0]
        avatar_url = profile.get("avatar_url")
        email_verified = bool(profile.get("email_verified", False))

        # 1. Match by provider identity
        existing_identity_user = db.get_user_by_provider(provider, provider_user_id)
        if existing_identity_user:
            logger.info(f"Social login: matched existing identity for user {existing_identity_user['id']}")
            # Update avatar or name if previously unset
            updates = {}
            if not existing_identity_user.get("avatar_url") and avatar_url:
                updates["avatar_url"] = avatar_url
            if updates:
                db.update_user(existing_identity_user["id"], **updates)
                existing_identity_user = db.get_user_by_id(existing_identity_user["id"])
            return existing_identity_user  # type: ignore

        # 2. Match by email
        existing_email_user = db.get_user_by_email(email)
        if existing_email_user:
            if not email_verified:
                logger.warning(
                    f"Rejected account linking for {email}: provider {provider} email is not verified."
                )
                raise OAuthError(
                    f"{provider.title()} email is not verified. Account linking requires a verified email."
                )

            logger.info(
                f"Social login: safely linking {provider} identity to existing user {existing_email_user['id']}"
            )
            linked_user = db.link_provider_identity(
                user_id=existing_email_user["id"],
                provider=provider,
                provider_user_id=provider_user_id,
                email=email,
                avatar_url=avatar_url,
            )
            return linked_user

        # 3. Create brand-new user
        logger.info(f"Social login: creating new user for {email} via {provider}")
        new_user = db.create_user(
            name=name,
            email=email,
            password_hash=None,
            auth_provider=provider,
            provider_user_id=provider_user_id,
            avatar_url=avatar_url,
        )
        return new_user


auth_service = AuthService()
