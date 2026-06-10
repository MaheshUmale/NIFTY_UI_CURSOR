"""Upstox OAuth2 authentication lifecycle.

Authorization Code Grant flow only. Provides login URL generation, code
exchange, token retrieval, and logout (token revocation).

Source citation:
    > src/auth/AGENTS.md — OAuth2 flow, no password grant, token header
      enforcement, rate-limit token bucket.
    > ALL_DOCS/UPSTOX-api-docs.json — Canonical API reference.
"""
from __future__ import annotations

import os
import time
from typing import Any
from urllib.parse import urlencode

import requests

from src.utils.exception_handler import TokenExpiredError, UpstoxAPIError, wrap_requests_exception
from src.utils.logger import get_logger

from .token_manager import TokenManager

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

UPSTOX_AUTH_BASE: str = "https://api.upstox.com/v2"
UPSTOX_LOGIN_URL: str = "https://api.upstox.com/v2/login/authorization/dialog"
RATE_LIMIT_CAPACITY: int = 200
RATE_LIMIT_WINDOW_SEC: int = 60


# ---------------------------------------------------------------------------
# Rate limiter
# ---------------------------------------------------------------------------


class _TokenBucket:
    """Simple token bucket rate limiter.

    Capacity 200, refill 200 per 60 seconds (Upstox standard limit).
    Thread-safe for single-threaded async use.
    """

    def __init__(self, capacity: int = RATE_LIMIT_CAPACITY, window_sec: int = RATE_LIMIT_WINDOW_SEC) -> None:
        self._capacity = capacity
        self._window_sec = window_sec
        self._tokens = capacity
        self._last_refill = time.monotonic()

    def acquire(self) -> None:
        """Block until a token is available."""
        now = time.monotonic()
        elapsed = now - self._last_refill
        self._tokens = min(self._capacity, self._tokens + int(elapsed * self._capacity / self._window_sec))
        self._last_refill = now

        if self._tokens <= 0:
            sleep_time = self._window_sec / self._capacity
            time.sleep(sleep_time)
            self._tokens = 1

        self._tokens -= 1


# ---------------------------------------------------------------------------
# Auth client
# ---------------------------------------------------------------------------


class UpstoxAuth:
    """Upstox OAuth2 authentication client.

    Parameters
    ----------
    client_id : str
        Upstox API key.
    client_secret : str
        Upstox API secret.
    redirect_uri : str
        Redirect URI registered against the API key.
    """

    def __init__(self, client_id: str, client_secret: str, redirect_uri: str) -> None:
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri
        self._token_manager = TokenManager()
        self._rate_limiter = _TokenBucket()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def login_url(self) -> str:
        """Build the Upstox OAuth2 authorization URL.

        Returns
        -------
        str
            The URL the user must visit in a browser to authorize the app.
        """
        params = urlencode({
            "client_id": self._client_id,
            "redirect_uri": self._redirect_uri,
            "response_type": "code",
        })
        return f"{UPSTOX_LOGIN_URL}?{params}"

    def exchange_code(self, auth_code: str) -> dict[str, Any]:
        """Exchange the authorization code for an access token.

        Parameters
        ----------
        auth_code : str
            The authorization code received from the OAuth2 callback.

        Returns
        -------
        dict
            The token response JSON from Upstox.

        Raises
        ------
        UpstoxAPIError
            If the API call fails (wrapped from a ``requests`` exception).
        """
        self._rate_limiter.acquire()

        payload = {
            "code": auth_code,
            "client_id": self._client_id,
            "client_secret": self._client_secret,
            "redirect_uri": self._redirect_uri,
            "grant_type": "authorization_code",
        }
        headers = {
            "accept": "application/json",
            "Content-Type": "application/x-www-form-urlencoded",
        }

        try:
            resp = requests.post(
                f"{UPSTOX_AUTH_BASE}/login/authorization/token",
                data=payload,
                headers=headers,
                timeout=30,
            )
            resp.raise_for_status()
            token_data: dict[str, Any] = resp.json()
        except requests.RequestException as exc:
            wrapped = wrap_requests_exception(exc, context="exchange_code")
            logger.exception("Failed to exchange auth code")
            raise wrapped from exc

        self._token_manager.save_token(token_data)
        logger.info("Token exchanged and saved successfully")
        return token_data

    def get_valid_token(self) -> dict[str, Any]:
        """Return a valid access token.

        Loads from the token file. If the file is missing or the token
        has expired, raises ``TokenExpiredError`` so the caller can
        re-authenticate.

        Returns
        -------
        dict
            The token JSON (must contain ``access_token`` and ``expires_at``).

        Raises
        ------
        TokenExpiredError
            If no valid token is available.
        """
        token = self._token_manager.load_token()
        if token is None:
            logger.warning("No valid token available — user must re-authenticate")
            raise TokenExpiredError(
                "Access token is missing or expired. Call login_url() then exchange_code()."
            )
        return token

    def logout(self) -> None:
        """Revoke the current token and remove the token file.

        Calls the Upstox revoke endpoint, then deletes the token JSON file.
        """
        try:
            token = self._token_manager.load_token()
            if token is None:
                logger.info("No token to revoke")
                return

            self._rate_limiter.acquire()
            headers = {
                "accept": "application/json",
                "Authorization": f"Bearer {token.get('access_token', '')}",
            }
            resp = requests.delete(
                f"{UPSTOX_AUTH_BASE}/logout",
                headers=headers,
                timeout=10,
            )
            if resp.status_code != 204:
                logger.warning("Logout returned non-204: %s", resp.status_code)

        except requests.RequestException as exc:
            wrapped = wrap_requests_exception(exc, context="logout")
            logger.exception("Logout request failed")
            raise wrapped from exc
        finally:
            # Always attempt to remove the token file
            token_path = "config/.access_token.json"
            try:
                os.remove(token_path)
            except FileNotFoundError:
                pass
            logger.info("Token file removed, logout complete")