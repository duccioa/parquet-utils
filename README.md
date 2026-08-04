# parquet-explorer

`parx` — a simple CLI to explore parquet and geoparquet files.

## Usage

```bash
parx                                   # show help
parx data.parquet                      # summary: metadata + per-column stats
parx data.parquet --groupby region     # numeric stats grouped by a column (max 10 groups)
parx data.parquet -o data.csv          # convert (parquet -> .csv/.xlsx, geoparquet -> .gpkg;
                                       # geoparquet -> .csv/.xlsx drops the geometry)
parx hex points.parquet -o hex.parquet -r 9                   # aggregate points to H3 hexagons (sum)
parx hex points.parquet -o hex.parquet -r 9 --aggr-fun "a=mean, b=sum"
```

Geoparquet files are detected automatically; geometry columns are summarised
separately (CRS, geometry types, empty geometries).

## Development

The environment is managed with [pixi](https://pixi.sh):

```bash
pixi install -e dev
pixi run -e dev pytest   # tests
pixi run -e dev ruff     # lint
pixi run -e dev ty       # type check
```
