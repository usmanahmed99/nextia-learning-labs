from assistant.data import Ticket
from assistant.evaluate import Row, misses, score


def test_score_counts_teams_needs_human_and_missing_answers():
    rows = [
        Row(Ticket("T-1", "C-1", "a", team="delivery", needs_human=False), {"team": "delivery", "needs_human": False}),
        Row(Ticket("T-2", "C-2", "b", team="payment", needs_human=True), {"team": "returns", "needs_human": True}),
        Row(Ticket("T-3", "C-3", "", team="", needs_human=True), None, "malformed_json"),
    ]
    s = score(rows)
    assert (s["team_correct"], s["team_scored"], s["needs_human_agree"], s["no_answer"]) == (1, 2, 2, 1)
    assert s["needs_human_true_caught"] == "1/2"
    assert len(misses(rows)) == 2
