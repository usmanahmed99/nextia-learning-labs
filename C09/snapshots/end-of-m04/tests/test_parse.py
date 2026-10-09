"""The same document in three formats gives the same clean text; the PDF's problems are handled."""

import pytest

from policy_assistant.documents import CORPUS
from policy_assistant.parse import dehyphenate, parse, pdf_lines

FORMATS = CORPUS / "formats"
STEMS = ["warranty-policy", "product-care-pw2200", "delivery-policy", "returns-policy.v4"]


@pytest.mark.parametrize("stem", STEMS)
def test_three_formats_same_text_and_metadata(stem):
    md, html, pdf = (parse(FORMATS / f"{stem}.{ext}") for ext in ("md", "html", "pdf"))
    assert md.text == html.text == pdf.text
    assert md.meta == html.meta == pdf.meta


def test_raw_pdf_text_has_the_problems():
    lines, meta, pages = pdf_lines(FORMATS / "warranty-policy.pdf")
    raw = [ln.text for ln in lines]
    assert pages == 2
    assert sum(t.startswith("Larkfield  |  Larkfield warranty policy") for t in raw) == 2   # header on every page
    assert "Sheds and greenhou-" in raw and "ses" in raw                                   # a hyphenated word
    assert "\x7f" in raw                                                                  # the bullet character
    assert meta["doc_id"] == "warranty-policy"


def test_clean_pdf_keeps_pages_sections_and_table_rows():
    doc = parse(FORMATS / "warranty-policy.pdf")
    assert "Page 1 of 2" not in doc.text and "Printed copies" not in doc.text
    table = next(b for b in doc.blocks if b.kind == "table")
    assert "Sheds and greenhouses | wooden and metal sheds, greenhouses | 5 years | glass and polycarbonate panels: 1 year" in table.text
    assert table.section == "Warranty periods by product category" and table.page == 1
    assert next(b for b in doc.blocks if b.text == "Safety problems").page == 2


def test_html_drops_navigation_and_footer():
    doc = parse(FORMATS / "delivery-policy.html")
    for noise in ("cookies", "Related articles", "Was this article helpful", "Privacy", "dataLayer"):
        assert noise not in doc.text


def test_dehyphenate():
    assert dehyphenate(["Sheds and greenhou-", "ses"]) == "Sheds and greenhouses"
    assert dehyphenate(["Pump kit PK-", "2200-07"]) == "Pump kit PK- 2200-07"   # not a word break: kept apart


def test_block_positions_trace_back_to_the_text():
    doc = parse(CORPUS / "documents" / "returns-policy.v3.md")
    for b in doc.blocks:
        assert doc.text[b.start:b.end] == b.text
