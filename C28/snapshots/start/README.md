# support-mcp

The support knowledge of two shops, **Larkfield** and **Bramble Books**: their policy documents and their tickets. In this course it becomes one MCP server that any AI application can use.

This project belongs to the course *MCP: Connect AI Applications to Tools and Data* on Nextia Learning. Every person, ticket and shop in it is made up.

## Set up (once)

macOS or Linux:

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
python -m pytest -q
```

Windows (PowerShell):

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
python -m pytest -q
```

You need no account, no key and no money.

## Use it

```sh
python -m support_mcp.knowledge search larkfield "return a damaged item"   # the business service alone
```


## Reset

The policy documents and tickets are read from `data/` at every start and never change.

## Files

| Path | What it is |
|---|---|
| `data/` | The synthetic data and its dataset card |
| `support_mcp/knowledge.py` | The business service: search and ticket lookup inside one organization |

## Licence

MIT (see `LICENSE`). The data is CC0 (see `data/dataset.md`).
