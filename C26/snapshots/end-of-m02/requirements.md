# Requirements: the shared document assistant

Owner: Kwame (solution architect). Reviewed with Omar (product), Grace (Larkfield support) and Ines (Bramble Books).

## Problem

Larkfield's help desk has an assistant that answers questions from Larkfield's own documents, with citations. Bramble Books wants the same assistant for its own documents, and two more shops may join next year. Today every shop would need its own copy. We need one assistant that several shops (tenants) share, where each shop sees only its own documents, at a cost per shop that Omar can put in a price.

## Users and journeys

| Who | Journey | What "done" looks like |
|---|---|---|
| Help-desk agent (Grace's team) | J1: asks a question while helping a customer | an answer with citations to the shop's documents, in a few seconds |
| Customer on the shop's website | J2: asks a question before writing a ticket | an answer from public documents only, or "the documents do not say" |
| Shop owner or editor (Ines, Mei) | J3: uploads a new or changed document | the document is searchable in minutes, with a short summary; the old version stays for audits |
| Shop owner | J4: sees what the assistant answered | every answer with its question, citations and document versions |
| Kwame and Amira | J5: add a new shop | a new tenant with its own documents and users, without a code change |

## Out of scope

- Answers from the internet or from general knowledge: the assistant uses only the shop's documents.
- Actions (refunds, order changes): the assistant answers; people act.
- Shops sharing documents with each other.
- Languages other than English and French.
- A mobile app.

## Quality attributes

A quality attribute is a property of the whole system (how fast, how available, how private). Each one below has a target that we can measure: an SLO (service level objective).

| ID | Attribute | Target (SLO) | How we measure | Kind |
|---|---|---|---|---|
| Q1 | Latency | 95% of answers in 6 s or less, every week | the API logs the time of each answer; p95 per week | target agreed with Grace; first estimate: about 4.6 s (the p95 of each measured step added; an upper estimate) |
| Q2 | Availability | the assistant answers 99.5% of questions in shop hours each month | the share of questions with a 2xx answer, from the logs | target agreed with Omar |
| Q3 | Privacy | no tenant ever sees another tenant's document or answer | the access tests on every change; a cross-tenant check in the evaluation set | verified by tests in the authentication course's way |
| Q4 | Answer quality | at least 85% correct on the shop's evaluation set; 0 answers without a citation | the evaluation set (67 questions for Larkfield) before every model or prompt change | first measurement: 86.6% (measured) |
| Q5 | Auditability | every answer kept 1 year with question, citations, document versions, tenant and user | a weekly query: answers without these fields = 0 | target from Ines's supplier contracts |
| Q6 | Maintainability | one developer can deploy a fix in one working day; a new tenant without a code change | the time from merge to production; the tenant checklist | target agreed with Amira |
| Q7 | Recovery | back within 4 hours (RTO); lose at most 1 hour of new data (RPO) | a restore test every quarter | target agreed with Omar and Mei |
| Q8 | Budget | at most US$150 a month for the first year, all tenants together | the cost model now; the cloud bill every month | Omar's budget |

## Verified and assumed

- Verified: Larkfield has 10 help-desk agents and 36 documents; Bramble Books has 3 documents today; the first answer-quality and latency numbers come from real runs (measured.toml).
- Assumed (check these first): how many customers will ask questions, how many questions they ask, how fast the shops grow, when the third and fourth shops join, how often documents change, and how often a question repeats (the cache). Each one is a range in demand.toml or design.toml with the reason for it.
- Open question for Omar: will customers see the assistant on the home page? That changes customer questions by a factor of about 2 (the high scenario).
