import geopandas as gpd
import pytest

from parquet_utils.cli import cli
from parquet_utils.hexagon import parse_aggr_fun


def test_parse_aggr_fun():
    assert parse_aggr_fun(None) == {}
    assert parse_aggr_fun("a=mean, b=sum") == {"a": "mean", "b": "sum"}


def test_parse_aggr_fun_invalid():
    with pytest.raises(ValueError, match="column=function"):
        parse_aggr_fun("a")


def test_hex_aggregates_nearby_points(runner, geo_parquet, tmp_path):
    output = tmp_path / "hex.parquet"
    result = runner.invoke(cli, ["hex", str(geo_parquet), "-o", str(output), "-r", "5"])
    assert result.exit_code == 0, result.output
    hexes = gpd.read_parquet(output)
    # the two points near (0.1, 51.5) share a cell at resolution 5
    assert len(hexes) == 2
    assert set(hexes["count"]) == {1, 2}
    assert sorted(hexes["value"]) == [3.0, 4.0]
    assert set(hexes.geom_type) == {"Polygon"}
    assert hexes.crs.to_epsg() == 4326


def test_hex_custom_aggregation(runner, geo_parquet, tmp_path):
    output = tmp_path / "hex.parquet"
    result = runner.invoke(
        cli,
        ["hex", str(geo_parquet), "-o", str(output), "-r", "5", "--aggr-fun", "value=mean"],
    )
    assert result.exit_code == 0, result.output
    hexes = gpd.read_parquet(output)
    assert sorted(hexes["value"]) == [1.5, 4.0]


def test_hex_unknown_column_fails(runner, geo_parquet, tmp_path):
    result = runner.invoke(
        cli,
        ["hex", str(geo_parquet), "-o", str(tmp_path / "h.parquet"), "--aggr-fun", "nope=mean"],
    )
    assert result.exit_code != 0
    assert "not found" in result.output


def test_hex_rejects_plain_parquet(runner, plain_parquet, tmp_path):
    result = runner.invoke(cli, ["hex", str(plain_parquet), "-o", str(tmp_path / "h.parquet")])
    assert result.exit_code != 0
    assert "not a geoparquet" in result.output
