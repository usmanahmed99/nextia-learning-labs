# ADR-0004: Managed PostgreSQL, not a database on our own virtual machine

## Status

Accepted. Mei.

## Context

Build versus buy. List prices (prices.toml): managed PostgreSQL B1ms with 32 GB storage costs about US$17.55 a month; PostgreSQL on our own B2s virtual machine with a P10 disk about US$53.58. People's time is an assumption (design.toml [labour]): 1 hour a month for the managed server, 6 hours for our own, at US$60 an hour.

## Options

1. Managed PostgreSQL flexible server: backups, point-in-time restore and minor updates included.
2. PostgreSQL on our own virtual machine: full control, we do backups, updates and restores.

## Decision

Option 1: US$77.55 a month with people's time, against US$413.58.

## Consequences

- The cheapest machine is not the cheapest total: people's time is the biggest cost of option 2.
- We depend on the provider's versions and extensions (pgvector must be on its list).

## Revisit when

- We need an extension the managed service does not offer, or
- the database needs more than a General Purpose 4 vCore server, where the machine price starts to matter more than people's time.
