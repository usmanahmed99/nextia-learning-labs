# Deployment record: ticket-api 1.1.0

The deployment checklist, the resource inventory and the clean-up record for the practice deployment of C18 Module 5. Every result has a label: **live** (from Azure) or **simulated** (from Docker on this computer). The API key is never written here.

- Route: live, Azure Container Apps, region `canadacentral`
- Date: 2026-10-07
- Tools: Docker Desktop 4.81.0 (Engine 29.6.1, Buildx 0.35.0), Azure CLI 2.88.0, containerapp extension 1.3.0b5
- Settings: `deploy/containerapp.yaml` (probes, resources, scale, environment values)

## 1. Deployment checklist

| Step | Command | Result (live) |
|---|---|---|
| Resource group, with tags | `az group create --name rg-ticket-api-practice --location canadacentral --tags purpose=practice course=C18` | Created |
| Registry, admin user off | `az acr create --resource-group rg-ticket-api-practice --name ticketapi4821 --sku Basic` | `ADMIN ENABLED False` |
| Build for the cloud and push | `az acr login --name ticketapi4821`, then `docker buildx build --platform linux/amd64 -t ticketapi4821.azurecr.io/ticket-api:1.1.0 --push .` | 27 s |
| Check the platform | `docker buildx imagetools inspect ticketapi4821.azurecr.io/ticket-api:1.1.0` | `linux/amd64` (and the build attestation, `unknown/unknown`) |
| Identity, pull only | `az identity create … --name id-ticket-api`, `az role assignment create … --role AcrPull --scope <registry id>` | Scope: the registry only |
| Environment | `az containerapp env create … --name cae-ticket-api` | Made `workspace-rgticketapipracticeXXXX` too |
| Container app | `az containerapp create … --ingress external --target-port 8000 --cpu 0.25 --memory 0.5Gi --min-replicas 0 --max-replicas 2 --secrets api-key=… --env-vars API_KEY=secretref:api-key REQUIRE_API_KEY=true SHOW_DOCS=false` | Revision `ticket-api--nz14cir`, `Running`, `Succeeded` |
| Probes, size, scale | `az containerapp update … --yaml deploy/containerapp.yaml` | Revision `ticket-api--0000001`, `Healthy`, traffic 100 |

Deployed image (tag and digest):

```text
ticketapi4821.azurecr.io/ticket-api:1.1.0@sha256:cfd04194eb1be66f49a40575f75a0b2105a74e172f953df26a355291a5191afd
```

Address: `https://ticket-api.nicewater-a307f95a.canadacentral.azurecontainerapps.io` (deleted on 2026-10-07).

The key: a new random key, made for this deployment only. It was in the app's secret `api-key` and in the terminal. It is not in this file, in Git or in the image. Anyone who needs to call the API asks the owner.

### Smoke checks (live)

| Check | Expected | Result (live) |
|---|---|---|
| `GET /health` (first request) | `200` | `200` `{"status":"ok"}`, 18.4 s (cold start from zero replicas) |
| `GET /ready` | `200` | `200` `{"status":"ready"}` |
| `POST /v1/classify` with the key | `200` | `200` billing, priority 1, confidence 0.7 |
| `POST /v1/classify` without the key | `401` | `401` |
| `GET /docs` | `404` | `404` |
| `http://…/health` | `301` to `https://` | `301` |
| `GET /v1/history` with the key | `503` `history_unavailable` (no database, on purpose) | `503` |

### Logs (live)

- `az containerapp logs show -g rg-ticket-api-practice -n ticket-api --tail 12 --format text`: the classify request `id=95f853debb5b`, the probes from `127.0.0.1`, and a `GET /` (404) from the ingress that nobody on the team sent.
- System logs: `az containerapp logs show … --type system` (JSON only).
- Log Analytics: `ContainerAppConsoleLogs_CL | where Log_s has 'classify'` found the same line, with `RevisionName_s` `ticket-api--0000001`, about 2 minutes later.

### A failed deployment (live)

The image `ticket-api:1.1.0-arm64` (built for `linux/arm64` only) made revision `ticket-api--0000002`. It stayed `Activating`: `ImagePullUnauthorized`, then `ImagePullFailure`. Revision `ticket-api--0000001` kept serving (`/health` 200). Fixed with `az containerapp update … --image ticketapi4821.azurecr.io/ticket-api:1.1.0`: revision `ticket-api--0000003`, `Healthy`, traffic 100.

## 2. Resource inventory

Made with `az resource list --resource-group rg-ticket-api-practice -o table` **before** the deletion. Not by tag: the tag `purpose=practice` is on the group only, and `az resource list --tag purpose=practice` finds nothing.

| Resource | Type | Made by | Can it charge? | How to stop it |
|---|---|---|---|---|
| `rg-ticket-api-practice` | Resource group | `az group create` | No | `az group delete` (deletes everything below) |
| `ticketapi4821` | Container registry, Basic | `az acr create` | **Yes**: about US$0.17 per day while it exists, used or not | Delete the group |
| `id-ticket-api` | User-assigned managed identity | `az identity create` | No | Delete the group |
| AcrPull on the registry | Role assignment (not listed by `az resource list`) | `az role assignment create` | No | Goes with the registry |
| `workspace-rgticketapipracticeXXXX` | Log Analytics workspace | **Automatic**, by `az containerapp env create` | **Yes**: log data above 5 GB a month (US$2.76 per GB) | Delete the group |
| `cae-ticket-api` | Container Apps environment | `az containerapp env create` | No (Consumption: you pay for apps) | Delete the group (it goes last) |
| `ticket-api` | Container app, 0.25 vCPU / 0.5 GiB, 0 to 2 replicas | `az containerapp create` | **Yes**, while a replica runs, above the monthly free grant | Delete the group; `minReplicas: 0` stops compute charges when idle |
| `kv-ticket-api-4821` (optional) | Key Vault, RBAC, soft delete 90 days | `az keyvault create` | Almost nothing; after deletion it is **soft-deleted**: no charge, but the name and the secret stay | Delete the group, then `az keyvault purge` |
| Local: `ticketapi4821.azurecr.io/ticket-api:1.1.0` and `:1.1.0-arm64` | Image tags on this computer | `docker buildx build --push` | No | `docker image rm` |
| Local: the registry token | Docker credential | `az acr login` | No, but it gives access to the registry | `docker logout ticketapi4821.azurecr.io` |

## 3. Clean-up record (live)

| Step | Command | Result (live) |
|---|---|---|
| Delete the group | `az group delete --name rg-ticket-api-practice --yes --no-wait` | Started 16:36 |
| While it runs | `az group show -n rg-ticket-api-practice --query properties.provisioningState -o tsv` | `Deleting` (the environment was the last resource) |
| The group is gone | `az group exists --name rg-ticket-api-practice` | `false` (17:04, about 28 minutes) |
| Soft-deleted vault | `az keyvault list-deleted --query "[].{name:name, purge:properties.scheduledPurgeDate}" -o table` | `kv-ticket-api-4821`, scheduled purge 2027-01-05 |
| Purge it | `az keyvault purge --name kv-ticket-api-4821` | No output, exit code 0 |
| No vault left | `az keyvault list-deleted --query "length(@)"` | `0` |
| No group left | `az group list --query "[?contains(name,'ticket-api')].name" -o tsv` | Nothing |
| No role left | `az role assignment list --all --query "[?contains(scope,'rg-ticket-api-practice')]" -o table` | Nothing |
| Local tags | `docker image rm ticketapi4821.azurecr.io/ticket-api:1.1.0 ticketapi4821.azurecr.io/ticket-api:1.1.0-arm64` | `Untagged: …` for both |
| Registry token | `docker logout ticketapi4821.azurecr.io` | `Removing login credentials for ticketapi4821.azurecr.io` |

Time with resources in Azure: 16:10 to 17:04, about 54 minutes. Expected cost: one day of the Basic registry (US$0.17) and a few cents or less of compute, inside the free grant. Prices checked on 2026-10-07 (Azure Retail Prices API, canadacentral, USD).

Kept on purpose: the local image `ticket-api:1.1.0` and the project.

---

## Simulated route (Docker on this computer)

Use this variant when you have no Azure subscription. The same configuration concepts: the same image and settings, a secret from a file, the same size limits, a health check on `/health`. Not simulated: HTTPS, scaling, revisions, the identity and the registry sign-in.

### Checklist (simulated)

| Step | Command | Result (simulated) |
|---|---|---|
| Local registry | `docker run -d --name ticket-api-registry -p 127.0.0.1:5000:5000 -v ticket-api-registry-data:/var/lib/registry registry:3.1.2` | Running on `127.0.0.1:5000` |
| Build for the cloud and push | `docker buildx build --platform linux/amd64 -t 127.0.0.1:5000/ticket-api:1.1.0 --push .` | 23 s without the build cache |
| Check the platform | `docker buildx imagetools inspect 127.0.0.1:5000/ticket-api:1.1.0` | `linux/amd64` |
| Tag in the registry | `curl -s http://127.0.0.1:5000/v2/ticket-api/tags/list` | `{"name":"ticket-api","tags":["1.1.0"]}` |
| Start the simulation | `docker compose -f deploy/local-cloud.yaml up -d` | `Up 12 seconds (healthy)` on `127.0.0.1:8080` |
| Limits | `docker stats --no-stream ticket-api-cloud-sim-api-1` | `56.92MiB / 512MiB` |
| Required setting | Empty `secrets/api_key.txt`, `up -d` | `Settings error: REQUIRE_API_KEY is true, but API_KEY is not set`, `Restarting (1)`; healthy again after the key was put back |

### Smoke checks (simulated)

| Check | Expected | Result (simulated) |
|---|---|---|
| `GET /health` | `200` | `200` |
| `GET /ready` | `200` | `200` |
| `POST /v1/classify` with the key (`requests/billing.json`) | `200` | `200` billing, priority 1, confidence 0.9 |
| `POST /v1/classify` without the key | `401` | `401` |
| `GET /docs` | `404` | `404` |
| `GET /v1/history` with the key | `503` | `503` |
| Cold start, `http://` → `301` | Live only | Not simulated |

Logs: `docker compose -f deploy/local-cloud.yaml logs api | grep 0008b89dda79` found the `401` request by its ID.

### Inventory (simulated, before deletion)

| Object | Kind | How to remove it |
|---|---|---|
| `ticket-api-cloud-sim-api-1` | Container (Compose project `ticket-api-cloud-sim`) | `docker compose -f deploy/local-cloud.yaml down` |
| `ticket-api-cloud-sim_default` | Network | Removed by `down` |
| `ticket-api-registry` | Container | `docker rm -f ticket-api-registry` |
| `ticket-api-registry-data` | Volume (the registry's images, 71.24MB) | `docker volume rm ticket-api-registry-data` |
| `127.0.0.1:5000/ticket-api:1.1.0`, `:1.1.0-arm64`, `registry:3.1.2` | Image tags | `docker image rm …` |

Nothing here costs money. Not in the list on purpose: the Module 3 database project (`ticket-api_pgdata`) and `ticket-api:1.1.0`.

### Clean-up record (simulated)

| Step | Command | Result (simulated) |
|---|---|---|
| Stop the simulation | `docker compose -f deploy/local-cloud.yaml down` | Container and network `Removed` |
| Remove the registry | `docker rm -f ticket-api-registry` | `ticket-api-registry` |
| Remove its data | `docker volume rm ticket-api-registry-data` | `ticket-api-registry-data` |
| Remove the tags | `docker image rm 127.0.0.1:5000/ticket-api:1.1.0 127.0.0.1:5000/ticket-api:1.1.0-arm64 registry:3.1.2` | `Untagged: …` |
| Nothing left | `docker ps -a --filter name=ticket-api-cloud-sim`, `docker ps -a --filter name=ticket-api-registry`, `docker volume ls --filter name=ticket-api-registry` | No lines |
