# News

## Unreleased

### Fixed

- The summary silently omitted columns that were neither numeric, string nor
  geometry — categorical (such as the `jenks` label column), boolean and
  datetime columns simply did not appear. They are now listed in a new
  **Other columns** table with type, NAs, distinct values and the values
  themselves.

- New `parx jenks <file> -c COLUMN` command: adds a `<column>_label` column
  with Jenks natural breaks classes, computed on a random sample of the rows
  (`--sample-size-perc`, default 10%) with `--class-num/-n` classes
  (default 5). Labels are a sequence number from low to high with the class
  range, e.g. `2 [134.1 - 362.3]`. Output defaults to
  `<file>_labeled.parquet`; `--output/-o` picks another file and
  `--overwrite` writes back to the input.

## 0.1.0 (2026-08-04)

First release of `parx`, a CLI to explore parquet and geoparquet files.

### Features

- `parx <file>` / `parx summary <file>`: file summary with metadata (format,
  rows, columns, row groups, file size, writer) and per-column statistics —
  numeric columns (NAs, min, q25, median, mean, q75, max, sum), string columns
  (NAs, empty strings) and, for geoparquet, a separate geometry summary
  (CRS, geometry types, NAs, empty geometries). Geoparquet files are detected
  automatically.
- `--groupby/-g COLUMN`: numeric statistics grouped by a column, skipped with
  a warning above 10 groups.
- `parx show <file>`: row display with first/last 4 columns and first/last
  5 rows by default; `--all-col`, `--cols` (names or 1-based indices),
  `--head [N]`, `--tail [N]` and `--rows START:STOP` (1-based, inclusive).
- `--output/-o <file>`: conversion detected from the output suffix — parquet
  to `.csv`/`.xlsx`, geoparquet to `.gpkg`, geoparquet to `.csv`/`.xlsx` with
  geometry columns dropped.
- `parx hex <file> -o <out> -r RES`: aggregation of point geoparquet files to
  H3 hexagons; numeric columns summed by default, per-column override with
  `--aggr-fun "col1=mean, col2=sum"`, plus a `count` column. Output is a
  geoparquet of hexagon polygons in EPSG:4326.

### Development

- pixi-managed environments with a `dev` feature and tasks: `pytest`, `ruff`
  and `ty`.
