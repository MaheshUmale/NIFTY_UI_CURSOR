"""Daily access-token persistence.

Stores and retrieves the Upstox OAuth2 token JSON at ``config/.access_token.json``.
Atomic writes prevent corruption. On POSIX, file permissions are set to 0600.

Source citation:
    > src/auth/AGENTS.md — Token storage, chmod 0600, gitignored.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from src.utils.logger import get_logger
from src.utils.time_utils import now_ist

logger = get_logger(__name__)


class TokenManager:
    """Read/write the Upstox access token from disk.

    Parameters
    ----------
    token_path : str
        Filesystem path to the token JSON. Default ``config/.access_token.json``.
    """

    def __init__(self, token_path: str = "config/.access_token.json") -> None:
        self._token_path = Path(token_path)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_token(self) -> dict[str, Any] | None:
        """Read the token file from disk.

        Returns
        -------
        dict or None
            The parsed token JSON if the file exists and is valid JSON.
            ``None`` if the file is missing or the token is expired.
        """
        if not self._token_path.exists():
            logger.debug("Token file not found at %s", self._token_path)
            return None

        try:
            raw = self._token_path.read_text(encoding="utf-8")
            data: dict[str, Any] = json.loads(raw)
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Failed to read token file: %s", exc)
            return None

        if self.is_expired(data):
            logger.info("Token expired — discarding")
            return None

        return data

    def save_token(self, token_data: dict[str, Any]) -> None:
        """Atomically write the token JSON to disk.

        Writes to a temporary file in the same directory, then renames
        (``os.replace``) to the target path for atomicity.

        On POSIX systems, ``chmod 0o600`` is applied after the rename.
        On Windows, the chmod is silently skipped.
        """
        self._token_path.parent.mkdir(parents=True, exist_ok=True)

        # Atomic write via temp file
        fd, tmp_path = tempfile.mkstemp(
            dir=str(self._token_path.parent),
            prefix=".access_token_tmp_",
            suffix=".json",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as tmp:
                json.dump(token_data, tmp, indent=2)
                tmp.flush()
                os.fsync(fd)

            os.replace(tmp_path, str(self._token_path))

            # POSIX permission mask
            try:
                os.chmod(str(self._token_path), 0o600)
            except (OSError, NotImplementedError):
                pass  # Windows or filesystem that doesn't support chmod

        except Exception:
            # Cleanup the temp file on failure
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            raise

        logger.debug("Token saved to %s", self._token_path)

    def is_expired(self, token_data: dict[str, Any]) -> bool:
        """Check whether the token is past its expiry time.

        Expects a key ``"expires_at"`` containing epoch milliseconds (UTC).
        If the key is missing, the token is considered **not** expired
        (fail-safe — caller will discover expiry at auth time).

        Returns
        -------
        bool
            ``True`` if the token has expired.
        """
        expires_at = token_data.get("expires_at")
        if expires_at is None:
            return False
        return expires_at <= now_ist().timestamp() * 1000