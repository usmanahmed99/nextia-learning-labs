# Access matrix

Who may do what in the help desk. Every request answers three questions on the server:

1. **Who is the caller?** A user ID from a checked token (Module 2). Never a name or an email
   address that the browser sends.
2. **In which organization?** The tenant in the request path (`larkfield` or `bramble`), and the
   caller's membership there. Never a tenant ID that the browser sends in a header or a body.
3. **What may they do there?** The role of that membership. A role belongs to a membership, not
   to a person.

The code is `ticket_api/access.py`; `python -m scripts.access_matrix` prints this table from it.

## Roles

| Action | What it is | owner | staff | read_only |
|---|---|---|---|---|
| `ticket.read` | list and read tickets, find similar tickets | yes | yes | yes |
| `ticket.write` | add a message to a ticket | yes | yes | 403 |
| `file.read` | get a download link for an attachment | yes | yes | yes |
| `file.upload` | upload an attachment | yes | yes | 403 |
| `document.read` | search the public help documents | yes | yes | yes |
| `document.read_staff` | also the staff-only documents | yes | yes | 403 |
| `member.read` | list the members of the organization | yes | yes | 403 |
| `member.manage` | invite, change a role, remove a member | yes | 403 | 403 |
| `export.create` | start a background export of tickets | yes | yes | 403 |
| `audit.read` | read the organization's audit events | yes | 403 | 403 |

## Rules

- **No membership: 404, for everything.** A person who is not a member of the organization gets
  the same answer as for an organization or a ticket that does not exist. They learn nothing,
  not even that the record exists.
- **A member whose role does not allow the action: 403.** They can already see the record, so a
  403 tells them nothing new.
- **A record of another organization: 404.** Every query includes the organization, so a ticket
  ID of the other shop is "not found", even when the ID is right.
- The platform administrator role (Kwame) is not a tenant role. It opens no organization's
  tickets by itself.

## Support access (Module 5)

A platform administrator who must help an organization asks for **support access**: one
organization, a reason of at least 10 characters, at most 60 minutes. It gives one action,
`ticket.read`, and nothing else. The organization's owner sees every grant
(`GET /v1/tenants/{tenant}/support-access`) and every use in the audit
(`support_access.used`, allowed or denied).

| Action | support (with an active grant) |
|---|---|
| `ticket.read` | yes |
| everything else | 403 |
| any action in another organization | 404 |

## Changes over time (Module 5)

| Change | When it takes effect |
|---|---|
| A member is removed, or their role changes | at their next request (memberships are read on every request) |
| A job was queued before the change | when the job runs: the worker checks the membership again |
| A cached answer | never served without the check: the check runs first, and every key starts with the organization and the access level |
| The person is disabled at the identity provider | a browser session: at its next refresh (within 10 minutes); an access token: until it expires (10 minutes + 30 seconds leeway) |
| An invitation | until it is used once, taken back, or expired (72 hours by default, 168 at most) |
| The organization is deleted | at once (status `deleting`); its records are purged by the worker |

## Worked example: Camille

Camille has two memberships: `staff` at Larkfield and `read_only` at Bramble Books.

| Request | Organization | Role | Decision |
|---|---|---|---|
| read ticket T-30002 | larkfield | staff | allowed |
| add a message to T-30002 | larkfield | staff | allowed |
| read ticket T-40001 | bramble | read_only | allowed |
| add a message to T-40001 | bramble | read_only | 403 (`read_only may not ticket.write`) |
| read T-40001 through Larkfield's path | larkfield | staff | 404 (not a Larkfield ticket) |
