"""Module 1's keyword baseline: BM25 over the sections of the Markdown documents. The number to beat."""

import sqlite3

from policy_assistant.documents import load_inventory, sections
from policy_assistant.evaluate import load_questions, retrieval_scores, summarise
from policy_assistant.lexical import KeywordIndex


def test_sections_of_a_document():
    info = next(d for d in load_inventory() if d.doc_id == "returns-policy" and d.version == "3")
    secs = sections(info)
    assert [s.section for s in secs][:2] == ["Who this policy is for", "Return window"]
    assert secs[1].passage_id == "returns-policy@v3#return-window"
    assert secs[1].text.startswith("Returns policy\n## Return window\n")


def test_baseline_hit_at_5():
    all_sections = [s for d in load_inventory() if d.format == "md" for s in sections(d)]
    index = KeywordIndex(sqlite3.connect(":memory:"))
    index.add((s.passage_id, s.text) for s in all_sections)
    by_id = {s.passage_id: s for s in all_sections}
    rows = [retrieval_scores(q, [by_id[h.id] for h in index.search(q.question, 5)], 5) for q in load_questions().values()]
    assert len(all_sections) == 154
    assert summarise(rows)["hit"] == 0.695      # 41 of 59 questions with relevant passages
