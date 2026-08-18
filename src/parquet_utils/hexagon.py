"""Aggregate point geoparquet files to H3 hexagons."""

import geopandas as gpd
import h3
import pandas as pd
from shapely.geometry import Polygon

DEFAULT_AGGR = "sum"


def parse_aggr_fun(spec: str | None) -> dict[str, str]:
    """Parse an aggregation spec like ``"col1=mean, col2=sum"``."""
    if not spec:
        return {}
    functions: dict[str, str] = {}
    for part in spec.split(","):
        part = part.strip()
        if not part:
            continue
        column, sep, function = part.partition("=")
        if not sep or not column.strip() or not function.strip():
            raise ValueError(
                f"invalid aggregation '{part}': expected 'column=function', "
                'e.g. "mycolumn1=mean, mycolumn2=sum"'
            )
        functions[column.strip()] = function.strip()
    return functions


def hex_aggregate(gdf: gpd.GeoDataFrame, res: int, aggr_fun: str | None = None) -> gpd.GeoDataFrame:
    """Aggregate a point GeoDataFrame to H3 hexagons at resolution ``res``.

    Numeric columns are summed by default; ``aggr_fun`` overrides the function
    per column. Returns hexagon polygons in EPSG:4326 with an ``h3`` index column.
    """
    if gdf.crs is None:
        raise ValueError("the input file has no CRS, cannot compute H3 cells")
    gdf = gdf.to_crs(4326)

    valid = gdf.geometry.notna() & ~gdf.geometry.is_empty
    gdf = gdf.loc[valid]
    geom_types = set(gdf.geom_type.unique())
    if geom_types - {"Point"}:
        raise ValueError(
            f"only Point geometries can be aggregated to hexagons, found: "
            f"{', '.join(sorted(geom_types))}"
        )

    df = pd.DataFrame(gdf.drop(columns=gdf.geometry.name))
    numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c].dtype)]
    aggregations = {col: DEFAULT_AGGR for col in numeric_cols}
    for column, function in parse_aggr_fun(aggr_fun).items():
        if column not in df.columns:
            raise ValueError(f"aggregation column '{column}' not found in the file")
        aggregations[column] = function

    df["h3"] = [
        h3.latlng_to_cell(point.y, point.x, res) for point in gdf.geometry
    ]
    grouped = df.groupby("h3")
    result = grouped.agg(aggregations) if aggregations else pd.DataFrame(index=grouped.size().index)
    result.insert(0, "count", grouped.size())
    result = result.reset_index()

    hexagons = [
        Polygon([(lng, lat) for lat, lng in h3.cell_to_boundary(cell)])
        for cell in result["h3"]
    ]
    return gpd.GeoDataFrame(result, geometry=hexagons, crs=4326)
