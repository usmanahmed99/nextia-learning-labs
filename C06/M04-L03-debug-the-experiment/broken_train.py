"""Tomás's training script for the ticket router. It runs, but the router is bad.

Run it from the folder ticket-router (it needs data/ and ticketnet.py):
    python broken_train.py
"""
import torch
from torch import nn

from ticketnet import BagOfWordsNet, Vocab, bag_of_words, evaluate, labels, load_split, set_seed

torch.set_num_threads(2)
LEARNING_RATE = 10
EPOCHS = 8

set_seed(0)
train_rows = load_split("data/train.csv")
valid_rows = load_split("data/valid.csv")
vocab = Vocab([r["text"] for r in train_rows])
x_train, y_train = bag_of_words(train_rows, vocab), labels(train_rows)
x_valid, y_valid = bag_of_words(valid_rows, vocab), labels(valid_rows)

# Mix the tickets once, so that the teams are not in file order.
mix = torch.randperm(len(x_train))
x_train = x_train[mix]

model = BagOfWordsNet(len(vocab))
optimizer = torch.optim.Adam(model.parameters(), lr=LEARNING_RATE)
loss_fn = nn.CrossEntropyLoss()

for epoch in range(1, EPOCHS + 1):
    model.train()
    order = torch.randperm(len(x_train))
    for i in range(0, len(order), 64):
        batch = order[i:i + 64]
        optimizer.zero_grad()
        loss = loss_fn(model(x_train[batch]), y_train[batch])
        loss.backward()
        optimizer.step()
    grad = model.layers[0].weight.grad.norm().item()
    train_loss, train_acc = evaluate(model, x_train, y_train)
    valid_loss, valid_acc = evaluate(model, x_valid, y_valid)
    print(f"epoch {epoch}: train loss {train_loss:8.3f}  acc {train_acc:6.1%} | "
          f"valid loss {valid_loss:8.3f}  acc {valid_acc:6.1%} | gradient norm {grad:8.3f}")
