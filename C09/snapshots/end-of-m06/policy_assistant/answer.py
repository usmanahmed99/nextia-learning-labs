"""Ask the model for an answer made of claims, each with the IDs of the passages that support it.

The request uses structured output (a strict JSON schema), as in the LLM applications course, so the
answer can be checked in code (cite.py). The prompt files are in prompts/: answer_v1.md, and from
Module 6 answer_v2.md, which adds one rule against instructions hidden inside documents.
"""

from dataclasses import dataclass

from pydantic import BaseModel, ConfigDict, ValidationError

from .config import load_prompt
from .context import Context

MAX_TOKENS = 2000   # reasoning models count their hidden reasoning in this limit too

SCHEMA = {
    "type": "object",
    "properties": {
        "answerable": {"type": "boolean", "description": "false when the passages do not answer the question"},
        "answer": {"type": "string", "description": "the short answer, in the language of the question"},
        "claims": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "one statement of fact from the answer"},
                    "chunk_ids": {"type": "array", "items": {"type": "string"},
                                  "description": "IDs of the passages that support the statement"},
                },
                "required": ["text", "chunk_ids"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["answerable", "answer", "claims"],
    "additionalProperties": False,
}


def response_format() -> dict:
    return {"type": "json_schema", "json_schema": {"name": "cited_answer", "strict": True, "schema": SCHEMA}}


def build_request(question: str, as_of: str, context: Context, model: str, prompt: str = "answer_v1") -> dict:
    system, user = load_prompt(prompt)
    return {
        "model": model,
        "messages": [{"role": "system", "content": system},
                     {"role": "user", "content": user.format(as_of=as_of, question=question, passages=context.text())}],
        "response_format": response_format(),
        "max_completion_tokens": MAX_TOKENS,
    }


def build_closed_book_request(question: str, model: str) -> dict:
    """The model alone: no passages, plain text (to show what it says without Larkfield's documents)."""
    system, user = load_prompt("closed_book")
    return {"model": model, "messages": [{"role": "system", "content": system},
                                         {"role": "user", "content": user.format(question=question)}],
            "max_completion_tokens": MAX_TOKENS}


@dataclass(frozen=True)
class Claim:
    text: str
    chunk_ids: tuple


@dataclass(frozen=True)
class Answer:
    answerable: bool
    answer: str
    claims: tuple

    def text(self) -> str:
        return " ".join([self.answer, *(c.text for c in self.claims)])

    def cited(self) -> list[str]:
        return list(dict.fromkeys(i for c in self.claims for i in c.chunk_ids))


class ClaimModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str
    chunk_ids: list[str]


class AnswerModel(BaseModel):
    """The same shape as SCHEMA, used to check the model's JSON (the second gate of the LLM applications course)."""
    model_config = ConfigDict(extra="forbid")
    answerable: bool
    answer: str
    claims: list[ClaimModel]


class AnswerProblem(Exception):
    """The model's output is not a usable answer (cut, refused, not JSON, not the schema)."""


def parse_answer(completion) -> Answer:
    if completion.refusal:
        raise AnswerProblem(f"refused: {completion.refusal}")
    if completion.finish_reason == "length":
        raise AnswerProblem("cut: the answer reached the token limit")
    try:
        data = AnswerModel.model_validate_json(completion.text or "")
    except ValidationError as e:
        raise AnswerProblem(f"not a valid answer: {e.errors()[0]['msg']}") from e
    return Answer(data.answerable, data.answer, tuple(Claim(c.text, tuple(c.chunk_ids)) for c in data.claims))
