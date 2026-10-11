import pytest

from costmodel.inputs import InputError, check_range, load_measured, load_prices, pick


def test_the_pack_prices_all_have_a_source():
    prices = load_prices()
    assert len(prices) >= 30
    assert all(p.source.startswith(("price:", "price page:")) for p in prices.values())


def test_the_pack_measured_values_all_name_their_run():
    measured = load_measured()
    assert len(measured) >= 30
    assert all(m.source.startswith("measured:") for m in measured.values())


def test_a_price_without_a_source_is_refused(write):
    path = write("prices.toml", '[x]\nvalue = 1.0\nunit = "US$"\n')
    with pytest.raises(InputError, match="has no source"):
        load_prices(path)


def test_a_negative_or_text_value_is_refused(write):
    with pytest.raises(InputError, match="negative"):
        load_prices(write("p.toml", '[x]\nvalue = -1\nunit = "US$"\nsource = "price: a page"\n'))
    with pytest.raises(InputError, match="must be a number"):
        load_prices(write("q.toml", '[x]\nvalue = "cheap"\nunit = "US$"\nsource = "price: a page"\n'))


def test_a_range_is_low_base_high():
    assert check_range("users", [1, 2, 3]) == (1.0, 2.0, 3.0)
    assert pick((1.0, 2.0, 3.0), "high") == 3.0
    for bad in ([3, 2, 1], [1, 2], 5, [-1, 0, 1]):
        with pytest.raises(InputError):
            check_range("users", bad)


def test_a_missing_file_says_where_it_should_be(tmp_path):
    with pytest.raises(InputError, match="is missing"):
        load_prices(tmp_path / "prices.toml")
