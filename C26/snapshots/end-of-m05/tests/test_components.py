from costmodel.components import check_diagram, components_table, load_components
from costmodel.inputs import ROOT


def test_every_component_has_a_job_an_owner_and_is_on_the_diagram():
    components = load_components()
    assert len(components) == 8
    assert check_diagram(components) == []
    assert "all are on the container diagram" in components_table(components)


def test_a_component_missing_from_the_diagram_is_reported(write):
    diagram = write("container.drawio", "<mxfile>Assistant API</mxfile>")
    missing = check_diagram(load_components(), diagram)
    assert "Assistant API" not in missing and "PostgreSQL" in missing


def test_the_sequences_name_the_parts_of_the_diagram():
    request = (ROOT / "architecture/request-flow.md").read_text(encoding="utf-8")
    ingestion = (ROOT / "architecture/ingestion-sequence.md").read_text(encoding="utf-8")
    for name in ("Assistant API", "PostgreSQL", "Model provider"):
        assert name in request and name in ingestion
    assert "Ingestion worker" in ingestion and "File storage" in ingestion


def test_the_tenant_travels_with_every_flow():
    text = (ROOT / "architecture/data-and-identity-flow.md").read_text(encoding="utf-8")
    for place in ("cache key", "job row", "row-level security", "tenant/"):
        assert place in text
