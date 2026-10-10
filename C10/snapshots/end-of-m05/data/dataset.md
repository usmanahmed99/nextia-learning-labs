# Dataset card: Larkfield support-resolution tasks

The data of the course *AI Agents and Workflow Orchestration* on Nextia Learning. Everything is made up for the course: no real customer wrote these tickets, the orders and payments are invented, and every write goes to a local practice database.

- **Licence:** CC0 1.0 (public domain dedication). Use it for anything.
- **Version:** 1.0, built by `reference/c10/data/build_data.py` in the site repository (no network, no model, no random numbers; two builds give identical `SHA256SUMS`).
- **The course's "today":** Friday 9 October 2026. Every date rule uses it.

## Files

| File | What it holds |
|---|---|
| `tasks.jsonl` | 70 resolution tasks: the ticket (text, attachments, customer), the slice, the expected outcome and actions, accepted alternative outcomes, forbidden changes, text the reply must not contain, and the simulated failures of the task |
| `larkfield.sqlite` | The practice database: 86 customers, 31 products (with stock), 87 orders, 98 order items, 89 boxes (shipments), 95 payments, 3 earlier refunds and 3 earlier return labels; empty tables for the writes (refunds, return labels, reshipments, ticket notes) and the operations register |
| `orders.csv`, `order_items.csv`, `payments.csv`, `shipments.csv` | The same orders as CSV, to read without SQL |
| `policy_passages.jsonl` | 24 passages from the policy collection of the RAG course (same text, version and dates), searched by the `search_policy` tool |
| `policy.md` | Grace's resolution policy: when a person must handle a ticket (H1 to H5) and the resolution rules (W1 to W8) |

## The tasks

| Slice | Tasks | What it tests |
|---|---|---|
| simple | 16 | one lookup and one action, a reply, or a request the workflow does not handle |
| multi_step | 11 | two orders, a missing box, payments to read, an order to find without its ID, a photo that is missing |
| needs_person | 10 | rules H1 to H5: safety, legal threats, requests outside the policy, unreadable tickets |
| policy | 9 | the edges of the rules: day 30 and day 31 of the return window, day 14 and 16 for damage, exactly 5 and 15 business days late, the returns policy version 4 that is not in force yet, a used item |
| adversarial | 8 | instructions inside a ticket, inside a courier note, inside an order's gift message and inside a supplier's policy passage; another customer's order; a made-up approval |
| failure | 8 | simulated failures of the mock services: a timeout, a service that is down, a refused write, and a timeout after the write (the change happened but the caller does not know) |
| new_wording | 8 | the same kinds of request in other words and in French, written after the fixed workflow's keyword lists were frozen |

Expected outcomes: resolve 28 (33 write actions), hand_to_person 22, reply_only 17, ask_customer 3. Eighteen tickets come from the LLM applications course (same ticket IDs, customers, text and orders); 52 were written for this course.

## How the labels were made

The course author read every ticket and applied Grace's written policy (`policy.md`) to the ticket and the state of the database, then wrote the expected outcome, the actions and a note with the reason. `check_labels.py` holds the course author's reading of each ticket (what the customer asks for, which order and item, whether a photo is attached, what the customer prefers, or which H rule applies) and applies the date and amount rules in code: it agrees with all 70 labels. Every task where a recorded run disagreed with the label was read again (`reference/c10/recordings/REVIEW.md`); one label changed on review (T-65001, from reply_only to hand_to_person, reply_only still accepted) and one task gained an accepted second outcome (T-90202, ask_customer).

It is one person's reading of a written policy. Six tasks accept a second outcome where the policy allows two readings (for example asking for the order ID instead of finding it). The fixed workflow's keyword lists were written by the same person who wrote the first 62 tasks, so on those tasks the fixed workflow is an optimistic baseline; the 8 `new_wording` tasks were written after those lists were frozen.

## Limits

- Made-up tickets are cleaner than real ones: few typos, one request per ticket in most cases.
- The policy is small and every rule is written down. Real policies have gaps that people fill.
- The failures are simulated by the mock services; real services fail in more ways.
- No real personal data: customer IDs only, a few first names, no addresses, no card numbers.
