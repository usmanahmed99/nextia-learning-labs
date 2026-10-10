"""The same ticket page with SQLAlchemy (an ORM) instead of plain SQL: what SQL does the ORM send?

    python -m venv .venv && .venv/bin/python -m pip install -r requirements.txt
    DATABASE_URL=postgresql+psycopg://tickets:...@127.0.0.1:5432/tickets .venv/bin/python compare.py

Optional, outside the project (the lesson Safe queries shows its output). It maps three tables, then
loads one page of a team's open tickets with the customer's name and the latest AI run:
1. the obvious ORM code (lazy loading): one query for the page, then more queries as the code touches
   each ticket's customer and runs (the N+1 query, hidden);
2. the same with selectinload(): a fixed number of queries;
3. a bound parameter, to show that the ORM never puts the value into the SQL text.
"""
import json
import os
import sys
import time
from datetime import datetime

import sqlalchemy
from sqlalchemy import ForeignKey, String, create_engine, event, select
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship, selectinload


class Base(DeclarativeBase):
    pass


class Customer(Base):
    __tablename__ = "customers"
    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    name: Mapped[str]


class AiRun(Base):
    __tablename__ = "ai_runs"
    run_id: Mapped[int] = mapped_column(primary_key=True)
    ticket_id: Mapped[str] = mapped_column(ForeignKey("tickets.ticket_id"))
    model: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime]


class Ticket(Base):
    __tablename__ = "tickets"
    ticket_id: Mapped[str] = mapped_column(String, primary_key=True)
    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.customer_id"))
    subject: Mapped[str]
    team: Mapped[str]
    status: Mapped[str]
    created_at: Mapped[datetime]
    customer: Mapped[Customer] = relationship()
    runs: Mapped[list[AiRun]] = relationship(order_by=AiRun.created_at.desc())


def page(session, eager):
    q = (select(Ticket).where(Ticket.status == "open", Ticket.team == "billing")
         .order_by(Ticket.created_at.desc(), Ticket.ticket_id.desc()).limit(20))
    if eager:
        q = q.options(selectinload(Ticket.customer), selectinload(Ticket.runs))
    rows = []
    for t in session.scalars(q):
        latest = t.runs[0] if t.runs else None
        rows.append((t.ticket_id, t.customer.name, latest.model if latest else None))
    return rows


def main():
    url = os.environ["DATABASE_URL"]
    engine = create_engine(url)
    statements = []
    event.listen(engine, "before_cursor_execute",
                 lambda conn, cursor, statement, params, context, many: statements.append(statement))
    out = {"sqlalchemy": sqlalchemy.__version__, "python": sys.version.split()[0]}
    for name, eager in (("lazy loading (the obvious code)", False), ("selectinload", True)):
        with Session(engine) as session:
            page(session, eager)  # warm up
        statements.clear()
        with Session(engine) as session:
            t = time.perf_counter()
            rows = page(session, eager)
            ms = (time.perf_counter() - t) * 1000
        out[name] = {"queries": len(statements), "ms": round(ms, 1), "first_row": rows[0],
                     "first_statements": statements[:3]}
        print(f"{name}: {len(statements)} queries, {ms:.1f} ms")
    q = select(Customer).where(Customer.name == "x' OR '1'='1")
    out["bound_parameter"] = str(q.compile(engine))
    print(out["bound_parameter"])
    with open(os.path.join(os.path.dirname(__file__), "result.json"), "w") as f:
        json.dump(out, f, indent=2, default=str)


if __name__ == "__main__":
    main()
