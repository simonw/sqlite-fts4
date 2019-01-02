import sqlite3
from sqlite_fts4 import register_functions, decode_matchinfo
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
def test_decode_matchinfo(conn, search, expected):
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
def test_underlying_decode_matchinfo(buf, expected):
    assert expected == decode_matchinfo(buf)


def test_annotate_matchinfo(conn):
    r = conn.execute("""
        select annotate_matchinfo(matchinfo(search, 'pcxnal'), 'pcxnal')
        from search where search match ?
    """, ["dog"]).fetchone()[0]
    expected = {
        "p": {
            "value": 1,
            "title": "Number of matchable phrases in the query"
        },
        "c": {
            "value": 1,
            "title": "Number of user defined columns in the FTS table"
        },
        "x": {
            "value": [
            {
                "column_index": 0,
                "phrase_index": 0,
                "hits_this_column_this_row": 1,
                "hits_this_column_all_rows": 2,
                "docs_with_hits": 2
            }
            ],
            "title": "Details for each phrase/column combination"
        },
        "n": {
            "value": 2,
            "title": "Number of rows in the FTS4 table"
        },
        "a": {
            "title": "Average number of tokens in the text values stored in each column",
            "value": [
            {
                "column_index": 0,
                "average_num_tokens": 2
            }
            ]
        },
        "l": {
            "title": "Length of value stored in current row of the FTS4 table in tokens for each column",
            "value": [
            {
                "column_index": 0,
                "length_of_value": 2
            }
            ]
        }
    }
    assert expected == json.loads(r)
