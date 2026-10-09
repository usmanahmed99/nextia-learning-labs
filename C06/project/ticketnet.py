"""Larkfield ticket router: the small networks of C06, in one readable file.

Every lesson and notebook of the course uses these definitions, so that the numbers agree.
Python 3.12+, PyTorch 2.x, CPU. Nothing here needs a graphics card.
"""
import csv
import math
import random
import re
from collections import Counter
from pathlib import Path

import torch
from torch import nn

TEAMS = ["delivery", "returns", "payment", "warranty", "account"]
PAD, UNK = 0, 1
MAX_TOKENS = 120  # longer tickets are cut; about 95% of training tickets are shorter


# ---------- data ----------

def load_split(path):
    """Read train.csv, valid.csv or test.csv into a list of dicts."""
    with open(path, newline="", encoding="utf-8") as fh:
        return list(csv.DictReader(fh))


def tokenize(text):
    """Lower-case words, numbers and single punctuation marks: "Isn't it?" -> ['isn', "'", 't', 'it', '?']."""
    return re.findall(r"[a-z]+|[0-9]+|[^\sa-z0-9]", text.lower())


class Vocab:
    """Token <-> ID. ID 0 is padding, ID 1 is any token that was not seen often enough in training."""

    def __init__(self, texts, min_count=2):
        counts = Counter(t for text in texts for t in tokenize(text))
        self.itos = ["<pad>", "<unk>"] + sorted(t for t, c in counts.items() if c >= min_count)
        self.stoi = {t: i for i, t in enumerate(self.itos)}

    def __len__(self):
        return len(self.itos)

    def encode(self, text, max_tokens=MAX_TOKENS):
        return [self.stoi.get(t, UNK) for t in tokenize(text)][:max_tokens]


def bag_of_words(rows, vocab):
    """One row per ticket, one column per vocabulary entry: how often the token appears. Shape (tickets, vocab)."""
    x = torch.zeros(len(rows), len(vocab))
    for i, r in enumerate(rows):
        for t in vocab.encode(r["text"]):
            x[i, t] += 1
    x[:, PAD] = 0
    return x


def token_ids(rows, vocab):
    """Padded token IDs, shape (tickets, longest ticket), with 0 after each ticket's last token."""
    seqs = [vocab.encode(r["text"]) or [UNK] for r in rows]
    width = max(len(s) for s in seqs)
    return torch.tensor([s + [PAD] * (width - len(s)) for s in seqs])


def labels(rows):
    return torch.tensor([TEAMS.index(r["team"]) for r in rows])


# ---------- models ----------

class BagOfWordsNet(nn.Module):
    """Counts of words -> hidden layer with ReLU -> one score per team."""

    def __init__(self, vocab_size, hidden=64, dropout=0.0):
        super().__init__()
        self.layers = nn.Sequential(
            nn.Linear(vocab_size, hidden), nn.ReLU(), nn.Dropout(dropout), nn.Linear(hidden, len(TEAMS)))

    def forward(self, x):  # x: (batch, vocab) -> (batch, 5)
        return self.layers(torch.log1p(x))


class AverageEmbeddingNet(nn.Module):
    """Each token -> a learned vector; average the vectors of a ticket; -> one score per team. Word order is lost."""

    def __init__(self, vocab_size, dim=64):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim, padding_idx=PAD)
        self.out = nn.Linear(dim, len(TEAMS))

    def forward(self, ids):  # ids: (batch, tokens)
        mask = (ids != PAD).unsqueeze(-1).float()            # (batch, tokens, 1)
        vectors = self.embed(ids) * mask                       # (batch, tokens, dim)
        mean = vectors.sum(1) / mask.sum(1).clamp(min=1)       # (batch, dim)
        return self.out(mean)


class TinyTransformer(nn.Module):
    """Token + position embeddings -> transformer blocks (attention, feed-forward) -> average -> one score per team."""

    def __init__(self, vocab_size, dim=64, heads=4, blocks=2, max_tokens=MAX_TOKENS, dropout=0.1):
        super().__init__()
        self.embed = nn.Embedding(vocab_size, dim, padding_idx=PAD)
        self.position = nn.Embedding(max_tokens, dim)
        block = nn.TransformerEncoderLayer(dim, heads, dim_feedforward=4 * dim, dropout=dropout,
                                           batch_first=True, norm_first=True)
        self.blocks = nn.TransformerEncoder(block, blocks, enable_nested_tensor=False)
        self.norm = nn.LayerNorm(dim)
        self.out = nn.Linear(dim, len(TEAMS))

    def forward(self, ids):  # ids: (batch, tokens)
        positions = torch.arange(ids.shape[1], device=ids.device)
        h = self.embed(ids) + self.position(positions)            # (batch, tokens, dim)
        h = self.blocks(h, src_key_padding_mask=ids == PAD)       # (batch, tokens, dim)
        mask = (ids != PAD).unsqueeze(-1).float()
        mean = (self.norm(h) * mask).sum(1) / mask.sum(1).clamp(min=1)
        return self.out(mean)                                     # (batch, 5)


# ---------- training ----------

def set_seed(seed=0):
    random.seed(seed)
    torch.manual_seed(seed)


def accuracy(model, x, y, batch_size=256):
    model.eval()
    with torch.no_grad():
        pred = torch.cat([model(x[i:i + batch_size]).argmax(1) for i in range(0, len(x), batch_size)])
    return (pred == y).float().mean().item()


def evaluate(model, x, y, batch_size=256):
    """Mean cross-entropy loss and accuracy, with no gradients and dropout switched off."""
    model.eval()
    loss_fn = nn.CrossEntropyLoss(reduction="sum")
    total, correct = 0.0, 0
    with torch.no_grad():
        for i in range(0, len(x), batch_size):
            logits = model(x[i:i + batch_size])
            total += loss_fn(logits, y[i:i + batch_size]).item()
            correct += (logits.argmax(1) == y[i:i + batch_size]).sum().item()
    return total / len(x), correct / len(x)


def train(model, x_train, y_train, x_valid, y_valid, epochs=20, batch_size=64, lr=1e-3,
          optimizer="adam", weight_decay=0.0, seed=0, log=print):
    """The five steps, in order, for every mini-batch. Returns one dict per epoch."""
    set_seed(seed)
    if optimizer == "adam":
        opt = torch.optim.Adam(model.parameters(), lr=lr, weight_decay=weight_decay)
    elif optimizer == "adamw":
        opt = torch.optim.AdamW(model.parameters(), lr=lr, weight_decay=weight_decay)
    elif optimizer == "momentum":
        opt = torch.optim.SGD(model.parameters(), lr=lr, momentum=0.9, weight_decay=weight_decay)
    else:
        opt = torch.optim.SGD(model.parameters(), lr=lr, weight_decay=weight_decay)
    loss_fn = nn.CrossEntropyLoss()
    history = []
    for epoch in range(1, epochs + 1):
        model.train()
        order = torch.randperm(len(x_train))
        for i in range(0, len(order), batch_size):
            idx = order[i:i + batch_size]
            opt.zero_grad()                              # 1. forget the last batch's gradients
            logits = model(x_train[idx])                 # 2. forward pass
            loss = loss_fn(logits, y_train[idx])         # 3. how wrong?
            loss.backward()                              # 4. backward pass: gradients
            opt.step()                                   # 5. update the weights
        tl, ta = evaluate(model, x_train, y_train)
        vl, va = evaluate(model, x_valid, y_valid)
        row = {"epoch": epoch, "train_loss": round(tl, 4), "train_acc": round(ta, 4),
               "valid_loss": round(vl, 4), "valid_acc": round(va, 4)}
        history.append(row)
        if log:
            log(row)
    return history


def count_parameters(model):
    return sum(p.numel() for p in model.parameters())


def data_dir(default="data"):
    return Path(default)


__all__ = [n for n in dir() if not n.startswith("_") and n not in ("csv", "math", "random", "re", "Counter", "Path")]
