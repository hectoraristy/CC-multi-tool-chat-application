from __future__ import annotations

import io
import json
import logging
from typing import Literal

import pandas as pd
from langchain_core.tools import tool
from tools.file_source import _read_raw

logger = logging.getLogger(__name__)

MAX_RESULT_ROWS = 100


def _load_csv(path: str) -> pd.DataFrame:
    raw = _read_raw(path)
    return pd.read_csv(io.StringIO(raw))


def _describe_csv(df: pd.DataFrame) -> str:
    lines = [
        f"Rows: {len(df)}, Columns: {len(df.columns)}",
        f"Columns: {', '.join(df.columns.tolist())}",
        "",
        "Dtypes:",
        df.dtypes.to_string(),
        "",
        "Numeric summary:",
        df.describe(include="number").to_string(),
    ]
    non_numeric = df.select_dtypes(exclude="number")
    if not non_numeric.empty:
        lines += ["", "Non-numeric summary:", non_numeric.describe().to_string()]
    return "\n".join(lines)


def _head_tail(df: pd.DataFrame, which: str, limit: int) -> str:
    subset = df.head(limit) if which == "head" else df.tail(limit)
    return f"Showing {len(subset)} of {len(df)} rows:\n{subset.to_string(index=False)}"


def _aggregate(df: pd.DataFrame, column: str, function: str, group_by: str) -> str:
    if column and column not in df.columns:
        return f"Column '{column}' not found. Available: {', '.join(df.columns.tolist())}"
    if group_by and group_by not in df.columns:
        return f"Group-by column '{group_by}' not found. Available: {', '.join(df.columns.tolist())}"

    allowed_funcs = {"sum", "mean", "count", "min", "max", "std", "median", "nunique"}
    if function not in allowed_funcs:
        return f"Unknown function '{function}'. Allowed: {', '.join(sorted(allowed_funcs))}"

    try:
        if group_by:
            grouped = df.groupby(group_by)
            if column:
                result = grouped[column].agg(function)
            else:
                result = grouped.agg(function)
        elif column:
            result = df[column].agg(function)
        else:
            result = df.select_dtypes(include="number").agg(function)

        if isinstance(result, (pd.DataFrame, pd.Series)):
            return f"{function}({column or 'all numeric'}):\n{result.to_string()}\n\n({len(df)} rows evaluated)"
        return f"{function}({column or 'all numeric'}): {result}\n({len(df)} rows evaluated)"
    except Exception as exc:
        return f"Aggregation error: {exc}"


def _query_csv(df: pd.DataFrame, filter_expr: str, limit: int) -> str:
    try:
        filtered = df.query(filter_expr)
    except Exception as exc:
        return f"Query error: {exc}\nAvailable columns: {', '.join(df.columns.tolist())}"
    total = len(filtered)
    subset = filtered.head(limit)
    result = subset.to_string(index=False)
    if total > limit:
        result += f"\n\n[Showing {limit} of {total} matching rows]"
    else:
        result += f"\n\n[{total} matching rows]"
    return result


def _value_counts(df: pd.DataFrame, column: str, limit: int) -> str:
    if column not in df.columns:
        return f"Column '{column}' not found. Available: {', '.join(df.columns.tolist())}"
    vc = df[column].value_counts().head(limit)
    return f"Value counts for '{column}' (top {limit}):\n{vc.to_string()}\n\n({df[column].nunique()} unique values total)"


def _search_csv(df: pd.DataFrame, search_text: str, limit: int) -> str:
    mask = df.astype(str).apply(lambda col: col.str.contains(search_text, case=False, na=False)).any(axis=1)
    matches = df[mask]
    total = len(matches)
    subset = matches.head(limit)
    if total == 0:
        return f"No rows contain '{search_text}'."
    result = subset.to_string(index=False)
    if total > limit:
        result += f"\n\n[Showing {limit} of {total} matching rows]"
    else:
        result += f"\n\n[{total} matching rows]"
    return result


def _describe_json(data: object) -> str:
    if isinstance(data, dict):
        lines = [f"JSON object with {len(data)} keys:"]
        for k, v in list(data.items())[:50]:
            vtype = type(v).__name__
            if isinstance(v, list):
                vtype = f"array[{len(v)}]"
            elif isinstance(v, dict):
                vtype = f"object({len(v)} keys)"
            elif isinstance(v, str):
                vtype = f"string({len(v)} chars)"
            lines.append(f"  {k}: {vtype}")
        return "\n".join(lines)
    if isinstance(data, list):
        lines = [f"JSON array with {len(data)} items."]
        if data:
            first = data[0]
            if isinstance(first, dict):
                lines.append(f"Item structure (first element): {', '.join(first.keys())}")
        return "\n".join(lines)
    return f"JSON value: {type(data).__name__}"


def _search_json(data: object, search_text: str, limit: int) -> str:
    matches: list[str] = []
    lower_search = search_text.lower()

    def _walk(obj: object, path: str) -> None:
        if len(matches) >= limit:
            return
        if isinstance(obj, dict):
            for k, v in obj.items():
                _walk(v, f"{path}.{k}")
        elif isinstance(obj, list):
            for i, v in enumerate(obj):
                _walk(v, f"{path}[{i}]")
        elif isinstance(obj, str) and lower_search in obj.lower():
            matches.append(f"{path}: {obj[:200]}")
        elif lower_search in str(obj).lower():
            matches.append(f"{path}: {obj}")

    _walk(data, "$")
    if not matches:
        return f"No matches for '{search_text}'."
    return f"Found {len(matches)} matches:\n" + "\n".join(matches)


@tool
def data_analysis(
    path: str,
    operation: Literal["describe", "head", "tail", "aggregate", "query", "value_counts", "search"] = "describe",
    column: str = "",
    function: str = "sum",
    group_by: str = "",
    filter_expr: str = "",
    search_text: str = "",
    limit: int = 20,
) -> str:
    """Analyze a CSV or JSON file server-side and return computed results.

    Use this tool for analytical queries on large files (sums, averages, filtering,
    searching, etc.) instead of reading the full file into context.

    Supports local file paths and S3 URIs (s3://bucket/key).

    Operations:
      - describe: column names, dtypes, row count, basic stats
      - head / tail: first or last N rows (set limit)
      - aggregate: apply function (sum/mean/count/min/max/std/median/nunique) to a column,
                   optionally grouped by another column
      - query: filter rows with a pandas query expression (e.g. "price > 100")
      - value_counts: unique value distribution for a column
      - search: find rows (CSV) or values (JSON) containing search_text
    """
    lower = path.lower()
    try:
        if lower.endswith(".csv"):
            return _handle_csv(path, operation, column, function, group_by, filter_expr, search_text, limit)
        if lower.endswith(".json"):
            return _handle_json(path, operation, column, function, group_by, filter_expr, search_text, limit)
        return f"Unsupported file type for analysis. Supported: .csv, .json"
    except FileNotFoundError as exc:
        return f"File not found: {exc}"
    except Exception as exc:
        logger.exception("data_analysis error for %s", path)
        return f"Analysis error: {exc}"


def _handle_csv(
    path: str,
    operation: str,
    column: str,
    function: str,
    group_by: str,
    filter_expr: str,
    search_text: str,
    limit: int,
) -> str:
    df = _load_csv(path)

    if operation == "describe":
        return _describe_csv(df)
    if operation in ("head", "tail"):
        return _head_tail(df, operation, limit)
    if operation == "aggregate":
        if not column:
            return _aggregate(df, "", function, group_by)
        return _aggregate(df, column, function, group_by)
    if operation == "query":
        if not filter_expr:
            return "Error: filter_expr is required for query operation."
        return _query_csv(df, filter_expr, limit)
    if operation == "value_counts":
        if not column:
            return "Error: column is required for value_counts operation."
        return _value_counts(df, column, limit)
    if operation == "search":
        if not search_text:
            return "Error: search_text is required for search operation."
        return _search_csv(df, search_text, limit)

    return f"Unknown operation '{operation}' for CSV files."


def _handle_json(
    path: str,
    operation: str,
    column: str,
    function: str,
    group_by: str,
    filter_expr: str,
    search_text: str,
    limit: int,
) -> str:
    raw = _read_raw(path)
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        return f"Invalid JSON: {exc}"

    if operation == "describe":
        return _describe_json(data)
    if operation == "search":
        if not search_text:
            return "Error: search_text is required for search operation."
        return _search_json(data, search_text, limit)

    if isinstance(data, list) and data and isinstance(data[0], dict):
        df = pd.DataFrame(data)
        return _handle_csv_df_operations(df, operation, column, function, group_by, filter_expr, search_text, limit)

    return f"Operation '{operation}' is only supported for CSV files or JSON arrays of objects."


def _handle_csv_df_operations(
    df: pd.DataFrame,
    operation: str,
    column: str,
    function: str,
    group_by: str,
    filter_expr: str,
    search_text: str,
    limit: int,
) -> str:
    """Route operations for a DataFrame already loaded (used for JSON arrays of objects)."""
    if operation in ("head", "tail"):
        return _head_tail(df, operation, limit)
    if operation == "aggregate":
        return _aggregate(df, column, function, group_by)
    if operation == "query":
        if not filter_expr:
            return "Error: filter_expr is required for query operation."
        return _query_csv(df, filter_expr, limit)
    if operation == "value_counts":
        if not column:
            return "Error: column is required for value_counts operation."
        return _value_counts(df, column, limit)
    if operation == "search":
        return _search_csv(df, search_text, limit)
    return f"Unknown operation '{operation}'."
