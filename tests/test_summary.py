from parquet_explorer.cli import cli


def test_no_args_shows_help(runner):
    result = runner.invoke(cli, [])
    assert result.exit_code == 0
    assert "Usage" in result.output
    assert "hex" in result.output


def test_file_argument_routes_to_summary(runner, plain_parquet):
    result = runner.invoke(cli, [str(plain_parquet)])
    assert result.exit_code == 0, result.output
    assert "Rows" in result.output
    assert "Numeric columns" in result.output
    assert "String columns" in result.output
    assert "ints" in result.output
    assert "words" in result.output


def test_summary_reports_parquet_format(runner, plain_parquet):
    result = runner.invoke(cli, ["summary", str(plain_parquet)])
    assert result.exit_code == 0, result.output
    assert "parquet" in result.output
    assert "geoparquet" not in result.output


def test_geo_summary_has_geometry_section(runner, geo_parquet):
    result = runner.invoke(cli, [str(geo_parquet)])
    assert result.exit_code == 0, result.output
    assert "geoparquet" in result.output
    assert "Geometry columns" in result.output
    assert "EPSG:4326" in result.output
    assert "Point" in result.output


def test_groupby(runner, plain_parquet):
    result = runner.invoke(cli, [str(plain_parquet), "--groupby", "group"])
    assert result.exit_code == 0, result.output
    assert "grouped by 'group'" in result.output


def test_groupby_skipped_when_too_many_groups(runner, many_groups_parquet):
    result = runner.invoke(cli, [str(many_groups_parquet), "-g", "group"])
    assert result.exit_code == 0, result.output
    assert "Skipping groupby" in result.output


def test_groupby_missing_column_fails(runner, plain_parquet):
    result = runner.invoke(cli, [str(plain_parquet), "-g", "nope"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_missing_file_fails(runner, tmp_path):
    result = runner.invoke(cli, [str(tmp_path / "nope.parquet")])
    assert result.exit_code != 0
