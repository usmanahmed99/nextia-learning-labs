"""The business service: search and ticket lookup, always inside one organization."""

import pytest

from support_mcp.knowledge import Knowledge, NotFound


def test_counts(knowledge):
    assert knowledge.counts() == {
        "larkfield": {"documents": 9, "tickets": 13},
        "bramble": {"documents": 5, "tickets": 8},
    }


def test_search_ranks_the_best_document_first(knowledge):
    hits = knowledge.search("larkfield", "return a damaged item")
    assert hits[0].doc_id == "damaged-or-wrong-items"
    assert len(hits) == 3
    assert hits[0].score >= hits[1].score >= hits[2].score


def test_search_stays_in_one_organization(knowledge):
    bramble = {h.doc_id for h in knowledge.search("bramble", "returns refund delivery damaged", limit=5)}
    assert "warranty-policy" not in bramble  # a Larkfield document
    assert bramble <= {d["doc_id"] for d in knowledge.documents("bramble")}


def test_staff_documents_only_for_staff(knowledge):
    public = [d["doc_id"] for d in knowledge.documents("larkfield")]
    staff = [d["doc_id"] for d in knowledge.documents("larkfield", staff=True)]
    assert "refund-approval-procedure" not in public
    assert "refund-approval-procedure" in staff
    assert not any(
        h.doc_id == "refund-approval-procedure" for h in knowledge.search("larkfield", "manual refund approval limits")
    )
    with pytest.raises(NotFound):
        knowledge.document("larkfield", "refund-approval-procedure", staff=False)


def test_a_ticket_of_the_other_organization_is_not_found(knowledge):
    assert knowledge.ticket("bramble", "T-40003")["subject"] == "Book arrived damaged"
    with pytest.raises(NotFound):
        knowledge.ticket("larkfield", "T-40003")


def test_an_unknown_organization_is_not_found(knowledge):
    with pytest.raises(NotFound):
        knowledge.search("nowhere", "returns")
    with pytest.raises(NotFound):
        knowledge.ticket("nowhere", "T-30002")


def test_search_without_usable_words_returns_nothing(knowledge):
    assert knowledge.search("larkfield", "a b ?") == []


def test_the_data_loads_the_same_way_twice():
    a, b = Knowledge(), Knowledge()
    assert a.search("larkfield", "gift card balance") == b.search("larkfield", "gift card balance")
