# Cloud design: ticket-api practice deployment

A minimal design to run `ticket-api:1.1.0` on Azure Container Apps for one practice session, then delete everything. Written before the deployment (Module 4). Module 5 builds it, and `DEPLOY.md` records what was made and removed.

Prices checked on 2026-10-07 (Azure Retail Prices API, canadacentral, USD, pay-as-you-go). Check the current prices before you deploy.

## What the service needs

| Need | Building block | Azure resource |
|---|---|---|
| Run the container from the image | Serverless containers | Container app `ticket-api` in the environment `cae-ticket-api` |
| A place for the image | Container registry | `ticketapi4821` (Basic) |
| A public HTTPS address | HTTPS ingress | The app's ingress: external, target port 8000 |
| Settings | The app's configuration | `REQUIRE_API_KEY=true`, `SHOW_DOCS=false` |
| The API key | A secret | Container Apps secret `api-key`, used as `API_KEY=secretref:api-key` |
| Permission to pull the image | A managed identity | `id-ticket-api` (user-assigned), role AcrPull on the registry |
| Logs | A log store | Log Analytics workspace (made automatically by the environment) |
| History records | Managed PostgreSQL | None: left out on purpose (see Decisions) |

## Region and resource group

- Region: `canadacentral` (the course's region; use the nearest region that has Container Apps). Every resource is in the same region.
- Resource group: `rg-ticket-api-practice`, tags `purpose=practice` and `course=C18`. Every resource goes in this group, so one delete removes them all.

## Identity and access

| Identity | Role | Scope | Why |
|---|---|---|---|
| Me (the person who deploys) | Owner or Contributor | My subscription, or only the practice group | Create and delete the practice resources |
| `id-ticket-api` | AcrPull | The registry `ticketapi4821` only | Pull the image, nothing more (least privilege) |

The registry's admin user stays **off**. No registry password exists in this design.

## Settings and secrets

| Name | Value | Secret? | Where |
|---|---|---|---|
| `API_KEY` | A new random key, made for this deployment | Yes | Container Apps secret `api-key`, referenced with `secretref:` |
| `REQUIRE_API_KEY` | `true` | No | Environment variable: without a key, the app does not start |
| `SHOW_DOCS` | `false` | No | Environment variable |
| `DATABASE_URL` | not set | (would be a secret) | Not used: history is off |

The key is never in the image, in Git, in a plain environment variable or in this file. Optional stretch: keep the key in a Key Vault (`kv-ticket-api-4821`) and reference it with `keyvaultref:` and `identityref:`; the identity then also gets Key Vault Secrets User on that vault only.

## Compute settings

0.25 vCPU and 0.5 GiB for each replica, minimum 0 replicas (scale to zero), maximum 2 replicas. The maximum is a cost limit as well as a scale limit.

## Cost estimate

| Case | Estimate |
|---|---|
| The practice: about 1 hour, then delete the group | A few cents: at most one day of the registry (US$0.17). The compute, the requests and the logs stay inside the monthly free amounts. |
| One replica running all month at the active rate | 648,000 vCPU-s - 180,000 free = 468,000 x US$0.000034 = US$15.91; 1,296,000 GiB-s - 360,000 free = 936,000 x US$0.000004 = US$3.74; total about **US$19.66** a month, plus the registry, about US$5. |
| The same with scale to zero and no traffic | US$0 for compute, plus the registry, about US$5 a month. |

Serverless is not free: it charges while a replica runs, and requests that I did not send can start a replica.

## Resource inventory

| Resource | Type | Made by | Can it charge? | How do I stop it? |
|---|---|---|---|---|
| `rg-ticket-api-practice` | Resource group | Me | No (it is a folder) | `az group delete --name rg-ticket-api-practice --yes`; this deletes everything in it |
| `ticketapi4821` | Container registry, Basic | Me | **Yes**: US$0.1666 a day while it exists, even if nothing uses it; storage above the 10 GiB included | Delete the registry (or the group) |
| `id-ticket-api` | User-assigned managed identity | Me | No | Delete it (or the group) |
| AcrPull for `id-ticket-api` on the registry | Role assignment | Me | No. Not listed by `az resource list` | Nothing to stop: Azure removes it with the registry and the identity (checked with `az role assignment list --all`). It is listed here so that I know it exists |
| `cae-ticket-api` | Container Apps environment (Consumption) | Me | No charge of its own in this design | Delete it (or the group) |
| `workspace-rgticketapipractice...` | Log Analytics workspace | **The environment, automatically** | **Yes**: per GB of logs above 5 GB a month (US$2.76 per GB) | Delete it (or the group). I did not ask for it, so I must look for it |
| `ticket-api` | Container app | Me | **Yes**: vCPU-seconds and GiB-seconds while a replica runs, and requests, above the monthly free grant | Scale to zero stops the compute charge; delete it (or the group) to stop everything |
| Data out to the internet | Egress | Responses to clients | Only above 100 GB a month | Delete the app |
| Optional: `kv-ticket-api-4821` | Key Vault | Me | **Yes**, a little: US$0.03 per 10,000 operations | Delete it (or the group), then `az keyvault purge --name kv-ticket-api-4821`. A deleted vault is soft-deleted for 90 days: no charge, but its name stays taken |
| Optional: a budget on the group | Cost Management budget | Me | No. It only sends an alert; it does not stop anything | Delete it after the practice |
| On my computer: the pushed image tags and the registry login | Local images, Docker credentials | Me | No | `docker image rm ticketapi4821.azurecr.io/ticket-api:1.1.0`, `docker logout ticketapi4821.azurecr.io` |

Checks after the clean-up: `az group exists --name rg-ticket-api-practice` returns `false`, and `az keyvault list-deleted` does not list the vault. Note: `az resource list --tag purpose=practice` is **not** a check, because the resources do not inherit the group's tag: it returned nothing even while the group still held its resources.

## Decisions

- **No database.** A managed PostgreSQL server charges for every hour that it exists. Without `DATABASE_URL`, the API classifies normally, and `/v1/history` returns `503 history_unavailable`. A real service adds Azure Database for PostgreSQL flexible server, in the same region, with `DATABASE_URL` as a secret.
- **No custom domain, no private network, no availability zones.** The platform's address and HTTPS are enough for a practice service.
- **No data that matters.** The practice uses a new key and test tickets only, and the service is deleted the same day.
