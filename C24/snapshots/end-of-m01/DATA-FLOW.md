# Data flow of the support assistant

This is the map of where data goes when a support team member asks the assistant for help with one
ticket. The dashed line is the **trust boundary**: only the two things inside it are instructions.
Everything outside is **data**. The model reads data, but the code must never let data decide what
happens. `python -m support_assistant boundaries` prints the same map from `trust_boundaries.json`.

```
                       +----------------------- trust boundary -----------------------+
 Team member --------->|  request ("Please help me handle ticket T-24002")             |
 (signed in: token)    |  system prompt (prompts/system_*.md)                          |
                       +--------------------------------+------------------------------+
                                                        |
 Customer ---> ticket text, attachment names --------->+|  user message
                                                        v
                                               +-----------------+      prompts and data
                                               |   tool loop     |--------------------------> model provider
                                               |  (assistant.py) |<-------------------------- (outside the shop)
                                               +--------+--------+      tool calls, draft
                                                        |
                    +-------------+---------------------+-------------------+-----------------+
                    v             v                     v                   v                 v
               get_order     search_docs            read_file           fetch_url       write tools
               (database:    (help documents,       (file area:         (any web host:  (refund, return label,
               orders of     both shops)            attachments and     supplier, the   e-mail: run at once
               both shops)                          ../config/)         metadata page)  in the weak start)
                    |             |                     |                   |                 |
                    +-------------+----------+----------+-------------------+                 v
                                             v                                        database, the outside world
                                   tool results (data) go back into the loop

 Stored after every run: the conversation and the audit log (both in the database). In the weak start
 both keep the message text, with no end date.
```

## Sensitive assets

| Asset | Where it lives | Who must never get it |
|---|---|---|
| Customers' names, e-mails, phones, messages | database, file area, stored conversations, audit log | another customer, the other shop, an outside address |
| The service key (a made-up secret) | `data/vfs/config/service.env` | anyone: the model, a reply, a log, a link |
| Cloud credentials (made up) | the metadata address `169.254.169.254` | anyone |
| The shop's money | refunds and return labels | a refund or label the policy does not allow |
| The shop's name | e-mails sent from the shop | an e-mail to the wrong address, or with a false promise |
