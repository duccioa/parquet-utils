"""Classify a column into Jenks natural breaks classes."""

import itertools

import jenkspy
import numpy as np
import pandas as pd

from parquet_utils.summary import _fmt

LABEL_SUFFIX = "_label"
SAMPLE_SEED = 0


def add_jenks_labels(
    df: pd.DataFrame, column: str, class_num: int = 5, sample_frac: float = 0.1
) -> tuple[str, int]:
    """Add a ``<column>_label`` column with Jenks classes to ``df`` in place.

    Breaks are computed on a random sample of ``sample_frac`` of the non-NA
    values (deterministic seed). Labels are a sequence number from low to high
    followed by the class range, e.g. ``2 [134.1 - 362.3]``. An existing label
    column is overwritten; NA values get an NA label.

    Returns the label column name and the number of classes used.
    """
    if column not in df.columns:
        raise ValueError(f"column '{column}' not found in the file")
    series = df[column]
    if not pd.api.types.is_numeric_dtype(series.dtype):
        raise ValueError(f"column '{column}' is not numeric ({series.dtype})")
    values = series.dropna()
    if values.nunique() <= class_num:
        raise ValueError(
            f"column '{column}' has only {values.nunique()} distinct values, "
            f"cannot build {class_num} classes"
        )

    n_sample = min(max(round(len(values) * sample_frac), class_num + 1), len(values))
    sample = values.sample(n=n_sample, random_state=SAMPLE_SEED)
    if sample.nunique() <= class_num:
        sample = values

    breaks = sorted(set(jenkspy.jenks_breaks(sample.to_numpy(), n_classes=class_num)))
    labels = [
        f"{i} [{_fmt(lower)} - {_fmt(upper)}]"
        for i, (lower, upper) in enumerate(itertools.pairwise(breaks), start=1)
    ]
    # open outer bins so values outside the sampled range still get a class
    bins = [-np.inf, *breaks[1:-1], np.inf]
    label_column = column + LABEL_SUFFIX
    df[label_column] = pd.cut(series, bins=bins, labels=labels)
    return label_column, len(labels)
