"""The district table: one measure for every fix of issue 12 in delivery-slots.

Put this file next to the project folder, then run it from inside the project:

    python -m pytest -q --rootdir=. ../district_table.py

Twelve postcodes, each with the zone that data/zones.csv gives it, or "refused" where Larkfield
does not deliver. The expected zones come from the data file and the two issues, not from any
fix. Written for the course by Nextia Learning (MIT).
"""

from pathlib import Path

import pytest

from delivery_slots.zones import UnknownPostcode, load_zones, zone_for

TABLE = [
    ("LS12 2AB", "west", "the customer of issue 12"),
    ("ls122ab", "west", "issue 12 typed as in issue 3: small letters, no space"),
    ("LS13 4EX", "west", "another west district that starts with LS1"),
    ("LS16 7QR", "north", "a north district that starts with LS1"),
    ("LS17 5DT", "north", "a north district that starts with LS1"),
    ("LS10 1LZ", "city", "a city district that starts with LS1"),
    ("LS1 4AP", "city", "a one-digit district"),
    ("LS14AP", "city", "a one-digit district without the space"),
    ("LS53QR", "west", "issue 3: no space"),
    (" ls4  2te ", "west", "spaces and small letters"),
    ("LS19 7XB", "refused", "starts like LS1, but Larkfield does not deliver there"),
    ("BD1 1AA", "refused", "another town"),
]


@pytest.fixture(scope="module")
def zones():
    return load_zones(Path("data") / "zones.csv")


@pytest.mark.parametrize("postcode, expected, why", TABLE, ids=[row[0].strip() for row in TABLE])
def test_district_table(zones, postcode, expected, why):
    try:
        got = zone_for(postcode, zones)
    except UnknownPostcode:
        got = "refused"
    assert got == expected, why
