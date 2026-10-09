"""Stable chunk IDs: the same chunk always has the same ID; a new version has new IDs."""

from policy_assistant.chunk import structure
from policy_assistant.documents import CORPUS, load_inventory
from policy_assistant.metadata import chunk_id
from policy_assistant.parse import parse


def test_same_input_same_id():
    assert chunk_id("returns-policy", "3", 0, 120) == chunk_id("returns-policy", "3", 0, 120)
    assert len(chunk_id("returns-policy", "3", 0, 120)) == 12


def test_a_new_version_gives_new_ids_for_the_same_text():
    v3 = structure(parse(CORPUS / "documents/returns-policy.v3.md"), "v3")
    v4 = structure(parse(CORPUS / "documents/returns-policy.v4.html"), "v4")
    same3 = next(c for c in v3 if c.section == "Exchanges")
    same4 = next(c for c in v4 if c.section == "Exchanges")
    assert same3.text == same4.text and same3.chunk_id != same4.chunk_id


def test_ids_do_not_depend_on_the_other_documents():
    infos = load_inventory()
    alone = structure(parse(infos[5].path), infos[5].file)
    together = [c for info in infos for c in structure(parse(info.path), info.file) if c.doc_id == infos[5].doc_id
                and c.version == infos[5].version]
    assert [c.chunk_id for c in alone] == [c.chunk_id for c in together]


def test_every_chunk_has_its_metadata():
    for info in load_inventory():
        for c in structure(parse(info.path), info.file):
            assert c.access in ("public", "staff") and c.language in ("en", "fr") and c.effective_from
            assert c.sections and c.source == info.file
