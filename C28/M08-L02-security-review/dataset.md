# Dataset card: support data of Larkfield and Bramble Books (synthetic), with a constructed prototype server

Used by: MCP: Connect AI Applications to Tools and Data, case study *Security review of an MCP integration*, `starter.zip` and `finished.zip` (folder `data/`)

| Field | Value |
|---|---|
| Source | Made up for Nextia Learning's course *MCP: Connect AI Applications to Tools and Data* (its project's `data/` folder, built by the course team). The prototype server `helpdesk-mcp` was written for this case study, with its weaknesses on purpose. |
| Publisher / creator | Nextia Learning |
| Licence | Data: [CC0 1.0](https://creativecommons.org/publicdomain/zero/1.0/) (public domain). Code: MIT (`LICENSE` in the project). |
| Attribution text | None needed. "Synthetic support data from Nextia Learning" is welcome. |
| Version or access date | Data version 1.0, the same bytes as the course project (see `data/SHA256SUMS`). Prototype version 0.3.0. |
| File used | `documents.jsonl`, `tickets.jsonl`, `tenants.csv`, `users.csv`, `memberships.csv`, kept in `data/`: yes |
| SHA-256 | `tickets.jsonl` 8573c0e7ed5ab7858cc66af5bd3e2e21a714e8f6315374937982ae59edaa1215; `memberships.csv` 27355a53ba38d5e13fc4de00bc7e1518fd9e185de4ee60c68dd67f2b56ca16c0; `documents.jsonl` f0c2960a8ae090d19e5962e3ea589648ff1ca5d6284a2ea9c4d851f2204fad34 (all in `data/SHA256SUMS`) |
| Size | 14 policy documents, 21 tickets, 2 organizations, 7 people, 6 memberships; under 60 KB |

## What one row means

A ticket is one customer's support request to one shop (Larkfield or Bramble Books). A membership gives one person one role in one shop: `owner`, `staff` or `read_only`. There is no target: the case study does not predict anything. It measures which attacks on the server get through and which normal requests still work.

## Why this dataset

A security review needs a system with people, organizations, roles, tokens and a write. The course's synthetic data has all of them, with fixed IDs that the course's lessons already use, and no real person in it. Attacking it is harmless, and it can be shared. Two open projects of deliberately vulnerable MCP servers were compared and not chosen (see `DATASET-RESEARCH.md` in the course repository): one has no licence file, uses an older protocol and needs Docker; the other is MIT but covers other weaknesses (code execution, outbound requests) and has no organizations, tokens or approvals.

## Changes we made

None to the data. The prototype server `helpdesk-mcp` 0.3.0 is new: it has five constructed weaknesses (a poisoned tool description, a token passed on to the ticket API, an organization chosen by the model, a refund recorded at once, and the host's whole environment passed to the server).

## Limitations and cautions

- Synthetic and small: 2 shops, 7 people. Bramble Books has one owner and no staff member, which the case study shows matters.
- Ticket T-30201 contains a constructed instruction to an AI assistant (from the course). The prototype's poisoned description is constructed too.
- The ticket API is a stub: it checks tokens like a real service but trusts its caller to name the organization.
- Do not run the prototype on a shared machine or a network, and do not reuse its code.
