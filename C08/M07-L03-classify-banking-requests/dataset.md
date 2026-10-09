# Dataset card: BANKING77

Used by: the case study *Classify banking requests with an LLM* of *Building Reliable Applications with LLM APIs*, `classify-banking-requests.ipynb` and `classify-banking-requests-solution.ipynb`

| Field | Value |
|---|---|
| Source | https://github.com/PolyAI-LDN/task-specific-datasets (folder `banking_data/`); also on Hugging Face as `PolyAI/banking77` |
| Publisher / creator | PolyAI: Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson, Ivan Vulić |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/ (the repository's `LICENSE` file, checked 2026-10-08) |
| Attribution text | "BANKING77" by PolyAI (Casanueva et al., 2020), https://github.com/PolyAI-LDN/task-specific-datasets, licensed under CC BY 4.0. Paper: *Efficient Intent Detection with Dual Sentence Encoders*, Proceedings of the 2nd Workshop on NLP for ConvAI, 2020, https://arxiv.org/abs/2003.04807 |
| Version or access date | Commit `57ec275d8078af65b7731c2a98be812d844a6d6b` (2022-04-29), downloaded 2026-10-08 |
| File used | `train.csv` and `test.csv`, downloaded by the notebook from the fixed commit above; not kept in this folder (the fixed commit URL does not change) |
| SHA-256 | train.csv `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`; test.csv `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d` |
| Size | train 10,003 rows × 2 columns (839,073 bytes); test 3,080 rows × 2 columns (239,961 bytes) |

## What one row means

One short message to the online support of a bank (`text`), with the intent that it expresses (`category`), one of 77 intents such as `card_arrival`, `top_up_failed` or `cancel_transfer`. The target is `category`.

## Why this dataset

It is the dataset of the deep learning course's case study *Fine-tune a small transformer*, with the same split, so the language model in this case study is scored on exactly the test messages where a fine-tuned DistilBERT reached 91.8% and TF-IDF with logistic regression 89.0%. Its 77 intents are fine-grained and many share words (`top_up_failed`, `top_up_reverted`, `pending_top_up`), so a prompt must do real work. The licence is clear. Compared with CLINC150 (CC BY 3.0; voice-assistant commands in 10 domains, no course baseline), MASSIVE (CC BY 4.0; voice-assistant commands) and the US CFPB complaint database (no explicit licence for the narratives; real people's complaints). Details: `reference/c08/m07/l03/DATASET-RESEARCH.md` in the course repository.

## Changes we made

None to the files. As in the deep learning course, the notebook holds out 1,000 messages of the official train file as a validation set (stratified by intent, `random_state=0`). The prompt versions are compared on these 1,000 messages. The official test file is used once, at the end. The more expensive model (`chat-strong`) answered a fixed sample of 770 test messages (10 per intent, stratified, `random_state=0`) to stay within the case study's budget.

## The recorded answers in this folder

`recordings/` holds the real answers of two models on Azure (gpt-6-luna as `chat-small`, gpt-6.1-sol as `chat-strong`), recorded 2026-10-08 and 2026-10-09. Each line has the message's index (in the validation set or in `test.csv`), the true intent, the model's answer and confidence, the tokens and the latency. The message texts are not copied; the notebook takes them from BANKING77. `prompts/` holds the two prompt versions. `SHA256SUMS` lists the checksums that the notebook verifies.

## Limitations and cautions

- The paper calls the texts "customer service queries" and does not say who wrote them. Do not treat them as a sample of real customers.
- One kind of bank, English only, mostly UK and European banking terms (top-up, SEPA, exchange rates). It says nothing about other banks, languages or channels.
- The intents overlap on purpose, and some labels are debatable (for example `card_arrival` and `card_delivery_estimate`; `get_physical_card` is mostly about finding the PIN). Part of every model's error is in the labels.
- 6 messages in the train file repeat another message, and 10 test messages also appear in the train file. A hosted model may also have seen this public dataset during its training; we cannot check that.
- The test file is balanced (40 messages per intent); the train file is not (35 to 187). Real traffic is not balanced either.
