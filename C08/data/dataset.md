# Dataset card: Larkfield help-desk evaluation set and orders (LLM applications course)

Used by: every lesson, snapshot and notebook of *Building Reliable Applications with LLM APIs* (folder `C08/`). The project `ticket-assistant` keeps a copy in its `data/` folder (`tickets.csv` = `eval_tickets.csv`).

| Field | Value |
|---|---|
| Source | Built for the course by [`build_data.py`](build_data.py) in this folder (rebuild: `python build_data.py ../../C06/data/valid.csv rebuilt/`, then compare with `SHA256SUMS`; no network, no model). 60 ticket texts come from the deep learning course's validation file (`C06/data/valid.csv`, CC0); 9 tickets, all customer IDs and all orders were written for this course. |
| Publisher / creator | Nextia Learning. The 60 reused texts were written by Claude Haiku 5.5 for the deep learning course (see its card). The 9 new tickets, the orders and the `needs_human` labels were written by the course lead, 2026-10-08. |
| Licence | CC0 1.0 (public domain dedication) |
| Attribution text | None required. "Synthetic data from Nextia Learning" is welcome. |
| Version or access date | 1.0, built 2026-10-08 |
| File used | `eval_tickets.csv`, `orders.csv`, `order_items.csv`, `orders.sqlite`, `policy.md`, kept in `data/`: yes |
| SHA-256 | See [`SHA256SUMS`](SHA256SUMS). |
| Size | 69 tickets × 9 columns (21 KB); 34 orders × 9 columns and 36 order lines × 4 columns; SQLite 16 KB |

## What one row means

`eval_tickets.csv`: one row is the first message of one support ticket to Larkfield, a fictional online home-and-garden shop in Canada, with the customer who sent it. The expected answers are `team` (`delivery`, `returns`, `payment`, `warranty`, `account`) and `needs_human` (`true` when a person must handle the ticket). The assistant must find both from the text.

| Column | Meaning |
|---|---|
| `ticket_id` | `T-6xxxx` (from the deep learning course) or `T-8000n` (written for this course) |
| `customer_id` | Who sent the ticket (`C-` and 5 digits). The help-desk app knows it; the model does not get it. |
| `text` | The customer's message. Empty for one ticket. |
| `attachments` | File names attached to the ticket (only `T-80006`). |
| `team` | The expected team. Empty for `T-80006` (no text: no team can be scored). |
| `needs_human` | The expected value, from the rule below. |
| `style` | How the ticket was written (not an input): the deep learning course's styles, or the case the course ticket covers (`other_customer`, `injection`, `refund_request`, `safety`, `french`, `empty`, `legal_threat`, `order_status`, `bad_order_id`). |
| `source` | `c06-valid` or `course` |
| `needs_human_rule` | The rule (H1 to H5) that makes `needs_human` true, else empty. |

`orders.csv` / `orders.sqlite` table `orders`: one order (`LK-` and 6 digits) with its customer, `status` (`processing`, `shipped`, `delivered`, `return_requested`, `return_received`, `refunded`, `cancelled`), dates, shipping fee and total in CAD. `order_items.csv` / table `order_items`: the products of each order.

## How it was made

1. **60 tickets from the deep learning course.** The validation file sorted by `ticket_id`, `random.Random(8)`; for each team (alphabetical) and each style, the tickets of that team and style shuffled, and the first ones taken whose order IDs are not used yet. Quota per team: plain 2, boundary 2, two_topics 2, negation 1, short 1, distractor 1, request_last 1, typos 1, long 1 (12 per team, 60 in all).
2. **9 tickets written for this course**, for what the 60 lack: an order ID of another customer (`T-80001`), a prompt-injection attempt (`T-80002`), a refund request that the assistant must not carry out (`T-80003`), a safety issue with a burn (`T-80004`), a French ticket (`T-80005`), an empty ticket with only an attachment (`T-80006`), a legal threat (`T-80007`), an order-status question (`T-80008`), and a mistyped order ID with 5 digits (`T-80009`; the real order is `LK-551906`).
3. **needs_human** follows the written rule in `policy.md` ("When a person must handle the ticket": H1 safety, H2 legal, H3 outside the policy, H4 access, H5 no readable request). The lead read every ticket and applied the rule by hand; the true cases and their rules are listed in `build_data.py`. Then the labels were reviewed against the recorded answers of both hosted models: every ticket where a model disagreed was read again. One label changed on review: `T-80003` (a refund without sending the item back) is true under H3, because the policy does not allow it. Four others stayed `false` although some models said `true`, because the ticket does not meet a rule: `T-64849`, `T-64960`, `T-65047` (a pan handle that came off: no safety concern is mentioned) and `T-65177`. One judgement call: `T-65266` (a split paddling pool, "I don't want it to be unsafe") counts as H1, because the rule says "even as a worry".
4. **Customer IDs**: unique, from `random.Random(9)`, for the 60 tickets; fixed for the 9 course tickets.
5. **Orders**: the 21 orders named in the tickets, written by hand to agree with what each ticket says (for example `LK-374058`: a return was requested but has not arrived; `LK-640933`: not dispatched yet, so the delivery slot can change), the real order behind the mistyped ID, the neighbour's order of `T-80001` (another customer), and 12 orders of other customers from `random.Random(10)`. Prices are made up; shipping is 9.95 under 100 dollars, free above.
6. The SQLite file is built from the same rows. Its header field "SQLite version that wrote the file" is set to 3.50.4, so the file is the same byte for byte on every computer.

Teams: account 12, delivery 17, payment 13, returns 13, warranty 13, none 1. `needs_human` true: 9 (H1 4, H2 1, H3 1, H4 2, H5 1).

## Why this dataset

The course builds an application, not a model: it needs a small, fixed set of tickets that is the same in every lesson, so that two prompt versions or two models can be compared fairly, and a few hard cases that real help desks see. Reusing the deep learning course's tickets connects the courses (the same five teams) and keeps the labels that two models agreed on. Real tickets and orders contain personal data and are not open.

## Changes we made

The 60 reused texts are unchanged. Columns `customer_id`, `attachments`, `needs_human`, `source` and `needs_human_rule` are new.

## Limitations and cautions

- Synthetic: the tickets and orders are more regular than real ones. 69 tickets are enough to see differences of several tickets, not of one or two.
- Only 9 tickets have `needs_human` true, so "needs_human agreement" is dominated by the easy `false` cases: always report how many of the 9 a model caught.
- `needs_human` is one person's reading of a written rule. Another reader could decide some boundary tickets differently.
- Do not use the data to judge any real company, product or customer.
