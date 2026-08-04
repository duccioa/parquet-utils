import geopandas as gpd
import pandas as pd

from parquet_explorer.cli import cli


def test_parquet_to_csv(runner, plain_parquet, tmp_path):
    output = tmp_path / "out.csv"
    result = runner.invoke(cli, [str(plain_parquet), "-o", str(output)])
    assert result.exit_code == 0, result.output
    round_trip = pd.read_csv(output)
    assert list(round_trip.columns) == ["ints", "floats", "words", "group"]
    assert len(round_trip) == 4


def test_parquet_to_excel(runner, plain_parquet, tmp_path):
    output = tmp_path / "out.xlsx"
    result = runner.invoke(cli, [str(plain_parquet), "--output", str(output)])
    assert result.exit_code == 0, result.output
    round_trip = pd.read_excel(output)
    assert len(round_trip) == 4


def test_geoparquet_to_gpkg(runner, geo_parquet, tmp_path):
    output = tmp_path / "out.gpkg"
    result = runner.invoke(cli, [str(geo_parquet), "-o", str(output)])
    assert result.exit_code == 0, result.output
    round_trip = gpd.read_file(output)
    assert len(round_trip) == 3
    assert round_trip.crs.to_epsg() == 4326


def test_parquet_to_gpkg_fails(runner, plain_parquet, tmp_path):
    result = runner.invoke(cli, [str(plain_parquet), "-o", str(tmp_path / "out.gpkg")])
    assert result.exit_code != 0
    assert ".gpkg" in result.output


def test_geoparquet_to_csv_drops_geometry(runner, geo_parquet, tmp_path):
    output = tmp_path / "out.csv"
    result = runner.invoke(cli, [str(geo_parquet), "-o", str(output)])
    assert result.exit_code == 0, result.output
    assert "dropped geometry" in result.output
    round_trip = pd.read_csv(output)
    assert list(round_trip.columns) == ["value", "name"]
    assert len(round_trip) == 3


def test_geoparquet_to_excel_drops_geometry(runner, geo_parquet, tmp_path):
    output = tmp_path / "out.xlsx"
    result = runner.invoke(cli, [str(geo_parquet), "-o", str(output)])
    assert result.exit_code == 0, result.output
    round_trip = pd.read_excel(output)
    assert "geometry" not in round_trip.columns
    assert len(round_trip) == 3


def test_unknown_suffix_fails(runner, plain_parquet, tmp_path):
    result = runner.invoke(cli, [str(plain_parquet), "-o", str(tmp_path / "out.json")])
    assert result.exit_code != 0
