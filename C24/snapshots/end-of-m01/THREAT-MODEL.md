# Threat model of the support assistant

Written in Module 1, before any control. It answers four questions: what we protect (the assets in
`DATA-FLOW.md`), who could harm it, how, and which threats to fix first. A **threat** is a way that
someone could get to an asset or cause an action that they should not.

## Actors

| Actor | What they can do | Trusted? |
|---|---|---|
| Support team member (Sam, staff; Grace, owner; Omar, read-only; Camille, two shops) | sign in, ask the assistant for help with a ticket | for their own shop and role only |
| Customer | write the ticket text, choose file names, attach files | no |
| Supplier or anyone with a web page | write a page the assistant may fetch, write a help-document passage | no |
| The model | propose tool calls and write a reply draft | no: it can be persuaded by data |
| Platform administrator (Kwame) | run the platform; has no shop membership | not for a shop's data |

## Threats, scored before any control

Likelihood and impact are 1 (low) to 3 (high). Priority = likelihood x impact. "Existing control" is
what the weak start has: nothing.

| # | Threat (a plausible path) | Asset | Likelihood | Impact | Priority | Existing control |
|---|---|---|---|---|---|---|
| T1 | A ticket asks for another shop's order; `get_order` reads any order | other shop's customer data | 3 | 3 | 9 | none |
| T2 | A ticket or a page makes the model fetch the metadata address or the server's admin page (SSRF) | cloud credentials, the service key | 2 | 3 | 6 | none |
| T3 | A file or ticket makes the model read `../config/service.env` and repeat it | the service key | 2 | 3 | 6 | none |
| T4 | A ticket asks for a refund that the policy does not allow; the write runs at once | the shop's money | 3 | 2 | 6 | none |
| T5 | Text in a tool result tells the model to e-mail data to an outside address | customer data | 2 | 3 | 6 | none |
| T6 | A jailbreak makes the model promise something in the reply (a discount) | the shop's money and name | 3 | 2 | 6 | none |
| T7 | A read-only member's request leads to a write | the shop's money | 2 | 2 | 4 | none |
| T8 | The log and the stored conversations keep every message and contact detail forever | customer data | 3 | 1 | 3 | none |

## What to fix first, and where the course fixes it

1. **T1, T4, T5, T7** (consequences of a model mistake): approval before a write, tenant and customer
   scope, e-mail only to the address on file, an output check. Module 2.
2. **T2, T3** (what a tool can reach): strict contracts, a file sandbox, an allow-list with SSRF
   protection, no write tools for a read-only member, secrets kept out of prompts and logs. Module 3.
3. **T8** (data kept): an inventory, minimized storage with an end date, and a delete. Module 4.
4. **T6** has no complete code control. A person reviews the reply (Module 5), and detection watches
   for it (Module 6).
