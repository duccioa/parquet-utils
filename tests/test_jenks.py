import numpy as np
import pandas as pd
import pytest

from parquet_utils.cli import cli


@pytest.fixture
def values_parquet(tmp_path):
    rng = np.random.default_rng(3)
    df = pd.DataFrame(
        {
            "value": np.concatenate([rng.uniform(0, 100, 199), [np.nan]]),
            "name": [f"row{i}" for i in range(200)],
        }
    )
    path = tmp_path / "values.parquet"
    df.to_parquet(path)
    return path


def test_jenks_default_output(runner, values_parquet):
    result = runner.invoke(cli, ["jenks", str(values_parquet), "-c", "value"])
    assert result.exit_code == 0, result.output
    out_path = values_parquet.with_name("values_labeled.parquet")
    assert out_path.exists()
    out = pd.read_parquet(out_path)
    labels = out["value_label"]
    assert labels.dropna().nunique() == 5
    # low values get label 1, high values label 5
    assert labels[out["value"].idxmin()].startswith("1 [")
    assert labels[out["value"].idxmax()].startswith("5 [")
    # NA value gets NA label
    assert labels[out["value"].isna()].isna().all()
    # labels carry the class range
    assert all(label.count("[") == 1 for label in labels.dropna().unique())


def test_jenks_class_num(runner, values_parquet):
    result = runner.invoke(cli, ["jenks", str(values_parquet), "-c", "value", "-n", "3"])
    assert result.exit_code == 0, result.output
    out = pd.read_parquet(values_parquet.with_name("values_labeled.parquet"))
    assert out["value_label"].dropna().nunique() == 3


def test_jenks_custom_output(runner, values_parquet, tmp_path):
    output = tmp_path / "custom.parquet"
    result = runner.invoke(
        cli, ["jenks", str(values_parquet), "-c", "value", "-o", str(output)]
    )
    assert result.exit_code == 0, result.output
    assert output.exists()


def test_jenks_overwrite(runner, values_parquet):
    result = runner.invoke(cli, ["jenks", str(values_parquet), "-c", "value", "--overwrite"])
    assert result.exit_code == 0, result.output
    out = pd.read_parquet(values_parquet)
    assert "value_label" in out.columns


def test_jenks_overwrite_conflicts_with_output(runner, values_parquet, tmp_path):
    result = runner.invoke(
        cli,
        ["jenks", str(values_parquet), "-c", "value", "--overwrite", "-o", str(tmp_path / "x.parquet")],
    )
    assert result.exit_code != 0


def test_jenks_replaces_existing_label_column(runner, tmp_path):
    df = pd.DataFrame({"value": range(100), "value_label": ["old"] * 100})
    path = tmp_path / "labeled.parquet"
    df.to_parquet(path)
    result = runner.invoke(cli, ["jenks", str(path), "-c", "value"])
    assert result.exit_code == 0, result.output
    out = pd.read_parquet(path.with_name("labeled_labeled.parquet"))
    assert "old" not in set(out["value_label"])


def test_jenks_non_numeric_column_fails(runner, values_parquet):
    result = runner.invoke(cli, ["jenks", str(values_parquet), "-c", "name"])
    assert result.exit_code != 0
    assert "not numeric" in result.output


def test_jenks_missing_column_fails(runner, values_parquet):
    result = runner.invoke(cli, ["jenks", str(values_parquet), "-c", "nope"])
    assert result.exit_code != 0
    assert "not found" in result.output


def test_jenks_too_few_distinct_values_fails(runner, tmp_path):
    df = pd.DataFrame({"value": [1.0, 2.0, 3.0] * 10})
    path = tmp_path / "few.parquet"
    df.to_parquet(path)
    result = runner.invoke(cli, ["jenks", str(path), "-c", "value"])
    assert result.exit_code != 0
    assert "distinct values" in result.output
