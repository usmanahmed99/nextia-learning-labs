# Incident plan

An **incident** is an event that harms, or could harm, customers, the shops or their data: a secret
in a reply, a refund nobody approved, another shop's data in a reply. This plan says who does what,
in what order, and what evidence to keep. Every step is a command in this project.

## 1. Detect

- `python -m support_assistant detect` reads the audit log; `detect FILE` reads a saved evaluation
  (`eval --attacks --save`). The rules read who, which tenant, which tool and the result code, never
  the message text.
- **High** alerts (`secret_held`, `private_address`) start this plan at once. **Medium** alerts
  (`blocked_tools`, `writes_refused`) are triaged the same day. **Low** alerts are reviewed weekly.

## 2. Contain (minutes)

| Situation | Command | Owner |
|---|---|---|
| A tool is being abused (for example `fetch_url`) | `incident disable-tool fetch_url --reason "..."` | Kwame |
| A user's sign-in may be stolen | `incident revoke usr-sam --reason "..."` | Kwame |
| A wrong change waits for approval | `reject AP-0001 --as usr-grace --reason "..."` | Grace |

The switches work at once, with no new release. `incident status` shows what is off.

## 3. Find out (hours)

- Start from the alert's run IDs and case IDs. Read the stored outcome of each run (the tools it
  used, what was blocked, what it proposed) before you read any customer text.
- Keep the evidence: the audit log rows of the runs, the approval rows, the saved evaluation file.
- Ask: which control stopped it, or which control is missing? Is it in `RESIDUAL-RISKS.md`?

## 4. Recover

- Roll back a wrong change with a new, approved change (a refund cannot be deleted; it is reversed).
- Rotate a secret that was ever sent anywhere. The made-up key in this project opens nothing.
- `incident enable-tool fetch_url` and `incident restore usr-sam` when the fix is in place.

## 5. Tell people

- The affected customers and the shop owner, in plain words: what happened, what data, what we did,
  what they can do. Omar (product) writes it; Grace approves it.
- Whether a regulator must be told, and when, is a legal question: ask a qualified reviewer at once.

## 6. Improve

- Add the attack to the evaluation set as a harmless case, run `eval --attacks --design secure
  --repeat 2 --save`, and compare with the last saved run.
- Update `THREAT-MODEL.md` and `RESIDUAL-RISKS.md`.
