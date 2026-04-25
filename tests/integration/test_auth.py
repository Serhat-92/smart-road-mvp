"""Integration tests for JWT authentication endpoints."""

from pathlib import Path
import sys
import unittest

from fastapi.testclient import TestClient


REPO_ROOT = Path(__file__).resolve().parents[2]
GATEWAY_API_ROOT = REPO_ROOT / "services" / "gateway-api"

gateway_api_root_str = str(GATEWAY_API_ROOT)
if gateway_api_root_str not in sys.path:
    sys.path.insert(0, gateway_api_root_str)

from app.main import app


class AuthIntegrationTests(unittest.TestCase):
    """Tests for /auth/token and /auth/me endpoints."""

    def _get_auth_headers(self, client):
        """Helper to obtain a valid JWT token and return auth headers."""
        response = client.post(
            "/auth/token",
            data={"username": "admin", "password": "admin123"},
        )
        token = response.json()["access_token"]
        return {"Authorization": f"Bearer {token}"}

    def test_login_with_valid_credentials_returns_token(self):
        """POST /auth/token with correct admin/admin123 → 200 + access_token."""
        with TestClient(app) as client:
            response = client.post(
                "/auth/token",
                data={"username": "admin", "password": "admin123"},
            )
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertIn("access_token", body)
            self.assertEqual(body["token_type"], "bearer")
            self.assertTrue(len(body["access_token"]) > 10)

    def test_login_with_wrong_password_returns_401(self):
        """POST /auth/token with wrong password → 401."""
        with TestClient(app) as client:
            response = client.post(
                "/auth/token",
                data={"username": "admin", "password": "wrongpassword"},
            )
            self.assertEqual(response.status_code, 401, response.text)

    def test_login_with_wrong_username_returns_401(self):
        """POST /auth/token with wrong username → 401."""
        with TestClient(app) as client:
            response = client.post(
                "/auth/token",
                data={"username": "unknown_user", "password": "admin123"},
            )
            self.assertEqual(response.status_code, 401, response.text)

    def test_me_with_valid_token_returns_user(self):
        """GET /auth/me with valid token → 200 + user info."""
        with TestClient(app) as client:
            headers = self._get_auth_headers(client)
            response = client.get("/auth/me", headers=headers)
            self.assertEqual(response.status_code, 200, response.text)
            body = response.json()
            self.assertEqual(body["username"], "admin")
            self.assertIn("role", body)

    def test_me_with_invalid_token_returns_401(self):
        """GET /auth/me with invalid/expired token → 401."""
        with TestClient(app) as client:
            headers = {"Authorization": "Bearer this-is-a-fake-invalid-token"}
            response = client.get("/auth/me", headers=headers)
            self.assertEqual(response.status_code, 401, response.text)

    def test_me_without_token_returns_403(self):
        """GET /auth/me without any Authorization header → 403."""
        with TestClient(app) as client:
            response = client.get("/auth/me")
            self.assertEqual(response.status_code, 403, response.text)


if __name__ == "__main__":
    unittest.main()
