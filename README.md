# Virtual columns in a pandas DataFrame

- `solution.py` - `add_virtual_column` (Part 1)
- `pipeline.py` - cleans `sales.csv` and writes `revenue_by_region.csv` (Part 2)
- `test_solution.py`, `test_pipeline.py` - my tests; `test_virtual_column.py` - sample tests

## Setup and usage

Python 3.10 or newer.

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt

python pipeline.py               # writes revenue_by_region.csv
pytest                           # runs all tests
```

## Assumptions (Part 1)

- The example in the task shows the new column as `price_total` although
  `"total"` was passed. I treat it as a typo: the column is named exactly
  `new_column`.
- `new_column` and the labels used in `role` must consist only of ASCII
  letters and underscores. Other columns of `df` are not checked.
- A role is `label (operator label)*` with `+`, `-`, `*` and optional
  whitespace. Numbers and parentheses are not supported. `*` is done before
  `+` and `-`.
- Incorrect input returns an empty DataFrame. This includes a column that is
  missing or not numeric.
- If `new_column` already exists, it is overwritten. The input DataFrame is
  not modified.

## Problems found in `sales.csv` (Part 2)

The file has 1507 rows after the header.

| Problem | Rows | Handling |
| --- | ---: | --- |
| Header label `Quantity ` has a trailing space | 1 label | Labels stripped and renamed to snake_case |
| Header row repeated inside the data | 1 | Removed |
| `TOTAL` row at the end | 1 | Removed |
| Order lines exported twice (identical rows) | 5 | Copy removed |
| Region spelled in different ways (` South`, `EAST`, `west  `) | 15 | Stripped, title case |
| Quantity with a space as thousands separator (`1 762`) | 4 | Read as 1762 |
| Negative quantity | 6 | Kept as a return (negative revenue) |
| Unit price with a decimal comma (`59,00`) | 7 | Comma replaced by a dot |
| Unit price missing | 4 | Filled with the price of the same product |
| Discount empty | 959 (963 with the copies) | Set to 0 |

After cleaning there are 1500 order lines, one per order ID. No order line
is dropped.

### Decisions

- **`1 762` is 1762.** These four rows are far above the other quantities
  (1 to 40) and add about 324,000 to the revenue. I keep them because the
  quantity in the `TOTAL` row (37150) only matches when they are read this
  way.
- **Negative quantities are returns.** They reduce revenue by 913.00 in
  total. The `TOTAL` row also counts them with their sign.
- **Missing unit price.** Each product has exactly one price in the file, so
  the price can be taken from the product. If it could not, the pipeline
  stops with an error.
- **Duplicates.** Order IDs are otherwise unique, so identical rows with the
  same ID are one line exported twice.
- A value that cannot be fixed raises an error with the order IDs, it is not
  dropped silently.
- Revenue is rounded to 2 decimals after summing.
