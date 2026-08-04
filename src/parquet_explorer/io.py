"""Reading parquet files and detecting geoparquet."""

from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq


def is_geoparquet(path: Path) -> bool:
    """A file is geoparquet if its schema carries the ``geo`` metadata key."""
    metadata = pq.read_schema(path).metadata or {}
    return b"geo" in metadata


def load_parquet(path: Path) -> tuple[pd.DataFrame, bool]:
    """Load a parquet file, as a GeoDataFrame when it is geoparquet.

    Returns the frame and a flag telling whether it is geoparquet.
    """
    if is_geoparquet(path):
        import geopandas as gpd

        return gpd.read_parquet(path), True
    return pd.read_parquet(path), False
