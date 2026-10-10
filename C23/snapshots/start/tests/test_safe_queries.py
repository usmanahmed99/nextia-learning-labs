"""Module 3, lesson 1: values go to the database as parameters, never inside the SQL text."""

import psycopg

from scripts import injection_demo

ATTACK = "x' OR '1'='1"


def test_string_building_lets_text_change_the_query(db_url):
    with psycopg.connect(db_url) as c:
        rows = injection_demo.find_customer_unsafe(c, ATTACK)
    assert len(rows) == 40  # every customer: the text changed the WHERE clause


def test_a_parameter_is_only_a_value(db_url):
    with psycopg.connect(db_url) as c:
        assert injection_demo.find_customer_safe(c, ATTACK) == []
        assert len(injection_demo.find_customer_safe(c, "olga.olsen@example.com")) == 1


def test_the_api_treats_a_quote_as_text(api):
    response = api.get("/v1/tickets", params={"team": "billing' OR '1'='1"})
    assert response.status_code == 422  # not a known team


def test_the_api_rejects_a_malformed_ticket_id(api):
    response = api.get("/v1/tickets/T-1' OR '1'='1")
    assert response.status_code == 422
