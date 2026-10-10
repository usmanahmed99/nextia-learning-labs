# A sample of public human ratings: MT-Bench human judgments

`mt_bench_sample.jsonl`: 60 items. One item is one question of MT-Bench (first turn) with the answers of two chatbots, and the votes of 2 or more human judges: `A` (the answer of `model_1` is better), `B` or `tie`. Each item also has the vote of a GPT-4 judge that was asked in both orders (`inconsistent` = its verdict changed when the order changed).

Data: MT-Bench human judgments, LMSYS (Zheng et al., 2023, "Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena", arXiv:2306.05685), https://huggingface.co/datasets/lmsys/mt_bench_human_judgments (revision f7d2896d), licensed under CC BY 4.0 (https://creativecommons.org/licenses/by/4.0/). Changes: we selected 60 first-turn items that have votes from 2 or more different human judges (sorted, then `random.Random(11).sample`), kept some fields, and wrote every label in a fixed model order (`model_1` is the name that comes first alphabetically).

The rater IDs (`expert_N`, `author_N`) are the dataset's own anonymous IDs. The answers were written by chatbots in 2023, and some of them are wrong. The builder and the comparison with other datasets are in the course's reference folder.
