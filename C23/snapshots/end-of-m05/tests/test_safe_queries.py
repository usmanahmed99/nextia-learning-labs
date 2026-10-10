"""Module 3, lesson 1: values go to the database as parameters, never inside the SQL text."""

import psycopg
import pytest

from scripts import injection_demo


@pytest.fixture
def api(grace):
    """Since the authentication course, the ticket routes need a member: Grace, at Larkfield."""
    return grace


ATTACK = "x' OR '1'='1"


def test_string_building_lets_text_change_the_query(db_url):
    with psycopg.connect(db_url) as c:
        rows = injection_demo.find_customer_unsafe(c, ATTACK)
    # every customer of BOTH shops: the text changed the WHERE clause, and the query has no
    # organization in it (the authentication course)
    assert len(rows) == 52


def test_a_parameter_is_only_a_value(db_url):
    with psycopg.connect(db_url) as c:
        assert injection_demo.find_customer_safe(c, ATTACK) == []
        # Olga Olsen shops at both Larkfield and Bramble Books: one row in each shop
        assert len(injection_demo.find_customer_safe(c, "olga.olsen@example.com")) == 2


def test_the_api_treats_a_quote_as_text(api):
    response = api.get("/v1/tenants/larkfield/tickets", params={"team": "billing' OR '1'='1"})
    assert response.status_code == 422  # not a known team


def test_the_api_rejects_a_malformed_ticket_id(api):
    response = api.get("/v1/tenants/larkfield/tickets/T-1' OR '1'='1")
    assert response.status_code == 422
