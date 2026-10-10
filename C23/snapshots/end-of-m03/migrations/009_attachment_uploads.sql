-- Uploads through signed URLs (Module 5): a row is made before the file exists
-- ("pending"), and becomes "stored" only after the API has checked the file.
ALTER TABLE attachments
    ADD COLUMN status text NOT NULL DEFAULT 'stored',
    ADD COLUMN created_at timestamptz NOT NULL DEFAULT now(),
    ALTER COLUMN sha256 DROP NOT NULL,
    ALTER COLUMN uploaded_at DROP NOT NULL,
    ADD CONSTRAINT attachments_status_known CHECK (status IN ('pending', 'stored', 'rejected')),
    ADD CONSTRAINT attachments_stored_is_complete
        CHECK (status <> 'stored' OR (sha256 IS NOT NULL AND uploaded_at IS NOT NULL)),
    -- The largest file the help desk keeps: 10 MiB.
    ADD CONSTRAINT attachments_size_limit CHECK (size_bytes <= 10485760);
ALTER TABLE attachments ALTER COLUMN status SET DEFAULT 'pending';
-- The clean-up job looks for old pending uploads.
CREATE INDEX attachments_pending_idx ON attachments (created_at) WHERE status = 'pending';
