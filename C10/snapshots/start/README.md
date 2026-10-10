# resolution-workflow

The project of the course *AI Agents and Workflow Orchestration* (Nextia Learning). Larkfield's support-resolution workflow: it reads a help-desk ticket, looks up the order, the payments and the policy, and proposes what to do. During the course it grows, module by module, into a workflow that waits for a person's approval before any change and makes every change safely. The full README comes in Module 6.

You need no account and no key. The order, payment and shipping systems are a **practice database on your computer** (a copy of `data/larkfield.sqlite`): every write is a mock write into that file, and nothing reaches a real system. The model decisions come from recordings of real models (the mock provider).

## Set up

```sh
python3 -m venv .venv
source .venv/bin/activate              # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m pytest
```

## First commands

```sh
python -m resolver tasks                          # the 70 tasks
python -m resolver show T-90103 --expected        # one ticket, and what Grace's policy expects
python -m resolver run T-90103 --variant fixed    # fixed steps: code decides, the model drafts the reply
python -m resolver run T-90103 --variant router   # the model chooses one path, code does the rest
python -m resolver run T-90103 --variant agent    # the model chooses every step
```

The lessons give the other commands as the project grows. To start again from a known state, copy the snapshot of the module you finished last (labs `C10/snapshots/`).

## Licence

MIT. The data in `data/` is CC0 (see `data/dataset.md`).
