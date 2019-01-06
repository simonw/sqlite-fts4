import sqlite3
from sqlite_fts4 import register_functions, decode_matchinfo
import pytest
import json


sqlite_version = tuple(
    map(
        int,
        sqlite3.connect(":memory:")
        .execute("select sqlite_version()")
        .fetchone()[0]
        .split("."),
    )
)


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
    r = conn.execute(
        """
        select annotate_matchinfo(matchinfo(search, 'pcxnalsy'), 'pcxnalsy')
        from search where search match ?
    """,
        ["hello dog"],
    ).fetchone()[0]
    expected = {
        "p": {
            "value": 2,
            "title": "Number of matchable phrases in the query",
            "idx": 0,
        },
        "c": {
            "value": 1,
            "title": "Number of user defined columns in the FTS table",
            "idx": 1,
        },
        "x": {
            "value": [
                {
                    "phrase_index": 0,
                    "column_index": 0,
                    "hits_this_column_this_row": 1,
                    "hits_this_column_all_rows": 1,
                    "docs_with_hits": 1,
                    "idxs": [2, 3, 4],
                },
                {
                    "phrase_index": 1,
                    "column_index": 0,
                    "hits_this_column_this_row": 1,
                    "hits_this_column_all_rows": 2,
                    "docs_with_hits": 2,
                    "idxs": [5, 6, 7],
                },
            ],
            "title": "Details for each phrase/column combination",
        },
        "n": {"value": 2, "title": "Number of rows in the FTS4 table", "idx": 8},
        "a": {
            "title": "Average number of tokens in each column across the whole table",
            "value": [{"column_index": 0, "average_num_tokens": 2, "idx": 9}],
        },
        "l": {
            "title": "Number of tokens in each column of the current row of the FTS4 table",
            "value": [{"column_index": 0, "num_tokens": 2, "idx": 10}],
        },
        "s": {
            "title": "Length of longest subsequence of phrase matching each column",
            "value": [
                {"column_index": 0, "length_phrase_subsequence_match": 2, "idx": 11}
            ],
        },
        "y": {
            "value": [
                {
                    "phrase_index": 0,
                    "column_index": 0,
                    "hits_for_phrase_in_col": 1,
                    "idx": 12,
                },
                {
                    "phrase_index": 1,
                    "column_index": 0,
                    "hits_for_phrase_in_col": 1,
                    "idx": 13,
                },
            ],
            "title": "Usable phrase matches for each phrase/column combination",
        },
    }
    assert expected == json.loads(r)


@pytest.mark.skipif(
    sqlite_version < (3, 8, 11), reason="matchinfo 'b' was added in SQLite 3.8.11"
)
def test_annotate_matchinfo_b(conn):
    r = conn.execute(
        """
        select annotate_matchinfo(matchinfo(search, 'pcb'), 'pcb')
        from search where search match ?
    """,
        ["hello dog"],
    ).fetchone()[0]
    expected = {
        "p": {
            "value": 2,
            "title": "Number of matchable phrases in the query",
            "idx": 0,
        },
        "c": {
            "value": 1,
            "title": "Number of user defined columns in the FTS table",
            "idx": 1,
        },
        "b": {
            "title": "Bitfield showing which phrases occur in which columns",
            "value": [1, 1],
            "decoded": {
                "phrase_0": "10000000000000000000000000000000",
                "phrase_1": "10000000000000000000000000000000",
            },
        },
    }
    assert expected == json.loads(r)
