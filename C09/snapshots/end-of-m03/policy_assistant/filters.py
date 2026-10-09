"""Metadata filters: which chunks may be retrieved for this question at all.

Applied BEFORE the top k is chosen (and so before anything reaches the model):
- as_of: only versions in force on that date (effective_from <= as_of, and as_of <= effective_to
  when the document has an end date). Which date? The policy governance document says: for returns,
  the delivery date; otherwise the day of the question.
- audience: "staff" (the help-desk assistant) may see every chunk; "public" (a customer-facing
  assistant) only chunks labelled public. A chunk without an access label counts as staff: when the
  label is missing, the safe choice is to hide it.
"""

from dataclasses import dataclass

AUDIENCES = ("staff", "public")


@dataclass(frozen=True)
class Filters:
    as_of: str | None = None        # YYYY-MM-DD, or None for no date filter
    audience: str = "staff"

    def __post_init__(self):
        if self.audience not in AUDIENCES:
            raise ValueError(f"audience must be one of {AUDIENCES}, not {self.audience!r}")

    def allows(self, chunk) -> bool:
        if self.audience == "public" and (getattr(chunk, "access", "") or "staff") != "public":
            return False
        if self.as_of:
            if chunk.effective_from and chunk.effective_from > self.as_of:
                return False
            if chunk.effective_to and self.as_of > chunk.effective_to:
                return False
        return True
