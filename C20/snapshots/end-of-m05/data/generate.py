"""Make Larkfield's help-desk data for the databases course. Standard library only, no network.

    python generate.py                  # both sizes into out/small and out/large
    python generate.py --size small     # one size
    python generate.py --out DIR        # another folder

The same command always writes the same bytes (a fixed seed per size). Each size folder gets a
SHA256SUMS file; `sha256sum -c SHA256SUMS` (or `shasum -a 256 -c`) checks a copy.

Everything is made up for the course: no real customer, ticket or file. The first customers are the
customers of the SQL course (same IDs, segment, region and join date; segment in lower case); their
names and email addresses are new and made up (example.com addresses only). The policy documents are
the ones of the RAG course (source/documents/, CC0).

small  40 customers, 200 tickets (25 Sep - 8 Oct 2026), real attachment files in files/
large  20,000 customers, 300,000 tickets (9 Oct 2025 - 8 Oct 2026); attachments are metadata only

Planted on purpose, in both sizes (the schema lessons find them): 3 messages whose ticket does not
exist (left over from test tickets that someone deleted by hand in the old help-desk tool).
"""

import argparse
import csv
import hashlib
import io
import json
import random
import shutil
import struct
import uuid
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE / "source"
VERSION = "1.0"

SIZES = {
    "small": {"seed": 2020, "customers": 40, "tickets": 200, "first_ticket": 30001,
              "start": date(2026, 9, 25), "end": date(2026, 10, 8), "files": True},
    "large": {"seed": 2021, "customers": 20000, "tickets": 300000, "first_ticket": 100001,
              "start": date(2025, 10, 9), "end": date(2026, 10, 8), "files": False},
}
TODAY = datetime(2026, 10, 9, 6, 0, tzinfo=timezone.utc)  # the export time: the course's "today"

FIRST = ["Ana", "Ben", "Chloe", "Daniel", "Elif", "Farah", "George", "Hana", "Ivan", "Jade", "Kofi", "Lena",
         "Marco", "Nadia", "Oscar", "Priyanka", "Quinn", "Rosa", "Samir", "Tara", "Uma", "Victor", "Wen",
         "Yusuf", "Zoe", "Amara", "Bruno", "Carmen", "Dev", "Emma", "Felix", "Grace", "Hugo", "Ines", "Jonas",
         "Keiko", "Liam", "Maya", "Noah", "Olga", "Pedro", "Rania", "Sofia", "Theo", "Valeria", "Will",
         "Ximena", "Yara", "Aiden", "Bea", "Cyrus", "Dina", "Ezra", "Fatima", "Gil", "Hiro", "Isla", "Jamal"]
LAST = ["Abara", "Becker", "Chen", "Dubois", "Eriksen", "Fernandes", "Garcia", "Haddad", "Ito", "Jensen",
        "Kowalski", "Lam", "Moreau", "Nakamura", "Okafor", "Petrov", "Quinlan", "Rossi", "Singh", "Tremblay",
        "Usman", "Varga", "Walsh", "Xu", "Yilmaz", "Zhang", "Adeyemi", "Brennan", "Costa", "Dimitrov", "Ekström",
        "Fischer", "Gomez", "Hughes", "Ivanova", "Kaur", "Lindqvist", "Martin", "Novak", "Olsen", "Park",
        "Ramos", "Santos", "Takahashi", "Ueda", "Vidal", "Wong", "Young", "Zielinski", "Bose", "Murphy"]
REGIONS = ["north", "south", "east", "west"]

# The shop's products (the agents course's catalogue).
PRODUCTS = [
    ("BBQ-GR310", "Ember GR-310 gas BBQ", 449.0), ("BENCH-WD", "wooden garden bench", 249.0),
    ("CAN-10", "watering can", 19.95), ("CHAIR-G", "garden chair", 54.0), ("COMPOST", "compost bin", 64.0),
    ("CUSH-4", "cushion covers (set of 4)", 36.0), ("FEEDER", "bird feeder", 22.0),
    ("GREENHOUSE", "greenhouse frame", 460.0), ("HAMMOCK", "hammock", 74.0),
    ("HOSE-25", "garden hose (25 m)", 34.5), ("HR-30", "AquaFlow HR-30 hose reel", 59.0),
    ("HT-550", "HT-550 electric hedge trimmer", 99.0), ("KT-180", "KT-180 electric kettle", 49.0),
    ("LADDER-3", "step ladder", 79.0), ("LIGHTS-6", "solar path lights (set of 6)", 45.0),
    ("PARASOL", "patio parasol", 129.0), ("PLANTER", "cedar planter", 89.0),
    ("POT-TC3", "terracotta pot (set of 3)", 27.5), ("PW-2200", "PW-2200 electric pressure washer", 189.0),
    ("RUG-W", "wool rug", 149.0), ("SHEARS", "pruning shears", 24.95), ("SHED-6X8", "garden shed", 899.0),
    ("TOOLCHEST", "tool chest", 119.0), ("TRAMP-10", "trampoline", 289.0), ("VAC-R1", "robot vacuum", 329.0),
]

TEAMS = ["shipping", "billing", "other", "account", "login"]  # the ticket API's categories
TEAM_WEIGHTS = [30, 23, 25, 12, 10]
CHANNELS = ["email", "web_form", "chat", "phone"]
CHANNEL_WEIGHTS = [42, 33, 18, 7]

# Subjects and first messages. {p} product, {o} order, {d} days, {a} amount, {m} month, {c} courier.
TEMPLATES = {
    "shipping": [
        ("Where is my order {o}?", "Hello, I ordered the {p} on order {o} {d} days ago and the tracking page has not changed since. Can you tell me when it will arrive?"),
        ("{p} not delivered", "My {p} (order {o}) was due last week. The courier {c} says it is still at the depot. Please help."),
        ("Parcel arrived damaged", "The box for order {o} arrived crushed and the {p} inside is cracked. I have attached a photo of the box and the item."),
        ("Only one box arrived", "Order {o} should be two boxes, but only one arrived. The {p} is missing. The tracking number shows delivered."),
        ("Change delivery address", "Can I change the delivery address for order {o}? I am moving next week and the {p} has not shipped yet."),
        ("Delivery driver left parcel outside", "The {p} from order {o} was left outside in the rain. The box is wet. Is the item still under warranty?"),
        ("Tracking number does not work", "The tracking number for my {p} (order {o}) gives an error on the {c} website."),
        ("Late delivery fee", "I paid for express delivery on order {o} but the {p} arrived {d} days late. Can I get the delivery fee back?"),
        ("Wrong item delivered", "I ordered the {p} but the parcel for order {o} contained something else. Photo attached."),
        ("When will the {p} be back in stock?", "I want to order the {p} but the website says out of stock. Do you know when it will be available again?"),
    ],
    "billing": [
        ("Charged twice for order {o}", "My card was charged two times for order {o}, {a} dollars each time. Please refund one of the payments."),
        ("Refund not received", "You approved a refund of {a} dollars for the {p} {d} days ago, but it is not on my card yet."),
        ("Invoice for my company", "I need an invoice with my company name for order {o} ({p}, {a} dollars). Can you send one?"),
        ("Wrong price charged", "The website showed the {p} at a lower price, but I was charged {a} dollars on order {o}. Receipt attached."),
        ("Discount code did not apply", "My discount code did not work on order {o}. I paid the full {a} dollars for the {p}."),
        ("Payment failed but money taken", "The checkout said my payment failed, but my bank shows a payment of {a} dollars to Larkfield."),
        ("Gift card balance", "I have a gift card and I want to know the balance before I order the {p}."),
        ("Receipt for warranty claim", "I lost the receipt for my {p}. Can you send a copy for order {o}? I need it for a warranty claim."),
    ],
    "account": [
        ("Change my email address", "Please change the email address on my account. I no longer use the old one."),
        ("Delete my account", "Please delete my account and all my data. I do not want to shop with Larkfield any more."),
        ("Update my phone number", "How do I change the phone number on my account? The profile page does not save it."),
        ("Merge two accounts", "I have two accounts with different email addresses. Can you merge them into one?"),
        ("Unsubscribe from emails", "I get three marketing emails a week. Please stop them, but keep the order emails."),
        ("Trade account application", "I run a small landscaping company. How do I open a trade account?"),
        ("Copy of my data", "Please send me a copy of all the personal data that you keep about me."),
    ],
    "login": [
        ("Cannot log in", "I cannot log in to my account. The password reset link in the email does not work."),
        ("Locked out of my account", "My account is locked after three wrong passwords. I need to see my order {o}."),
        ("Verification code not arriving", "The verification code for sign in never arrives on my phone."),
        ("Two-factor problem", "I changed my phone and now I cannot finish the two-factor step. Please help me get back in."),
        ("Password reset email missing", "I asked for a password reset four times today and no email arrived. I checked the spam folder."),
    ],
    "other": [
        ("How do I assemble the {p}?", "The instructions for the {p} are missing from the box. Where can I find them?"),
        ("{p} stopped working", "My {p} stopped working after {d} days. It does not turn on any more. Is it under warranty?"),
        ("Question about the {p}", "Is the {p} suitable for use in winter? I live in the north and it gets very cold."),
        ("Return the {p}", "I want to return the {p} from order {o}. It is unused and still in the box."),
        ("Missing part", "The {p} from order {o} arrived without the screws. Can you send them?"),
        ("Installation service", "Do you offer installation for the {p}? I cannot do it myself."),
        ("Product smells of burning", "My {p} smells of burning when I use it. I stopped using it. What should I do?"),
        ("Recycling old item", "Can you take back my old {p} when you deliver the new one?"),
        ("Bulk order", "I want to order 20 of the {p} for a community garden. Is there a discount?"),
    ],
}
AGENT_REPLIES = {
    "shipping": [
        "Thank you for your message. I have checked order {o} with {c} and I will update you within one business day.",
        "Sorry about this. I have asked the warehouse to look at order {o}. You will get an email when we know more.",
        "Thank you for the photo. We will send a replacement {p} this week, and a free return label for the damaged one.",
        "Could you send a photo of the item and the label on the box? Then I can open a claim with the courier.",
        "Your parcel is at the {c} depot and will be delivered tomorrow.",
    ],
    "billing": [
        "I can see the problem. I have started a refund of {a} dollars. It can take 5 to 10 business days to reach your card.",
        "I have sent the invoice for order {o} to your email address.",
        "I checked the payments for order {o}. The second payment was only an authorisation, and your bank will release it.",
        "Could you send the receipt or a screenshot of the payment? Then I can check it with our payments team.",
    ],
    "account": [
        "Your request is done. Please reply if anything is still not right.",
        "For your security, please confirm this request from the email address on your account.",
        "I have passed your request to our privacy team. They answer within 30 days, as the privacy policy says.",
    ],
    "login": [
        "I have reset your sign-in. Please try again and use the newest email that we sent.",
        "I have unlocked your account. You can sign in again now.",
        "Please check that your phone can receive text messages from short numbers, then ask for a new code.",
    ],
    "other": [
        "Thank you for your message. You can find the instructions for the {p} on its product page, under Downloads.",
        "I have passed this to our product team. A specialist will contact you within two business days.",
        "Please stop using the {p} now. We will collect it and send a replacement. Your safety comes first.",
        "Yes, the {p} is covered by the warranty. I have started a claim for you.",
    ],
}
CUSTOMER_FOLLOW_UPS = [
    "Thank you, that works now.", "Any news on this? It has been {d} days.", "I attached the photo you asked for.",
    "Yes, please send the replacement.", "I still have not received anything.", "Great, thanks for the quick help!",
    "The refund is on my card now. Thanks.", "Can I talk to someone on the phone about this?",
]
DRAFTS = [
    "Hello {n}, thank you for contacting Larkfield. I am sorry about the problem with your {p}. I have checked order {o}, and a colleague will confirm the next step today.",
    "Hello {n}, thank you for your message about order {o}. I understand that this is frustrating. We will look at it and reply within one business day.",
    "Hello {n}, I am sorry about the problem with your {p}. Could you please send a photo of the item, so that we can help you quickly?",
    "Hello {n}, thank you for writing to us. I have passed your question about the {p} to the right team, and they will contact you soon.",
]
COURIERS = ["Northline", "ParcelGo", "SwiftPost"]

# Dated prices of the model deployments (US$ per million tokens, input / output; checked 2026-10-08).
PRICES = {"chat-small": (0.10, 0.50), "chat-strong": (2.00, 10.00)}


def ts(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d %H:%M:%S+00")


def make_uuid(rng: random.Random) -> str:
    return str(uuid.UUID(int=rng.getrandbits(128), version=4))


# ---------- small synthetic files (PNG and PDF, standard library only) ----------

def png(width: int, height: int, pixel) -> bytes:
    raw = bytearray()
    for y in range(height):
        raw.append(0)
        for x in range(width):
            raw.extend(pixel(x, y))
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    head = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", head) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def photo(rng: random.Random) -> bytes:
    """A made-up 'photo' of a parcel or an item: a box shape on a floor, with a crack line."""
    w, h = 320, 240
    floor = (rng.randint(120, 170), rng.randint(110, 150), rng.randint(90, 130))
    box = (rng.randint(170, 210), rng.randint(130, 160), rng.randint(80, 110))
    x0, y0 = rng.randint(40, 90), rng.randint(40, 80)
    x1, y1 = x0 + rng.randint(140, 190), y0 + rng.randint(100, 130)
    crack = [(x0 + 20 + i * 6, y0 + 10 + (i * 7 + rng.randint(-3, 3))) for i in range(18)]
    crack_set = {(x + dx, y + dy) for x, y in crack for dx in (0, 1) for dy in (0, 1)}
    noise = [rng.randint(-6, 6) for _ in range(97)]

    def pixel(x, y):
        n = noise[(x * 31 + y * 17) % 97]
        if (x, y) in crack_set:
            return (40, 30, 25)
        if x0 <= x <= x1 and y0 <= y <= y1:
            base = box if (x - x0) > 6 and (y - y0) > 6 else (box[0] - 40, box[1] - 40, box[2] - 30)
        else:
            base = floor
        return tuple(max(0, min(255, c + n)) for c in base)
    return png(w, h, pixel)


def pdf(lines: list[str]) -> bytes:
    """A one-page PDF receipt with plain text lines (Helvetica)."""
    text = "BT /F1 12 Tf 50 780 Td 16 TL " + " ".join(
        "(" + ln.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)") + ") '" for ln in lines) + " ET"
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 595 842] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        b"<< /Length " + str(len(text)).encode() + b" >>\nstream\n" + text.encode("latin-1") + b"\nendstream",
    ]
    out = io.BytesIO()
    out.write(b"%PDF-1.4\n")
    offsets = []
    for i, body in enumerate(objects, 1):
        offsets.append(out.tell())
        out.write(f"{i} 0 obj\n".encode() + body + b"\nendobj\n")
    xref = out.tell()
    out.write(f"xref\n0 {len(objects) + 1}\n0000000000 65535 f \n".encode())
    for off in offsets:
        out.write(f"{off:010d} 00000 n \n".encode())
    out.write(f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF\n".encode())
    return out.getvalue()


# ---------- the tables ----------

def customers(rng: random.Random, n: int) -> list[dict]:
    with open(SOURCE / "sql-course-customers.csv", newline="", encoding="utf-8") as f:
        sql_course = list(csv.DictReader(f))
    rows, used = [], set()
    for i in range(1, n + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        base = f"{first}.{last}".lower().replace("ö", "o")
        email, k = f"{base}@example.com", 2
        while email in used:
            email, k = f"{base}{k}@example.com", k + 1
        used.add(email)
        if i <= len(sql_course):
            src = sql_course[i - 1]
            segment, region, joined = src["segment"].lower(), src["region"] or None, src["joined_on"]
        else:
            segment = rng.choices(["home", "trade", "business"], [70, 20, 10])[0]
            region = rng.choice(REGIONS) if rng.random() > 0.03 else None
            joined = (date(2019, 1, 1) + timedelta(days=rng.randint(0, 2700))).isoformat()
        rows.append({"customer_id": f"C-{i:04d}", "name": f"{first} {last}", "email": email, "segment": segment,
                     "region": region, "joined_on": joined,
                     "created_at": f"{joined} {rng.randint(7, 21):02d}:{rng.randint(0, 59):02d}:{rng.randint(0, 59):02d}+00"})
    return rows


def fill(template: str, rng: random.Random, product: tuple, order: str, name: str = "") -> str:
    return template.format(p=product[1], o=order, d=rng.randint(2, 21), a=f"{product[2]:.2f}",
                           c=rng.choice(COURIERS), n=name.split()[0] if name else "there", m="")


def status_for(created: datetime, rng: random.Random) -> str:
    age = (TODAY - created).total_seconds() / 86400
    if age < 2:
        return rng.choices(["open", "pending", "resolved"], [65, 20, 15])[0]
    if age < 14:
        return rng.choices(["open", "pending", "resolved", "closed"], [18, 14, 48, 20])[0]
    return rng.choices(["open", "pending", "resolved", "closed"], [1.5, 1, 10, 87.5])[0]


def generate(size: str, out: Path) -> None:
    cfg = SIZES[size]
    rng = random.Random(cfg["seed"])
    if (out / "files").exists():
        shutil.rmtree(out / "files")
    out.mkdir(parents=True, exist_ok=True)
    cust = customers(rng, cfg["customers"])
    # A few customers write many tickets: weights from a Pareto distribution.
    weights = [rng.paretovariate(1.6) for _ in cust]
    # The customer with the most tickets is a business account (its staff write for many sites).
    top = max(range(len(cust)), key=weights.__getitem__)
    if top >= 240:
        cust[top]["segment"] = "business"
    cum, total = [], 0.0
    for w in weights:
        total += w
        cum.append(total)
    start = datetime.combine(cfg["start"], datetime.min.time(), tzinfo=timezone.utc)
    span = (datetime.combine(cfg["end"], datetime.min.time(), tzinfo=timezone.utc) + timedelta(days=1) - start).total_seconds()
    n = cfg["tickets"]
    # Ticket times in order: sorted uniform times, nudged to the shop's hours.
    times = sorted(start + timedelta(seconds=rng.random() * span) for _ in range(n))
    times = [t.replace(hour=(7 + (t.hour * 14) // 24)) for t in times]
    times.sort()

    tickets, messages, attachments, runs, files = [], [], [], [], {}
    message_id = run_id = 0
    for i, created in enumerate(times):
        tid = f"T-{cfg['first_ticket'] + i}"
        day = created.date().isoformat()
        for _ in range(20):  # a customer who had joined by then
            c = rng.choices(cust, cum_weights=cum)[0]
            if c["joined_on"] <= day:
                break
        else:
            c = cust[0]
        team = rng.choices(TEAMS, TEAM_WEIGHTS)[0]
        product = rng.choice(PRODUCTS)
        order = f"LK-{rng.randint(100000, 999999)}"
        subject_t, body_t = rng.choice(TEMPLATES[team])
        subject, body = fill(subject_t, rng, product, order), fill(body_t, rng, product, order)
        urgent = any(w in body.lower() for w in ("cannot", "locked", "two times", "burning", "charged two"))
        priority = 1 if urgent else rng.choices([2, 3], [70, 30])[0]
        status = status_for(created, rng)
        channel = rng.choices(CHANNELS, CHANNEL_WEIGHTS)[0]
        # Messages after the first one (the first message is the ticket's body).
        n_msgs = {"open": rng.choices([0, 1, 2], [55, 35, 10])[0], "pending": rng.choices([1, 2, 3], [50, 35, 15])[0],
                  "resolved": rng.choices([1, 2, 3, 4], [30, 35, 25, 10])[0],
                  "closed": rng.choices([1, 2, 3, 4, 5], [25, 35, 22, 12, 6])[0]}[status]
        t = created
        for k in range(n_msgs):
            t = t + timedelta(minutes=rng.randint(20, 60 * 30))
            if t > TODAY - timedelta(minutes=5):
                break
            message_id += 1
            author = "agent" if k % 2 == 0 else "customer"
            text = fill(rng.choice(AGENT_REPLIES[team] if author == "agent" else CUSTOMER_FOLLOW_UPS), rng, product, order)
            messages.append({"message_id": message_id, "ticket_id": tid, "author": author, "body": text,
                             "created_at": ts(t)})
        updated = t
        closed = None
        if status in ("resolved", "closed"):
            closed = min(t + timedelta(minutes=rng.randint(5, 600)), TODAY - timedelta(minutes=1))
            updated = closed
        tickets.append({"ticket_id": tid, "customer_id": c["customer_id"], "subject": subject, "body": body,
                        "channel": channel, "team": team, "priority": priority, "status": status,
                        "created_at": ts(created), "updated_at": ts(updated), "closed_at": ts(closed) if closed else None})
        # Attachments: photos for damage and wrong items, receipts for billing.
        wants = ("photo" in body.lower() or "attached" in body.lower() or "receipt" in body.lower())
        if wants or rng.random() < 0.06:
            for k in range(1 if rng.random() < 0.8 else 2):
                aid = make_uuid(rng)
                is_pdf = team == "billing" or (not wants and rng.random() < 0.3)
                name = f"receipt-{order}.pdf" if is_pdf else f"photo-{k + 1}.png"
                ctype = "application/pdf" if is_pdf else "image/png"
                key = f"tickets/{tid}/{aid}/{name}"
                if cfg["files"]:
                    content = pdf(["Larkfield - receipt", f"Order {order}", f"Customer {c['customer_id']}",
                                   f"Item: {product[1]}", f"Price: {product[2]:.2f} CAD", "Paid by card",
                                   "Made-up document for a course. Not a real receipt."]) if is_pdf else photo(rng)
                    files[key] = content
                    size_b, sha = len(content), hashlib.sha256(content).hexdigest()
                else:
                    size_b = int(min(9_500_000, rng.lognormvariate(12.2, 1.0))) if not is_pdf else rng.randint(1800, 90_000)
                    sha = hashlib.sha256(aid.encode()).hexdigest()  # no file exists for the large size
                attachments.append({"attachment_id": aid, "ticket_id": tid, "file_name": name, "content_type": ctype,
                                    "size_bytes": size_b, "sha256": sha, "object_key": key,
                                    "uploaded_at": ts(created + timedelta(seconds=rng.randint(5, 120)))})
        # AI runs: every ticket is classified; about half get a drafted reply from a language model.
        run_id += 1
        version = "keywords-1.1" if created >= datetime(2026, 10, 1, tzinfo=timezone.utc) else "keywords-1.0"
        runs.append({"run_id": run_id, "ticket_id": tid, "task": "classify", "model": version, "prompt_version": None,
                     "tokens_in": 0, "tokens_out": 0, "cost_usd": "0", "latency_ms": rng.randint(0, 3), "status": "ok",
                     "output": json.dumps({"category": team, "priority": priority}),
                     "created_at": ts(created + timedelta(seconds=1))})
        if rng.random() < 0.5:
            run_id += 1
            model = "chat-strong" if rng.random() < 0.15 else "chat-small"
            prompt = "draft-v2" if created >= datetime(2026, 6, 1, tzinfo=timezone.utc) else "draft-v1"
            tin = int(rng.lognormvariate(6.75, 0.3)) + (180 if prompt == "draft-v2" else 0)
            tout = int(rng.lognormvariate(4.9, 0.35))
            r = rng.random()
            status_r = "ok" if r < 0.965 else ("error" if r < 0.985 else "timeout")
            if model == "chat-small":
                latency = int(rng.lognormvariate(7.05, 0.25))
            else:
                latency = int(rng.lognormvariate(8.2, 0.3))
            output = fill(rng.choice(DRAFTS), rng, product, order, c["name"]) if status_r == "ok" else None
            if status_r == "timeout":
                latency, tout = 30000, 0
            if status_r == "error":
                tout = 0
            pin, pout = PRICES[model]
            cost = (tin * pin + tout * pout) / 1_000_000
            runs.append({"run_id": run_id, "ticket_id": tid, "task": "draft_reply", "model": model,
                         "prompt_version": prompt, "tokens_in": tin, "tokens_out": tout, "cost_usd": f"{cost:.8f}",
                         "latency_ms": latency, "status": status_r, "output": output,
                         "created_at": ts(created + timedelta(seconds=2 + latency // 1000))})
    # The planted problem: three messages of test tickets that were deleted by hand in the old tool.
    missing = [f"T-{cfg['first_ticket'] - k}" for k in (7, 4, 2)]
    for k, tid in enumerate(missing):
        message_id += 1
        messages.append({"message_id": message_id, "ticket_id": tid, "author": "agent",
                         "body": "Test message, please ignore.",
                         "created_at": ts(start + timedelta(hours=3 + k))})

    docs = documents()
    write_csv(out / "customers.csv", cust)
    write_csv(out / "tickets.csv", tickets)
    write_csv(out / "messages.csv", messages)
    write_csv(out / "attachments.csv", attachments)
    write_csv(out / "documents.csv", docs)
    write_csv(out / "ai_runs.csv", runs)
    if files:
        for key, content in files.items():
            p = out / "files" / key
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(content)
    counts = {"customers": len(cust), "tickets": len(tickets), "messages": len(messages),
              "attachments": len(attachments), "documents": len(docs), "ai_runs": len(runs), "files": len(files)}
    (out / "counts.json").write_text(json.dumps({"size": size, "version": VERSION, **counts}, indent=2) + "\n")
    names = sorted(p.relative_to(out).as_posix() for p in out.rglob("*")
                   if p.is_file() and p.name != "SHA256SUMS" and not p.name.startswith("ticket_embeddings"))
    sums = "".join(f"{hashlib.sha256((out / n).read_bytes()).hexdigest()}  {n}\n" for n in names)
    (out / "SHA256SUMS").write_text(sums)
    print(f"{size}: " + ", ".join(f"{k} {v:,}" for k, v in counts.items()) + f" -> {out}")


def documents() -> list[dict]:
    rows = []
    for p in sorted((SOURCE / "documents").glob("*.md")):
        text = p.read_text(encoding="utf-8")
        _, front, body = text.split("---\n", 2)
        meta = {}
        for line in front.splitlines():
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"')
        body = body.strip() + "\n"
        rows.append({"doc_id": meta["doc_id"], "version": int(meta.get("version", 1)), "title": meta["title"],
                     "doc_type": meta.get("doc_type"), "language": meta.get("language", "en"),
                     "access": meta.get("access", "public"), "effective_from": meta.get("effective_from") or None,
                     "effective_to": meta.get("effective_to") or None, "body": body,
                     "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest()})
    return rows


def write_csv(path: Path, rows: list[dict]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--size", choices=["small", "large", "both"], default="both")
    ap.add_argument("--out", type=Path, default=HERE / "out")
    args = ap.parse_args()
    for size in (["small", "large"] if args.size == "both" else [args.size]):
        generate(size, args.out / size)


if __name__ == "__main__":
    main()
