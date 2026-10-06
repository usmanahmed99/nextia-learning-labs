# C02: Python for Practical AI Engineering

Data and notebooks for [Python for Practical AI Engineering](https://learning.nextia-ai.com/courses/python/).

| Path | Used in | What it is |
|---|---|---|
| `data/tickets.csv` | Modules 4 to 6, final assignment | 15 synthetic support tickets: 9 valid, 6 with one problem each. |
| `data/tickets.json` | Module 4 | The same tickets as JSON, as a web service sends them. |
| `data/tickets-excel.csv` | Module 5 | The same tickets, saved by a spreadsheet program. |
| `data/tickets-v2.csv`, `data/tickets-v2.json` | Final assignment | 20 tickets in the new format, with `channel` and `subject`. |
| `M06-L01-notebook-discipline/` | Module 6, lesson 1 | A notebook about hidden state and restart-and-run-all. |

The dataset card is [data/dataset.md](data/dataset.md).

## Get a data file

In your project folder, with the terminal in `ticket-cleaner`:

```sh
curl -o data/tickets.csv https://raw.githubusercontent.com/usmanahmed99/nextia-learning-labs/main/C02/data/tickets.csv
```

On Windows, in PowerShell, type `curl.exe` instead of `curl`. You can also open the link in a browser and save the file into your `data` folder.
