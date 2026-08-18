"""Pretty-print rows of a parquet file."""

import re
import shlex

import pandas as pd
from rich.console import Console
from rich.table import Table

from parquet_utils.summary import _fmt

DEFAULT_N = 5
EDGE_COLS = 4
ELLIPSIS = "…"

Segment = tuple[range, pd.DataFrame]


def _parse_cols(spec: str, df: pd.DataFrame) -> list[str]:
    """Parse a column spec: names (quotes allowed) or 1-based indices."""
    lexer = shlex.shlex(spec, posix=True)
    lexer.whitespace = ","
    lexer.whitespace_split = True
    tokens = [token.strip() for token in lexer if token.strip()]
    if not tokens:
        raise ValueError("--cols is empty")
    if all(re.fullmatch(r"\d+", token) for token in tokens):
        columns = []
        for token in tokens:
            index = int(token)
            if not 1 <= index <= df.shape[1]:
                raise ValueError(f"column index {index} out of range (1-{df.shape[1]})")
            columns.append(str(df.columns[index - 1]))
        return columns
    missing = [token for token in tokens if token not in df.columns]
    if missing:
        raise ValueError(f"columns not found: {', '.join(missing)}")
    return tokens


def _parse_rows(spec: str, n_rows: int) -> tuple[int, int]:
    """Parse a row range like ``5:10`` (1-based, inclusive; open ends allowed)."""
    match = re.fullmatch(r"\s*(\d*)\s*:\s*(\d*)\s*", spec)
    if not match or (not match.group(1) and not match.group(2)):
        raise ValueError(f"invalid --rows '{spec}': expected START:STOP, e.g. 5:10")
    start = int(match.group(1)) if match.group(1) else 1
    stop = int(match.group(2)) if match.group(2) else n_rows
    if start < 1 or stop < start:
        raise ValueError(f"invalid --rows '{spec}': need 1 <= START <= STOP")
    return start, min(stop, n_rows)


def _row_segments(
    df: pd.DataFrame, head: int | None, tail: int | None, rows: str | None
) -> list[Segment | None]:
    """Pick the rows to display as segments; ``None`` marks an elided gap."""
    n_rows = len(df)
    if rows is not None:
        start, stop = _parse_rows(rows, n_rows)
        return [(range(start, stop + 1), df.iloc[start - 1 : stop])]
    if head is not None and tail is None:
        h = min(head, n_rows)
        return [(range(1, h + 1), df.head(h))]
    if tail is not None and head is None:
        t = min(tail, n_rows)
        return [(range(n_rows - t + 1, n_rows + 1), df.tail(t))]
    h = head if head is not None else DEFAULT_N
    t = tail if tail is not None else DEFAULT_N
    if h + t >= n_rows:
        return [(range(1, n_rows + 1), df)]
    return [
        (range(1, h + 1), df.head(h)),
        None,
        (range(n_rows - t + 1, n_rows + 1), df.tail(t)),
    ]


def print_show(
    df: pd.DataFrame,
    all_col: bool = False,
    cols: str | None = None,
    head: int | None = None,
    tail: int | None = None,
    rows: str | None = None,
    console: Console | None = None,
) -> None:
    """Print rows of ``df`` as a rich table."""
    console = console or Console()
    if all_col and cols:
        raise ValueError("--all-col and --cols cannot be combined")
    if rows is not None and (head is not None or tail is not None):
        raise ValueError("--rows cannot be combined with --head or --tail")

    cols_elided = False
    if cols:
        columns = _parse_cols(cols, df)
    elif all_col or df.shape[1] <= 2 * EDGE_COLS:
        columns = [str(c) for c in df.columns]
    else:
        columns = [str(c) for c in df.columns[:EDGE_COLS]] + [
            str(c) for c in df.columns[-EDGE_COLS:]
        ]
        cols_elided = True

    segments = _row_segments(df, head, tail, rows)

    headers = columns[:EDGE_COLS] + [ELLIPSIS] + columns[EDGE_COLS:] if cols_elided else columns
    table = Table(caption=f"{len(df):,} rows × {df.shape[1]:,} columns")
    table.add_column("#", style="dim", justify="right")
    for name in headers:
        table.add_column(name, overflow="ellipsis", max_width=40)

    for segment in segments:
        if segment is None:
            table.add_row(*[ELLIPSIS] * (len(headers) + 1))
            continue
        positions, frame = segment
        for position, (_, row) in zip(positions, frame.iterrows()):
            values = [_fmt(row[column]) for column in columns]
            if cols_elided:
                values = values[:EDGE_COLS] + [ELLIPSIS] + values[EDGE_COLS:]
            table.add_row(str(position), *values)
    console.print(table)
