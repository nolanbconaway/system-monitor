"""Pages for the computer_facts schema of postgres."""

import datetime
import itertools
import os

from bokeh import embed, models, palettes, plotting
from flask import Blueprint, render_template
from psycopg2 import connect, sql
import pandas as pd

bp = Blueprint("computer_facts", __name__)

COLORMAP = palettes.Dark2
TZ = "America/New_York"
INTERVAL = pd.Timedelta(minutes=10)
SQL_TEMPLATE = sql.SQL(
    """
    select 
        date_trunc('minute', ts_utc) at time zone {tz} as ts,
        fact_name,
        avg(fact_value) as fact_value

    from public.computer_facts

    where fact_name in ({facts})
    and ts_utc >= {utc_lowerbound}

    group by 1, 2
    order by 1, 2
    """
)


def db_query(*facts, lb: str = None) -> list:
    """Get data out of postgres via the sql template."""
    lb = lb or (
        datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None)
        - datetime.timedelta(days=4)
    )
    query = SQL_TEMPLATE.format(
        facts=sql.SQL(",").join([sql.Literal(f) for f in facts]),
        utc_lowerbound=sql.Literal(lb),
        tz=sql.Literal(TZ),
    )
    with connect(os.environ["POSTGRES_LOCAL_DSN"]) as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            keys = tuple(i.name for i in curs.description)
            df = pd.DataFrame([dict(zip(keys, row)) for row in curs])

    if df.empty:
        return []

    # floor to interval, and set frequency
    df = (
        df.assign(ts=lambda x: pd.to_datetime(x["ts"]).dt.floor(INTERVAL))
        .groupby(["fact_name", "ts"])
        .mean()
        .reset_index()
    )

    # fill in missing values for each fact_name using asfreq
    df = pd.concat(
        [
            rows.set_index("ts")
            .asfreq(INTERVAL)
            .reset_index()
            .assign(fact_name=fact_name)
            for fact_name, rows in df.groupby("fact_name")
        ]
    )
    # back to list of dicts
    return [
        {
            "ts": row["ts"].to_pydatetime(),
            "fact_name": str(row["fact_name"]),
            "fact_value": float(row["fact_value"]),
        }
        for _, row in df.iterrows()
    ]


def make_timeseries_plot() -> plotting.Figure:
    """Make an empty timeseries plot with all my customizations."""
    plot = plotting.figure(plot_width=900, plot_height=400, x_axis_type="datetime")
    plot.toolbar.active_drag = None
    plot.toolbar.active_scroll = None
    plot.toolbar.active_tap = None
    plot.toolbar.logo = None
    plot.toolbar_location = None
    plot.xaxis.formatter = models.DatetimeTickFormatter(
        hours=["%a %I%p"], days=["%a %I%p"]
    )
    return plot


def make_fact_lines(plot: plotting.Figure, data: list) -> plotting.Figure:
    n_facts = len({i["fact_name"] for i in data})
    if n_facts == 1:
        cmap = ["#1b9e77"]
    elif n_facts == 2:
        cmap = ["#1b9e77", "#d95f02"]
    else:
        cmap = list(COLORMAP[n_facts])

    for key, series in itertools.groupby(
        sorted(data, key=lambda x: x["fact_name"]), lambda x: x["fact_name"]
    ):
        x, y = zip(*[(i["ts"], i["fact_value"]) for i in series])
        plot.line(x, y, legend_label=key, color=cmap.pop(), line_width=2)
    return plot


def plot_temps(data: list) -> plotting.Figure:
    """Return the bokeh of temperature data."""
    plot = make_timeseries_plot()
    plot.yaxis.formatter = models.PrintfTickFormatter(format="%d°f")
    plot.y_range = models.Range1d(0, 250)
    if not data:
        return plot
    plot = make_fact_lines(plot, data)
    plot.legend.location = "bottom_left"  # because the legend requires glyphs
    return plot


def plot_percents(data: list) -> plotting.Figure:
    """Return the bokeh of temperature data."""
    plot = make_timeseries_plot()
    plot.yaxis.formatter = models.NumeralTickFormatter(format="0%")
    plot.y_range = models.Range1d(0, 1)
    if not data:
        return plot

    plot = make_fact_lines(plot, data)
    plot.legend.location = "top_left"  # because the legend requires glyphs
    return plot


def plot_network(data: list) -> plotting.Figure:
    """Return the bokeh of network data (mbps)."""
    plot = make_timeseries_plot()
    plot.yaxis.formatter = models.NumeralTickFormatter(format="0")
    plot.y_range = models.Range1d(0, 500)
    if not data:
        return plot

    plot = make_fact_lines(plot, data)
    plot.legend.location = "bottom_left"  # because the legend requires glyphs
    return plot


@bp.route("/")
def render_computer_facts():
    plots = {
        "Temperatures": plot_temps(
            db_query("temp/system76_acpi/f", "temp/nvme/f", "temp/coretemp/avg/f")
        ),
        "Usage Pct": plot_percents(
            db_query("usage/hd/pct", "usage/cpu/pct", "usage/memory/pct")
        ),
        "Network Mbps": plot_network(db_query("network/down/mbps", "network/up/mbps")),
    }
    return render_template(
        "computer_facts.html",
        plots={k: embed.components(p) for k, p in plots.items()},
    )
