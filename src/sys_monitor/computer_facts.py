"""Pages for the computer_facts schema of postgres."""

import datetime
import itertools
import json
import os

import pandas as pd
from bokeh import embed, models, palettes, plotting
from flask import Blueprint, render_template
from psycopg2 import connect, sql

bp = Blueprint("computer_facts", __name__)

TIMESTEP_MINS = 5  # timeseries aggregation step
PLOT_TIME_RANGE_HOURS = 24
COLORMAP = palettes.Dark2
TZ = "America/New_York"

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


def db_query(*facts, lb: str = None, regularize: bool = True) -> list:
    """Get data out of postgres via the sql template."""
    lb = lb or (
        datetime.datetime.now(datetime.timezone.utc)
        - datetime.timedelta(hours=PLOT_TIME_RANGE_HOURS)
    )
    query = SQL_TEMPLATE.format(
        facts=sql.SQL(",").join([sql.Literal(f) for f in facts]),
        utc_lowerbound=sql.Literal(lb),
        tz=sql.Literal(TZ),
    )
    with connect(os.environ["PSYCOPG_URI"]) as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            keys = tuple(i.name for i in curs.description)
            data = [dict(zip(keys, row)) for row in curs]

    if regularize:
        data = regularize_timeseries(data)

    return data


def regularize_timeseries(data: list) -> list:
    """Regularize the timeseries data to TIMESTEP_MINS intervals."""
    out = []
    for key, group in pd.DataFrame(data).groupby("fact_name"):
        group = (
            group.assign(ts=lambda d: d.ts.dt.floor(f"{TIMESTEP_MINS}min"))
            .groupby("ts")
            .mean()
            .asfreq(f"{TIMESTEP_MINS}min")
            .reset_index()
            .rename(columns={"index": "ts"})
            .assign(fact_name=key)
            .to_dict(orient="records")
        )
        out += group

    return out


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
    # ensure the x axis goes back PLOT_TIME_RANGE_HOURS hours
    plot.x_range = models.Range1d(
        datetime.datetime.now() - datetime.timedelta(hours=PLOT_TIME_RANGE_HOURS),
        datetime.datetime.now(),
    )
    return plot


def make_fact_lines(plot: plotting.Figure, data: list) -> plotting.Figure:
    cmap = list(COLORMAP[len({i["fact_name"] for i in data})])
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
    plot = make_fact_lines(plot, data)
    plot.legend.location = "top_left"  # because the legend requires glyphs
    return plot


def plot_percents(data: list) -> plotting.Figure:
    """Return the bokeh of temperature data."""
    plot = make_timeseries_plot()
    plot.yaxis.formatter = models.NumeralTickFormatter(format="0%")
    plot.y_range = models.Range1d(0, 1)
    plot = make_fact_lines(plot, data)
    plot.legend.location = "top_left"  # because the legend requires glyphs
    return plot


def plot_counts(data: list) -> plotting.Figure:
    """Return the bokeh of temperature data."""
    plot = make_timeseries_plot()
    plot = make_fact_lines(plot, data)
    plot.legend.location = "top_left"  # because the legend requires glyphs
    return plot


def get_plots():
    """Return all plots as a dict of title: bokeh figure."""
    return {
        "Moomoo Queue Counts": plot_counts(
            db_query("moomoo_queue_updated", "moomoo_queue_new", "moomoo_queue_old")
        ),
        "Temperatures": plot_temps(db_query("cpu_temp_f", "gpu_temp_f", "rpi_temp_f")),
        "Usage Pct": plot_percents(
            db_query("hd_use_pct", "cpu_use_pct", "memory_use_pct")
        ),
    }


@bp.route("/")
def render_computer_facts():
    plots = get_plots()
    return render_template(
        "computer_facts.html",
        plots={k: embed.components(p) for k, p in plots.items()},
    )


@bp.route("/latest.json")
def render_latest_facts():
    data = db_query(
        "cpu_temp_f",
        "gpu_temp_f",
        "rpi_temp_f",
        "hd_use_pct",
        "cpu_use_pct",
        "memory_use_pct",
        "moomoo_queue_updated",
        "moomoo_queue_new",
        "moomoo_queue_old",
        regularize=False,
        lb=datetime.datetime.utcnow() - datetime.timedelta(minutes=60),
    )

    # get the most recent of each fact
    latest = {}
    groupfn = lambda x: x["fact_name"]  # noqa: E731
    sortfn = lambda x: (x["fact_name"], x["ts"])  # noqa: E731
    for fact, group in itertools.groupby(sorted(data, key=sortfn), groupfn):
        latest[fact] = list(group)[-1]
        del latest[fact]["fact_name"]  # remove redundant key
    return json.dumps(latest, default=str)
