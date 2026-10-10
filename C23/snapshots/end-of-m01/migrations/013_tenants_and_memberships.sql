-- Organizations (tenants), the people who sign in (users), and who may do what
-- where (memberships with a role). The authentication course, Module 1.
--
-- A user is identified by the identity provider's stable user ID (the token's
-- "sub"), never by an email address: an address can change, and two providers
-- can have the same one. A role belongs to a membership, not to a user: Camille
-- is staff at Larkfield and read-only at Bramble Books.
CREATE TABLE tenants (
    tenant_id  text        PRIMARY KEY,
    name       text        NOT NULL,
    status     text        NOT NULL DEFAULT 'active',
    created_at timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT tenants_id_format CHECK (tenant_id ~ '^[a-z][a-z0-9-]{1,30}$'),
    CONSTRAINT tenants_status_known CHECK (status IN ('active', 'deleting'))
);

CREATE TABLE users (
    user_id       text        PRIMARY KEY,
    name          text        NOT NULL,
    email         text        NOT NULL,
    -- A platform role is not a tenant role: it never opens a tenant's data by itself.
    platform_role text,
    created_at    timestamptz NOT NULL DEFAULT now(),
    CONSTRAINT users_platform_role_known CHECK (platform_role IN ('platform_admin'))
);
-- Not unique: the same address can come from two providers (or two accounts) with two
-- different user IDs. An email address is contact data, never the key of a person.
CREATE INDEX users_email_idx ON users (lower(email));

CREATE TABLE memberships (
    tenant_id  text        NOT NULL REFERENCES tenants (tenant_id),
    user_id    text        NOT NULL REFERENCES users (user_id),
    role       text        NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (tenant_id, user_id),
    CONSTRAINT memberships_role_known CHECK (role IN ('owner', 'staff', 'read_only'))
);
-- "Which organizations is this user a member of?" (the other direction of the key).
CREATE INDEX memberships_user_idx ON memberships (user_id);

-- An invitation is a one-time code for one email address and one role. Only the
-- code's SHA-256 is stored: a copy of the database does not give the codes away.
CREATE TABLE invitations (
    invitation_id uuid        PRIMARY KEY,
    tenant_id     text        NOT NULL REFERENCES tenants (tenant_id),
    email         text        NOT NULL,
    role          text        NOT NULL,
    code_sha256   text        NOT NULL UNIQUE,
    invited_by    text        NOT NULL REFERENCES users (user_id),
    created_at    timestamptz NOT NULL DEFAULT now(),
    expires_at    timestamptz NOT NULL,
    accepted_at   timestamptz,
    accepted_by   text        REFERENCES users (user_id),
    revoked_at    timestamptz,
    CONSTRAINT invitations_role_known CHECK (role IN ('owner', 'staff', 'read_only')),
    CONSTRAINT invitations_expiry_after_creation CHECK (expires_at > created_at),
    CONSTRAINT invitations_accepted_has_user CHECK ((accepted_at IS NULL) = (accepted_by IS NULL))
);

-- Every row that exists today belongs to the first organization.
INSERT INTO tenants (tenant_id, name, created_at) VALUES ('larkfield', 'Larkfield', '2024-01-08 09:00:00+00');
