import sqlite3
from sqlite_fts4_rank import register_functions, decode_matchinfo
import pytest
import json


@pytest.fixture
def conn():
    conn = sqlite3.connect(":memory:")
    register_functions(conn)
    conn.executescript(
        """
        CREATE VIRTUAL TABLE search USING fts4(content TEXT);
    """
    )
    conn.execute('insert into search (content) values ("hello dog")')
    conn.execute('insert into search (content) values ("dog")')
    return conn


def test_fixture_sets_up_database(conn):
    assert 2 == conn.execute("select count(*) from search").fetchone()[0]


@pytest.mark.parametrize(
    "search,expected",
    [("hello", [1, 1, 1, 1, 1, 2, 2, 2]), ("dog", [1, 1, 1, 2, 2, 2, 2, 2])],
)
def test_annotate_matchinfo(conn, search, expected):
    r = conn.execute(
        """
        select decode_matchinfo(matchinfo(search, 'pcxnal'))
        from search where search match ?
    """,
        [search],
    ).fetchone()[0]
    assert expected == json.loads(r)


@pytest.mark.parametrize(
    "buf,expected",
    [
        (
            b"\x01\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00\x02\x00\x00\x00",
            (1, 2, 2, 2),
        )
    ],
)
def test_decode_matchinfo(buf, expected):
    assert expected == decode_matchinfo(buf)
