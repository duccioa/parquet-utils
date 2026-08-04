import pytest

from parquet_explorer.cli import cli
from parquet_explorer.show import _parse_rows

WIDE_ENV = {"COLUMNS": "300"}


def invoke(runner, args):
    return runner.invoke(cli, args, env=WIDE_ENV)


def test_default_shows_edge_columns_and_rows(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet)])
    assert result.exit_code == 0, result.output
    # first 4 and last 4 columns, middle elided
    assert "c01" in result.output
    assert "c04" in result.output
    assert "c07" in result.output
    assert "my col" in result.output
    assert "c05" not in result.output
    assert "…" in result.output
    # first 5 and last 5 rows
    assert "r01c01" in result.output
    assert "r05c01" in result.output
    assert "r10c01" not in result.output
    assert "r16c01" in result.output
    assert "r20c01" in result.output
    assert "20 rows" in result.output


def test_all_col(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--all-col"])
    assert result.exit_code == 0, result.output
    assert "c05" in result.output
    assert "r01c05" in result.output


def test_cols_by_name_with_quotes(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--cols", "c02,'my col'"])
    assert result.exit_code == 0, result.output
    assert "r01c02" in result.output
    assert "r01cm" in result.output
    assert "r01c01" not in result.output


def test_cols_by_index(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--cols", "1,3"])
    assert result.exit_code == 0, result.output
    assert "r01c01" in result.output
    assert "r01c03" in result.output
    assert "r01c02" not in result.output


def test_cols_unknown_name_fails(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--cols", "nope"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_cols_index_out_of_range_fails(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--cols", "0,3"])
    assert result.exit_code != 0
    assert "out of range" in result.output


def test_head_with_value(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--head", "3"])
    assert result.exit_code == 0, result.output
    assert "r03c01" in result.output
    assert "r04c01" not in result.output
    assert "r20c01" not in result.output


def test_head_bare_defaults_to_five(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--head"])
    assert result.exit_code == 0, result.output
    assert "r05c01" in result.output
    assert "r06c01" not in result.output
    assert "r20c01" not in result.output


def test_tail(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--tail", "2"])
    assert result.exit_code == 0, result.output
    assert "r19c01" in result.output
    assert "r20c01" in result.output
    assert "r01c01" not in result.output


def test_head_and_tail_together(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--head", "2", "--tail", "2"])
    assert result.exit_code == 0, result.output
    assert "r02c01" in result.output
    assert "r19c01" in result.output
    assert "r10c01" not in result.output


def test_rows_range(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--rows", "5:10"])
    assert result.exit_code == 0, result.output
    assert "r05c01" in result.output
    assert "r10c01" in result.output
    assert "r04c01" not in result.output
    assert "r11c01" not in result.output


def test_rows_invalid_spec_fails(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--rows", "abc"])
    assert result.exit_code != 0
    assert "START:STOP" in result.output


def test_rows_conflicts_with_head(runner, wide_parquet):
    result = invoke(runner, ["show", str(wide_parquet), "--rows", "1:3", "--head", "2"])
    assert result.exit_code != 0


def test_parse_rows_open_ends():
    assert _parse_rows(":3", 20) == (1, 3)
    assert _parse_rows("18:", 20) == (18, 20)
    assert _parse_rows("5:100", 20) == (5, 20)
    with pytest.raises(ValueError, match="START"):
        _parse_rows("10:5", 20)
