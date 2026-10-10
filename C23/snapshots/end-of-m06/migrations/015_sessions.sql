-- Browser sessions (the authentication course, Module 3).
--
-- The browser keeps only a random session ID in an HttpOnly cookie. The server keeps
-- the rest here: who signed in, when the session ends, and the provider's refresh
-- token (encrypted with SESSION_KEY), so that the server can ask the provider again
-- every few minutes whether the person may still sign in.

-- A sign-in that has started: the state, nonce and PKCE verifier wait here for the
-- provider's answer (one use; ten minutes).
CREATE TABLE login_requests (
    state         text        PRIMARY KEY,
    nonce         text        NOT NULL,
    code_verifier text        NOT NULL,
    return_to     text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz NOT NULL
);

CREATE TABLE sessions (
    -- The SHA-256 of the cookie's value: a copy of this table cannot be used as a cookie.
    session_sha256          text        PRIMARY KEY,
    user_id                 text        NOT NULL REFERENCES users (user_id),
    csrf_token              text        NOT NULL,
    scopes                  text        NOT NULL,
    refresh_token_encrypted bytea,
    access_expires_at       timestamptz NOT NULL,
    created_at              timestamptz NOT NULL DEFAULT now(),
    last_seen_at            timestamptz NOT NULL DEFAULT now(),
    expires_at              timestamptz NOT NULL,
    ended_at                timestamptz,
    end_reason              text,
    CONSTRAINT sessions_end_has_reason CHECK ((ended_at IS NULL) = (end_reason IS NULL))
);
CREATE INDEX sessions_user_idx ON sessions (user_id) WHERE ended_at IS NULL;
