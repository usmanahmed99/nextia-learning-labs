from types import SimpleNamespace

from policy_assistant.context import assemble, estimate_tokens, format_passage, jaccard


def chunk(cid, doc_id, text, version="1"):
    return SimpleNamespace(chunk_id=cid, doc_id=doc_id, version=version, title="T", doc_type="guide",
                           effective_from="2026-01-01", effective_to="", section="S", text=text)


SAFETY = "Never run the pressure washer for more than 2 minutes with the trigger released: the pump overheats."


def test_estimate_tokens():
    assert estimate_tokens("abcd" * 10) == 10


def test_near_duplicates_from_two_documents_are_removed():
    a = chunk("a", "product-care-pw2200", "PW-2200 guide\n" + SAFETY)
    b = chunk("b", "product-care-pw2400", "PW-2400 guide\n" + SAFETY)
    assert jaccard(a.text, b.text) == 1.0                       # the title line is left out
    ctx = assemble([a, b])
    assert ctx.ids == ["a"] and ctx.dropped == [("b", "near-duplicate of a")]


def test_two_versions_of_one_document_are_both_kept():
    v3 = chunk("v3", "returns-policy", "Returns\nYou can return an unused item within 30 days.", "3")
    v4 = chunk("v4", "returns-policy", "Returns\nYou can return an unused item within 30 days.", "4")
    assert assemble([v3, v4]).ids == ["v3", "v4"]


def test_budget():
    chunks = [chunk(str(i), f"d{i}", " ".join(f"w{i}x{j}" for j in range(200))) for i in range(5)]
    cost = estimate_tokens(format_passage(chunks[0]))      # 342 estimated tokens per passage
    ctx = assemble(chunks, budget=2 * cost + 10)
    assert len(ctx.ids) == 2 and ctx.tokens == 2 * cost
    assert [reason for _, reason in ctx.dropped] == ["over budget"] * 3


def test_a_passage_shows_its_id_dates_and_type():
    text = format_passage(chunk("3fa9c2d1b0e4", "d", "Title\nbody"))
    assert text.startswith("[3fa9c2d1b0e4] T | guide, version 1, in force from 2026-01-01, no end date | section: S\n")
