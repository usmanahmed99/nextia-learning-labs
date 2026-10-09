"""The whole question-answering pipeline: search -> context -> model -> parse -> citation check."""

from dataclasses import dataclass, field

from .answer import Answer, AnswerProblem, build_request, parse_answer
from .cite import check_answer
from .context import BUDGET, Context, assemble
from .filters import Filters
from .providers import ProviderError

K = 5


@dataclass
class AskResult:
    question: str
    as_of: str
    context: Context
    request: dict
    answer: Answer | None = None
    problem: str = ""
    checks: list = field(default_factory=list)
    completion: object = None


def ask(question: str, as_of: str, retriever, provider, model: str = "chat-small", method: str = "rerank",
        k: int = K, audience: str = "staff", prompt: str = "answer_v1", budget: int = BUDGET,
        use_date_filter: bool = True, language: str = "en") -> AskResult:
    filters = Filters(as_of=as_of if use_date_filter else None, audience=audience)
    results = retriever.search(question, method=method, k=k, filters=filters)
    context = assemble([r.chunk for r in results], budget)
    request = build_request(question, as_of, context, model, prompt)
    out = AskResult(question, as_of, context, request)
    try:
        out.completion = provider.complete(request)
        out.answer = parse_answer(out.completion)
    except (ProviderError, AnswerProblem) as e:
        out.problem = str(e)
        return out
    out.checks = check_answer(out.answer, retriever.store, context.ids, language, f"{as_of} {question}", audience)
    return out
