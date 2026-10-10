-- Forward repair: fill score for the rows that version 1.1.0 wrote during the
-- rollout of 1.2.0. Run it after no 1.1.0 instance is left, so no new empty
-- rows appear. It changes no structure, so every version keeps working.
UPDATE classifications SET score = confidence WHERE score IS NULL;
