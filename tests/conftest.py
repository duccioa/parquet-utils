from pathlib import Path

import geopandas as gpd
import pandas as pd
import pytest
from click.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def plain_parquet(tmp_path: Path) -> Path:
    df = pd.DataFrame(
        {
            "ints": [1, 2, 3, 4],
            "floats": [1.5, 2.5, None, 4.5],
            "words": ["x", "", None, "y"],
            "group": ["u", "u", "v", "v"],
        }
    )
    path = tmp_path / "plain.parquet"
    df.to_parquet(path)
    return path


@pytest.fixture
def many_groups_parquet(tmp_path: Path) -> Path:
    df = pd.DataFrame({"value": range(20), "group": [f"g{i}" for i in range(20)]})
    path = tmp_path / "many_groups.parquet"
    df.to_parquet(path)
    return path


@pytest.fixture
def wide_parquet(tmp_path: Path) -> Path:
    """20 rows, 10 columns (c01..c09 plus 'my col'), self-describing values."""
    n = 20
    data = {f"c{i:02d}": [f"r{r:02d}c{i:02d}" for r in range(1, n + 1)] for i in range(1, 10)}
    data["my col"] = [f"r{r:02d}cm" for r in range(1, n + 1)]
    path = tmp_path / "wide.parquet"
    pd.DataFrame(data).to_parquet(path)
    return path


@pytest.fixture
def geo_parquet(tmp_path: Path) -> Path:
    gdf = gpd.GeoDataFrame(
        {"value": [1.0, 2.0, 4.0], "name": ["a", "b", "c"]},
        geometry=gpd.points_from_xy([0.1, 0.1001, 10.0], [51.5, 51.5001, 45.0]),
        crs=4326,
    )
    path = tmp_path / "points.parquet"
    gdf.to_parquet(path)
    return path
