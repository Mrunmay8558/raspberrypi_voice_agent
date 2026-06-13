import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from loguru import logger

from config import DASHBOARD_AUTH_FILE
from config import DASHBOARD_DEFAULT_USERNAME
from config import DASHBOARD_SESSION_TTL_HOURS

PBKDF2_ITERATIONS = 310_000
SESSION_COOKIE_NAME = "voice_dashboard_session"


@dataclass(frozen=True)
class GeneratedCredentials:
    username: str
    password: str


class AuthStore:
    def __init__(self, path: Path = DASHBOARD_AUTH_FILE) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, datetime] = {}

    def ensure_credentials(self) -> GeneratedCredentials | None:
        if self.path.exists():
            return None

        password = self._generate_password()
        self._write_credentials(DASHBOARD_DEFAULT_USERNAME, password)
        logger.warning(
            "Created first-run dashboard login username='{}' password='{}'",
            DASHBOARD_DEFAULT_USERNAME,
            password,
        )
        return GeneratedCredentials(DASHBOARD_DEFAULT_USERNAME, password)

    def verify_password(self, username: str, password: str) -> bool:
        record = self._read_record()
        if username != record.get("username"):
            return False

        salt = base64.b64decode(record["salt"])
        expected_hash = base64.b64decode(record["password_hash"])
        actual_hash = self._hash_password(password, salt)
        return hmac.compare_digest(actual_hash, expected_hash)

    def change_password(
        self, username: str, current_password: str, new_password: str
    ) -> bool:
        if not self.verify_password(username, current_password):
            return False
        self._write_credentials(username, new_password)
        self._sessions.clear()
        logger.info("Dashboard password changed for username='{}'", username)
        return True

    def create_session(self, username: str) -> str:
        token = secrets.token_urlsafe(32)
        expires_at = datetime.now(timezone.utc) + timedelta(
            hours=DASHBOARD_SESSION_TTL_HOURS
        )
        self._sessions[token] = expires_at
        logger.info("Dashboard session created for username='{}'", username)
        return token

    def verify_session(self, token: str | None) -> bool:
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
        if token:
            self._sessions.pop(token, None)

    def _read_record(self) -> dict:
        return json.loads(self.path.read_text())

    def _write_credentials(self, username: str, password: str) -> None:
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
        return hashlib.pbkdf2_hmac(
            "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
        )

    @staticmethod
    def _generate_password() -> str:
        return secrets.token_urlsafe(18)
