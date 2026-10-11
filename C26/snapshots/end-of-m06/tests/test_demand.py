import pytest

from costmodel.demand import active, demand_table, evidence_counts, load_demand, questions_per_day
from costmodel.inputs import InputError

TENANT = """
[settings]
days_per_month = 30
peak_hour_share = [0.1, 0.1, 0.2]
peak_minute_factor = [2, 2, 4]
[settings.evidence]
peak_hour_share = "verified: the ticket log"
peak_minute_factor = "assumed: a guess"
[tenants.shop]
name = "Shop"
joins_in_month = {joins}
staff_users = [2, 2, 2]
staff_questions_per_day = [10, 10, 10]
customers_per_day = [50, 50, 50]
customer_questions_per_day = [2, 2, 2]
documents = [10, 10, 10]
words_per_document = [100, 100, 100]
document_changes_per_month = [1, 1, 1]
user_growth_per_month = [0.1, 0.1, 0.1]
[tenants.shop.evidence]
staff_users = "verified: the rota"
staff_questions_per_day = "assumed: a guess"
customers_per_day = "assumed: a guess"
customer_questions_per_day = "assumed: a guess"
documents = "verified: counted"
words_per_document = "verified: counted"
document_changes_per_month = "assumed: a guess"
user_growth_per_month = "assumed: a guess"
"""


def test_questions_per_day_is_staff_plus_customers(write):
    d = load_demand(write("demand.toml", TENANT.format(joins=0)))
    # 2 staff x 10 + 50 customers x 2 = 120
    assert questions_per_day(d.tenants[0], "base") == 120


def test_growth_compounds_from_the_month_the_tenant_joins(write):
    d = load_demand(write("demand.toml", TENANT.format(joins=2)))
    t = d.tenants[0]
    assert active(d, 1) == [] and active(d, 2) == [t]
    assert questions_per_day(t, "base", month=4) == pytest.approx(120 * 1.1 ** 2)


def test_every_value_needs_evidence(write):
    text = TENANT.format(joins=0).replace('documents = "verified: counted"', 'documents = "counted"')
    with pytest.raises(InputError, match="'documents' needs evidence"):
        load_demand(write("demand.toml", text))


def test_growth_is_a_share_not_a_percent(write):
    text = TENANT.format(joins=0).replace("user_growth_per_month = [0.1, 0.1, 0.1]", "user_growth_per_month = [2, 2, 2]")
    with pytest.raises(InputError, match="is a share"):
        load_demand(write("demand.toml", text))


def test_the_pack_demand_counts_verified_and_assumed():
    d = load_demand()
    verified, assumed = evidence_counts(d)
    assert verified > 0 and assumed > verified      # most demand numbers are still assumptions
    assert [t.name for t in active(d, 0)] == ["Larkfield", "Bramble Books"]


def test_the_demand_table_shows_the_busiest_hour(write):
    text = demand_table(load_demand(write("demand.toml", TENANT.format(joins=0))))
    assert "All tenants" in text and "Busiest hour" in text
    assert "120" in text and "12" in text     # 120 a day, 10% in the busiest hour
