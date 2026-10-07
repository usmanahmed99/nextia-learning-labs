"""Run a SQL query on larkfield.db and print the result as a table.

Nextia Learning, C04: SQL and Data Preparation for AI.

    python q.py queries/01-first-look.sql     run the query in a file
    python q.py "SELECT COUNT(*) FROM tickets"  run a query that you type
    python q.py queries/report.sql --all       print every row (the default is 20)

The script uses the Python standard library only. It opens the database
read-only, so a query cannot change the data by mistake. If a file holds
more than one statement, only the last one prints a result.
"""

import sqlite3
import sys
from pathlib import Path

DB = Path("larkfield.db")
LIMIT = 20


def main():
    args = [a for a in sys.argv[1:] if a != "--all"]
    if len(args) != 1:
        sys.exit(__doc__.split("\n\n")[1])
    if not DB.exists():
        sys.exit(f"{DB} is not in this folder. Run the script from your project folder, "
                 "or build the database first: python get_data.py")
    source = Path(args[0])
    sql = source.read_text(encoding="utf-8") if source.suffix == ".sql" else args[0]

    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        statements = [s for s in split(sql) if s.strip()]
        for statement in statements[:-1]:
            con.execute(statement)
        cursor = con.execute(statements[-1]) if statements else None
    except sqlite3.Error as error:
        sys.exit(f"SQL error: {error}")
    if cursor is None or cursor.description is None:
        print("(The statement ran and returned no rows.)")
        return

    header = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    shown = rows if "--all" in sys.argv else rows[:LIMIT]
    cells = [["NULL" if v is None else str(v) for v in row] for row in shown]
    widths = [max([len(h)] + [len(r[i]) for r in cells]) for i, h in enumerate(header)]
    print("  ".join(h.ljust(w) for h, w in zip(header, widths)))
    print("  ".join("-" * w for w in widths))
    for r in cells:
        print("  ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip())
    more = f" (showing {len(shown)}; add --all to see every row)" if len(shown) < len(rows) else ""
    print(f"\n{len(rows)} row{'s' if len(rows) != 1 else ''}{more}")


def split(sql):
    """Split a script into statements at semicolons outside quotes and comments."""
    statement, quote, i = "", None, 0
    while i < len(sql):
        ch = sql[i]
        if quote:
            statement += ch
            if ch == quote:
                quote = None
        elif ch in "'\"":
            quote = ch
            statement += ch
        elif sql.startswith("--", i):
            end = sql.find("\n", i)
            i = len(sql) if end == -1 else end
            continue
        elif ch == ";":
            yield statement
            statement = ""
        else:
            statement += ch
        i += 1
    yield statement


if __name__ == "__main__":
    main()
