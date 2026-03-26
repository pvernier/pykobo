import pandas as pd
import pytest

from pykobo.utility import (
    capitalize_column_values,
    clean_df,
    convert_toint,
    fillna,
    fix_typos,
    lowercase_column_values,
    lowercase_columns_name,
    reconcile_columns,
    reconcile_columns_append,
    trim_columns_values,
)


def test_clean_df():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "c": [5, 6]})
    result = clean_df(df, ["a", "c"])
    assert list(result.columns) == ["a", "c"]
    assert list(result["a"]) == [1, 2]


def test_lowercase_columns_name():
    df = pd.DataFrame({"Name": [1], "AGE": [2], "city": [3]})
    lowercase_columns_name(df)
    assert list(df.columns) == ["name", "age", "city"]


def test_lowercase_column_values():
    df = pd.DataFrame({"x": ["Alice", "BOB", "charlie"]})
    lowercase_column_values(df, "x")
    assert list(df["x"]) == ["alice", "bob", "charlie"]


def test_capitalize_column_values():
    df = pd.DataFrame({"x": ["alice", "bob", "CHARLIE"]})
    capitalize_column_values(df, "x")
    assert list(df["x"]) == ["Alice", "Bob", "Charlie"]


def test_trim_columns_values_whitespace():
    df = pd.DataFrame({"a": ["  hello  ", "  world"], "b": [1, 2]})
    result = trim_columns_values(df)
    assert result["a"].tolist() == ["hello", "world"]
    assert result["b"].tolist() == [1, 2]


def test_trim_columns_values_trailing_dot():
    df = pd.DataFrame({"a": ["hello.", "world."]})
    result = trim_columns_values(df)
    assert result["a"].tolist() == ["hello", "world"]


def test_trim_columns_values_non_string_unchanged():
    df = pd.DataFrame({"a": [1.5, None, 3]})
    result = trim_columns_values(df)
    assert result["a"].tolist()[0] == 1.5
    assert result["a"].tolist()[2] == 3


def test_reconcile_columns_null_criteria():
    df = pd.DataFrame({"col1": [None, "val1", None], "col2": ["val2", "val3", "val4"]})
    reconcile_columns(df, "col1", "col2", "result")
    assert list(df.columns) == ["result"]
    assert df["result"].tolist() == ["val2", "val1", "val4"]


def test_reconcile_columns_string_criteria():
    df = pd.DataFrame({"col1": ["n/a", "val1", "n/a"], "col2": ["val2", "val3", "val4"]})
    reconcile_columns(df, "col1", "col2", "result", criteria="n/a")
    assert list(df.columns) == ["result"]
    assert df["result"].tolist() == ["val2", "val1", "val4"]


def test_reconcile_columns_invalid_criteria():
    df = pd.DataFrame({"col1": [1], "col2": [2]})
    with pytest.raises(TypeError):
        reconcile_columns(df, "col1", "col2", "result", criteria=42)


def test_reconcile_columns_append():
    df = pd.DataFrame({"col1": ["hello {name}", "world"], "col2": ["Alice", "ignored"]})
    reconcile_columns_append(df, "col1", "col2", "result", to_replace="{name}")
    assert "result" in df.columns
    assert "col1" not in df.columns
    assert "col2" not in df.columns
    assert df["result"].tolist() == ["hello Alice", "world"]


def test_reconcile_columns_append_numeric_col():
    """col1 of non-object dtype is cast to str before the replacement."""
    df = pd.DataFrame({"col1": [1.0, 2.0], "col2": ["a", "b"]})
    reconcile_columns_append(df, "col1", "col2", "result", to_replace="1.0")
    assert "result" in df.columns


def test_fix_typos():
    df = pd.DataFrame({"x": ["teh", "correct", "teh"]})
    fix_typos(df, "x", [("teh", "the")])
    assert df["x"].tolist() == ["the", "correct", "the"]


def test_fix_typos_multiple():
    df = pd.DataFrame({"x": ["teh", "recieve", "wrold"]})
    fix_typos(df, "x", [("teh", "the"), ("recieve", "receive"), ("wrold", "world")])
    assert df["x"].tolist() == ["the", "receive", "world"]


def test_fillna():
    df = pd.DataFrame({"x": [1.0, None, 3.0]})
    fillna(df, "x")
    assert df["x"].tolist() == [1.0, 0, 3.0]


def test_convert_toint():
    df = pd.DataFrame({"x": [1.0, 2.0, 3.0]})
    convert_toint(df, "x")
    assert df["x"].dtype == int
    assert df["x"].tolist() == [1, 2, 3]
