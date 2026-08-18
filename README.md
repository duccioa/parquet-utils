# parquet-explorer

`parx` — a simple CLI to explore parquet and geoparquet files from the terminal.

Point it at a file to get a quick overview — metadata, per-column statistics,
a peek at the rows — or use it to convert files and aggregate points to H3
hexagons. Geoparquet files are detected automatically and geometry columns get
their own summary (CRS, geometry types, empty geometries).

## Installation

The project is managed with [pixi](https://pixi.sh):

```bash
pixi install
pixi run parx --help
```

Or install the package into any environment with pip:

```bash
pip install .
```

## Usage

### Summary

```bash
parx data.parquet
```

Prints:

- **File metadata** — format (parquet/geoparquet), number of rows and columns,
  row groups, file size, writer.
- **Numeric columns** — type, NAs, min, q25, median, mean, q75, max, sum.
- **String columns** — type, NAs, number of empty strings.
- **Other columns** (categorical, boolean, datetime, …) — type, NAs, number of
  distinct values, and the values themselves (a range if there are many).
- **Geometry columns** (geoparquet only, shown separately) — CRS, geometry
  types, NAs, number of empty geometries.

Group the numeric statistics by a column with `--groupby/-g` (skipped with a
warning if the column has more than 10 groups):

```bash
parx data.parquet --groupby region
```

`parx data.parquet` is a shortcut for `parx summary data.parquet`; bare `parx`
prints the help.

### Show rows

```bash
parx show data.parquet
```

By default prints the first and last 5 rows and the first and last 4 columns
(elided parts are marked with `…`).

| Option | Meaning |
| --- | --- |
| `--all-col` | print all columns |
| `--cols "col1,col2,'col 3'"` | only these columns; quote names with spaces or commas |
| `--cols "1,2,3,5,8"` | columns by 1-based index |
| `--head [N]` | only the first N rows (default 5) |
| `--tail [N]` | only the last N rows (default 5) |
| `--rows 5:10` | rows 5 to 10, 1-based and inclusive; open ends allowed (`:10`, `18:`) |

### Convert

```bash
parx data.parquet --output data.csv
```

The output format is detected from the suffix:

- parquet → `.csv` or `.xlsx`
- geoparquet → `.gpkg`
- geoparquet → `.csv` or `.xlsx` (geometry columns are dropped)

### Hexagon aggregation

Aggregate a point geoparquet file to [H3](https://h3geo.org) hexagons:

```bash
parx hex points.parquet --output hex.parquet --res 9
```

Numeric columns are summed by default; override per column with
`--aggr-fun "mycolumn1=mean, mycolumn2=sum"` (any pandas aggregation function
name works). The output is a geoparquet file of hexagon polygons in EPSG:4326
with the `h3` cell id, a `count` of input points, and the aggregated columns.
Input geometries must be points with a CRS; rows with missing or empty
geometries are ignored.

### Jenks classification

Add a Jenks natural breaks class column to a parquet file:

```bash
parx jenks data.parquet --column price
```

The breaks are computed over `--column/-c` on a random sample of the rows
(`--sample-size-perc`, default 0.1 = 10%) with `--class-num/-n` classes
(default 5). The result is stored in a `<column>_label` column — a sequence
number from low to high values followed by the class range, e.g.
`2 [134.1 - 362.3]`. An existing column of that name is overwritten.

The output goes to `<file>_labeled.parquet` by default; use `--output/-o` for
a different file or `--overwrite` to write back to the input file.

## Development

Create the dev environment and run the checks:

```bash
pixi install -e dev
pixi run -e dev pytest   # tests
pixi run -e dev ruff     # lint
pixi run -e dev ty       # type check
```

The package lives in `src/parquet_explorer/`:

- `cli.py` — rich-click CLI (`parx` entry point)
- `io.py` — parquet loading and geoparquet detection
- `summary.py` — file and column summaries
- `show.py` — row display
- `convert.py` — format conversion
- `hexagon.py` — H3 aggregation
- `jenks.py` — Jenks natural breaks classification
