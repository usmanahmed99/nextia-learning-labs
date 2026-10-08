# Deep Learning and Transformers Explained

Files for [Deep Learning and Transformers Explained](https://learning.nextia-ai.com/courses/deep-learning/).

| Path | Used in | What it is |
|---|---|---|
| [`data/`](data) | Every lesson | Larkfield's ticket texts (train, validation, test) and their [dataset card](data/dataset.md). Synthetic, CC0. |
| [`get_data.py`](get_data.py) | Set up PyTorch | Downloads the tickets and `ticketnet.py` into your project folder and checks them (`python get_data.py`, or `--reset`). |
| [`project/ticketnet.py`](project/ticketnet.py) | Every lesson with code | The course's small networks in one readable file: the tokenizer and vocabulary, the bag-of-words network, the average-embedding network, the tiny transformer and the training loop. |
| [`data-source/`](data-source) | Not needed to learn | How the data was made: the scripts, the routing policy and every raw model reply. Rebuild the data with `python build_dataset.py`. |
| `Mnn-Lnn-<slug>/` | The lessons | Lesson notebooks (learner and solution). They open in Colab or Kaggle and run on a CPU. |

The code is MIT-licensed and the data is CC0 (see [LICENSE](LICENSE)).
