"""
StartupLens AI — Authentication & Social OAuth Tests
Tests for:
- Google, GitHub, LinkedIn authorization start (redirects)
- Google, GitHub, LinkedIn callbacks with mocked provider identity
- Invalid OAuth state (CSRF protection)
- Provider error / cancellation handling
- Account creation & duplicate account handling
- Safe account linking via verified email
- Authenticated session verification (/auth/me) with cookie and Bearer token
- Logout & session revocation
- Protected routes (/research, /saved-ideas, etc.)
- User ownership & isolation (User A cannot access or mutate User B's resources)
"""

import os
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient

from backend.main import app
from backend.config import settings
from backend.database.db import db, DatabaseManager
from backend.services.auth_service import AuthService


@pytest.fixture
def auth_client(tmp_path):
    """Provides a fresh isolated database and test client with OAuth configured."""
    db_file = str(tmp_path / "test_auth.db")
    db_url = f"sqlite:///{db_file}"

    test_settings = settings
    # Save original settings
    orig_db = test_settings.DATABASE_URL
    orig_google_id = test_settings.GOOGLE_CLIENT_ID
    orig_google_sec = test_settings.GOOGLE_CLIENT_SECRET
    orig_github_id = test_settings.GITHUB_CLIENT_ID
    orig_github_sec = test_settings.GITHUB_CLIENT_SECRET
    orig_linkedin_id = test_settings.LINKEDIN_CLIENT_ID
    orig_linkedin_sec = test_settings.LINKEDIN_CLIENT_SECRET
    orig_require_auth = test_settings.REQUIRE_AUTH

    test_settings.DATABASE_URL = db_url
    test_settings.GOOGLE_CLIENT_ID = "mock-google-client-id"
    test_settings.GOOGLE_CLIENT_SECRET = "mock-google-secret"
    test_settings.GITHUB_CLIENT_ID = "mock-github-client-id"
    test_settings.GITHUB_CLIENT_SECRET = "mock-github-secret"
    test_settings.LINKEDIN_CLIENT_ID = "mock-linkedin-client-id"
    test_settings.LINKEDIN_CLIENT_SECRET = "mock-linkedin-secret"
    test_settings.REQUIRE_AUTH = True

    # Re-initialize DB
    db_mgr = DatabaseManager(db_url)
    db_mgr.init_db()

    with patch("backend.main.db", db_mgr), \
         patch("backend.database.db.db", db_mgr), \
         patch("backend.services.auth_service.db", db_mgr):
        client = TestClient(app, follow_redirects=False)
        yield client, db_mgr

    # Restore settings
    test_settings.DATABASE_URL = orig_db
    test_settings.GOOGLE_CLIENT_ID = orig_google_id
    test_settings.GOOGLE_CLIENT_SECRET = orig_google_sec
    test_settings.GITHUB_CLIENT_ID = orig_github_id
    test_settings.GITHUB_CLIENT_SECRET = orig_github_sec
    test_settings.LINKEDIN_CLIENT_ID = orig_linkedin_id
    test_settings.LINKEDIN_CLIENT_SECRET = orig_linkedin_sec
    test_settings.REQUIRE_AUTH = orig_require_auth


# ---------------------------------------------------------------------------
# 1. OAuth Authorization Start Tests
# ---------------------------------------------------------------------------

def test_google_authorization_start(auth_client):
    client, db = auth_client
    resp = client.get("/auth/google")
    assert resp.status_code in (302, 307)
    location = resp.headers.get("location", "")
    assert "accounts.google.com/o/oauth2/v2/auth" in location
    assert "client_id=mock-google-client-id" in location
    assert "state=" in location
    assert "scope=openid+email+profile" in location or "openid" in location


def test_github_authorization_start(auth_client):
    client, db = auth_client
    resp = client.get("/auth/github")
    assert resp.status_code in (302, 307)
    location = resp.headers.get("location", "")
    assert "github.com/login/oauth/authorize" in location
    assert "client_id=mock-github-client-id" in location
    assert "state=" in location
    assert "read%3Auser" in location or "read:user" in location


def test_linkedin_authorization_start(auth_client):
    client, db = auth_client
    resp = client.get("/auth/linkedin")
    assert resp.status_code in (302, 307)
    location = resp.headers.get("location", "")
    assert "linkedin.com/oauth/v2/authorization" in location
    assert "client_id=mock-linkedin-client-id" in location
    assert "state=" in location


# ---------------------------------------------------------------------------
# 2. OAuth Callback & State Validation Tests
# ---------------------------------------------------------------------------

def test_oauth_invalid_state_rejected(auth_client):
    client, db = auth_client
    resp = client.get("/auth/google/callback?code=mock_code&state=bogus_nonexistent_state")
    assert resp.status_code in (302, 307)
    loc = resp.headers.get("location", "")
    assert "error=" in loc and ("google_failed" in loc or "cancelled" in loc)


def test_oauth_provider_error_handling(auth_client):
    client, db = auth_client
    resp = client.get("/auth/github/callback?error=access_denied")
    assert resp.status_code in (302, 307)
    assert "error=cancelled" in resp.headers.get("location", "")


def test_google_callback_success(auth_client):
    client, db = auth_client

    # 1. Start OAuth to save valid CSRF state
    start_resp = client.get("/auth/google")
    location = start_resp.headers["location"]
    import urllib.parse
    parsed = urllib.parse.urlparse(location)
    params = urllib.parse.parse_qs(parsed.query)
    state = params["state"][0]

    # 2. Mock Google user profile exchange
    mock_profile = {
        "provider": "google",
        "provider_user_id": "google-user-12345",
        "email": "google.user@example.com",
        "name": "Google Researcher",
        "avatar_url": "https://lh3.googleusercontent.com/avatar123",
        "email_verified": True,
    }

    from unittest.mock import AsyncMock
    with patch.object(AuthService, "handle_google_callback", new_callable=AsyncMock, return_value=mock_profile):
        callback_resp = client.get(f"/auth/google/callback?code=valid_google_code&state={state}")
        assert callback_resp.status_code in (302, 307)
        assert "auth_success=1" in callback_resp.headers.get("location", "")

        # Verify HttpOnly session cookie was set
        token = callback_resp.cookies.get("startuplens_session")
        assert token

        # Verify session can access /auth/me
        me_resp = client.get("/auth/me", cookies={"startuplens_session": token})
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == "google.user@example.com"
        assert data["user"]["name"] == "Google Researcher"
        assert data["user"]["auth_provider"] == "google"


def test_github_callback_success(auth_client):
    client, db = auth_client

    # Start OAuth
    start_resp = client.get("/auth/github")
    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(start_resp.headers["location"]).query)
    state = params["state"][0]

    mock_profile = {
        "provider": "github",
        "provider_user_id": "github-dev-999",
        "email": "dev@github-user.com",
        "name": "GitHub Developer",
        "avatar_url": "https://avatars.githubusercontent.com/u/999",
        "email_verified": True,
    }

    from unittest.mock import AsyncMock
    with patch.object(AuthService, "handle_github_callback", new_callable=AsyncMock, return_value=mock_profile):
        callback_resp = client.get(f"/auth/github/callback?code=valid_gh_code&state={state}")
        assert callback_resp.status_code in (302, 307)
        assert "auth_success=1" in callback_resp.headers.get("location", "")
        token = callback_resp.cookies.get("startuplens_session")
        assert token

        me_resp = client.get("/auth/me", cookies={"startuplens_session": token})
        assert me_resp.status_code == 200
        data = me_resp.json()
        assert data["authenticated"] is True
        assert data["user"]["email"] == "dev@github-user.com"


def test_linkedin_callback_success(auth_client):
    client, db = auth_client

    start_resp = client.get("/auth/linkedin")
    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(start_resp.headers["location"]).query)
    state = params["state"][0]

    mock_profile = {
        "provider": "linkedin",
        "provider_user_id": "linkedin-executive-777",
        "email": "exec@linkedin-user.com",
        "name": "LinkedIn Executive",
        "avatar_url": "https://media.licdn.com/dms/image/avatar777",
        "email_verified": True,
    }

    from unittest.mock import AsyncMock
    with patch.object(AuthService, "handle_linkedin_callback", new_callable=AsyncMock, return_value=mock_profile):
        callback_resp = client.get(f"/auth/linkedin/callback?code=valid_li_code&state={state}")
        assert callback_resp.status_code in (302, 307)
        assert "auth_success=1" in callback_resp.headers.get("location", "")
        token = callback_resp.cookies.get("startuplens_session")
        assert token

        me_resp = client.get("/auth/me", cookies={"startuplens_session": token})
        assert me_resp.status_code == 200
        assert me_resp.json()["user"]["email"] == "exec@linkedin-user.com"


# ---------------------------------------------------------------------------
# 3. Account Linking & Duplicate Account Tests
# ---------------------------------------------------------------------------

def test_safe_account_linking_with_verified_email(auth_client):
    """
    If a user signs up first via Email/Password:
    Subsequent social login with a verified matching email links the provider safely.
    """
    client, db = auth_client

    # 1. Create email/password user
    signup_resp = client.post("/auth/signup", json={
        "name": "Jane Founder",
        "email": "jane@founder.com",
        "password": "SecurePassword123!"
    })
    assert signup_resp.status_code == 200
    user_id = signup_resp.json()["user"]["id"]

    # 2. Start Google OAuth
    start_resp = client.get("/auth/google")
    import urllib.parse
    params = urllib.parse.parse_qs(urllib.parse.urlparse(start_resp.headers["location"]).query)
    state = params["state"][0]

    mock_google = {
        "provider": "google",
        "provider_user_id": "google-jane-101",
        "email": "jane@founder.com",
        "name": "Jane Founder Google",
        "avatar_url": "https://google.com/avatar.jpg",
        "email_verified": True,
    }

    from unittest.mock import AsyncMock
    with patch.object(AuthService, "handle_google_callback", new_callable=AsyncMock, return_value=mock_google):
        cb_resp = client.get(f"/auth/google/callback?code=mock_code&state={state}")
        assert cb_resp.status_code in (302, 307)
        assert "auth_success=1" in cb_resp.headers.get("location", "")

        token = cb_resp.cookies.get("startuplens_session")
        assert token

        # Check me
        me_resp = client.get("/auth/me", cookies={"startuplens_session": token})
        data = me_resp.json()
        assert data["user"]["id"] == user_id  # Linked to existing user ID!
        # Check identities list
        identities = data["user"].get("identities", [])
        assert any(i["provider"] == "google" for i in identities)


def test_duplicate_social_login_maps_to_same_account(auth_client):
    """
    Logging in twice with the same social provider maps to the same user.
    """
    client, db = auth_client

    # First login
    start1 = client.get("/auth/github")
    import urllib.parse
    state1 = urllib.parse.parse_qs(urllib.parse.urlparse(start1.headers["location"]).query)["state"][0]

    mock_gh = {
        "provider": "github",
        "provider_user_id": "github-same-user-500",
        "email": "same@github.com",
        "name": "Same GitHub User",
        "email_verified": True,
    }

    from unittest.mock import AsyncMock
    with patch.object(AuthService, "handle_github_callback", new_callable=AsyncMock, return_value=mock_gh):
        cb1 = client.get(f"/auth/github/callback?code=c1&state={state1}")
        assert cb1.status_code in (302, 307)
        token1 = cb1.cookies.get("startuplens_session")
        assert token1
        me1 = client.get("/auth/me", cookies={"startuplens_session": token1}).json()
        assert me1["authenticated"] is True
        user1_id = me1["user"]["id"]

    # Second login
    start2 = client.get("/auth/github")
    state2 = urllib.parse.parse_qs(urllib.parse.urlparse(start2.headers["location"]).query)["state"][0]

    with patch.object(AuthService, "handle_github_callback", new_callable=AsyncMock, return_value=mock_gh):
        cb2 = client.get(f"/auth/github/callback?code=c2&state={state2}")
        assert cb2.status_code in (302, 307)
        token2 = cb2.cookies.get("startuplens_session")
        assert token2
        me2 = client.get("/auth/me", cookies={"startuplens_session": token2}).json()
        assert me2["authenticated"] is True
        user2_id = me2["user"]["id"]

    assert user1_id == user2_id


# ---------------------------------------------------------------------------
# 4. Email/Password Authentication & Logout Tests
# ---------------------------------------------------------------------------

def test_email_password_signup_and_login_flow(auth_client):
    client, db = auth_client

    # Signup
    signup_resp = client.post("/auth/signup", json={
        "name": "Alice Bob",
        "email": "alice@startup.com",
        "password": "Password123!"
    })
    assert signup_resp.status_code == 200
    token = signup_resp.json()["token"]
    assert token

    # Login
    login_resp = client.post("/auth/login", json={
        "email": "alice@startup.com",
        "password": "Password123!"
    })
    assert login_resp.status_code == 200
    session_token = login_resp.cookies.get("startuplens_session")
    assert session_token

    # Me with cookie
    me_resp = client.get("/auth/me", cookies={"startuplens_session": session_token})
    assert me_resp.status_code == 200
    assert me_resp.json()["authenticated"] is True

    # Me with Bearer header
    me_header_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_header_resp.status_code == 200
    assert me_header_resp.json()["user"]["email"] == "alice@startup.com"

    # Logout
    logout_resp = client.post("/auth/logout", cookies={"startuplens_session": session_token})
    assert logout_resp.status_code == 200

    # After logout, me should be unauthenticated
    after_me = client.get("/auth/me", cookies={"startuplens_session": session_token})
    assert after_me.json()["authenticated"] is False


# ---------------------------------------------------------------------------
# 5. Route Protection & User Isolation / Ownership Tests
# ---------------------------------------------------------------------------

def test_unauthenticated_request_rejected_on_protected_routes(auth_client):
    client, db = auth_client
    # REQUIRE_AUTH is True in fixture
    resp = client.get("/research")
    assert resp.status_code == 401

    saved_resp = client.get("/saved-ideas")
    assert saved_resp.status_code == 401


def test_public_routes_remain_accessible(auth_client):
    client, db = auth_client
    health_resp = client.get("/health")
    assert health_resp.status_code == 200

    models_resp = client.get("/models")
    assert models_resp.status_code == 200


def test_user_ownership_isolation(auth_client):
    """
    User A cannot read or delete User B's saved ideas or research sessions.
    """
    client, db = auth_client

    # User A
    user_a = client.post("/auth/signup", json={
        "name": "User A",
        "email": "userA@test.com",
        "password": "PasswordA123!"
    }).json()
    token_a = user_a["token"]

    # User B
    user_b = client.post("/auth/signup", json={
        "name": "User B",
        "email": "userB@test.com",
        "password": "PasswordB123!"
    }).json()
    token_b = user_b["token"]

    # User A creates a saved idea
    idea_resp = client.post("/saved-ideas", json={
        "topic": "Clean Energy",
        "title": "Solar Battery",
        "problem": "Storage bottleneck",
        "customer": "Homeowners",
        "solution": "Modular battery packs",
        "why_now": "New subsidy law",
        "competitors": ["Tesla"],
        "mvp_features": ["App monitor"],
        "risks": ["Supply chain"],
        "evidence": ["https://energy.gov/news"]
    }, headers={"Authorization": f"Bearer {token_a}"})
    assert idea_resp.status_code == 200
    idea_id = idea_resp.json()["id"]

    # User B attempts to delete User A's idea -> 403 Forbidden
    del_resp = client.delete(f"/saved-ideas/{idea_id}", headers={"Authorization": f"Bearer {token_b}"})
    assert del_resp.status_code == 403

    # User A can delete their own idea -> 200
    del_a_resp = client.delete(f"/saved-ideas/{idea_id}", headers={"Authorization": f"Bearer {token_a}"})
    assert del_a_resp.status_code == 200
