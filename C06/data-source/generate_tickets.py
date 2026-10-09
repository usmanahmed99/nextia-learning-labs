"""Write Larkfield ticket texts for C06 with a hosted model (authors only).

Step 1 (`write`): Claude Haiku 5.5 writes tickets from explicit specs (team, scenario,
product, twist, length). Raw replies go to raw/written-*.jsonl, so nothing is lost if a
run stops. Step 2 (`check`): Claude Sonnet 5.5 reads each ticket and the routing policy,
without the spec, and names the team. Raw replies go to raw/checked-*.jsonl.
`build_dataset.py` turns the raw files into the published splits, offline.

Run from this folder, with the keys loaded in your own shell only:
    set -a; . ~/.config/nextia/llm.env; set +a
    python generate_tickets.py write
    python generate_tickets.py check
"""
import json
import random
import re
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "c07" / "m02"))  # authors' repository
sys.path.insert(0, str(Path(__file__).resolve().parent))  # labs: llm.py is copied next to this file
from llm import call  # noqa: E402

HERE = Path(__file__).parent
RAW = HERE / "raw"
SEED = 6006
N_TICKETS = 5600
BATCH = 20

POLICY = (HERE / "routing_policy.md").read_text(encoding="utf-8")

TEAM_SHARE = {"delivery": 0.30, "returns": 0.22, "payment": 0.18, "warranty": 0.15, "account": 0.15}

SCENARIOS = {
    "delivery": [
        "the parcel has not arrived and the expected date has passed",
        "tracking has not updated for several days",
        "the courier left the parcel in the wrong place or with a neighbour",
        "the customer wants to change the delivery address or slot before dispatch",
        "the item arrived damaged in transit (box crushed, broken on arrival)",
        "only part of the order arrived; a box is missing",
        "the courier says delivered but nothing was received",
        "a large item (furniture, shed) needs a two-person delivery booking",
    ],
    "returns": [
        "the customer changed their mind and wants to send the item back",
        "the customer needs a return label or return instructions",
        "the customer wants to exchange for another size or colour",
        "the wrong item was sent and the customer wants to send it back",
        "the customer sent a return and asks if it was received",
        "the customer asks whether a sale or opened item can be returned",
        "the customer wants to book a collection for a bulky return",
    ],
    "payment": [
        "the customer was charged twice for one order",
        "the card was declined at checkout although it works elsewhere",
        "the customer needs an invoice or a VAT receipt",
        "a discount or promo code did not apply to the total",
        "a refund was confirmed by email but has not reached the card",
        "the customer asks about paying in instalments or by bank transfer",
        "the amount charged differs from the price shown at checkout",
    ],
    "warranty": [
        "the product stopped working after some weeks or months of normal use",
        "a part broke during normal use and the customer wants a repair",
        "the customer asks what the guarantee covers and for how long",
        "the product has a fault that appeared later, not on arrival (leaks, rust, motor noise)",
        "the customer wants a replacement under guarantee",
        "the customer reports a possible safety problem with a product they have used",
    ],
    "account": [
        "the customer cannot log in or did not get the password reset email",
        "the customer wants to change the email address on the account",
        "the customer wants to delete the account or their personal data",
        "the customer wants to stop marketing emails",
        "loyalty points are missing from the account",
        "the customer wants to update saved addresses or saved cards",
        "the customer was locked out after too many attempts",
    ],
}

PRODUCTS = [
    "petrol lawn mower", "cordless hedge trimmer", "garden hose reel", "rattan patio set", "wooden garden bench",
    "raised vegetable bed", "electric kettle", "cast iron frying pan", "set of terracotta pots", "solar path lights",
    "pressure washer", "folding parasol", "compost bin", "bird feeder", "kitchen bin", "bathroom cabinet",
    "LED desk lamp", "wool rug", "bed linen set", "garden shed", "greenhouse", "barbecue grill",
    "watering can", "pruning shears", "robot vacuum", "curtain pole", "cushion covers", "trampoline",
    "paddling pool", "leaf blower", "log store", "fire pit", "hammock", "tool chest", "step ladder",
]

# (twist, share, instruction for the writer)
TWISTS = [
    ("plain", 0.33, "A clear ticket about its own topic."),
    ("distractor", 0.20, "Also mention, in passing, words that belong to another team's topic "
                          "(for example a smooth delivery, a past refund, a login), but the request is clearly the given scenario."),
    ("second_sentence", 0.14, "Start with background or a thing that is already solved; the real request comes only in the last sentence."),
    ("negation", 0.08, "Say explicitly what the problem is NOT (for example 'not a delivery problem', 'I don't want a refund'), then the real request."),
    ("short", 0.10, "Very short: 3 to 9 words, like a chat message or a subject line."),
    ("typos", 0.08, "Informal, with typos, missing punctuation and lower case, as typed on a phone."),
    ("long", 0.07, "Long and rambling: 90 to 150 words, with a story before the request."),
]

TONES = ["polite", "neutral", "annoyed", "anxious", "very brief", "friendly", "formal"]

# Wave 2 (added after a pilot: bag-of-words already scored 96-97% on wave 1, so the task
# needed tickets on the policy's real boundaries, where the same words lead to different teams).
N_HARD = 2000
BOUNDARIES = [
    # (share, {team: scenario}, how)
    (0.30, {"delivery": "the item was already damaged or faulty when it was unpacked on the day it arrived",
            "warranty": "the item worked well at first and the same kind of damage or fault appeared after some weeks or months of use"},
     "Describe the damage in detail first. Mention WHEN it happened only once, briefly, in the middle or at the end, "
     "not in the first sentence. Use words like broken, cracked, faulty, replace in both cases."),
    (0.25, {"returns": "the customer sent an item back and asks where the refund is; the shop has not confirmed that it received the item",
            "payment": "the shop confirmed the refund by email some days ago, but the money is still not on the card"},
     "Mention the return, the refund and the card in both cases. The deciding detail (whether the shop confirmed "
     "receipt or the refund) appears only once, briefly, not in the first sentence."),
    (0.15, {"account": "the customer wants to remove or update a card saved in their account settings",
            "payment": "the customer's card was charged an unexpected or wrong amount"},
     "Mention the card, the account and a recent order in both cases; the deciding detail appears only once."),
    (0.30, {t: s for t, s in [("delivery", "the parcel is late or lost"), ("returns", "the customer wants to send an item back"),
                              ("payment", "the customer was charged twice"), ("warranty", "a product broke after months of use"),
                              ("account", "the customer cannot sign in")]},
     "Write two topics: first, 2-3 sentences about a DIFFERENT, already solved problem from another area of the shop "
     "(pick one: delivery, returns, payment, guarantee, account), then one short sentence with the real, current request below."),
]


def hard_specs() -> list[dict]:
    rng = random.Random(SEED + 1)
    out = []
    for i in range(N_HARD):
        share, scen, how = rng.choices(BOUNDARIES, weights=[b[0] for b in BOUNDARIES])[0]
        team = rng.choice(sorted(scen))
        out.append({
            "spec_id": f"H{i:05d}", "team": team, "scenario": scen[team], "product": rng.choice(PRODUCTS),
            "twist": "two_topics" if len(scen) == 5 else "boundary", "how": how,
            "tone": rng.choice(TONES), "order_ref": rng.random() < 0.35,
        })
    return out


def specs() -> list[dict]:
    rng = random.Random(SEED)
    teams = rng.choices(list(TEAM_SHARE), weights=list(TEAM_SHARE.values()), k=N_TICKETS)
    twists = rng.choices([t[0] for t in TWISTS], weights=[t[1] for t in TWISTS], k=N_TICKETS)
    out = []
    for i, (team, twist) in enumerate(zip(teams, twists)):
        out.append({
            "spec_id": f"S{i:05d}",
            "team": team,
            "scenario": rng.choice(SCENARIOS[team]),
            "product": rng.choice(PRODUCTS),
            "twist": twist,
            "tone": rng.choice(TONES),
            "order_ref": rng.random() < 0.35,
        })
    return out + hard_specs()


def write_prompt(batch: list[dict]) -> str:
    rules = {t[0]: t[2] for t in TWISTS}
    lines = []
    for s in batch:
        lines.append(json.dumps({
            "spec_id": s["spec_id"], "topic": s["scenario"], "product": s["product"],
            "how": s.get("how") or rules[s["twist"]], "tone": s["tone"],
            "include_order_number": s["order_ref"],
        }))
    return (
        "You write realistic customer messages for the help desk of Larkfield, a fictional online shop for home and "
        "garden products in Canada. Write one first message from a customer for each spec below.\n\n"
        "Rules:\n- English only. Vary the wording, length and opening; do not start every message the same way.\n"
        "- Never name the help-desk team or the category. Do not use the words 'team', 'category' or 'department'.\n"
        "- No real brand names, no real people, no real addresses or phone numbers.\n"
        "- If include_order_number is true, mention an order number like LK-482913 (invent the digits).\n"
        "- Sign with a first name only sometimes, never with an email address.\n\n"
        "Specs (one JSON object per line):\n" + "\n".join(lines) + "\n\n"
        "Reply with one JSON object per line and nothing else: {\"spec_id\": \"...\", \"text\": \"...\"}"
    )


def check_prompt(batch: list[dict]) -> str:
    lines = [json.dumps({"id": r["spec_id"], "text": r["text"]}) for r in batch]
    return (
        "You route customer messages for Larkfield's help desk. Read the routing policy, then choose exactly one team "
        "for each message. If the message is too unclear to route, answer \"unclear\".\n\n"
        f"{POLICY}\n\nMessages (one JSON object per line):\n" + "\n".join(lines) + "\n\n"
        "Reply with one JSON object per line and nothing else: {\"id\": \"...\", \"team\": \"delivery|returns|payment|warranty|account|unclear\"}"
    )


def parse_lines(text: str) -> list[dict]:
    rows = []
    for line in text.splitlines():
        line = line.strip().strip(",")
        if not line.startswith("{"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            m = re.search(r"\{.*\}", line)
            if m:
                try:
                    rows.append(json.loads(m.group(0)))
                except json.JSONDecodeError:
                    pass
    return rows


def done_ids(pattern: str, key: str) -> set[str]:
    ids = set()
    for f in RAW.glob(pattern):
        for line in f.read_text(encoding="utf-8").splitlines():
            rec = json.loads(line)
            ids.update(r[key] for r in rec["rows"] if key in r)
    return ids


lock = threading.Lock()


def run(kind: str) -> None:
    RAW.mkdir(exist_ok=True)
    if kind == "write":
        todo_all = specs()
        done = done_ids("written-*.jsonl", "spec_id")
        todo = [s for s in todo_all if s["spec_id"] not in done]
        model, make, maxtok = "claude-haiku-5-5", write_prompt, 6000
    else:
        written = {}
        for f in sorted(RAW.glob("written-*.jsonl")):
            for line in f.read_text(encoding="utf-8").splitlines():
                for r in json.loads(line)["rows"]:
                    if "spec_id" in r and "text" in r:
                        written[r["spec_id"]] = r
        done = done_ids("checked-*.jsonl", "id")
        todo = [r for k, r in sorted(written.items()) if k not in done]
        model, make, maxtok = "claude-sonnet-5-5", check_prompt, 3000
    batches = [todo[i:i + BATCH] for i in range(0, len(todo), BATCH)]
    print(f"{kind}: {len(todo)} items in {len(batches)} calls", flush=True)
    out_file = RAW / f"{'written' if kind == 'write' else 'checked'}-{model}.jsonl"
    totals = {"in": 0, "out": 0}

    def one(batch):
        r = call("anthropic", model, make(batch), max_tokens=maxtok, temperature=None)
        rows = parse_lines(r["text"])
        with lock:
            with out_file.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps({"model": model, "input_tokens": r["input_tokens"],
                                     "output_tokens": r["output_tokens"], "stop_reason": r["stop_reason"],
                                     "rows": rows}) + "\n")
            totals["in"] += r["input_tokens"]
            totals["out"] += r["output_tokens"]
        return len(rows)

    with ThreadPoolExecutor(6) as pool:
        got = sum(pool.map(one, batches))
    print(f"{kind}: got {got} rows; tokens in {totals['in']:,}, out {totals['out']:,}", flush=True)


if __name__ == "__main__":
    run(sys.argv[1])
