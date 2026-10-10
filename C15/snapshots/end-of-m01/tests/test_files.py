import json

from ticket_cleaner.files import read_rows, write_json


def test_csv_with_byte_order_mark(tmp_path):
    path = tmp_path / "tickets.csv"
    path.write_text("id,status\nT-1001,open\n", encoding="utf-8-sig")
    assert read_rows(path) == [{"id": "T-1001", "status": "open"}]


def test_write_json_makes_the_folder(tmp_path):
    path = tmp_path / "reports" / "summary.json"
    write_json({"selected": 0}, path)
    assert json.loads(path.read_text(encoding="utf-8")) == {"selected": 0}
    assert not (tmp_path / "reports" / "summary.json.tmp").exists()
