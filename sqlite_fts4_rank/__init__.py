import struct
import math
import json
import traceback
from functools import wraps


def register_functions(conn):
    "Registers these custom functions against an SQLite connection"
    conn.create_function("rank_score", 1, rank_score)
    conn.create_function("annotate_match_info", 1, annotate_match_info)
    conn.create_function("pretty_print_match_info", 2, pretty_print_match_info)


def wrap_sqlite_function_in_error_logger(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception:
            traceback.print_exc()
            raise

    return wrapper


def annotate_match_info(buf):
    return str(list(parse_match_info(buf)))


def parse_match_info(buf):
    # buf is a bytestring of unsigned integers, each 4 bytes long
    return struct.unpack("I" * (len(buf) // 4), buf)


def _error(m):
    return {"error": m}


@wrap_sqlite_function_in_error_logger
def pretty_print_match_info(buf, format_string):
    return json.dumps(_pretty_print_match_info(buf, format_string), indent=2)


def _pretty_print_match_info(buf, format_string):
    # See https://www.sqlite.org/fts3.html#matchinfo for detailed specification
    match_info = list(parse_match_info(buf))
    p_num_phrases = None
    c_num_columns = None
    results = {}
    for ch in format_string:
        if ch == "p":
            p_num_phrases = match_info.pop(0)
            results["p"] = {
                "value": p_num_phrases,
                "title": "Number of matchable phrases in the query",
            }
        elif ch == "c":
            c_num_columns = match_info.pop(0)
            results["c"] = {
                "value": c_num_columns,
                "title": "Number of user defined columns in the FTS table",
            }
        elif ch == "x":
            # Depends on p and c
            if None in (p_num_phrases, c_num_columns):
                return _error("'x' must be preceded by 'p' and 'c'")
            info = []
            results["x"] = {
                "value": info,
                "title": "Details for each phrase/column combination",
            }
            # 3 * c_num_columns * p_num_phrases
            for column_index in range(c_num_columns):
                for phrase_index in range(p_num_phrases):
                    hits_this_column_this_row = match_info.pop(0)
                    hits_this_column_all_rows = match_info.pop(0)
                    docs_with_hits = match_info.pop(0)
                    info.append(
                        {
                            "column_index": column_index,
                            "phrase_index": phrase_index,
                            "hits_this_column_this_row": hits_this_column_this_row,
                            "hits_this_column_all_rows": hits_this_column_all_rows,
                            "docs_with_hits": docs_with_hits,
                        }
                    )
        elif ch == "y":
            if None in (p_num_phrases, c_num_columns):
                return _error("'y' must be preceded by 'p' and 'c'")
            info = []
            results["y"] = {
                "value": info,
                "title": "Usable phrase matches for each phrase/column combination",
            }
            print(
                "Doing y - should be {} values - match_info is {}".format(
                    c_num_columns * p_num_phrases, match_info
                )
            )
            for column_index in range(c_num_columns):
                for phrase_index in range(p_num_phrases):
                    hits_for_phrase_in_col = match_info.pop(0)
                    info.append(
                        {
                            "column_index": column_index,
                            "phrase_index": phrase_index,
                            "hits_for_phrase_in_col": hits_for_phrase_in_col,
                        }
                    )
        elif ch == "b":
            if None in (p_num_phrases, c_num_columns):
                return _error("'b' must be preceded by 'p' and 'c'")
            results["b"] = {
                "title": "More compact form of option 'y'",
                "value": [
                    match_info.pop(0)
                    for i in range(((c_num_columns + 31) // 32) * p_num_phrases)
                ],
            }
        elif ch == "n":
            results["n"] = {
                "value": match_info.pop(0),
                "title": "Number of rows in the FTS4 table",
            }
        elif ch == "a":
            if c_num_columns is None:
                return _error("'a' must be preceded by 'c'")
            results["a"] = {
                "title": "Average number of tokens in the text values stored in each column",
                "value": [
                    {"column_index": i, "average_num_tokens": match_info.pop(0)}
                    for i in range(c_num_columns)
                ],
            }
        elif ch == "l":
            if c_num_columns is None:
                return _error("'l' must be preceded by 'c'")
            results["l"] = {
                "title": "Length of value stored in current row of the FTS4 table in tokens for each column",
                "value": [
                    {"column_index": i, "length_of_value": match_info.pop(0)}
                    for i in range(c_num_columns)
                ],
            }
        elif ch == "s":
            if c_num_columns is None:
                return _error("'s' must be preceded by 'c'")
            results["s"] = {
                "title": "Length of longest subsequence of phrase matching each column",
                "value": [
                    {
                        "column_index": i,
                        "length_phrase_subsequence_match": match_info.pop(0),
                    }
                    for i in range(c_num_columns)
                ],
            }
    return results


def rank_score(raw_match_info):
    # Score using match_info called w/default args 'pcx' - based on example rank
    # function http://sqlite.org/fts3.html#appendix_a
    # The overall relevancy returned is the sum of the relevancies of each
    # column value in the FTS table. The relevancy of a column value is the
    # sum of the following for each reportable phrase in the FTS query:
    #   (<hit count > / <global hit count>)
    match_info = _pretty_print_match_info(raw_match_info, "pcx")
    score = 0.0
    x_phrase_column_details = match_info["x"]["value"]
    for details in x_phrase_column_details:
        hits_this_column_this_row = details["hits_this_column_this_row"]
        hits_this_column_all_rows = details["hits_this_column_all_rows"]
        if hits_this_column_this_row > 0:
            score += float(hits_this_column_this_row) / hits_this_column_all_rows
    return -score
