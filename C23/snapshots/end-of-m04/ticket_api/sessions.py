"""Browser sessions: the backend keeps the tokens, the browser keeps a cookie (Module 3).

A session has three clocks:
- idle:      it ends after SESSION_IDLE_MINUTES without a request (default 30)
- absolute:  it ends SESSION_MAX_HOURS after sign-in, whatever happens (default 8)
- provider:  when the access token's time is over (10 minutes), the server uses the refresh
             token to ask the provider again. If the provider says no (the account was
             disabled, the refresh token was revoked), the session ends at that request.

The cookie's value is a random 256-bit ID; the table keeps only its SHA-256. The refresh
token is kept encrypted (Fernet, from the cryptography package) with SESSION_KEY.
"""

import hashlib
import logging
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

import psycopg
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger("ticket_api")

COOKIE = "ticket_session"


class SessionEnded(Exception):
    """The session cookie names no session, or a session that has ended."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Session:
    session_sha256: str
    user_id: str
    csrf_token: str
    scopes: frozenset[str]
    expires_at: datetime
    idle_expires_at: datetime


def digest(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def now() -> datetime:
    return datetime.now(UTC)


class SessionStore:
    def __init__(self, key: str | None, idle_minutes: float = 30, max_hours: float = 8):
        if not key:
            logger.warning("SESSION_KEY is not set: sessions end when the API stops")
            key = Fernet.generate_key().decode()
        self.fernet = Fernet(key)
        self.idle = timedelta(minutes=idle_minutes)
        self.max = timedelta(hours=max_hours)

    # ---------- sign-in ----------

    def start_login(self, conn: psycopg.Connection, return_to: str) -> tuple[str, str, str]:
        """A new sign-in: returns (state, nonce, code_verifier), kept for ten minutes."""
        state, nonce = secrets.token_urlsafe(24), secrets.token_urlsafe(24)
        # RFC 7636: a verifier has 43 to 128 characters. (The first version of this code made
        # 32; the practice provider took it, Keycloak refused it: "invalid_code_verifier".)
        verifier = secrets.token_urlsafe(48)  # 64 characters
        conn.execute("DELETE FROM login_requests WHERE expires_at < now()")
        conn.execute(
            "INSERT INTO login_requests (state, nonce, code_verifier, return_to, expires_at)"
            " VALUES (%s, %s, %s, %s, now() + interval '10 minutes')",
            (state, nonce, verifier, return_to),
        )
        return state, nonce, verifier

    def finish_login(self, conn: psycopg.Connection, state: str) -> dict | None:
        """The waiting sign-in for this state, used once (deleted), or None."""
        return conn.execute(
            "DELETE FROM login_requests WHERE state = %s AND expires_at > now()"
            " RETURNING nonce, code_verifier, return_to",
            (state,),
        ).fetchone()

    def create(
        self,
        conn: psycopg.Connection,
        user_id: str,
        scopes: str,
        refresh_token: str | None,
        access_expires_at: datetime,
    ) -> str:
        """A new session with a NEW random ID (never one the browser brought: that would allow
        session fixation). Returns the cookie's value."""
        value = secrets.token_urlsafe(32)
        conn.execute(
            "INSERT INTO sessions (session_sha256, user_id, csrf_token, scopes,"
            " refresh_token_encrypted, access_expires_at, expires_at)"
            " VALUES (%s, %s, %s, %s, %s, %s, %s)",
            (
                digest(value),
                user_id,
                secrets.token_urlsafe(24),
                scopes,
                self.fernet.encrypt(refresh_token.encode()) if refresh_token else None,
                access_expires_at,
                now() + self.max,
            ),
        )
        return value

    # ---------- every request ----------

    def load(self, conn: psycopg.Connection, value: str) -> dict:
        """The session row of a cookie, if it is still valid; else SessionEnded (and the row
        is marked ended with the reason)."""
        row = conn.execute(
            "SELECT * FROM sessions WHERE session_sha256 = %s", (digest(value),)
        ).fetchone()
        if row is None:
            raise SessionEnded("unknown")
        if row["ended_at"] is not None:
            raise SessionEnded(row["end_reason"])
        t = now()
        if t >= row["expires_at"]:
            self.end(conn, row["session_sha256"], "absolute_timeout")
            raise SessionEnded("absolute_timeout")
        if t >= row["last_seen_at"] + self.idle:
            self.end(conn, row["session_sha256"], "idle_timeout")
            raise SessionEnded("idle_timeout")
        return row

    def touch(self, conn: psycopg.Connection, row: dict) -> Session:
        conn.execute(
            "UPDATE sessions SET last_seen_at = now() WHERE session_sha256 = %s",
            (row["session_sha256"],),
        )
        return Session(
            session_sha256=row["session_sha256"],
            user_id=row["user_id"],
            csrf_token=row["csrf_token"],
            scopes=frozenset(row["scopes"].split()),
            expires_at=row["expires_at"],
            idle_expires_at=now() + self.idle,
        )

    def refresh_token(self, row: dict) -> str | None:
        if row["refresh_token_encrypted"] is None:
            return None
        try:
            return self.fernet.decrypt(bytes(row["refresh_token_encrypted"])).decode()
        except InvalidToken:  # SESSION_KEY changed: the old sessions cannot be read
            return None

    def renewed(
        self, conn: psycopg.Connection, row: dict, refresh_token: str, access_expires_at: datetime
    ) -> None:
        conn.execute(
            "UPDATE sessions SET refresh_token_encrypted = %s, access_expires_at = %s"
            " WHERE session_sha256 = %s",
            (self.fernet.encrypt(refresh_token.encode()), access_expires_at, row["session_sha256"]),
        )

    def end(self, conn: psycopg.Connection, session_sha256: str, reason: str) -> None:
        conn.execute(
            "UPDATE sessions SET ended_at = now(), end_reason = %s"
            " WHERE session_sha256 = %s AND ended_at IS NULL",
            (reason, session_sha256),
        )

    def end_all_for(self, conn: psycopg.Connection, user_id: str, reason: str) -> int:
        return conn.execute(
            "UPDATE sessions SET ended_at = now(), end_reason = %s"
            " WHERE user_id = %s AND ended_at IS NULL",
            (reason, user_id),
        ).rowcount
