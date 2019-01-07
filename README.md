# sqlite-fts4

[![PyPI](https://img.shields.io/pypi/v/sqlite-fts4.svg)](https://pypi.org/project/sqlite-fts4/)
[![Travis CI](https://travis-ci.com/simonw/sqlite-fts4.svg?branch=master)](https://travis-ci.com/simonw/sqlite-fts4)
[![License](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://github.com/simonw/sqlite-fts4/blob/master/LICENSE)

Custom SQLite functions written in Python for ranking documents indexed using the FTS4 extension.

Read [Exploring search relevance algorithms with SQLite](https://simonwillison.net/2019/Jan/7/exploring-search-relevance-algorithms-sqlite/) for further details on this project.

## Demo

You can try out these SQL functions [using this interactive demo](https://datasette-sqlite-fts4.datasette.io/24ways-fts4?sql=select%0D%0A++++json_object%28%0D%0A++++++++"label"%2C+articles.title%2C+"href"%2C+articles.url%0D%0A++++%29+as+article%2C%0D%0A++++articles.author%2C%0D%0A++++rank_score%28matchinfo%28articles_fts%2C+"pcx"%29%29+as+score%2C%0D%0A++++rank_bm25%28matchinfo%28articles_fts%2C+"pcnalx"%29%29+as+bm25%2C%0D%0A++++json_object%28%0D%0A++++++++"pre"%2C+annotate_matchinfo%28matchinfo%28articles_fts%2C+"pcxnalyb"%29%2C+"pcxnalyb"%29%0D%0A++++%29+as+annotated_matchinfo%2C%0D%0A++++matchinfo%28articles_fts%2C+"pcxnalyb"%29+as+matchinfo%2C%0D%0A++++decode_matchinfo%28matchinfo%28articles_fts%2C+"pcxnalyb"%29%29+as+decoded_matchinfo%0D%0Afrom%0D%0A++++articles_fts+join+articles+on+articles.rowid+%3D+articles_fts.rowid%0D%0Awhere%0D%0A++++articles_fts+match+%3Asearch%0D%0Aorder+by+bm25&search=jquery+maps).

## Usage

This module implements several custom SQLite3 functions. You can register them against an existing SQLite connection like so:

    import sqlite3
    from sqlite_fts4 import register_functions

    conn = sqlite3.connect(":memory:")
    register_functions(conn)

If you only want a subset of the functions registered you can do so like this:

    from sqlite_fts4 import rank_score

    conn = sqlite3.connect(":memory:")
    conn.create_function("rank_score", 1, rank_score)

if you want to use these functions with [Datasette](https://github.com/simonw/datasette) you can enable them by installing the [datasette-sqlite-fts4](https://github.com/simonw/datasette-sqlite-fts4) plugin:

    pip install datasette-sqlite-fts4

## rank_score()

This is an extremely simple ranking function, based on [an example](https://www.sqlite.org/fts3.html#appendix_a) in the SQLite documentation. It generates a score for each document using the sum of the score for each column. The score for each column is calculated as the number of search matches in that column divided by the number of search matches for every column in the index - a classic [TF-IDF](https://en.wikipedia.org/wiki/Tf%E2%80%93idf) calculation.

You can use it in a query like this:

    select *, rank_score(matchinfo(docs, "pcx")) as score
    from docs where docs match "dog"
    order by score desc

You *must* use the `"pcx"` matchinfo format string here, or you will get incorrect results.

## rank_bm25()

An implementation of the [Okapi BM25](https://en.wikipedia.org/wiki/Okapi_BM25) scoring algorithm. Use it in a query like this:

    select *, rank_bm25(matchinfo(docs, "pcnalx")) as score
    from docs where docs match "dog"
    order by score desc

You *must* use the `"pcnalx"` matchinfo format string here, or you will get incorrect results.

## decode_matchinfo()

SQLite's [built-in matchinfo() function](https://www.sqlite.org/fts3.html#matchinfo) returns results as a binary string. This binary represents a list of 32 bit unsigned integers, but reading the binary results is not particularly human-friendly.

The `decode_matchinfo()` function decodes the binary string and converts it into a JSON list of integers.

Usage:

    select *, decode_matchinfo(matchinfo(docs, "pcx"))
    from docs where docs match "dog"

Example output:

    hello dog, [1, 1, 1, 1, 1]

## annotate_matchinfo()

This function decodes the matchinfo document into a verbose JSON structure that describes exactly what each of the returned integers actually means.

Full documentation for the different format string options can be found here: https://www.sqlite.org/fts3.html#matchinfo

You need to call this function with the same format string as was passed to `matchinfo()` - for example:

    select annotate_matchinfo(matchinfo(docs, "pcxnal"), "pcxnal")
    from docs where docs match "dog"

The returned JSON will include a key for each letter in the format string. For example:

    {
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
            "value": 3,
            "title": "Number of rows in the FTS4 table"
        },
        "a": {
            "title":"Average number of tokens in the text values stored in each column",
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
