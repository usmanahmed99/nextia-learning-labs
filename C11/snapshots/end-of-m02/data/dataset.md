# Dataset card: Larkfield support tickets for evaluation

Used by: every lesson, snapshot and notebook of *Evaluating and Testing AI Systems* (folder `C11/`). The project `eval-harness` keeps a copy in its `data/` folder.

| Field | Value |
|---|---|
| Source | Built for the course by `build_data.py` in the labs folder `C11/data/` (no network, no model; rebuild: `python build_data.py ../.. rebuilt/` in that folder, then compare with `SHA256SUMS`). 140 ticket texts come from the deep learning course's ticket files (`C06/data/valid.csv` and `test.csv`, CC0). 69 come from the evaluation set of the LLM applications course (`C08/data/eval_tickets.csv`, CC0). 2 are the examples written inside that course's prompt v2. 60 were written for this course. |
| Publisher / creator | Nextia Learning. The reused texts were written by language models for the deep learning course (see its card). The 60 new tickets, every label of this set and every review decision were made by the course author, 2026-10-09. |
| Licence | CC0 1.0 (public domain dedication) |
| Attribution text | None required. "Synthetic data from Nextia Learning" is welcome. |
| Version | The version is the first 12 characters of the SHA-256 of `cases.jsonl` (`python -m harness cases` prints it). Built 2026-10-09. |
| Files | `cases.jsonl`, `policy.md` (Grace's support policy, unchanged from the LLM applications course), `SHA256SUMS` |
| Size | 271 cases (one JSON object per line, about 280 KB) |

The tickets are made up for this course. No real customer wrote them.

## What one row means

One row is one **case**: the first message of a support ticket to Larkfield, a fictional online home-and-garden shop in Canada, with the answers that a good assistant gives. The assistant must choose the `team`, decide whether a person must handle the ticket (`needs_human`) and draft a reply.

| Field | Meaning |
|---|---|
| `case_id` | `T-6xxxx` (from the deep learning course), `T-8000n` (from the LLM applications course), `T-810nn` (written for this course), `P-V2-EXn` (an example inside prompt v2) |
| `text`, `attachments` | What the customer sent. Two tickets have no text, only an attachment. |
| `split` | `dev` (102 cases: use them while you change a prompt), `holdout` (98: frozen, used once for the release decision), `contaminated` (71: the tickets that prompt v2 was written and compared on, and its two examples) |
| `slice` | One group per case, for results by group: `normal`, `boundary` (on one of the policy's two team boundaries), `difficult` (two topics, negation, typos, a long story, a distractor, the request at the end, very short), `french`, `needs_person` (one of the rules H1 to H5 applies), `unanswerable` (the policy does not answer the request). A case is in the first group of this order that fits: French, needs a person, unanswerable, boundary, normal, difficult. |
| `tags` | Extra marks: `other_customer`, `injection`, `refund_promise_risk`, `policy_silent`, `not_covered`, `outside_window`, `typos` |
| `critical` | `true` for cases where one wrong answer blocks a release: safety (H1), access (H4), instructions in the ticket, and requests the assistant must not promise |
| `expected` | `team` (empty when no team can be scored), `needs_human`, `rule` (H1 to H5, or empty), `next_step` (what a good reply contains) |
| `criteria` | Codes for the reply: `must` (for example `photo`, `person_will_contact`, `stop_using`, `reply_in_french`) and `must_not` (`claims_action`, `asks_secret`, `other_customer_details`, `promises_outcome`) |
| `label` | Who labelled it, when, how, where the team label came from, whether it was read again on review, and what changed |

| Slice | dev | holdout |
|---|---|---|
| normal | 12 | 11 |
| boundary | 14 | 14 |
| difficult | 30 | 29 |
| French | 10 | 10 |
| needs a person | 22 | 21 |
| unanswerable | 14 | 13 |

Teams in dev and holdout: account 32, delivery 45, payment 36, returns 37, warranty 47, none 3. A person must handle 47 of the 200 (H1 safety 23, H2 legal 5, H3 outside the policy 6, H4 access 9, H5 no readable request 4). 37 cases are critical.

## How it was made

1. **140 tickets from the deep learning course.** Its validation and test files, without the 60 tickets that the LLM applications course used, sorted by `ticket_id`, with `random.Random(11)`: first 15 tickets that mention a safety word, then, for each team and writing style, a fixed number of tickets (6 plain, 6 boundary, 2 each of two topics, negation, distractor, request at the end, typos and long, 1 short) whose order IDs were not used yet.
2. **60 tickets written for this course:** 20 in French, 25 that need a person (safety worries, legal threats, requests the policy does not allow, another customer's order or account, instructions to the assistant inside the ticket, no readable request), and 15 questions that the policy does not answer.
3. **Labels.** The course author applied Grace's written policy (`policy.md`) to every case by reading it: the team, the rule that makes `needs_human` true, the next step and the reply criteria. The team of a reused ticket is the deep learning course's label (two models agreed on it); the author read it again.
4. **Splits.** In each slice, the cases were shuffled with `random.Random(12)` and given alternately to dev and holdout.
5. **Review.** Two systems were run on every case (2026-10-09). The author read every case where a system disagreed with a label or failed a reply criterion (63 cases of the 200). 32 labels changed, all of them the next step: wrong or damaged items on arrival need a photo (the policy's rule 3), not the return steps (10); on safety tickets the next step is to stop using the product and wait for a person, not the warranty route (16); tickets that a person handles anyway (a legal threat, instructions in the ticket, a lost order) need no promise to check (5); a trimmer the customer has tested is not unused, so the return steps do not apply (1). No team or `needs_human` label changed. 21 cases stayed `needs_human: false` although a system said `true` (for example a question about paying in instalments, a kettle that stopped working, an account locked after wrong passwords, a question about an extended warranty): no rule of the policy applies. Two team labels stayed although a system chose another team: `T-65388` (a drawer bent in transit; the customer wants to send the chest back: returns) and `T-65615` (cannot sign in: account). Each changed case says what changed and why in `label.changed`. The version of the set before the review was `263bbd4f180d`.

## Why this dataset

The evaluation set of the LLM applications course had 69 tickets, and the models were near the ceiling on it: a difference of one to three tickets proved nothing. This set is about three times as large, has more cases where a person must decide, and has slices, so that a failure in a small group can be found. Reusing the deep learning course's tickets connects the courses. Keeping the LLM applications course's tickets as a separate `contaminated` split shows what happens when you test on the examples you tuned a prompt on. Real tickets contain personal data and are not open.

## Limitations and cautions

- **Synthetic.** The tickets are more regular than real ones: few typos, one request each, and a writing style that language models produce. A score on this set says how the assistant handles tickets like these, not how it handles your customers. Real tickets would be harder.
- **One reader.** Every label is one person's reading of a written policy. Another reader could decide some boundary cases differently. The course author is the only labeller; there is no second human rater for these labels.
- **Small slices.** A slice of 10 to 14 cases moves by 7 to 10 points when one case changes. Read slice results with their intervals.
- The `contaminated` split also differs from the others in difficulty: it was built with a different quota. A gap between it and dev is not only contamination.
- Do not use the data to judge any real company, product or customer.
