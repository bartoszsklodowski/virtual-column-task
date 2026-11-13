"""Part 2: clean sales.csv and write the total revenue of each region.

Usage:
    python pipeline.py [INPUT_CSV] [OUTPUT_CSV]

Defaults: sales.csv and revenue_by_region.csv next to this file.
"""

import re
import sys
from pathlib import Path

import pandas

from solution import add_virtual_column

BASE_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT = BASE_DIR / "sales.csv"
DEFAULT_OUTPUT = BASE_DIR / "revenue_by_region.csv"

EXPECTED_COLUMNS = [
    "order_id",
    "region",
    "product",
    "quantity",
    "unit_price",
    "discount",
    "order_date",
]
REVENUE_ROLE = "quantity * unit_price - discount"

_INTEGER_RE = r"-?\d+"
_DECIMAL_RE = r"\d+(?:\.\d+)?"


def _normalise_label(label: str) -> str:
    """'Quantity ' -> 'quantity', 'Unit Price' -> 'unit_price'."""
    return re.sub(r"\s+", "_", label.strip().lower())


def read_raw(path) -> pandas.DataFrame:
    """Read the export as text, so that nothing is guessed before cleaning."""
    return pandas.read_csv(path, dtype=str, keep_default_na=False)


def clean(raw: pandas.DataFrame) -> tuple[pandas.DataFrame, dict[str, int]]:
    """Return the cleaned order lines and a count of rows for each problem.

    Rows are only removed when they are not order lines (repeated header,
    totals row) or are exact copies of another line. Every other problem is
    fixed in place. Anything that cannot be fixed raises ValueError instead
    of being dropped silently.
    """
    report: dict[str, int] = {}
    raw_labels = [str(label) for label in raw.columns]

    df = raw.astype(str)
    df.columns = [_normalise_label(label) for label in raw_labels]
    report["header_labels_with_stray_whitespace"] = sum(
        label != label.strip() for label in raw_labels
    )
    if list(df.columns) != EXPECTED_COLUMNS:
        raise ValueError(f"Unexpected columns: {list(df.columns)}")

    # Leading/trailing whitespace is never meaningful in this export.
    unstripped_region = df["region"]
    df = df.apply(lambda column: column.str.strip())

    # Rows that are not order lines: the header repeated inside the data
    # and the totals row at the end of the export.
    stripped_labels = [label.strip() for label in raw_labels]
    is_header = (df == stripped_labels).all(axis=1)
    is_total = df["order_id"].str.upper() == "TOTAL"
    report["repeated_header_rows"] = int(is_header.sum())
    report["total_rows"] = int(is_total.sum())
    df = df[~(is_header | is_total)]

    # The same order line exported twice.
    is_duplicate = df.duplicated(keep="first")
    report["duplicate_rows"] = int(is_duplicate.sum())
    df = df[~is_duplicate]

    if df["order_id"].duplicated().any():
        conflicting = df.loc[df["order_id"].duplicated(keep=False), "order_id"]
        raise ValueError(
            f"Order IDs with conflicting lines: {sorted(set(conflicting))}"
        )

    # Region: one spelling per region ('west', 'EAST' -> 'West', 'East').
    region = df["region"].str.title()
    report["region_spelling_fixed"] = int((region != unstripped_region[df.index]).sum())
    df["region"] = region
    _require(df, df["region"] != "", "region is empty")

    # Quantity: a space is used as a thousands separator ('1 762').
    quantity = df["quantity"].str.replace(r"\s+", "", regex=True)
    report["quantity_thousands_separator"] = int((quantity != df["quantity"]).sum())
    _require(df, quantity.str.fullmatch(_INTEGER_RE), "quantity is not an integer")
    df["quantity"] = quantity.astype("int64")
    report["negative_quantity_kept"] = int((df["quantity"] < 0).sum())

    # Unit price: a decimal comma in some rows ('59,00'), missing in others.
    price = df["unit_price"].str.replace(",", ".", regex=False)
    report["unit_price_decimal_comma"] = int((price != df["unit_price"]).sum())
    is_missing = price == ""
    report["unit_price_missing_filled"] = int(is_missing.sum())
    _require(
        df,
        is_missing | price.str.fullmatch(_DECIMAL_RE),
        "unit price is not a number",
    )
    df["unit_price"] = pandas.to_numeric(price.where(~is_missing), errors="raise")
    df["unit_price"] = _fill_missing_prices(df)

    # Discount: empty means no discount.
    is_empty = df["discount"] == ""
    report["discount_empty_set_to_zero"] = int(is_empty.sum())
    _require(
        df,
        is_empty | df["discount"].str.fullmatch(_DECIMAL_RE),
        "discount is not a number",
    )
    df["discount"] = pandas.to_numeric(df["discount"].where(~is_empty, "0"))

    df["order_date"] = pandas.to_datetime(df["order_date"], format="%Y-%m-%d")
    df = df.reset_index(drop=True)

    report["clean_rows"] = len(df)
    return df, report


def _require(df: pandas.DataFrame, is_ok: pandas.Series, problem: str) -> None:
    is_ok = is_ok.astype(bool)
    if not is_ok.all():
        bad = df.loc[~is_ok, "order_id"].tolist()
        raise ValueError(f"Cannot clean {len(bad)} row(s), {problem}: {bad[:10]}")


def _fill_missing_prices(df: pandas.DataFrame) -> pandas.Series:
    """Fill a missing unit price with the price of the same product.

    This is only safe when the product has exactly one price in the rest of
    the file, so anything else is an error.
    """
    known = df.dropna(subset=["unit_price"])
    prices_per_product = known.groupby("product")["unit_price"].unique()
    missing = df["unit_price"].isna()
    for product in df.loc[missing, "product"].unique():
        prices = prices_per_product.get(product, [])
        if len(prices) != 1:
            raise ValueError(
                f"Cannot fill the unit price of {product!r}: "
                f"expected one known price, found {list(prices)}"
            )
    lookup = prices_per_product.map(lambda prices: prices[0])
    return df["unit_price"].fillna(df["product"].map(lookup))


def add_revenue(df: pandas.DataFrame) -> pandas.DataFrame:
    result = add_virtual_column(df, REVENUE_ROLE, "revenue")
    if result.empty and not df.empty:
        raise ValueError(f"Could not compute revenue with role {REVENUE_ROLE!r}")
    return result


def revenue_by_region(df: pandas.DataFrame) -> pandas.DataFrame:
    totals = df.groupby("region", as_index=False)["revenue"].sum()
    totals["revenue"] = totals["revenue"].round(2)
    return totals.sort_values("region").reset_index(drop=True)


def run(input_path=DEFAULT_INPUT, output_path=DEFAULT_OUTPUT):
    cleaned, report = clean(read_raw(input_path))
    totals = revenue_by_region(add_revenue(cleaned))
    totals.to_csv(output_path, index=False, float_format="%.2f", lineterminator="\n")
    return totals, report


def main(argv: list[str]) -> None:
    input_path = argv[1] if len(argv) > 1 else DEFAULT_INPUT
    output_path = argv[2] if len(argv) > 2 else DEFAULT_OUTPUT
    totals, report = run(input_path, output_path)
    print("Cleaning report (rows affected):")
    for problem, count in report.items():
        print(f"  {problem}: {count}")
    print(f"\nWrote {output_path}:")
    print(totals.to_string(index=False))


if __name__ == "__main__":
    main(sys.argv)
