# Capability catalog (worked example)

Design before code. For each user need: who chooses the capability, which kind fits, and its contract.

| User need | Who chooses | Kind | Name | Input (bounded) | Output (bounded) | Why this kind |
|---|---|---|---|---|---|---|
| "What does our policy say about X?" | the model | tool | `search_knowledge` | `query` 3–200 characters, `limit` 1–5 | at most 5 matches: title, URI, snippet ≤ 300 characters | the model decides when it needs to look something up |
| "What is ticket T-30002 about?" | the model | tool | `get_ticket` | `ticket_id` matching `T-` + 5 digits | one ticket, first name only, last 3 messages | the model needs the facts of the ticket it works on |
| "Show me the full returns policy." | the application or the person | resource | `policy://{tenant}/{doc_id}` | a URI from the list or the template | the document's Markdown | it is content to read and attach, not an action |
| "Draft a reply to this ticket." | the person | prompt | `draft_reply` | `ticket_id` | one user message with the steps | a repeatable workflow that the person starts |
| "Refund this customer 25 dollars." | the model proposes, a person approves | tool (write) | `propose_refund` | ticket, amount ≤ 100.00, reason 3–200 characters | a proposal with an operation ID; no effect | a change with an effect needs a person; added only after the permission tests pass |

## Rejected on purpose

| Idea | Why not |
|---|---|
| `run_sql(query)` | Any query the model writes, on any table, of any organization. Narrow tools only. |
| `run_shell(command)` | Unlimited effects on the server's computer. |
| `get_customer(email)` | Personal data the support answers do not need. |
| `list_all_tickets()` | Unbounded output; a ticket ID is enough. |
| `refund(ticket, amount)` that pays at once | An effect without a person's approval. |
