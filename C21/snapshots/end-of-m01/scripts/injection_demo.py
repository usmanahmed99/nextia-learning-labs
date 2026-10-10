"""SQL injection on your own computer: a query built from strings, then with a parameter.

    python -m scripts.injection_demo                      a normal email address
    python -m scripts.injection_demo "x' OR '1'='1"       text that changes the query

The search looks for one customer by email address. The unsafe version pastes the
text into the SQL; the safe version sends it as a parameter, separate from the SQL.
Nothing is changed in the database: both versions only read.
"""

import sys

import psycopg

from ticket_api.config import load_env, read_secret


def find_customer_unsafe(conn: psycopg.Connection, email: str) -> list[tuple]:
    # DO NOT DO THIS: the text becomes part of the SQL.
    sql = f"SELECT customer_id, name, email FROM customers WHERE email = '{email}'"
    print(f"  SQL sent: {sql}")
    return conn.execute(sql).fetchall()


def find_customer_safe(conn: psycopg.Connection, email: str) -> list[tuple]:
    sql = "SELECT customer_id, name, email FROM customers WHERE email = %s"
    print(f"  SQL sent: {sql}    value sent separately: {email!r}")
    return conn.execute(sql, (email,)).fetchall()


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    email = argv[0] if argv else "olga.olsen@example.com"
    load_env()
    with psycopg.connect(read_secret("DATABASE_URL")) as conn:
        for name, find in (
            ("unsafe (string building)", find_customer_unsafe),
            ("safe (parameter)", find_customer_safe),
        ):
            print(f"{name}:")
            try:
                rows = find(conn, email)
                print(f"  {len(rows)} row(s)" + (f", first: {rows[0]}" if rows else ""))
            except psycopg.Error as error:
                conn.rollback()
                print(f"  error: {str(error).strip().splitlines()[0]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
