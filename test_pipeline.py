"""Tests for Part 2 (pipeline.py)."""

from pathlib import Path

import pandas as pd
import pytest

import pipeline

HEADER = ["Order ID", "Region", "Product", "Quantity ", "Unit Price", "Discount", "Order Date"]


def raw(*rows):
    return pd.DataFrame([list(row) for row in rows], columns=HEADER, dtype=str)


def line(order_id="SO-1", region="North", product="Mouse", quantity="2",
         unit_price="29.50", discount="", order_date="2026-01-02"):
    return (order_id, region, product, quantity, unit_price, discount, order_date)


# --- clean(): one test per problem -----------------------------------------


def test_clean_row_gets_types_and_snake_case_labels():
    df, report = pipeline.clean(raw(line(discount="1.50")))
    assert list(df.columns) == pipeline.EXPECTED_COLUMNS
    assert df.loc[0, "quantity"] == 2
    assert df.loc[0, "unit_price"] == 29.5
    assert df.loc[0, "discount"] == 1.5
    assert df.loc[0, "order_date"] == pd.Timestamp("2026-01-02")
    assert report["header_labels_with_stray_whitespace"] == 1
    assert report["clean_rows"] == 1


def test_region_spelling_is_normalised():
    df, report = pipeline.clean(raw(
        line("SO-1", "North"), line("SO-2", " north"), line("SO-3", "NORTH  "),
        line("SO-4", "west"),
    ))
    assert df["region"].tolist() == ["North", "North", "North", "West"]
    assert report["region_spelling_fixed"] == 3


def test_repeated_header_and_total_rows_are_removed():
    df, report = pipeline.clean(raw(
        line("SO-1"),
        tuple(HEADER),
        line("SO-2"),
        ("TOTAL", "", "", "4", "", "0.00", ""),
    ))
    assert df["order_id"].tolist() == ["SO-1", "SO-2"]
    assert report["repeated_header_rows"] == 1
    assert report["total_rows"] == 1


def test_exact_duplicates_are_removed_once():
    df, report = pipeline.clean(raw(line("SO-1"), line("SO-1"), line("SO-2")))
    assert df["order_id"].tolist() == ["SO-1", "SO-2"]
    assert report["duplicate_rows"] == 1


def test_same_order_id_with_different_values_is_an_error():
    with pytest.raises(ValueError, match="conflicting"):
        pipeline.clean(raw(line("SO-1", quantity="2"), line("SO-1", quantity="3")))


def test_thousands_separator_in_quantity():
    df, report = pipeline.clean(raw(line(quantity="1 762")))
    assert df.loc[0, "quantity"] == 1762
    assert report["quantity_thousands_separator"] == 1


def test_negative_quantity_is_kept_as_a_return():
    df, report = pipeline.clean(raw(line(quantity="-2")))
    assert df.loc[0, "quantity"] == -2
    assert report["negative_quantity_kept"] == 1
    assert pipeline.add_revenue(df).loc[0, "revenue"] == -59.0


def test_decimal_comma_in_unit_price():
    df, report = pipeline.clean(raw(line(unit_price="29,50")))
    assert df.loc[0, "unit_price"] == 29.5
    assert report["unit_price_decimal_comma"] == 1


def test_missing_unit_price_is_filled_from_the_same_product():
    df, report = pipeline.clean(raw(
        line("SO-1", product="Mouse", unit_price="29.50"),
        line("SO-2", product="Mouse", unit_price=""),
        line("SO-3", product="Keyboard", unit_price="89.00"),
    ))
    assert df["unit_price"].tolist() == [29.5, 29.5, 89.0]
    assert report["unit_price_missing_filled"] == 1


def test_missing_unit_price_without_a_reference_is_an_error():
    with pytest.raises(ValueError, match="Cannot fill the unit price"):
        pipeline.clean(raw(line("SO-1", product="Mouse", unit_price="")))


def test_missing_unit_price_with_two_candidate_prices_is_an_error():
    with pytest.raises(ValueError, match="Cannot fill the unit price"):
        pipeline.clean(raw(
            line("SO-1", unit_price="29.50"),
            line("SO-2", unit_price="31.00"),
            line("SO-3", unit_price=""),
        ))


def test_empty_discount_means_zero():
    df, report = pipeline.clean(raw(line("SO-1", discount=""), line("SO-2", discount="5.90")))
    assert df["discount"].tolist() == [0.0, 5.9]
    assert report["discount_empty_set_to_zero"] == 1


@pytest.mark.parametrize(
    "bad",
    [
        {"quantity": "two"},
        {"quantity": "2.5"},
        {"quantity": ""},
        {"unit_price": "abc"},
        {"discount": "10%"},
        {"region": ""},
        {"order_date": "02/01/2026"},
    ],
)
def test_values_that_cannot_be_fixed_fail_loudly(bad):
    with pytest.raises(ValueError):
        pipeline.clean(raw(line("SO-1"), line("SO-2", **bad)))


def test_unexpected_columns_are_an_error():
    with pytest.raises(ValueError, match="Unexpected columns"):
        pipeline.clean(pd.DataFrame({"a": ["1"]}))


# --- revenue ----------------------------------------------------------------


def test_revenue_is_quantity_times_price_minus_line_discount():
    df, _ = pipeline.clean(raw(line(quantity="4", unit_price="10.00", discount="3.00")))
    assert pipeline.add_revenue(df).loc[0, "revenue"] == 37.0


def test_revenue_by_region_sums_and_sorts():
    df, _ = pipeline.clean(raw(
        line("SO-1", "West", quantity="1", unit_price="10.00"),
        line("SO-2", "east", quantity="2", unit_price="10.00", discount="0.50"),
        line("SO-3", "West ", quantity="3", unit_price="10.00"),
    ))
    totals = pipeline.revenue_by_region(pipeline.add_revenue(df))
    assert totals.to_dict("records") == [
        {"region": "East", "revenue": 19.5},
        {"region": "West", "revenue": 40.0},
    ]


# --- the real file ----------------------------------------------------------


@pytest.fixture(scope="module")
def real():
    return pipeline.clean(pipeline.read_raw(pipeline.DEFAULT_INPUT))


def test_real_file_cleaning_report(real):
    _, report = real
    assert report == {
        "header_labels_with_stray_whitespace": 1,
        "repeated_header_rows": 1,
        "total_rows": 1,
        "duplicate_rows": 5,
        "region_spelling_fixed": 15,
        "quantity_thousands_separator": 4,
        "negative_quantity_kept": 6,
        "unit_price_decimal_comma": 7,
        "unit_price_missing_filled": 4,
        "discount_empty_set_to_zero": 959,
        "clean_rows": 1500,
    }


def test_real_file_is_ready_for_calculations(real):
    df, _ = real
    assert df["order_id"].is_unique
    assert sorted(df["region"].unique()) == ["Central", "East", "North", "South", "West"]
    assert not df.isna().any().any()
    assert df["quantity"].dtype == "int64"
    assert df["unit_price"].dtype == "float64"
    assert df["discount"].dtype == "float64"
    assert (df["unit_price"] > 0).all()
    assert (df["discount"] >= 0).all()
    assert df.groupby("product")["unit_price"].nunique().eq(1).all()


def test_real_file_agrees_with_its_own_total_row(real):
    """The TOTAL row sums every exported line, duplicates included."""
    df, _ = real
    source = pipeline.read_raw(pipeline.DEFAULT_INPUT)
    total = source[source["Order ID"] == "TOTAL"].iloc[0]
    copied_ids = source.loc[source.duplicated(keep="first"), "Order ID"]
    copies = df[df["order_id"].isin(copied_ids)]
    assert df["quantity"].sum() + copies["quantity"].sum() == int(total["Quantity "])
    assert round(df["discount"].sum() + copies["discount"].sum(), 2) == float(total["Discount"])


def test_committed_output_is_up_to_date(tmp_path):
    output = tmp_path / "out.csv"
    pipeline.run(pipeline.DEFAULT_INPUT, output)
    committed = Path(pipeline.DEFAULT_OUTPUT)
    assert committed.read_text().splitlines() == output.read_text().splitlines()
