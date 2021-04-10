"""Pages for the computer_facts schema of postgres."""
import datetime
import itertools
import os

from bokeh import embed, models, palettes, plotting
from flask import Blueprint, render_template
from psycopg2 import connect, sql

bp = Blueprint("computer_facts", __name__)

COLORMAP = palettes.Dark2

SQL_TEMPLATE = sql.SQL(
    """
    select 
        date_trunc('minute', ts_utc) as ts,
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
    lb = lb or (datetime.datetime.utcnow() - datetime.timedelta(days=1))
    query = SQL_TEMPLATE.format(
        facts=sql.SQL(",").join([sql.Literal(f) for f in facts]),
        utc_lowerbound=sql.Literal(lb),
    )
    with connect(os.environ["PSYCOPG_URI"]) as conn:
        with conn.cursor() as curs:
            curs.execute(query)
            keys = tuple(i.name for i in curs.description)
            return [dict(zip(keys, row)) for row in curs]


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
    return make_fact_lines(plot, data)


def plot_percents(data: list) -> plotting.Figure:
    """Return the bokeh of temperature data."""
    plot = make_timeseries_plot()
    plot.yaxis.formatter = models.NumeralTickFormatter(format="0%")
    plot.y_range = models.Range1d(0, 1)
    return make_fact_lines(plot, data)


@bp.route("/")
def render_computer_facts():
    plots = {
        "Temperatures": plot_temps(db_query("cpu_temp_f", "gpu_temp_f", "rpi_temp_f")),
        "Usage Pct": plot_percents(
            db_query("hd_use_pct", "cpu_use_pct", "memory_use_pct")
        ),
    }
    return render_template(
        "computer_facts.html",
        plots={k: embed.components(p) for k, p in plots.items()},
    )
