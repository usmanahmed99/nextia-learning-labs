"""Make the second shop's help-desk data and the people of the authentication course.

    python build_data.py                # writes bramble/ and identity/ (in the project: data/)
    python build_data.py --out DIR      # another folder

Standard library only, no network. The same command always writes the same bytes (fixed seed);
each folder gets a SHA256SUMS file.

Everything is made up for the course. Bramble Books is a made-up independent bookshop; its
customers, orders, tickets and files are invented. The first four customers have the names of the
AI security course's Bramble customers (same IDs). Customer B-20105 has the same email address as
Larkfield's customer C-0001 (Olga Olsen shops at both): a per-shop rule must allow that.

out/bramble/   customers, tickets, messages, attachments (with small PNG and PDF files), ai_runs,
               documents: the same columns as the databases course's small data (without the
               message and run numbers: the database gives those), so the same loader reads both. Vectors: embed_bramble.py (optional; needs sentence-transformers).
out/identity/  tenants, users (the people who sign in) and memberships (who has which role where).
"""

import argparse
import csv
import hashlib
import json
import random
import shutil
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
# The file makers of the databases course's generator (PNG and PDF, standard library only): next to
# this file in the project, or in the databases course's folder.
C20_DATA = HERE.parent.parent / "c20" / "project" / "data"  # the site repository
sys.path.insert(0, str(HERE.parent.parent / "C20" / "data"))  # the labs repository
sys.path.insert(0, str(C20_DATA))
from generate import pdf, photo  # noqa: E402

SEED = 2023
TODAY = datetime(2026, 10, 9, 6, 0, tzinfo=timezone.utc)  # the same export time as Larkfield's data
START = datetime(2026, 9, 26, 7, 0, tzinfo=timezone.utc)

# ---------------------------------------------------------------- the people (identity)
TENANTS = [
    ("larkfield", "Larkfield", "2024-01-08 09:00:00+00"),
    ("bramble", "Bramble Books", "2026-09-15 09:00:00+00"),
]
# user_id (the provider's stable "sub"), name, email, platform_role
USERS = [
    ("usr-grace", "Grace", "grace@larkfield.example", ""),
    ("usr-sam", "Sam", "sam@larkfield.example", ""),
    ("usr-omar", "Omar", "omar@larkfield.example", ""),
    ("usr-ines", "Ines", "ines@bramble.example", ""),
    ("usr-camille", "Camille", "camille@larkfield.example", ""),
    ("usr-tomas", "Tomás", "tomas@larkfield.example", ""),
    ("usr-kwame", "Kwame", "kwame@larkfield.example", "platform_admin"),
]
MEMBERSHIPS = [
    ("larkfield", "usr-grace", "owner", "2024-01-08 09:00:00+00"),
    ("larkfield", "usr-sam", "staff", "2024-03-04 09:00:00+00"),
    ("larkfield", "usr-omar", "read_only", "2025-02-17 09:00:00+00"),
    ("larkfield", "usr-camille", "staff", "2025-06-02 09:00:00+00"),
    ("bramble", "usr-ines", "owner", "2026-09-15 09:00:00+00"),
    ("bramble", "usr-camille", "read_only", "2026-09-22 09:00:00+00"),
]

# ---------------------------------------------------------------- Bramble Books
CUSTOMERS = [
    # customer_id, name, email, segment, region, joined_on
    ("B-20101", "Eleanor Price", "eleanor.price@mail.example", "home", "west", "2026-09-16"),
    ("B-20102", "Samir Haddad", "samir.haddad@mail.example", "home", "west", "2026-09-16"),
    ("B-20103", "Chloé Martin", "chloe.martin@courriel.example", "home", "east", "2026-09-17"),
    ("B-20104", "Peter Novak", "peter.novak@mail.example", "home", "west", "2026-09-18"),
    ("B-20105", "Olga Olsen", "olga.olsen@example.com", "home", "north", "2026-09-18"),
    ("B-20106", "Ruth Adeyemi", "ruth.adeyemi@mail.example", "home", "west", "2026-09-19"),
    ("B-20107", "Westshore Reading Circle", "books@westshore-circle.example", "business", "west", "2026-09-19"),
    ("B-20108", "Daniel Okoro", "daniel.okoro@mail.example", "home", "south", "2026-09-20"),
    ("B-20109", "Mina Park", "mina.park@mail.example", "home", "west", "2026-09-21"),
    ("B-20110", "Harbour Primary School", "library@harbour-school.example", "business", "west", "2026-09-22"),
    ("B-20111", "Leo Fischer", "leo.fischer@mail.example", "home", "east", "2026-09-23"),
    ("B-20112", "Agnes Moreau", "agnes.moreau@mail.example", "home", "west", "2026-09-24"),
]

BOOKS = [("The Orchard Year", 28.00), ("Maps of Small Rivers", 52.00), ("A Field Guide to Moss", 34.50),
         ("The Lighthouse Cookbook", 41.00), ("Night Trains of Europe", 37.00), ("Quiet Gardens", 45.00),
         ("The Clockmaker's Daughter", 22.00), ("Stars for Beginners", 19.50), ("Salt and Cedar", 26.00)]

# team, priority, subject, body. {b} book, {o} order, {a} amount.
TICKETS = [
    ("billing", 1, "Charged twice for order {o}",
     "My card was charged two times for order {o}, {a} dollars each time. Please refund one of the payments."),
    ("billing", 1, "Charged twice for my book order",
     "I paid once for order {o} but my bank shows two payments of {a} dollars. Can you refund the second one?"),
    ("billing", 2, "Refund not received for order {o}",
     "I returned {b} two weeks ago and I still have no refund for order {o}."),
    ("billing", 2, "Gift card was not accepted",
     "The checkout refused my Bramble gift card when I tried to pay for {b}."),
    ("billing", 3, "Invoice for the school library",
     "Please send an invoice with our school's name for order {o}. Our accounts team needs it."),
    ("shipping", 2, "Where is my order {o}?",
     "I ordered {b} (order {o}) last week and the tracking page has not changed for four days."),
    ("shipping", 1, "Book arrived damaged",
     "{b} arrived with a bent cover and torn pages. The box was crushed. Order {o}. Photo attached."),
    ("shipping", 2, "Wrong book in my parcel",
     "I ordered {b} but the parcel for order {o} had a different book in it."),
    ("shipping", 3, "Change the delivery address of {o}",
     "Can you send order {o} to my office instead? It has not shipped yet."),
    ("shipping", 2, "Pre-order date changed",
     "The pre-order date for {b} moved again. Is order {o} still coming this month?"),
    ("account", 3, "Update my email address",
     "I have a new email address. Please change it on my Bramble account."),
    ("account", 3, "Close my account",
     "Please close my account and delete my reading list."),
    ("login", 2, "Cannot sign in to my account",
     "The sign-in page says my password is wrong, but the reset email never arrives."),
    ("login", 3, "Two accounts with one email",
     "I think I made two accounts by mistake. Can you join them?"),
    ("other", 3, "Signed copy request",
     "Will you have signed copies of {b} at the author's visit? I would like to reserve one."),
    ("other", 3, "Book club discount",
     "Our reading circle buys ten copies each month. Is there a discount for book clubs?"),
    ("other", 3, "Do you buy used books?",
     "I have two boxes of used novels. Do you buy or trade used books?"),
]
AGENT_REPLIES = [
    "Thank you for writing to Bramble Books. I have checked order {o} and passed it to our team.",
    "Sorry about this. Could you send a photo of the book and the box? Then we can send a new copy.",
    "I can see the second payment for order {o}. We have refunded it; you will see it in 3 to 5 days.",
    "Your order {o} left our shop yesterday. The courier's page can take a day to show it.",
]
CUSTOMER_FOLLOW_UPS = ["Thank you, that helps.", "Any news on this?", "I have attached the photo now."]
DRAFTS = ["Hello {n}, thank you for writing to Bramble Books. I have passed your question about {b} to the right "
          "person, and they will contact you soon.",
          "Hello {n}, I am sorry that {b} arrived damaged. We will send a new copy of order {o} today."]
PRICES = {"chat-small": (0.10, 0.50)}

DOCUMENTS = [
    # doc_id, version, title, doc_type, access, effective_from, body
    ("returns-policy", 1, "Returning a book", "policy", "public", "2026-09-15",
     "# Returning a book\n\nYou can return a book within 30 days if it is unread and in the condition we sent it."
     " We refund the price of the book to the card you paid with. We do not refund the delivery cost unless the "
     "book was damaged or wrong.\n\nA damaged or wrong book: write to us within 14 days with a photo. We send a "
     "new copy or refund the whole order, as you prefer.\n"),
    ("delivery-policy", 1, "Delivery times", "policy", "public", "2026-09-15",
     "# Delivery times\n\nWe ship within 2 business days. Delivery in British Columbia takes 2 to 4 business "
     "days, and 4 to 8 days to the rest of Canada. Delivery costs 6.50 dollars, or nothing for orders over "
     "60 dollars.\n\nPre-orders ship on the day the publisher releases the book.\n"),
    ("supplier-terms", 1, "Wholesale terms (staff only)", "supplier", "staff", "2026-09-15",
     "# Wholesale terms (staff only)\n\nOur wholesaler gives Bramble Books 40 percent off the list price, and 45 "
     "percent on orders of 50 books or more. Do not share these terms with customers. Book clubs and schools "
     "may get 10 percent off; an owner approves larger discounts.\n"),
]


def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S+00")


def make_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


def write_csv(path: Path, header: list[str], rows: list[list]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(header)
        w.writerows(rows)


def sha256sums(folder: Path) -> None:
    lines = []
    for p in sorted(folder.rglob("*")):
        if p.is_file() and p.name != "SHA256SUMS":
            lines.append(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.relative_to(folder).as_posix()}")
    (folder / "SHA256SUMS").write_text("\n".join(lines) + "\n", encoding="utf-8")


def identity(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)
    write_csv(out / "tenants.csv", ["tenant_id", "name", "created_at"], [list(t) for t in TENANTS])
    write_csv(out / "users.csv", ["user_id", "name", "email", "platform_role"], [list(u) for u in USERS])
    write_csv(out / "memberships.csv", ["tenant_id", "user_id", "role", "created_at"],
              [list(m) for m in MEMBERSHIPS])
    sha256sums(out)


def status_for(created: datetime, rng: random.Random) -> str:
    age = (TODAY - created).days
    if age < 2:
        return rng.choice(["open", "open", "pending"])
    return rng.choices(["resolved", "closed", "open", "pending"], [45, 25, 18, 12])[0]


def bramble(out: Path) -> dict:
    rng = random.Random(SEED)
    # The vectors (ticket_embeddings.*, from embed_bramble.py) stay; everything else is made again.
    if (out / "files").exists():
        shutil.rmtree(out / "files")
    (out / "files").mkdir(parents=True)

    customers = []
    for cid, name, email, segment, region, joined in CUSTOMERS:
        created = datetime.fromisoformat(joined).replace(hour=rng.randint(8, 18), minute=rng.randint(0, 59),
                                                          second=rng.randint(0, 59), tzinfo=timezone.utc)
        customers.append([cid, name, email, segment, region, joined, ts(created)])

    tickets, messages, attachments, runs = [], [], [], []
    span = (TODAY - START).total_seconds()
    created_times = sorted(START + timedelta(seconds=rng.uniform(0, span - 7200)) for _ in range(40))
    # Ticket 1 and 2 are the "Charged twice" tickets of the lessons (similar to Larkfield's T-30002).
    plan = [0, 1, 6] + [rng.randrange(len(TICKETS)) for _ in range(37)]
    for i, created in enumerate(created_times):
        tid = f"T-{40001 + i}"
        team, priority, subject, body = TICKETS[plan[i]]
        customer = customers[[0, 1, 2][i] if i < 3 else rng.randrange(len(customers))]
        book, price = rng.choice(BOOKS)
        order = f"BB-{310000 + rng.randint(5, 999)}"
        qty = 10 if "circle" in customer[1].lower() or "school" in customer[1].lower() else 1
        amount = f"{price * qty + (0 if price * qty > 60 else 6.5):.2f}"
        fill = {"b": book, "o": order, "a": amount}
        subject, body = subject.format(**fill), body.format(**fill)
        status = status_for(created, rng) if i >= 3 else ["open", "pending", "open"][i]
        channel = rng.choices(["email", "web_form", "chat", "phone"], [45, 35, 15, 5])[0]
        last = created
        n_msgs = rng.choice([0, 1, 1, 2, 2, 3])
        t = created
        for k in range(n_msgs):
            t = t + timedelta(minutes=rng.randint(20, 900))
            if t >= TODAY:
                break
            author = "agent" if k % 2 == 0 else "customer"
            text = (rng.choice(AGENT_REPLIES) if author == "agent" else rng.choice(CUSTOMER_FOLLOW_UPS))
            messages.append([tid, author, text.format(**fill), ts(t)])
            last = t
        closed = ""
        if status in ("resolved", "closed"):
            close = last + timedelta(minutes=rng.randint(30, 600))
            if close >= TODAY:
                status, close = "pending", None
            else:
                closed = ts(close)
                last = close
        tickets.append([tid, customer[0], subject, body, channel, team, priority, status, ts(created), ts(last),
                        closed])
        # files: photos of damaged books, receipts for billing questions
        files = []
        if "damaged" in subject.lower():
            files.append(("photo-1.png", "image/png", photo(rng)))
        if team == "billing" and plan[i] in (0, 1, 2):
            files.append((f"receipt-{order}.pdf", "application/pdf",
                          pdf(["Bramble Books", f"Receipt for order {order}", f"Customer: {customer[1]}",
                               f"{book} x {qty}", f"Total: {amount} CAD", "Paid by card"])))
        up = created
        for name, kind, data in files:
            att = make_uuid(rng)
            up = up + timedelta(seconds=rng.randint(10, 120))
            key = f"tickets/{tid}/{att}/{name}"
            (out / "files" / key).parent.mkdir(parents=True, exist_ok=True)
            (out / "files" / key).write_bytes(data)
            attachments.append([att, tid, name, kind, len(data), hashlib.sha256(data).hexdigest(), key, ts(up)])
        # AI runs: a keyword classification for every ticket, a draft reply for most
        out_json = json.dumps({"category": team, "priority": priority})
        runs.append([tid, "classify", "keywords-1.0", "", 0, 0, "0", rng.randint(2, 6), "ok", out_json,
                     ts(created + timedelta(seconds=1))])
        if rng.random() < 0.7:
            tin, tout = rng.randint(800, 1300), rng.randint(90, 220)
            cin, cout = PRICES["chat-small"]
            cost = (tin * cin + tout * cout) / 1_000_000
            draft = DRAFTS[1 if "damaged" in subject.lower() else 0].format(n=customer[1].split()[0], **fill)
            runs.append([tid, "draft_reply", "chat-small", "draft-v2", tin, tout, f"{cost:.8f}",
                         rng.randint(600, 2400), "ok", draft, ts(created + timedelta(seconds=2))])

    documents = []
    for doc_id, version, title, doc_type, access, start, body in DOCUMENTS:
        documents.append([doc_id, version, title, doc_type, "en", access, start, "", body,
                          hashlib.sha256(body.encode()).hexdigest()])

    write_csv(out / "customers.csv", ["customer_id", "name", "email", "segment", "region", "joined_on",
                                      "created_at"], customers)
    write_csv(out / "tickets.csv", ["ticket_id", "customer_id", "subject", "body", "channel", "team", "priority",
                                    "status", "created_at", "updated_at", "closed_at"], tickets)
    write_csv(out / "messages.csv", ["ticket_id", "author", "body", "created_at"], messages)
    write_csv(out / "attachments.csv", ["attachment_id", "ticket_id", "file_name", "content_type", "size_bytes",
                                        "sha256", "object_key", "uploaded_at"], attachments)
    write_csv(out / "ai_runs.csv", ["ticket_id", "task", "model", "prompt_version", "tokens_in",
                                    "tokens_out", "cost_usd", "latency_ms", "status", "output", "created_at"],
              runs)
    write_csv(out / "documents.csv", ["doc_id", "version", "title", "doc_type", "language", "access",
                                      "effective_from", "effective_to", "body", "sha256"], documents)
    counts = {"tenant": "bramble", "customers": len(customers), "tickets": len(tickets), "messages": len(messages),
              "attachments": len(attachments), "documents": len(documents), "ai_runs": len(runs),
              "files": len(attachments)}
    (out / "counts.json").write_text(json.dumps(counts, indent=2) + "\n", encoding="utf-8")
    return counts


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    # In the project, the folders are next to this file; in the authors' copy, in out/.
    default = HERE if (HERE / "generate.py").exists() else HERE / "out"
    parser.add_argument("--out", type=Path, default=default)
    args = parser.parse_args()
    identity(args.out / "identity")
    counts = bramble(args.out / "bramble")
    sha256sums(args.out / "bramble")
    print(f"Wrote {args.out / 'identity'} and {args.out / 'bramble'}: {counts}")


if __name__ == "__main__":
    main()
