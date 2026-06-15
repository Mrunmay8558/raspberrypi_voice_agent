"""Authentication and session helpers for the dashboard.

This module owns dashboard login credentials, password hashing, and
in-memory session tracking. The FastAPI app initializes one `AuthStore`
instance at startup and exposes it through `app.state`.
"""

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime
from datetime import timedelta
from datetime import timezone
from pathlib import Path

from config import DASHBOARD_AUTH_FILE
from config import DASHBOARD_DEFAULT_USERNAME
from config import DASHBOARD_SESSION_TTL_HOURS
from dashboard.commons.logger import logger

PBKDF2_ITERATIONS = 310_000
SESSION_COOKIE_NAME = "voice_dashboard_session"

logging = logger(__name__)


@dataclass(frozen=True)
class GeneratedCredentials:
    """First-run credentials generated for the dashboard.

    Attributes:
        username: Generated dashboard username.
        password: Generated dashboard password.
    """

    username: str
    password: str


class AuthStore:
    """Persist dashboard credentials and manage active sessions.

    The store keeps a single credential record on disk and tracks
    authenticated browser sessions in memory for the current process.
    """

    def __init__(self, path: Path = DASHBOARD_AUTH_FILE) -> None:
        """Initialize the auth store.

        Args:
            path: Credential file used for the dashboard login.
        """
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, datetime] = {}

    def ensure_credentials(self) -> GeneratedCredentials | None:
        """Create first-run credentials when no auth file exists.

        Returns:
            GeneratedCredentials | None: New credentials for first-run setup,
            or `None` when credentials already exist.
        """
        if self.path.exists():
            return None

        password = self._generate_password()
        self._write_credentials(DASHBOARD_DEFAULT_USERNAME, password)
        logging.warning(
            "Created first-run dashboard login username='%s' password='%s'",
            DASHBOARD_DEFAULT_USERNAME,
            password,
        )
        return GeneratedCredentials(DASHBOARD_DEFAULT_USERNAME, password)

    def verify_password(self, username: str, password: str) -> bool:
        """Validate a username/password pair against stored credentials.

        Args:
            username: Submitted dashboard username.
            password: Submitted dashboard password.

        Returns:
            bool: `True` when the credentials match the stored record.
        """
        record = self._read_record()
        if username != record.get("username"):
            return False

        salt = base64.b64decode(record["salt"])
        expected_hash = base64.b64decode(record["password_hash"])
        actual_hash = self._hash_password(password, salt)
        return hmac.compare_digest(actual_hash, expected_hash)

    def change_password(
        self,
        username: str,
        current_password: str,
        new_password: str,
    ) -> bool:
        """Replace the dashboard password and clear active sessions.

        Args:
            username: Dashboard username.
            current_password: Existing password for verification.
            new_password: Replacement password.

        Returns:
            bool: `True` when the password was updated.
        """
        if not self.verify_password(username, current_password):
            return False
        self._write_credentials(username, new_password)
        self._sessions.clear()
        logging.info("Dashboard password changed for username='%s'", username)
        return True

    def create_session(self, username: str) -> str:
        """Create a new authenticated dashboard session.

        Args:
            username: Authenticated dashboard username.

        Returns:
            str: Session token stored in the browser cookie.
        """
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=DASHBOARD_SESSION_TTL_HOURS
        )
        self._sessions[token] = expires_at
        logging.info("Dashboard session created for username='%s'", username)
        return token

    def verify_session(self, token: str | None) -> bool:
        """Check whether a dashboard session token is still valid.

        Args:
            token: Cookie value submitted by the client.

        Returns:
            bool: `True` when the session exists and is not expired.
        """
        if not token:
            return False
        expires_at = self._sessions.get(token)
        if expires_at is None:
            return False
        if expires_at <= datetime.now(timezone.utc):
            self._sessions.pop(token, None)
            return False
        return True

    def revoke_session(self, token: str | None) -> None:
        """Remove a session token from the active session store.

        Args:
            token: Session token to remove.
        """
        if token:
            self._sessions.pop(token, None)

    def _read_record(self) -> dict:
        """Load the stored credential record from disk."""
        return json.loads(self.path.read_text())

    def _write_credentials(self, username: str, password: str) -> None:
        """Hash and store dashboard credentials on disk.

        Args:
            username: Dashboard username to persist.
            password: Plain-text password to hash and persist.
        """
        salt = secrets.token_bytes(16)
        password_hash = self._hash_password(password, salt)
        record = {
            "username": username,
            "salt": base64.b64encode(salt).decode("ascii"),
            "password_hash": base64.b64encode(password_hash).decode("ascii"),
            "algorithm": "pbkdf2_sha256",
            "iterations": PBKDF2_ITERATIONS,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.path.write_text(json.dumps(record, indent=2))
        self.path.chmod(0o600)

    @staticmethod
    def _hash_password(password: str, salt: bytes) -> bytes:
        """Hash a password with PBKDF2-SHA256."""
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )

    @staticmethod
    def _generate_password() -> str:
        """Generate a random first-run dashboard password."""
        return secrets.token_urlsafe(18)
