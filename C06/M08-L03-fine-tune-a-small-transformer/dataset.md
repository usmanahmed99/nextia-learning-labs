# Dataset card: BANKING77

Used by: the case study *Fine-tune a small transformer* of *Deep Learning and Transformers Explained*, `fine-tune-a-small-transformer.ipynb` and `fine-tune-a-small-transformer-solution.ipynb`

| Field | Value |
|---|---|
| Source | https://github.com/PolyAI-LDN/task-specific-datasets (folder `banking_data/`); also on Hugging Face as `PolyAI/banking77` |
| Publisher / creator | PolyAI: Iñigo Casanueva, Tadas Temčinas, Daniela Gerz, Matthew Henderson, Ivan Vulić |
| Licence | Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/ (the repository's `LICENSE` file) |
| Attribution text | "BANKING77" by PolyAI (Casanueva et al., 2020), https://github.com/PolyAI-LDN/task-specific-datasets, licensed under CC BY 4.0. Paper: *Efficient Intent Detection with Dual Sentence Encoders*, Proceedings of the 2nd Workshop on NLP for ConvAI, 2020, https://arxiv.org/abs/2003.04807 |
| Version or access date | Commit `57ec275d8078af65b7731c2a98be812d844a6d6b` (2022-04-29), downloaded 2026-10-08 |
| File used | `train.csv` and `test.csv`, downloaded by the notebook from the fixed commit above; not kept in `data/` (the fixed commit URL does not change) |
| SHA-256 | train.csv `b06e26ac675513959a63135f11b94ea7786ed02da65db93a5650d8838cbc664b`; test.csv `d12d6e3bc4c3103966ae786dc435913c0c563dfa328f5a3646d0e62cfeeb474d` |
| Size | train 10,003 rows × 2 columns (839,073 bytes); test 3,080 rows × 2 columns (239,961 bytes) |

## What one row means

One short message to the online support of a bank (`text`), with the intent that it expresses (`category`), one of 77 intents such as `card_arrival`, `top_up_failed` or `cancel_transfer`. The target is `category`.

## Why this dataset

It is the same task as the course's running example: send a support message to the right handler. Its 77 intents are fine-grained and many share words (`top_up_failed`, `top_up_reverted`, `pending_top_up`), so it tests whether a model reads more than word counts. The messages are short (median 10 words), so a small pretrained encoder can be fine-tuned on a CPU. The licence is clear. Compared with: the US CFPB complaint database (narratives withdrawn from publication in 2026, no explicit licence field), the SMS Spam Collection (CC BY 4.0, but two classes and too easy), MASSIVE (CC BY 4.0, voice-assistant commands, not support messages), and popular review and news datasets (unclear terms). Details: `reference/c06/m08/l03/DATASET-RESEARCH.md` in the course repository.

## Changes we made

None to the files. The notebook holds out 1,000 messages of the official train file as a validation set (stratified by intent, `random_state=0`), so 9,003 messages remain for training. For the learning curve, it takes stratified samples of 100, 500 and 2,000 training messages (`random_state` 0, 1 and 2). The official test file is used once, at the end.

## Limitations and cautions

- The paper calls the texts "customer service queries" and does not say who wrote them. Do not treat them as a sample of real customers.
- One kind of bank, English only, mostly UK and European banking terms (top-up, SEPA, exchange rates). It says nothing about other banks, languages or channels.
- The intents overlap on purpose, and some labels are debatable (for example `card_arrival` and `card_delivery_estimate`). Accuracy near 90% partly reflects this ambiguity.
- 6 messages in the train file repeat another message, and 10 test messages also appear in the train file (in the course's word tokens).
- The test file is balanced (40 messages per intent); the train file is not (35 to 187). Real traffic is not balanced either.
