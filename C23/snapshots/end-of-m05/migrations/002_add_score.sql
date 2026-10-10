-- Expand: add the new column next to the old one. It may be empty, because
-- version 1.1.0 of the app still writes rows without it during the rollout.
ALTER TABLE classifications ADD COLUMN IF NOT EXISTS score real;
