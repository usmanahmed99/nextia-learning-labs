# Integration map (worked example)

Three AI applications need the same support knowledge. Before MCP, each one gets its own integration.

| AI application | Who uses it | What it needs | Integration without MCP | With MCP |
|---|---|---|---|---|
| Help desk assistant | Sam, Camille (staff) | search policies, read a ticket, propose a refund | custom code in the help desk: two API calls and a tool schema for its model | MCP client to `support-mcp` |
| Editor assistant | staff writing replies | search policies, read a policy | a plug-in written for that editor | the editor's MCP client, same server |
| A partner's app (Omar's plan) | a partner company | search public policies | a partner API with its own keys, schemas and docs | a remote MCP connection with a token and scopes |

Count the integrations: without MCP, 3 applications × 1 service = 3 custom integrations, and each new application adds one. With MCP: 1 server, and each application needs only an MCP client, which most AI applications already have.

## When MCP is not needed

- One application and one service: a direct API call, or a tool defined inside the application, is simpler.
- The model needs no tools or data at run time.

## What MCP standardizes, and what stays yours

| MCP standardizes | Your application and server still decide |
|---|---|
| How a client finds a server's tools, resources and prompts (discovery) | Which tools exist, and how narrow they are |
| The message format (JSON-RPC 2.0) and the transports (stdio, Streamable HTTP) | Who the caller is and what they may do (authorization) |
| How a tool is called and how a result or an error comes back | Whether a person must approve a call |
| How a remote server says where to get a token | Limits, logs, and what the model is allowed to see |
