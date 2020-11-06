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
CREATE VIRTUAL TABLE search USING fts4(c0, c1);
INSERT INTO search (c0, c1) VALUES ("this is about a dog", "more about that dog dog");
INSERT INTO search (c0, c1) VALUES ("this is about a cat", "stuff on that cat cat");
INSERT INTO search (c0, c1) VALUES ("something about a ferret", "yeah a ferret ferret");
INSERT INTO search (c0, c1) VALUES ("both of them", "both dog dog and cat here");
INSERT INTO search (c0, c1) VALUES ("not mammals", "maybe talk about fish");
    """
    )
    return conn


def test_fixture_sets_up_database(conn):
    assert 5 == conn.execute("select count(*) from search").fetchone()[0]


@pytest.mark.parametrize(
    "search,expected",
    [
        ("dog", [1, 2, 1, 1, 1, 2, 4, 2, 5, 4, 5, 5, 5]),
        ("cat", [1, 2, 1, 1, 1, 2, 3, 2, 5, 4, 5, 5, 5]),
    ],
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


def test_rank_bm25(conn):
    results = conn.execute(
        """
        select c0, c1, rank_bm25(matchinfo(search, 'pcnalx')) as bm25
        from search where search match ?
    """,
        ["dog"],
    ).fetchall()
    assert ("this is about a dog", "more about that dog dog") == results[0][:2]
    assert pytest.approx(-1.459328) == results[0][2]
    assert ("both of them", "both dog dog and cat here") == results[1][:2]
    assert pytest.approx(-0.438011) == results[1][2]


def test_rank_bm25_no_match(conn):
    results = conn.execute(
        """
        select c0, c1, rank_bm25(matchinfo(search, 'pcnalx')) as bm25
        from search limit 1
    """
    ).fetchall()
    assert None == results[0][2]


def test_annotate_matchinfo(conn):
    r = conn.execute(
        """
        select annotate_matchinfo(matchinfo(search, 'pcxnals'), 'pcxnals')
        from search where search match ?
    """,
        ["dog"],
    ).fetchone()[0]
    expected = {
        "p": {
            "value": 1,
            "title": "Number of matchable phrases in the query",
            "idx": 0,
        },
        "c": {
            "value": 2,
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
                    "phrase_index": 0,
                    "column_index": 1,
                    "hits_this_column_this_row": 2,
                    "hits_this_column_all_rows": 4,
                    "docs_with_hits": 2,
                    "idxs": [5, 6, 7],
                },
            ],
            "title": "Details for each phrase/column combination",
        },
        "n": {"value": 5, "title": "Number of rows in the FTS4 table", "idx": 8},
        "a": {
            "title": "Average number of tokens in each column across the whole table",
            "value": [
                {"column_index": 0, "average_num_tokens": 4, "idx": 9},
                {"column_index": 1, "average_num_tokens": 5, "idx": 10},
            ],
        },
        "l": {
            "title": "Number of tokens in each column of the current row of the FTS4 table",
            "value": [
                {"column_index": 0, "num_tokens": 5, "idx": 11},
                {"column_index": 1, "num_tokens": 5, "idx": 12},
            ],
        },
        "s": {
            "title": "Length of longest subsequence of phrase matching each column",
            "value": [
                {"column_index": 0, "length_phrase_subsequence_match": 1, "idx": 13},
                {"column_index": 1, "length_phrase_subsequence_match": 1, "idx": 14},
            ],
        },
    }
    assert expected == json.loads(r)


def test_annotate_matchinfo_empty(conn):
    r = conn.execute(
        """
        select annotate_matchinfo(matchinfo(search, 'pcxnals'), 'pcxnals')
        from search limit 1
    """
    ).fetchone()[0]
    assert {} == json.loads(r)


@pytest.mark.skipif(
    sqlite_version < (3, 8, 11), reason="matchinfo 'b' was added in SQLite 3.8.11"
)
def test_annotate_matchinfo_b(conn):
    r = conn.execute(
        """
        select annotate_matchinfo(matchinfo(search, 'pcb'), 'pcb')
        from search where search match ?
    """,
        ["something ferret"],
    ).fetchone()[0]
    expected = {
        "title": "Bitfield showing which phrases occur in which columns",
        "value": [1, 3],
        "decoded": {
            "phrase_0": "10000000000000000000000000000000",
            "phrase_1": "11000000000000000000000000000000",
        },
    }
    assert expected == json.loads(r)["b"]


@pytest.mark.skipif(
    sqlite_version < (3, 8, 10), reason="matchinfo 'y' was added in SQLite 3.8.10"
)
def test_annotate_matchinfo_y(conn):
    r = conn.execute(
        """
        select annotate_matchinfo(matchinfo(search, 'pcy'), 'pcy')
        from search where search match ?
    """,
        ["something ferret"],
    ).fetchone()[0]
    expected = {
        "value": [
            {
                "phrase_index": 0,
                "column_index": 0,
                "hits_for_phrase_in_col": 1,
                "idx": 2,
            },
            {
                "phrase_index": 0,
                "column_index": 1,
                "hits_for_phrase_in_col": 0,
                "idx": 3,
            },
            {
                "phrase_index": 1,
                "column_index": 0,
                "hits_for_phrase_in_col": 1,
                "idx": 4,
            },
            {
                "phrase_index": 1,
                "column_index": 1,
                "hits_for_phrase_in_col": 2,
                "idx": 5,
            },
        ],
        "title": "Usable phrase matches for each phrase/column combination",
    }
    assert expected == json.loads(r)["y"]
