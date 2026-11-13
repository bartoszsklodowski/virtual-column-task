"""Part 1: add a calculated ("virtual") column to a pandas DataFrame."""

import re

import pandas

_LABEL = r"[A-Za-z_]+"
_OPERATOR = r"[-+*]"
_LABEL_RE = re.compile(_LABEL)
# A role is: label (operator label)*, with optional whitespace around tokens.
_ROLE_RE = re.compile(rf"\s*{_LABEL}(?:\s*{_OPERATOR}\s*{_LABEL})*\s*")
_TOKEN_RE = re.compile(rf"{_LABEL}|{_OPERATOR}")


def _is_valid_label(label: object) -> bool:
    return isinstance(label, str) and _LABEL_RE.fullmatch(label) is not None


def add_virtual_column(df: pandas.DataFrame, role: str, new_column: str) -> pandas.DataFrame:
    """Return a copy of ``df`` with ``new_column`` computed from ``role``.

    ``role`` is an expression built from column labels and the operators
    ``+``, ``-`` and ``*`` (``*`` binds tighter than ``+`` and ``-``), for
    example ``"quantity * price - discount"``.

    An empty DataFrame is returned when the input is incorrect: a label that
    is not made only of letters and underscores, a malformed role, or a role
    that uses a column which is missing, ambiguous or not numeric.
    The input DataFrame is never modified.
    """
    empty = pandas.DataFrame([])

    if not isinstance(df, pandas.DataFrame):
        return empty
    if not _is_valid_label(new_column):
        return empty
    if not isinstance(role, str) or _ROLE_RE.fullmatch(role) is None:
        return empty

    tokens = _TOKEN_RE.findall(role)
    labels, operators = tokens[0::2], tokens[1::2]

    operands = []
    for label in labels:
        if label not in df.columns:
            return empty
        column = df[label]
        # Duplicated labels give a DataFrame here: the role is ambiguous.
        if not isinstance(column, pandas.Series):
            return empty
        if not pandas.api.types.is_numeric_dtype(column):
            return empty
        operands.append(column)

    # First pass: fold multiplications into terms, so that "*" has
    # precedence. Second pass: add and subtract the terms left to right.
    terms = [operands[0]]
    signs = []
    for operator, operand in zip(operators, operands[1:]):
        if operator == "*":
            terms[-1] = terms[-1] * operand
        else:
            signs.append(operator)
            terms.append(operand)

    values = terms[0]
    for sign, term in zip(signs, terms[1:]):
        values = values + term if sign == "+" else values - term

    result = df.copy()
    result[new_column] = values
    return result
