from helpers import pack

from costmodel.growth import growth_table, timeline
from costmodel.recovery import load_recovery, plans, recovery_table


def test_a_nightly_dump_misses_a_one_hour_rpo():
    d, g, m, p = pack()
    r = load_recovery()
    by = {x["plan"]: x for x in plans(r, m, 0.4)}
    assert not by["nightly dump to file storage"]["meets_rpo"]
    assert by["managed point-in-time restore"]["meets_rpo"]


def test_copying_the_data_is_a_small_part_of_the_recovery_time():
    d, g, m, p = pack()
    r = load_recovery()
    restore_minutes = 0.4 * 1000 / m["restore_mb_per_s"].value / 60
    assert restore_minutes < 1 < plans(r, m, 0.4)[1]["rto_minutes"]
    assert "Test the restore" in recovery_table(r, m, 0.4)


def test_growth_base_needs_no_step_in_the_first_year():
    d, g, m, p = pack()
    rows = timeline(d, g, m, p, "base")
    assert len(rows) == 13 and not any(r["signals"] for r in rows)


def test_growth_high_hits_the_provider_quota_first():
    d, g, m, p = pack()
    rows = timeline(d, g, m, p, "high")
    assert "provider quota" in rows[0]["signals"]
    assert "database storage" not in rows[-1]["signals"]
    assert "First signal: provider quota in month 0" in growth_table(rows, "high")
