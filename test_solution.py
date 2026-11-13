"""Extra tests for Part 1 (add_virtual_column)."""

import pandas as pd
import pytest

from solution import add_virtual_column


@pytest.fixture
def fruits():
    return pd.DataFrame(
        {"name": ["banana", "apple"], "quantity": [10, 3], "price": [10, 1]}
    )


def test_example_from_the_task(fruits):
    result = add_virtual_column(fruits, "quantity * price", "total")
    assert list(result.columns) == ["name", "quantity", "price", "total"]
    assert result["total"].tolist() == [100, 3]


def test_input_is_not_modified(fruits):
    before = fruits.copy()
    add_virtual_column(fruits, "quantity * price", "total")
    assert fruits.equals(before)


def test_multiplication_before_addition_and_subtraction():
    df = pd.DataFrame({"a": [2, 10], "b": [3, 4], "c": [4, 5]})
    assert add_virtual_column(df, "a + b * c", "r")["r"].tolist() == [14, 30]
    assert add_virtual_column(df, "a * b - c", "r")["r"].tolist() == [2, 35]
    assert add_virtual_column(df, "a - b * c + a", "r")["r"].tolist() == [-8, 0]


def test_subtraction_is_left_to_right():
    df = pd.DataFrame({"a": [10], "b": [3], "c": [2]})
    assert add_virtual_column(df, "a - b - c", "r")["r"].tolist() == [5]


def test_same_column_used_twice():
    df = pd.DataFrame({"a": [3, 4]})
    assert add_virtual_column(df, "a * a", "square")["square"].tolist() == [9, 16]


def test_single_column_role_copies_the_column():
    df = pd.DataFrame({"a": [3, 4]})
    assert add_virtual_column(df, "a", "b")["b"].tolist() == [3, 4]


def test_floats_and_missing_values():
    df = pd.DataFrame({"a": [1.5, None], "b": [2.0, 1.0]})
    result = add_virtual_column(df, "a * b", "r")
    assert result["r"][0] == 3.0
    assert pd.isna(result["r"][1])


def test_underscore_and_uppercase_labels():
    df = pd.DataFrame({"_A": [1], "B_": [2]})
    assert add_virtual_column(df, "_A+B_", "_")["_"].tolist() == [3]


def test_labels_that_are_python_keywords():
    df = pd.DataFrame({"in": [1], "class": [2]})
    assert add_virtual_column(df, "in + class", "and")["and"].tolist() == [3]


def test_whitespace_around_tokens():
    df = pd.DataFrame({"a": [1], "b": [2]})
    assert add_virtual_column(df, "\ta  +\n b ", "r")["r"].tolist() == [3]


def test_existing_column_is_overwritten():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = add_virtual_column(df, "a + b", "b")
    assert list(result.columns) == ["a", "b"]
    assert result["b"].tolist() == [3]


def test_index_is_preserved():
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]}, index=["x", "y"])
    result = add_virtual_column(df, "a + b", "r")
    assert result.index.tolist() == ["x", "y"]


def test_unused_columns_with_other_labels_do_not_matter():
    df = pd.DataFrame({"a": [1], "b": [2], "Order ID": ["x"], 7: [0]})
    assert add_virtual_column(df, "a + b", "r")["r"].tolist() == [3]


@pytest.mark.parametrize(
    "role",
    [
        "",
        "   ",
        "a +",
        "+ a",
        "- a",
        "a b",
        "a + + b",
        "a ** b",
        "a / b",
        "a % b",
        "(a + b)",
        "a + 2",
        "a * b2",
        "a + b; a",
        "a + missing",
        "a + B",
        "a + __import__",
        None,
        5,
    ],
)
def test_invalid_role_gives_empty_dataframe(role):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4], "b2": [5, 6]})
    assert add_virtual_column(df, role, "r").empty


@pytest.mark.parametrize(
    "new_column",
    ["", " ", "total1", "to tal", "to-tal", "total ", "łączna", None, 3],
)
def test_invalid_new_column_gives_empty_dataframe(new_column):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert add_virtual_column(df, "a + b", new_column).empty


def test_only_ascii_letters_count_as_letters():
    # Assumption: "letters" means A-Z and a-z, in the role and in new_column.
    df = pd.DataFrame({"ilość": [1], "b": [2]})
    assert add_virtual_column(df, "ilość + b", "r").empty


def test_non_numeric_column_gives_empty_dataframe(fruits):
    assert add_virtual_column(fruits, "name + name", "r").empty
    assert add_virtual_column(fruits, "name * quantity", "r").empty


def test_duplicated_column_label_gives_empty_dataframe():
    df = pd.DataFrame([[1, 2, 3]], columns=["a", "a", "b"])
    assert add_virtual_column(df, "a + b", "r").empty


def test_not_a_dataframe_gives_empty_dataframe():
    assert add_virtual_column([[1, 2]], "a + b", "r").empty


def test_dataframe_without_rows():
    df = pd.DataFrame({"a": pd.Series(dtype="int64"), "b": pd.Series(dtype="int64")})
    result = add_virtual_column(df, "a + b", "r")
    assert list(result.columns) == ["a", "b", "r"]
    assert len(result) == 0
