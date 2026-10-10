# Optional: the ticket page with an ORM

The lesson *Safe queries* compares plain SQL with an ORM (an object-relational mapper). This folder has the comparison that the lesson shows: the same page of tickets with SQLAlchemy 2.1.4. It is not part of the course project, and you do not need it.

```sh
python3 -m venv .venv
source .venv/bin/activate                  # Windows: .venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
export DATABASE_URL=postgresql+psycopg://tickets:<your password>@127.0.0.1:5432/tickets
python compare.py
```

(Windows: `$env:DATABASE_URL = "postgresql+psycopg://tickets:<your password>@127.0.0.1:5432/tickets"`.)

It prints how many SQL queries each version sends for one page of 20 tickets, and the SQL that the ORM makes for a value: a bound parameter, never the value inside the SQL text. `result.json` has the output of the run that the lesson quotes (on the large data, with the indexes of Module 4).
