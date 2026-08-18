"""parx command line interface."""

from pathlib import Path
from typing import TYPE_CHECKING, cast

import rich_click as click
from click.exceptions import UsageError

if TYPE_CHECKING:
    import geopandas as gpd

from parquet_explorer.convert import convert
from parquet_explorer.hexagon import hex_aggregate
from parquet_explorer.io import load_parquet
from parquet_explorer.jenks import add_jenks_labels
from parquet_explorer.show import print_show
from parquet_explorer.summary import print_summary


class ParxGroup(click.RichGroup):
    """Group that routes ``parx <file.parquet>`` to the ``summary`` command."""

    def resolve_command(
        self, ctx: click.Context, args: list[str]
    ) -> tuple[str | None, click.Command | None, list[str]]:
        try:
            return super().resolve_command(ctx, args)
        except UsageError:
            summary_cmd = self.get_command(ctx, "summary")
            assert summary_cmd is not None
            return "summary", summary_cmd, args


@click.group(cls=ParxGroup, invoke_without_command=True, no_args_is_help=False)
@click.version_option(package_name="parquet-explorer")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """Explore parquet and geoparquet files.

    Pass a file directly to print a summary: `parx data.parquet`.
    """
    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())
        ctx.exit(0)


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--groupby",
    "-g",
    metavar="COLUMN",
    help="Group numeric summaries by this column (skipped if more than 10 groups).",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Convert the file instead of summarising it. "
    "Format is detected from the suffix: .csv, .xlsx (parquet) or .gpkg (geoparquet).",
)
def summary(file: Path, groupby: str | None, output: Path | None) -> None:
    """Print a summary of a parquet file, or convert it with --output."""
    df, is_geo = load_parquet(file)
    if output is not None:
        try:
            note = convert(df, is_geo, output)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Written {output}" + (f" ({note})" if note else ""))
        return
    try:
        print_summary(file, df, is_geo, groupby=groupby)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--all-col", is_flag=True, help="Print all columns instead of the first and last 4."
)
@click.option(
    "--cols",
    metavar="SPEC",
    help="Comma-separated column names or 1-based column indices, "
    "e.g. \"col1,col2,'col 3'\" or \"1,2,3,5,8\". Quote names containing commas.",
)
@click.option(
    "--head",
    type=click.IntRange(min=1),
    is_flag=False,
    flag_value=5,
    default=None,
    metavar="N",
    help="Print only the first N rows [default: 5].",
)
@click.option(
    "--tail",
    type=click.IntRange(min=1),
    is_flag=False,
    flag_value=5,
    default=None,
    metavar="N",
    help="Print only the last N rows [default: 5].",
)
@click.option(
    "--rows",
    metavar="START:STOP",
    help="Print rows START to STOP (1-based, inclusive), e.g. 5:10.",
)
def show(
    file: Path,
    all_col: bool,
    cols: str | None,
    head: int | None,
    tail: int | None,
    rows: str | None,
) -> None:
    """Print rows of a parquet file as a table.

    Without options, prints the first and last 5 rows and the first
    and last 4 columns.
    """
    df, _ = load_parquet(file)
    try:
        print_show(df, all_col=all_col, cols=cols, head=head, tail=tail, rows=rows)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option(
    "--output",
    "-o",
    required=True,
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output geoparquet file with the hexagon polygons.",
)
@click.option(
    "--res",
    "-r",
    default=9,
    show_default=True,
    type=click.IntRange(0, 15),
    help="H3 resolution.",
)
@click.option(
    "--aggr-fun",
    metavar="SPEC",
    help='Per-column aggregation functions, e.g. "mycolumn1=mean, mycolumn2=sum". '
    "Numeric columns default to sum.",
)
def hex(file: Path, output: Path, res: int, aggr_fun: str | None) -> None:
    """Aggregate a point geoparquet file to H3 hexagons."""
    df, is_geo = load_parquet(file)
    if not is_geo:
        raise click.ClickException(f"'{file}' is not a geoparquet file")
    try:
        result = hex_aggregate(cast("gpd.GeoDataFrame", df), res, aggr_fun)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_parquet(output)
    click.echo(f"Written {output} ({len(result):,} hexagons at resolution {res})")


@cli.command()
@click.argument("file", type=click.Path(exists=True, dir_okay=False, path_type=Path))
@click.option("--column", "-c", required=True, help="Numeric column to classify.")
@click.option(
    "--sample-size-perc",
    default=0.1,
    show_default=True,
    type=click.FloatRange(0, 1, min_open=True),
    help="Fraction of the rows used to compute the breaks.",
)
@click.option(
    "--class-num",
    "-n",
    default=5,
    show_default=True,
    type=click.IntRange(min=2),
    help="Number of classes.",
)
@click.option(
    "--overwrite",
    is_flag=True,
    help="Write the result back to FILE instead of a new file.",
)
@click.option(
    "--output",
    "-o",
    type=click.Path(dir_okay=False, path_type=Path),
    help="Output parquet file [default: <file>_labeled.parquet].",
)
def jenks(
    file: Path,
    column: str,
    sample_size_perc: float,
    class_num: int,
    overwrite: bool,
    output: Path | None,
) -> None:
    """Add a Jenks natural breaks class column to a parquet file.

    Classes are computed over COLUMN on a random sample of the rows and
    stored in a `<column>_label` column (overwritten if it exists). Labels
    are a sequence number from low to high values with the class range,
    e.g. "2 [134.1 - 362.3]".
    """
    if overwrite and output is not None:
        raise click.ClickException("--overwrite and --output cannot be combined")
    out = file if overwrite else (output or file.with_name(f"{file.stem}_labeled.parquet"))
    if out.suffix.lower() != ".parquet":
        raise click.ClickException(f"output must be a .parquet file, got '{out.name}'")
    df, _ = load_parquet(file)
    try:
        label_column, n_classes = add_jenks_labels(
            df, column, class_num=class_num, sample_frac=sample_size_perc
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    out.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out)
    click.echo(f"Written {out} ('{label_column}' with {n_classes} classes)")


if __name__ == "__main__":
    cli()
