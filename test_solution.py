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


def test_subtraction_is_left_to_right():
    df = pd.DataFrame({"a": [10], "b": [3], "c": [2]})
    assert add_virtual_column(df, "a - b - c", "r")["r"].tolist() == [5]


def test_existing_column_is_overwritten():
    df = pd.DataFrame({"a": [1], "b": [2]})
    result = add_virtual_column(df, "a + b", "b")
    assert list(result.columns) == ["a", "b"]
    assert result["b"].tolist() == [3]


@pytest.mark.parametrize("label", ["Order ID", "b2", "to-tal", 7])
def test_any_invalid_column_label_gives_empty_dataframe(label):
    # Also when the role does not use that column.
    df = pd.DataFrame({"a": [1], "b": [2], label: [0]})
    assert add_virtual_column(df, "a + b", "r").empty


@pytest.mark.parametrize(
    "role",
    ["", "a +", "+ a", "a b", "a / b", "(a + b)", "a + 2", "a + missing", None],
)
def test_invalid_role_gives_empty_dataframe(role):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert add_virtual_column(df, role, "r").empty


@pytest.mark.parametrize("new_column", ["", "total1", "to tal", "to-tal", None])
def test_invalid_new_column_gives_empty_dataframe(new_column):
    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    assert add_virtual_column(df, "a + b", new_column).empty


def test_non_numeric_column_gives_empty_dataframe(fruits):
    assert add_virtual_column(fruits, "name * quantity", "r").empty


def test_duplicated_column_label_gives_empty_dataframe():
    df = pd.DataFrame([[1, 2, 3]], columns=["a", "a", "b"])
    assert add_virtual_column(df, "a + b", "r").empty


def test_not_a_dataframe_gives_empty_dataframe():
    assert add_virtual_column([[1, 2]], "a + b", "r").empty
