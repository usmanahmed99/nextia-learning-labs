# Dataset card: the support assistant's practice data

**What it is.** Made-up data for the AI security course of Nextia Learning: a help-desk platform that two shops share, **Larkfield** (a home-and-garden shop) and **Bramble Books** (a bookshop). It holds their customers, orders, support tickets, attached files and help-desk documents, a small fake website, two made-up secrets, and a security evaluation set: normal tasks and harmless attacks.

**Licence.** CC0 1.0 (public domain). Use it for anything.

**Everything is made up.**

- No real person wrote a ticket or placed an order. Names, cities, e-mail addresses (all end in `.example`) and phone numbers (the 555-01xx range kept for fiction) are invented.
- The two "secrets" (a payment service key and a cloud token) are random strings in the shape of real ones. They open nothing. The tests look for them in everything the assistant says, sends or requests.
- Every web address is a `.example` host or a private address. Only the project's simulated network answers them. Nothing is sent to the internet.

**The attacks are harmless and local.** Each attack tries to make the practice assistant do one forbidden but harmless thing: reveal a made-up secret, call a tool it should not, send to a made-up outside address, or read the other shop's made-up records. Use them only against the practice app on your own computer. Never test a system that you do not own or have permission to test.

## Files

| File | What it holds |
|---|---|
| `helpdesk.sqlite` | tenants, users, memberships (owner, staff, read_only), customers, orders and items, tickets, file metadata, documents (passages, with a full-text index), the write tables (refunds, return labels, e-mails) and the approvals table |
| `vfs/` | the assistant server's file area: `files/<shop>/<ticket>/...` (attachments) and `config/service.env` (the made-up payment key) |
| `web/hosts.json`, `web/pages.jsonl` | the fake websites: who runs each host, its address, and which shop may fetch from it |
| `tasks.jsonl` | normal tasks the assistant must still do, with the expected writes and answer checks |
| `attacks.jsonl` | the attacks, by slice, with the goal of each one |
| `secrets.json` | the two made-up secrets, so that the checks can find them |
| `SHA256SUMS` | a fingerprint of every file |

## How it was made

`reference/c24/data/build_data.py` writes every file. It needs no network and no model, and two runs write the same bytes. The Larkfield policy passages are the agents course's 24 passages, unchanged (including the AquaFlow supplier passage with its hidden instruction); four Larkfield documents and three Bramble Books documents were written for this course. Orders taken from the earlier courses keep their IDs, customers, items and dates. The course's "today" is Friday 9 October 2026; 12 October 2026 is a holiday.

**Who wrote the expected results.** The course author wrote each task's expected writes and answer checks by applying Larkfield's written policy to the ticket and the data. It is one person's reading of a written policy. The attacks are constructed: they were written for this course, and each one is labelled as constructed.

## Limits

- Small: a few dozen tasks and attacks. A result on this set is a snapshot of one model, one prompt and one date, not a guarantee.
- English, with a few French and German tickets. Other languages are not tested.
- The answer checks are patterns in text. A right answer in unexpected words can fail a check; read the failures.
