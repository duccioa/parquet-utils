"""Convert parquet files to other formats, detected from the output suffix."""

from pathlib import Path

import pandas as pd

PLAIN_FORMATS = {".csv", ".xlsx"}
GEO_FORMATS = {".gpkg"}


def convert(df: pd.DataFrame, is_geo: bool, output: Path) -> str | None:
    """Write ``df`` to ``output``: parquet -> csv/xlsx, geoparquet -> gpkg.

    A geoparquet written to csv/xlsx has its geometry columns dropped.
    Returns an optional note about the conversion.
    """
    suffix = output.suffix.lower()
    if suffix not in PLAIN_FORMATS | GEO_FORMATS:
        raise ValueError(
            f"cannot convert to '{suffix or '<no suffix>'}': "
            "supported outputs are .csv, .xlsx and .gpkg"
        )
    if suffix in GEO_FORMATS and not is_geo:
        raise ValueError("only geoparquet files can be converted to .gpkg")

    output.parent.mkdir(parents=True, exist_ok=True)
    if suffix in GEO_FORMATS:
        df.to_file(output, driver="GPKG")
        return None

    note = None
    if is_geo:
        geometry_cols = [col for col in df.columns if str(df[col].dtype) == "geometry"]
        df = pd.DataFrame(df.drop(columns=geometry_cols))
        note = f"dropped geometry column(s): {', '.join(geometry_cols)}"
    if suffix == ".csv":
        df.to_csv(output, index=False)
    else:
        df.to_excel(output, index=False)
    return note
