"""Two workers (recorded): the resolver decides from the investigator's report only."""

from resolver.data import load_task
from resolver.evaluate import run_and_score
from resolver.providers import MockProvider


def test_the_resolver_sees_the_report_not_the_tool_results():
    _, state = run_and_score(load_task("T-90103"), "workers", "chat-small", MockProvider().complete)
    report = next(e for e in state.events if e.kind == "note" and e.name == "report").detail["report"]
    assert report["orders"] == ["LK-640436"]
    # A real hand-off failure: the investigator wrote "the attached photo was not accessible" under
    # "missing"; the resolver, which also sees "Attachments: IMG_3381.jpg" in the ticket, trusts the report
    # and asks the customer for a photo that is already attached (the single agent proposed the reshipment and label).
    assert any("photo" in m for m in report["missing"])
    assert state.proposal.outcome == "ask_customer"
