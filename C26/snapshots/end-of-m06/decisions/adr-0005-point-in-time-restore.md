# ADR-0005: Point-in-time restore, tested every quarter

## Status

Accepted. Mei and Omar.

## Context

Q7: back within 4 hours (RTO), lose at most 1 hour of new data (RPO). A nightly dump can lose up to 24 hours of answers and uploads. The data copy itself is fast: the databases course restored 316 MB in 7.9 s on a laptop (measured); the rest of the recovery time is people and a new server (assumptions in design.toml [recovery]).

## Options

1. A nightly dump to file storage: simple, RPO 24 hours.
2. The managed service's point-in-time restore: RPO of minutes (from the provider's documentation; to test), a restore makes a new server.

## Decision

Option 2, with a restore test every quarter that records the real time of every step.

## Consequences

- The RPO target is met on paper; the first restore test shows if the RTO is too.
- Files in file storage need their own protection (soft delete and versions), because the database restore does not bring them back.

## Revisit when

- A restore test takes more than 2 hours, or
- a tenant asks for an RPO under 5 minutes.
