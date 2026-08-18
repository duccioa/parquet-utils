"""Rich summaries of parquet files."""

from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from rich.console import Console
from rich.table import Table

MAX_GROUPS = 10
MAX_VALUES = 10

NUMERIC_STATS = ["NAs", "min", "q25", "median", "mean", "q75", "max", "sum"]


def _human_size(n_bytes: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n_bytes) < 1024 or unit == "TB":
            return f"{n_bytes:,.1f} {unit}" if unit != "B" else f"{n_bytes:,.0f} {unit}"
        n_bytes /= 1024
    return f"{n_bytes:,.1f} TB"


def _fmt(value: Any) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return "-"
    try:
        if pd.isna(value):
            return "-"
    except (TypeError, ValueError):
        pass
    if isinstance(value, (np.integer, np.floating, np.bool_)):
        value = value.item()
    if isinstance(value, bool):
        return str(value)
    if isinstance(value, int):
        return f"{value:,}"
    if isinstance(value, float):
        return f"{value:,.4g}"
    return str(value)


def _numeric_stats(series: pd.Series) -> dict[str, Any]:
    return {
        "NAs": int(series.isna().sum()),
        "min": series.min(),
        "q25": series.quantile(0.25),
        "median": series.median(),
        "mean": series.mean(),
        "q75": series.quantile(0.75),
        "max": series.max(),
        "sum": series.sum(),
    }


def _split_columns(df: pd.DataFrame) -> tuple[list[str], list[str], list[str], list[str]]:
    """Split column names into (geometry, numeric, string, other) groups.

    Every column lands in exactly one group, so nothing is left out of the
    summary: categorical, boolean and datetime columns fall into 'other'.
    """
    geometry, numeric, string, other = [], [], [], []
    for col in df.columns:
        dtype = df[col].dtype
        if str(dtype) == "geometry":
            geometry.append(col)
        elif isinstance(dtype, pd.CategoricalDtype):
            other.append(col)
        elif pd.api.types.is_numeric_dtype(dtype) and not pd.api.types.is_bool_dtype(dtype):
            numeric.append(col)
        elif pd.api.types.is_string_dtype(dtype) or dtype == object:
            string.append(col)
        else:
            other.append(col)
    return geometry, numeric, string, other


def _file_table(path: Path, df: pd.DataFrame, is_geo: bool) -> Table:
    meta = pq.read_metadata(path)
    table = Table(title=str(path), show_header=False, title_justify="left")
    table.add_column(style="bold cyan")
    table.add_column()
    table.add_row("Format", "geoparquet" if is_geo else "parquet")
    table.add_row("Rows", f"{meta.num_rows:,}")
    table.add_row("Columns", f"{len(df.columns):,}")
    table.add_row("Row groups", f"{meta.num_row_groups:,}")
    table.add_row("File size", _human_size(path.stat().st_size))
    table.add_row("Created by", meta.created_by or "-")
    return table


def _numeric_table(df: pd.DataFrame, columns: list[str]) -> Table:
    table = Table(title="Numeric columns", title_justify="left")
    table.add_column("Column", style="bold")
    table.add_column("Type")
    for stat in NUMERIC_STATS:
        table.add_column(stat, justify="right")
    for col in columns:
        stats = _numeric_stats(df[col])
        table.add_row(col, str(df[col].dtype), *(_fmt(stats[s]) for s in NUMERIC_STATS))
    return table


def _string_table(df: pd.DataFrame, columns: list[str]) -> Table:
    table = Table(title="String columns", title_justify="left")
    table.add_column("Column", style="bold")
    table.add_column("Type")
    table.add_column("NAs", justify="right")
    table.add_column("Empty strings", justify="right")
    for col in columns:
        series = df[col]
        table.add_row(
            col,
            str(series.dtype),
            f"{int(series.isna().sum()):,}",
            f"{int((series == '').sum()):,}",
        )
    return table


def _other_table(df: pd.DataFrame, columns: list[str]) -> Table:
    """Categorical, boolean, datetime and any other non-numeric columns."""
    table = Table(title="Other columns", title_justify="left")
    table.add_column("Column", style="bold")
    table.add_column("Type")
    table.add_column("NAs", justify="right")
    table.add_column("Unique", justify="right")
    table.add_column("Values", overflow="fold")
    for col in columns:
        series = df[col]
        if isinstance(series.dtype, pd.CategoricalDtype):
            uniques = list(series.cat.categories)
        else:
            uniques = sorted(series.dropna().unique())
        if len(uniques) <= MAX_VALUES:
            shown = ", ".join(_fmt(v) for v in uniques)
        else:
            shown = f"{_fmt(uniques[0])} … {_fmt(uniques[-1])}"
        table.add_row(
            col,
            str(series.dtype),
            f"{int(series.isna().sum()):,}",
            f"{len(uniques):,}",
            shown or "-",
        )
    return table


def _geometry_table(df: pd.DataFrame, columns: list[str]) -> Table:
    table = Table(title="Geometry columns", title_justify="left")
    table.add_column("Column", style="bold")
    table.add_column("CRS")
    table.add_column("Types")
    table.add_column("NAs", justify="right")
    table.add_column("Empty geoms", justify="right")
    for col in columns:
        series = df[col]
        crs = getattr(series, "crs", None)
        types = ", ".join(sorted(series.geom_type.dropna().unique())) or "-"
        table.add_row(
            col,
            crs.to_string() if crs is not None else "-",
            types,
            f"{int(series.isna().sum()):,}",
            f"{int(series.is_empty.sum()):,}",
        )
    return table


def _grouped_numeric_table(df: pd.DataFrame, groupby: str, columns: list[str]) -> Table:
    table = Table(title=f"Numeric columns grouped by '{groupby}'", title_justify="left")
    table.add_column(groupby, style="bold cyan")
    table.add_column("Column", style="bold")
    table.add_column("rows", justify="right")
    for stat in NUMERIC_STATS:
        table.add_column(stat, justify="right")
    for key, group in df.groupby(groupby, dropna=False):
        for col in columns:
            stats = _numeric_stats(group[col])
            table.add_row(
                _fmt(key),
                col,
                f"{len(group):,}",
                *(_fmt(stats[s]) for s in NUMERIC_STATS),
            )
        table.add_section()
    return table


def print_summary(
    path: Path,
    df: pd.DataFrame,
    is_geo: bool,
    groupby: str | None = None,
    console: Console | None = None,
) -> None:
    """Print the full summary of a parquet file to the console."""
    console = console or Console()
    geometry_cols, numeric_cols, string_cols, other_cols = _split_columns(df)

    console.print(_file_table(path, df, is_geo))
    if numeric_cols:
        console.print(_numeric_table(df, numeric_cols))
    if string_cols:
        console.print(_string_table(df, string_cols))
    if other_cols:
        console.print(_other_table(df, other_cols))
    if geometry_cols:
        console.print(_geometry_table(df, geometry_cols))

    if groupby is None:
        return
    if groupby not in df.columns:
        raise ValueError(f"groupby column '{groupby}' not found in the file")
    n_groups = df[groupby].nunique(dropna=False)
    if n_groups > MAX_GROUPS:
        console.print(
            f"[yellow]Skipping groupby: '{groupby}' has {n_groups} groups "
            f"(more than {MAX_GROUPS}).[/yellow]"
        )
        return
    grouped_cols = [c for c in numeric_cols if c != groupby]
    if not grouped_cols:
        console.print("[yellow]No numeric columns to group.[/yellow]")
        return
    console.print(_grouped_numeric_table(df, groupby, grouped_cols))
