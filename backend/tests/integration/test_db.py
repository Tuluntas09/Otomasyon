"""Integration tests for app.data.persistence.db — connection and schema init."""

import sqlite3

import pytest

from app.data.persistence.db import get_connection, init_schema


@pytest.fixture()
def mem_conn():
    conn = get_connection(":memory:")
    yield conn
    conn.close()


def test_get_connection_returns_sqlite_connection(mem_conn):
    assert isinstance(mem_conn, sqlite3.Connection)


def test_row_factory_is_set(mem_conn):
    assert mem_conn.row_factory == sqlite3.Row


def test_init_schema_creates_holdings_table(mem_conn):
    init_schema(mem_conn)
    result = mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='holdings'"
    ).fetchone()
    assert result is not None


def test_init_schema_creates_watchlist_table(mem_conn):
    init_schema(mem_conn)
    result = mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='watchlist'"
    ).fetchone()
    assert result is not None


def test_init_schema_creates_prices_table(mem_conn):
    init_schema(mem_conn)
    result = mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='prices'"
    ).fetchone()
    assert result is not None


def test_init_schema_is_idempotent(mem_conn):
    init_schema(mem_conn)
    init_schema(mem_conn)
    tables = mem_conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = {r["name"] for r in tables}
    assert {"holdings", "watchlist", "prices"}.issubset(names)
