# Recorded session: fix issue 12 in delivery-slots

| | |
|---|---|
| Case study | Fix a bug in an unfamiliar codebase |
| Assistant | Aider 0.86.2 (open source, Apache-2.0), in a terminal |
| Model | `chat-strong`, the larger model (gpt-6.1-sol-2026-09-29), on Azure |
| Settings | Aider edit format `diff`; default temperature; repository map on; edits applied to the files, no commits; shell commands not allowed; the test command `python -m pytest -q` only in turn 3; every question from Aider answered yes |
| Project | `delivery-slots`, the starter, with its Git history |
| Checks run after each turn | `python -m pytest`, ruff, and the district table (12 postcodes; the case study's step "Compare the fixes") |
| Model calls, tokens, cost | 6 calls; 30,327 tokens in, 2,619 out; US$0.0868 at the deployment's price per token (you pay nothing to read this transcript) |

A different run, another model or another assistant can give a different answer. The folder path is shown as `~/projects/delivery-slots`. Aider prints the lines "Analytics have been permanently disabled" and "Detected dumb terminal" because of the recording settings.

Before the session: tests: 35 passed in 0.04s · ruff check: pass · ruff format --check: pass · district table: 6 failed, 6 passed in 0.02s

## Turn 1 (ask mode: the assistant may not change files)

Files added to the chat by Amira: none (the assistant sees Aider's map of the repository).

### Prompt

````text
I have never seen this project. Customer support filed this issue:

# Issue 12: no evening slots for LS12, although the delivery page promises them

Status: open
Reported by: Grace, customer support

A customer wrote to us on Monday morning. Her email, as she sent it:

> Hello,
>
> Your delivery page says that West Leeds gets evening deliveries on Tuesdays and
> Thursdays, 6 to 8 pm. I live in Armley, LS12 2AB, and I work during the day.
> This morning (Monday, about 10 o'clock) I ordered a garden bench, order L-40213.
> For Tuesday the checkout offered me only 8-10, 10-12 and 12-2. No evening slot
> at all. My sister in Burley, LS4, has an evening delivery booked for tomorrow,
> so the evening slots do exist.
>
> Can you deliver my bench on Tuesday evening, please?
>
> Ruth

What I checked: on the checkout page, `LS12 2AB` and Tuesday 13 October show the
same three daytime slots. Monday 10:00 is long before the 20:00 cut-off. The
order L-40213 is paid, and it has no delivery slot yet. I told Ruth that we will
come back to her today.

Hana and Luis are at the trade fair until Friday. Amira (help-desk tools) said
that she can look at it.

Before anyone changes code, I need a map of the project. Please answer from the
repository map:

1. In two or three lines: what does this project do?
2. Each file in delivery_slots/, with one line on what it does.
3. The functions that this command goes through, in order, from cli.py to the
   lines it prints:

       python -m delivery_slots --now 2026-10-12T10:00 slots "LS12 2AB" --day 2026-10-13

Do not change any file, and do not guess the cause yet.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with ask edit format
Git repo: .git with 27 files
Repo-map: using 4096 tokens, auto refresh


delivery_slots/cli.py
## 1. What the project does

This is a CSV-backed delivery-slot tool with a command-line interface. It lists slots for a postcode
and date, books an order into a slot, and prints a driver’s manifest for a date and zone.
Its modules handle postcode lookup, slot capacity and booking cut-offs, and storing bookings.

## 2. Files in `delivery_slots/`

| File | Role |
|---|---|
| `__init__.py` | Package initializer; its contents have not been supplied. |
| `__main__.py` | Entry point for `python -m delivery_slots`; its contents have not been supplied. |
| `cli.py` | Parses command-line arguments, loads CSV data, dispatches commands, and prints results 
or booking/postcode errors. |
| `bookings.py` | Defines `Booking` and provides functions to load bookings and save a booking. |
| `checkout.py` | Provides `book(...)` and the `BookingError` exception for refused bookings. |
| `manifest.py` | Selects bookings for a day and zone and formats the driver’s manifest. |
| `postcodes.py` | Provides postcode normalization through `normalise(...)`. |
| `slots.py` | Defines plan rows and slots; loads the slot plan, calculates cut-offs, and supplies 
slots with availability information. |
| `zones.py` | Loads postcode-to-zone mappings and resolves a postcode to a zone, with 
`UnknownPostcode` for failed lookups. |

## 3. Command flow

For:

```sh
python -m delivery_slots --now 2026-10-12T10:00 slots "LS12 2AB" --day 2026-10-13
```

The following sequence is visible in `cli.py`. The wiring from `__main__.py` into `cli.main()` is 
not shown in the supplied contents.

1. **`cli.main(argv)`**
   - Calls **`build_parser()`**, then the parser’s **`parse_args(argv)`**.
   - Parses `--now` with `datetime.fromisoformat` and `--day` with `date.fromisoformat`.
   - Uses the supplied Monday 10:00 time rather than `datetime.now()`.
   - Selects `cmd_slots` as `args.run`.
   - Uses the default data folder, `data`.

2. **`cli.load(Path("data"))`**
   Calls these loaders in order:
   - **`zones.load_zones(data/zones.csv)`**
   - **`slots.load_plan(data/slot-plan.csv)`**
   - **`bookings.load_bookings(data/bookings.csv)`**

   Returns a `Data` object containing the loaded data and bookings-file path.

3. **`cli.cmd_slots(args, data, now)`**
   - Calls **`zones.zone_for("LS12 2AB", data.zones)`**.
   - Calls **`slots.slots_for(zone, args.day, data.plan, data.bookings, now)`**.
   - Calls **`postcodes.normalise("LS12 2AB")`** and prints:
     ```text
     LS12 2AB is in zone <resolved zone>.
     ```

4. **Output branch**
   - If no slots are returned, calls **`cli.day_text(args.day)`** and prints:
     ```text
     Zone <resolved zone> has no delivery slots on Tuesday 13 October 2026.
     ```
     Then returns `0`.
   - Otherwise, calls **`slots.cutoff_for(args.day)`** and **`cli.day_text(args.day)`**, then prints
the heading:
     ```text
     Slots on Tuesday 13 October 2026 (orders close <cut-off weekday> at <cut-off time>):
     ```

5. **For each returned slot: `cli.describe(slot)`**
   Checks, in order:
   - `slot.closed` → `closed`
   - `slot.places_left == 0` → `full`
   - `slot.places_left == 1` → `1 place left`
   - Otherwise → `<count> places left`

   The loop prints:
   ```text
     <start>-<end>  <description>
   ```
   `cmd_slots` then returns `0`.

If `zone_for` raises `UnknownPostcode`, `main` prints `Error: <message>` to standard error and 
returns `1`.

The summaries do not reveal the internal call order within `zone_for`, `slots_for`, or the CSV 
loaders, so this trace stops at those function boundaries. No files have been changed, and no cause 
is inferred.

Tokens: 3.1k sent, 1.0k received. Cost: $0.02 message, $0.02 session.

delivery_slots/bookings.py

delivery_slots/checkout.py

delivery_slots/manifest.py

delivery_slots/postcodes.py

delivery_slots/slots.py

delivery_slots/zones.py
Those six files, plus the supplied `cli.py`, are enough to trace the internal calls—the previous 
answer incorrectly said their contents were unavailable.

Please also add:

- `delivery_slots/__main__.py` — to confirm how `python -m delivery_slots` calls the CLI.
- `delivery_slots/__init__.py` — to complete the package-file map.
- `data/zones.csv`, `data/slot-plan.csv`, and `data/bookings.csv` — if you want the exact printed 
output, rather than just the function flow.

No further files are needed for the requested map and trace.

Tokens: 5.7k sent, 125 received. Cost: $0.01 message, $0.03 session.

data/bookings.csv

data/slot-plan.csv

data/zones.csv

delivery_slots/__init__.py

delivery_slots/__main__.py
No others are needed. All files required for the project map, complete function trace, and exact 
output are now available.

My earlier requests were unnecessary: you had already supplied these files in full. I’ll use those 
contents, without changing files or investigating the cause yet.

Tokens: 6.5k sent, 57 received. Cost: $0.01 message, $0.04 session.
````

**After turn 1:** 3 model calls, 15,302 tokens in, 1,224 out (US$0.0428). Changes since the start: 0 files, +0 −0 lines (no file).

Checks: tests: 35 passed in 0.03s · ruff check: pass · ruff format --check: pass · district table: 6 failed, 6 passed in 0.02s

## Turn 2 (ask mode: the assistant may not change files)

Files added to the chat by Amira: `delivery_slots/zones.py`, `delivery_slots/postcodes.py`, `data/zones.csv`.

### Prompt

````text
Targeted questions. For LS12 2AB on Tuesday, the customer was offered 08:00-10:00,
10:00-12:00 and 12:00-14:00. In data/slot-plan.csv, those are the city zone's
slots, not the west zone's.

1. Where in the code is the zone of a postcode decided? Name the function and
   the lines.
2. Walk through that function for "LS12 2AB", with the rows of data/zones.csv
   in their order. Which zone does it return, and at which step?
3. Which other districts in data/zones.csv get a wrong zone in the same way?

Answer from the code only. Do not change any file.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with ask edit format
Git repo: .git with 27 files
Repo-map: using 4096 tokens, auto refresh
Added data/zones.csv to the chat.
Added delivery_slots/postcodes.py to the chat.
Added delivery_slots/zones.py to the chat.
Restored previous conversation history.


data/slot-plan.csv
## 1. Where the zone is decided

In **`delivery_slots/zones.py`, `zone_for()`**, defined on line **27**. The decision is made on 
lines **33–36**:

```python
code = normalise(postcode).replace(" ", "")
for district, zone in zones.items():
    if code.startswith(district):
        return zone
```

It returns the zone of the **first district that matches the start of the postcode**, not 
necessarily the complete district.

## 2. Walk-through for `"LS12 2AB"`

`load_zones()` preserves the CSV row order.

1. `normalise("LS12 2AB")` produces `"LS12 2AB"`.
2. Removing spaces produces `"LS122AB"`.
3. The first CSV row is **`LS1,city`**.
4. `"LS122AB".startswith("LS1")` is **`True`**.
5. Line **36** immediately returns **`"city"`**.

No later rows are checked—including **`LS12,west`**. This explains why this lookup selects the city 
zone.

## 3. Other districts assigned the wrong zone

| District | Intended zone in CSV | First matching district | Returned zone |
|---|---|---|---|
| LS13 | west | LS1 | city |
| LS16 | north | LS1 | city |
| LS17 | north | LS1 | city |

**LS10 and LS11** also match `LS1` before reaching their own rows, but their intended zone is 
already `city`, so their returned zone is not wrong.

No files have been changed.

Tokens: 4.0k sent, 536 received. Cost: $0.01 message, $0.01 session.
````

**After turn 2:** 1 model call, 3,989 tokens in, 536 out (US$0.0133). Changes since the start: 0 files, +0 −0 lines (no file).

Checks: tests: 35 passed in 0.02s · ruff check: pass · ruff format --check: pass · district table: 6 failed, 6 passed in 0.02s

## Between turns 2 and 3: Amira's own step (no assistant)

Amira ran the command of the issue (it printed `LS12 2AB is in zone city.`), shrank the input to one postcode, and wrote the failing test `test_two_digit_districts` in `tests/test_zones.py`. She committed it: "Add a failing test for issue 12: LS12 2AB is in zone west".

Checks: tests: 4 failed, 35 passed in 0.04s · ruff check: pass · ruff format --check: pass · district table: 6 failed, 6 passed in 0.03s

## Turn 3 (Aider runs the tests after each edit)

Files added to the chat by Amira: `delivery_slots/zones.py`, `tests/test_zones.py`.

### Prompt

````text
I committed a failing test: test_two_digit_districts in tests/test_zones.py.
It fails four times. For example, zone_for("LS12 2AB", zones) returns "city";
expected "west". `python -m pytest -q` prints "4 failed, 35 passed".

Fix zone_for so that these tests pass.
- Change only delivery_slots/zones.py. Do not change the tests or the data.
- Postcodes typed without a space must still work (issue 3,
  test_postcode_without_a_space).
- Keep the change small. In two lines, say why it fixes the cause.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with diff edit format
Git repo: .git with 27 files
Repo-map: using 4096 tokens, auto refresh
Added delivery_slots/zones.py to the chat.
Added tests/test_zones.py to the chat.
Restored previous conversation history.

Match the complete district by removing the postcode’s final three characters, so LS12 cannot match 
LS1.
Removing spaces first preserves support for compact postcodes such as `ls53qr`.

delivery_slots/zones.py
```python
<<<<<<< SEARCH
    Customers type postcodes with or without the space ("LS5 3QR", "ls53qr"),
    so the district is matched at the start of the postcode.
    """
    code = normalise(postcode).replace(" ", "")
    for district, zone in zones.items():
        if code.startswith(district):
            return zone
=======
    Customers type postcodes with or without the space ("LS5 3QR", "ls53qr"),
    so remove spaces and the final three characters to get the district.
    """
    code = normalise(postcode).replace(" ", "")
    district = code[:-3]
    if district in zones:
        return zones[district]
>>>>>>> REPLACE
```

Tokens: 6.2k sent, 317 received. Cost: $0.02 message, $0.02 session.
Applied edit to delivery_slots/zones.py
.......................................                                                      [100%]
39 passed in 0.03s
````

**After turn 3:** 1 model call, 6,243 tokens in, 317 out (US$0.0157). Changes since Amira's commit: 1 files, +4 −4 lines (delivery_slots/zones.py).

Checks: tests: 39 passed in 0.03s · ruff check: pass · ruff format --check: pass · district table: 12 passed in 0.02s

## Turn 4 (ask mode: the assistant may not change files)

Files added to the chat by Amira: `delivery_slots/zones.py`, `tests/test_zones.py`, `data/zones.csv`.

### Prompt

````text
Review your change to zone_for. Give the inputs for which the new zone_for could
still return a wrong zone, or fail in an unexpected way. For each one, say what
it returns now. Do not change any file.
````

### What the assistant printed

````text
Analytics have been permanently disabled.
Detected dumb terminal, disabling fancy input and pretty output.

Aider v0.86.2
Model: openai/chat-strong with ask edit format
Git repo: .git with 27 files
Repo-map: using 4096 tokens, auto refresh
Added data/zones.csv to the chat.
Added delivery_slots/zones.py to the chat.
Added tests/test_zones.py to the chat.
Restored previous conversation history.

For a complete, correctly formed postcode, the change extracts the district correctly, with or 
without a space. The remaining weakness is that it **assumes the final three characters are a valid 
inward code**, without checking them.

| Input | Result now | Problem |
|---|---|---|
| `"LS12 ABC"` | `"west"` | Accepts an invalid inward code: it must start with a digit. |
| `"LS12 123"` | `"west"` | Accepts an invalid inward code: its last two characters must be letters.
|
| `"LS12 !!!"` | `"west"` | Accepts arbitrary punctuation as the inward code. |
| `"LS12 2A"` | `"city"` | An incomplete inward code makes the extracted district `LS1`, rather than
`LS12`. |
| `"LS16 7Q"` | `"city"` | Likewise, truncation extracts `LS1`, rather than `LS16`. |
| `"LS1 22AB"` | `"west"` | An extra inward-code character makes the extracted district `LS12`, 
rather than the supplied `LS1`. |
| `"LS12"` | Raises `UnknownPostcode` | A district-only input is not supported: removing three 
characters leaves `L`. |

These malformed inputs should not necessarily receive a zone at all; the surprising behaviour is 
that some receive a plausible but incorrect zone instead of being rejected. The four regression 
cases are fixed, but this change does not validate postcode structure.

No files changed.

Tokens: 4.8k sent, 542 received. Cost: $0.02 message, $0.02 session.
````

**After turn 4:** 1 model call, 4,793 tokens in, 542 out (US$0.0150). Changes since Amira's commit: 1 files, +4 −4 lines (delivery_slots/zones.py).

Checks: tests: 39 passed in 0.04s · ruff check: pass · ruff format --check: pass · district table: 12 passed in 0.02s

## The assistant's change

This is `fix-issue-12.patch`. It applies to the starter after Amira's test commit (`git apply fix-issue-12.patch`).

```diff
diff --git a/delivery_slots/zones.py b/delivery_slots/zones.py
index 15852d6..25181f2 100644
--- a/delivery_slots/zones.py
+++ b/delivery_slots/zones.py
@@ -28,10 +28,10 @@ def zone_for(postcode: str, zones: dict[str, str]) -> str:
     """The zone of a postcode, for example "west" for "LS5 3QR".
 
     Customers type postcodes with or without the space ("LS5 3QR", "ls53qr"),
-    so the district is matched at the start of the postcode.
+    so remove spaces and the final three characters to get the district.
     """
     code = normalise(postcode).replace(" ", "")
-    for district, zone in zones.items():
-        if code.startswith(district):
-            return zone
+    district = code[:-3]
+    if district in zones:
+        return zones[district]
     raise UnknownPostcode(f"We do not deliver to {normalise(postcode)}.")
```
