# Releases of the escalation model

This file is the model registry of escalation-service. Each model version has
one row. A version is never changed: a fix is a new version. The digest is the
value for MODEL_SHA256. Only the course's bundles have these digests: your own
bundles have your own digests.

| Version | Bundle digest (MODEL_SHA256) | Status | Since | Evidence | Approved by |
|---|---|---|---|---|---|
| 1.0.0 | `8f233029aa4c896dce1a5b3dfa970cd085088386bbe7784519f15a5b1a433b74` | live (known good) | 2026-10-08 | C05 validation: ROC AUC 0.752, flagged 19.3% of May. July: flagged 20.1%, precision 0.333, recall 0.480. Parity 14 of 14. Rollback drill: back to 1.0.0 in 7.0 s, parity 14 of 14. | Grace (support lead), Priya (model owner) |
| 1.1.0-rc1 | `fa04bc40bea99723095ec4db600b7060fbfce0f2ec461534bb06c1829b47fe06` | retired | 2026-10-08 | Shadow run, July: flagged 87.0% of the last 1,000 tickets (86.1% of all 1,400). Precision 0.159. Balanced class weights moved every score up, and the threshold 0.19 was kept. Never answered a real request. Bundle removed from the image. | Grace, Priya |
| 1.1.0 | `382077148b6cad58238e4832f0951c6556f82832bc6e7de1d3a2335bd6d36af0` | candidate | 2026-10-08 | June: ROC AUC 0.749, flagged 19.3%. July (offline): flagged 19.4%, precision 0.342, recall 0.474. Also above 20% from 15 July. Next: a shadow run on new tickets. | not yet |

Statuses: candidate → shadow → live → known good → retired. A live version that
fails goes to rolled back, and the known-good version is live again.

## History

| Date | Event | Who |
|---|---|---|
| 2026-10-08 | 1.0.0 live. | Amira, approved by Grace |
| 2026-10-08 | 1.1.0-rc1 and 1.1.0 made with `retrain.py`; tests and parity pass for both. | Tomás, Priya |
| 2026-10-08 | Shadow run: 1.0.0 live, 1.1.0-rc1 shadow, 1,400 July tickets. Alert: shadow flag rate 0.870 is above the review capacity 0.20. rc1 not made live. | Amira |
| 2026-10-08 | Rollback drill on the test computer: 1.1.0-rc1 live, 300 July tickets, alert (flag rate 0.837). Back to 1.0.0: healthy after 7.0 s, about 2 s with no service, parity 14 of 14, contract checks pass. | Amira |
| 2026-10-08 | 1.1.0-rc1 retired: status retired, bundle removed from the next image. | Amira, approved by Grace |
