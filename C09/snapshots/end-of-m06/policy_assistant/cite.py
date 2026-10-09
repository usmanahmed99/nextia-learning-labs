"""Check the citations of an answer in code. What code can check, and what it cannot.

For every claim:
1. exists:      every cited ID is a chunk in the index. (Fails: a made-up ID.)
2. in_context:  every cited ID was in the passages given to the model. (Fails: an ID of a real chunk
                that the model did not see, for example copied from an earlier answer.)
3. cited:       the claim cites at least one ID. (Fails: a claim without evidence.)
   allowed:     for a public audience, every cited passage is public. (Fails: a staff-only passage
                cited to a customer.)
4. numbers:     every number and code in the claim (30, 12.95, PK-2200-07) appears in a cited
                passage (with its header: version, dates) or in the question and its date.
                (Fails: "45 days" cited to a passage that says 30.)
5. words:       at least half of the claim's content words appear in the cited passages (a final
                "s" is ignored: "reports" = "report").
                (Fails: a claim about something the passages do not mention.)
Checks 4 and 5 are only clues: a claim can share every word with a passage and still say the
opposite ("can" / "cannot"), and a correct French claim about an English passage shares few words
(reported as "other language", not as a failure). A person, or a stronger judge, decides those.
"""

import re
from dataclasses import dataclass, field

from .context import format_passage

STOP = set("""a an and are as at be by can cannot do does for from has have if in into is it its may must no not of on
or our that the their them then there these they this to under up was we were what when where which who will with
within without you your le la les un une des de du et est en pour pas dans par sur au aux ce qui que se sa son ses
vous votre vos il elle ne ou si plus""".split())
NUMBER = re.compile(r"\b[A-Z]{2,4}(?:-[A-Z0-9]+)+\b|\d+(?:[.,]\d+)?")


def numbers(text: str) -> set[str]:
    """Numbers and codes: '1,000' and '2,200' become 1000 and 2200; the French '9,95' becomes 9.95."""
    text = re.sub(r"(\d),(\d{3})\b", r"\1\2", text)
    found = {n.replace(",", ".") for n in NUMBER.findall(text)}
    return {(n.lstrip("0") or "0") if n.isdigit() else n for n in found}   # "09" (a date) = "9"


def content_words(text: str) -> set[str]:
    words = {w for w in re.findall(r"[a-zà-ÿ]+", text.lower()) if w not in STOP and len(w) > 2}
    return {w[:-1] if len(w) > 3 and w.endswith("s") else w for w in words}


@dataclass
class ClaimCheck:
    text: str
    chunk_ids: tuple
    problems: list = field(default_factory=list)   # missing_id, not_in_context, not_allowed, no_citation, number_not_found, unsupported
    note: str = ""

    @property
    def ok(self) -> bool:
        return not self.problems


def check_claim(claim, store, context_ids: list[str], language: str = "en", question: str = "",
                audience: str = "staff") -> ClaimCheck:
    """`question`: the question and its date; numbers taken from them are not unsupported."""
    result = ClaimCheck(claim.text, tuple(claim.chunk_ids))
    if not claim.chunk_ids:
        result.problems.append("no_citation")
        return result
    passages = []
    for cid in claim.chunk_ids:
        chunk = store.chunk(cid)
        if chunk is None:
            result.problems.append(f"missing_id:{cid}")
            continue
        if cid not in context_ids:
            result.problems.append(f"not_in_context:{cid}")
        if audience == "public" and chunk.access != "public":
            result.problems.append(f"not_allowed:{cid}")
        passages.append(chunk)
    if not passages:
        return result
    source = " ".join(format_passage(p) for p in passages)
    missing = sorted(numbers(claim.text) - numbers(source) - numbers(question))
    if missing:
        result.problems.append("number_not_found:" + ",".join(missing))
    words = content_words(claim.text)
    if any(p.language != language for p in passages):
        result.note = "other language: the word check was skipped"
    elif words:
        share = len(words & content_words(source)) / len(words)
        if share < 0.5:
            result.problems.append(f"unsupported:{share:.2f}")
    return result


def check_answer(answer, store, context_ids: list[str], language: str = "en", question: str = "",
                 audience: str = "staff") -> list[ClaimCheck]:
    return [check_claim(c, store, context_ids, language, question, audience) for c in answer.claims]
