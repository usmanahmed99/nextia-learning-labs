from policy_assistant.chunk import fixed, overlapping, structure
from policy_assistant.documents import CORPUS
from policy_assistant.metadata import chunk_id
from policy_assistant.parse import parse

WARRANTY = "documents/warranty-policy.pdf"


def doc():
    return parse(CORPUS / WARRANTY)


def test_fixed_chunks_have_100_words_and_cut_the_table():
    chunks = fixed(doc(), WARRANTY)
    assert [len(c.text.split()) for c in chunks[:-1]] == [100] * (len(chunks) - 1)
    table_rows = [c for c in chunks if "Hand garden tools" in c.text or "Larkfield Pro range |" in c.text]
    assert len({c.chunk_id for c in table_rows}) == 2          # the table is split between two chunks


def test_overlap_repeats_25_words():
    a, b = overlapping(doc(), WARRANTY)[:2]
    assert a.text.split()[-25:] == b.text.split()[:25]


def test_structure_keeps_the_table_whole_with_its_heading_and_title():
    chunks = structure(doc(), WARRANTY)
    table = [c for c in chunks if "Product category | Examples" in c.text]
    assert len(table) == 1
    assert table[0].text.startswith("Larkfield warranty policy\nWarranty periods by product category\n")
    assert "Larkfield Pro range | any product marked Pro | 5 years | covers trade use" in table[0].text
    assert table[0].sections == ("Warranty periods by product category",)


def test_every_chunk_traces_back_to_its_source():
    d = doc()
    for make in (fixed, overlapping, structure):
        for c in make(d, WARRANTY):
            assert d.text[c.start:c.end] in c.text
            assert c.source == WARRANTY and c.pages and c.doc_id == "warranty-policy" and c.version == "5"
            assert c.chunk_id == chunk_id("warranty-policy", "5", c.start, c.end)
