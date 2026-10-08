# Dataset card: synthetic home-care visit notes

Used by: the case study *Choose a model that runs on your own hardware* (`starter.zip`, `finished.zip` in this folder, file `local-model-choice/data/notes.jsonl`)

| Field | Value |
|---|---|
| Source | Written for this case study; no outside source |
| Publisher / creator | Nextia Learning, 2026-10-08 |
| Licence | CC0 1.0 Universal (https://creativecommons.org/publicdomain/zero/1.0/) for the notes; MIT for the code of the project |
| Attribution text | None required. Suggested: "Synthetic home-care visit notes, Nextia Learning (2026), CC0." |
| Version or access date | 2026-10-08 |
| File used | `data/notes.jsonl` in both zips: yes |
| SHA-256 | `04c5c0079bbf2524ad11af5e0e886f962fed6f5a882028252d099140c2bc044d` |
| Size | 18 notes × 5 fields (`id`, `kind`, `language`, `text`, `key`), 7647 bytes |

## What one row means

One short note that a home-care worker writes after a visit, and the answer key for the handover form: `fall`, `medication`, `pain_score`, `urgency` (with the acceptable alternatives) and the facts that a complete summary must mention.

## Why this dataset

The case study needs text that a privacy rule would forbid to send to a provider: notes about the health of named clients. Real notes of this kind cannot be published, and public clinical-note collections need credentialed access or have licences that do not allow redistribution in a course. Synthetic notes show the same problems (negations, missing facts, a message that is not a note, French) with no risk to a real person.

## Changes we made

None: the notes were written for the case study. Five kinds: 8 routine, 4 difficult, 3 with missing information, 1 that is not a visit note, 2 in French.

## Limitations and cautions

- Every client, worker, code and event is invented. A resemblance to a real person is a coincidence.
- 18 notes are a small test set: a difference of one or two notes between two models is noise.
- Real notes are longer, messier, and use abbreviations of the agency. A real agency must build its test set from its own notes, inside its own systems.
- The French notes were written by the author and were not checked by a second fluent reader.
