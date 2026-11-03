"""Generate the history charts, each at the panel's size and the full-screen
viewer's, from one registry (spec
docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md § 4.3).

    python3 scripts/generators/gen_te_history_charts.py           # write the file
    python3 scripts/generators/gen_te_history_charts.py --check   # exit 1 if stale

Writes gui/te_history_charts_generated.gui. Never edit that file: edit CHARTS,
the size tables or a fragment in scripts/generators/te_history_charts/, and
run this script. test_te_history_charts.py fails while the committed file is
stale. A manual generator, kept out of POST_LOAD_REGENERATORS (as
gen_te_systems_window.py), so a reload never rewrites the charts.

THE SHAPE. Each chart is two wrapper types:

    te_hist_<id>        the panel's size (SMALL); the chart's section, still
                        hand-written, instances it where the chart sits
    te_hist_<id>_large  the full-screen viewer's (LARGE)

each a plain flowcontainer holding one te_history_chart instance with its
blockoverrides inline. That is the shape that draws: gotcha #37 was a type
derived from te_history_plot, which this is not. The wrapper mirrors the
chart's own parentanchor and adds nothing else, so the panel lays out as
before; a chart's own visible sits on the section's instance of the wrapper,
so a hidden chart leaves no spacing behind.

A FRAGMENT is one chart's te_history_chart instance as it stood in its section,
dedented, with each size a placeholder. Fragments live one file a system,
te_history_charts/<system>.gui.in, each opened by an "@fragment <name>" line:

    ${frame}            the frame (plot_size): "<width> <height>"
    ${bars_<v>}         a bar's width while the chart's range variable is v
    ${bar_h}            the bars' height
    ${box_h}            Demographics: the box the bars sit in under the pip lane
    ${zero_y:<f>}       a hand-placed zero line's y, f of the way up the bars
    ${thin:<x>}         a cap or floor of x in the axis's units, x at SMALL and
    ${thin:<a>+<x>}     thinned by the bars' height ratio at LARGE, so it draws
                        as many pixels; a + x is a floor above the axis's min a
    ${<param>}          a chart's own params (the Reserve's goods share one
                        fragment through ${good})

At SMALL every placeholder gives back the literal it replaced. The generator
adds the blockoverrides a fragment doesn't carry where the size differs from
te_history_chart's own defaults (which are SMALL's monthly): at LARGE, a
monthly chart's frame, bars and widths, an annual chart's widths. At SMALL it
adds only the open button beside the title (chart_open, which opens the
chart's viewer) and the title's width beside it (open_overrides), so the
panel's charts are otherwise the fragments' text. The large wrapper leaves out
the fragment's whole-line comments, which describe the panel's size.

ADDING A CHART: record the series (history_charts.md), add its fragment to its
system's file, a Chart line below, instance te_hist_<id> in its section, then
run this script.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[2]
GUI_OUT = ROOT / "gui" / "te_history_charts_generated.gui"
FRAGMENTS = Path(__file__).resolve().parent / "te_history_charts"
BOM = b"\xef\xbb\xbf"   # exactly one, as every .gui carries

KINDS = ("monthly", "annual", "annual_pips")


# --- the sizes ------------------------------------------------------------------

@dataclass(frozen=True)
class Dims:
    """One kind of chart at one size.

    plot     the bars' width over a full range: every range's bar count divides it
    left     the frame's left of the bars: 8, or 48 where axis labels sit there
    frame    plot_size: left + plot + te_history_plot's 8 px right margin, and the
             height (the bars' box, plus the pip lane over it for annual_pips)
    bar_h    the bars' height, 6 px clear of their box's top and bottom
    box_h    annual_pips: the box the bars sit in, at the frame's foot
    text_w   the legend's max_width (chart_text_width)
    title_w  the title's max_width (chart_title_width): on the panel, the
             legend's less the open button and its gap beside the title
    empty_w  the empty state's max_width (empty_width)
    """
    plot: int
    left: int
    frame: tuple[int, int]
    bar_h: int
    text_w: int
    title_w: int
    empty_w: int
    box_h: int | None = None


@dataclass(frozen=True)
class Size:
    name: str
    suffix: str                       # the wrapper's name after te_hist_<id>
    kinds: dict = field(hash=False)   # kind -> Dims

    def __getitem__(self, kind: str) -> Dims:
        return self.kinds[kind]


# The open button beside a panel chart's title (te_chart_open_button, charts PR
# C2): its side, and the title row's spacing before it.
OPEN_BUTTON = 24
OPEN_GAP = 4
TITLE_W = 484   # te_history_chart's chart_title_width default

# The panel's size: today's literals. The monthly row is te_history_chart's own
# defaults (test_te_history_charts.py holds the type to it), but for the title,
# which the open button narrows from the type's 484 to 456.
SMALL = Size("small", "", {
    "monthly": Dims(plot=480, left=8, frame=(496, 96), bar_h=84, text_w=484, title_w=456, empty_w=420),
    "annual": Dims(plot=400, left=48, frame=(456, 180), bar_h=168, text_w=484, title_w=456, empty_w=420),
    "annual_pips": Dims(plot=400, left=48, frame=(456, 132), bar_h=84, text_w=484, title_w=456, empty_w=420,
                        box_h=96),
})

# The viewer's: one plot width for every chart, 1200, which divides 240 / 60 / 12
# months and 100 / 20 / 5 years (owner call 7), the bars 336 tall. The title
# keeps the type's 484 (no button beside it, and no title comes near it).
LARGE = Size("large", "_large", {
    "monthly": Dims(plot=1200, left=8, frame=(1216, 348), bar_h=336, text_w=1204, title_w=484, empty_w=1000),
    "annual": Dims(plot=1200, left=48, frame=(1256, 348), bar_h=336, text_w=1244, title_w=484, empty_w=1000),
    "annual_pips": Dims(plot=1200, left=48, frame=(1256, 384), bar_h=336, text_w=1244, title_w=484, empty_w=1000,
                        box_h=348),
})

SIZES = (SMALL, LARGE)
PIP_LANE = 36   # annual_pips: the frame's height over the bars' box


# --- the ranges -----------------------------------------------------------------

@dataclass(frozen=True)
class Range:
    """A range variable the charts of a kind share (a GetVariableSystem value).

    values   the three buttons' values, shortest first; unset is the last
    samples  how many samples each shows (months or years)
    labels   the three buttons' loc keys
    button_w the buttons' width (te_history_range_button's size)
    """
    var: str
    values: tuple[str, str, str]
    samples: tuple[int, int, int]
    labels: tuple[str, str, str]
    button_w: int


RANGES = {
    "te_hist_range": Range("te_hist_range", ("1", "5", "20"), (12, 60, 240),
                           ("te_hist_range_1y", "te_hist_range_5y", "te_hist_range_20y"), 72),
    "te_demog_hist_range": Range("te_demog_hist_range", ("5", "20", "100"), (5, 20, 100),
                                 ("te_hist_range_5y", "te_hist_range_20y", "te_demog_hist_range_100y"), 96),
    "ch_model_hist_range": Range("ch_model_hist_range", ("5", "20", "100"), (5, 20, 100),
                                 ("ch_model_hist_range_5", "ch_model_hist_range_20", "ch_model_hist_range_100"), 96),
}


def bars(dims: Dims, rng: Range) -> dict[str, int]:
    """A bar's width at each of the range's values: the plot over its samples."""
    out = {}
    for value, n in zip(rng.values, rng.samples):
        if dims.plot % n:
            raise ValueError(f"{rng.var}={value}: {n} samples don't divide a {dims.plot} px plot")
        out[value] = dims.plot // n
    return out


# --- the registry ---------------------------------------------------------------

@dataclass(frozen=True)
class Chart:
    """One history chart.

    id        te_hist_<id> and te_hist_<id>_large; the viewer's popup key (C2)
    system    its tab (gen_te_systems_window.TABS' key) and its fragment file
    kind      monthly, annual or annual_pips (annual with a pip lane over the bars)
    fragment  its name in the system's fragment file
    entry     the journal entry the viewer reads through GetPlayerJournalEntry
              (None: Demographics, which reads Country)
    gate      the viewer's scope-free gate: the tab's scripted GUI, on a parent
              of the entry's datacontext (gotcha #29)
    range     its range variable (RANGES)
    params    the names the fragment substitutes, as (name, value) pairs
    """
    id: str
    system: str
    kind: str
    fragment: str
    entry: str | None
    gate: str
    range: str
    params: tuple[tuple[str, str], ...] = ()


def _monthly(system: str, entry: str, gate: str, ids: list[str]) -> list[Chart]:
    return [Chart(i, system, "monthly", i, entry, gate, "te_hist_range") for i in ids]


ST_RES_GOODS = ["grain", "ammunition", "oil", "small_arms", "artillery", "aeroplanes", "tanks", "fertilizer"]

CHARTS: list[Chart] = (
    _monthly("banking", "je_banking_cycle", "te_budget_banking_tab_sgui",
             ["bank_value", "bank_momentum", "bank_bubble", "mon_policy", "mon_policy_digital",
              "mon_rate_paid", "mon_inflation", "mon_fx"])
    + [Chart(f"st_res_{g}", "strategic_reserve", "monthly", "st_res", "je_strategic_reserve",
             "te_market_strategic_reserve_tab_sgui", "te_hist_range", (("good", g),)) for g in ST_RES_GOODS]
    + [Chart(i, "demographics", "annual_pips", i, None, "te_pops_demog_tab_sgui", "te_demog_hist_range")
       for i in ["demog_births_deaths", "demog_migration", "demog_e0", "demog_tfr", "demog_median",
                 "demog_causes", "demog_gini", "demog_wc"]]
    + [Chart("ch_models", "cultural_hegemony", "annual", "ch_models", "je_cultural_hegemony",
             "te_society_ch_tab_sgui", "ch_model_hist_range")]
    + _monthly("nuclear_weapons", "je_nuclear_program", "te_military_nuclear_tab_sgui", ["nd_taboo", "nd_taboo_tgt"])
    + _monthly("united_nations", "je_united_nations", "te_diplomacy_un_tab_sgui", ["un_auth", "un_target"])
    + _monthly("global_warming", "je_global_warming", "te_market_global_warming_tab_sgui", ["gw_temp", "gw_share"])
    + _monthly("colonial_empire", "je_colonial_empire", "te_window_colonial_empire_tab_sgui",
               ["ce_stability", "ce_drift"])
)

BY_ID = {c.id: c for c in CHARTS}
SYSTEMS = list(dict.fromkeys(c.system for c in CHARTS))


def wrapper_name(chart: Chart, size: Size) -> str:
    return f"te_hist_{chart.id}{size.suffix}"


def popup_key(chart: Chart) -> str:
    """The chart's te_popup value: its open button sets it, its viewer shows on it."""
    return f"chart_{chart.id}"


# --- fragments ------------------------------------------------------------------

MARK = re.compile(r"^@fragment (\w+)$")
PLACEHOLDER = re.compile(r"\$\{(\w+)(?::([^}]*))?\}")
CHART_OPEN = "te_history_chart = {"


def fragments(system: str) -> dict[str, str]:
    """The system's fragments by name: each chart's instance text, dedented."""
    path = FRAGMENTS / f"{system}.gui.in"
    out: dict[str, list[str]] = {}
    current = None
    for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
        m = MARK.match(line)
        if m:
            current = m.group(1)
            if current in out:
                raise ValueError(f"{path.name}:{n}: fragment {current} twice")
            out[current] = []
        elif current is not None:
            out[current].append(line)
        elif line.strip() and not line.startswith("#"):
            raise ValueError(f"{path.name}:{n}: text before the first @fragment")
    texts = {}
    for name, lines in out.items():
        while lines and not lines[-1].strip():
            lines.pop()
        if not lines or lines[0] != CHART_OPEN or lines[-1] != "}":
            raise ValueError(f"{path.name}: fragment {name} isn't one te_history_chart instance at column 0")
        texts[name] = "\n".join(lines)
    return texts


def fragment(chart: Chart) -> str:
    return fragments(chart.system)[chart.fragment]


# --- rendering ------------------------------------------------------------------

def _num(d: Decimal) -> str:
    text = format(d.normalize(), "f")
    return "0" if text in ("-0", "0") else text


def _thin(arg: str, ratio: Decimal) -> str:
    m = re.fullmatch(r"(-?\d+(?:\.\d+)?)\+(\d+(?:\.\d+)?)|(\d+(?:\.\d+)?)", arg)
    if not m:
        raise ValueError(f"${{thin:{arg}}}: write x or a+x")
    base, x = (Decimal(m.group(1)), Decimal(m.group(2))) if m.group(2) else (Decimal(0), Decimal(m.group(3)))
    if ratio == 1:
        return _num(base + x)
    # three places: CFixedPoint's precision, a thousandth of a unit
    return _num((base + x * ratio).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP))


def values(chart: Chart, size: Size) -> dict[str, str]:
    """Each plain placeholder's text for the chart at the size."""
    dims = size[chart.kind]
    out = {"frame": f"{dims.frame[0]} {dims.frame[1]}", "bar_h": str(dims.bar_h),
           "text_w": str(dims.text_w), "empty_w": str(dims.empty_w)}
    if dims.box_h is not None:
        out["box_h"] = str(dims.box_h)
    out.update({f"bars_{v}": str(w) for v, w in bars(dims, RANGES[chart.range]).items()})
    out.update(dict(chart.params))
    return out


def substitute(text: str, chart: Chart, size: Size) -> str:
    plain = values(chart, size)
    dims, small = size[chart.kind], SMALL[chart.kind]
    ratio = Decimal(small.bar_h) / Decimal(dims.bar_h)

    def one(m: re.Match) -> str:
        name, arg = m.group(1), m.group(2)
        if name == "thin" and arg is not None:
            return _thin(arg, ratio)
        if name == "zero_y" and arg is not None:
            margin = Decimal((dims.box_h or dims.frame[1]) - dims.bar_h) / 2
            return str(-int((margin + Decimal(arg) * dims.bar_h).quantize(Decimal(1), rounding=ROUND_HALF_UP)))
        if arg is None and name in plain:
            return plain[name]
        raise ValueError(f"{chart.id}: unknown placeholder {m.group(0)}")

    out = PLACEHOLDER.sub(one, text)
    if "$" in out:
        raise ValueError(f"{chart.id}: a $ left after substitution")
    return out


def _override(name: str, lines: list[str]) -> list[str]:
    return [f'blockoverride "{name}" {{'] + [f"\t{ln}" for ln in lines] + ["}"]


def plot_layouts(dims: Dims, rng: Range) -> list[str]:
    """The three plots of te_history_chart's default plot_layouts at other bar
    sizes: one a range, the full range's shown while neither shorter one is set."""
    widths = bars(dims, rng)
    short, middle, full = rng.values

    def has(v: str) -> str:
        return f"GetVariableSystem.HasValue( '{rng.var}', '{v}' )"

    tests = {short: has(short), middle: has(middle), full: f"Not( Or( {has(short)}, {has(middle)} ) )"}
    out = []
    for v in rng.values:
        out += ["te_history_plot = {", f'\tvisible = "[{tests[v]}]"']
        out += [f"\t{ln}" for ln in _override("bar_size", [f"size = {{ {widths[v]} {dims.bar_h} }}"])]
        out.append("}")
    return out


def open_overrides(chart: Chart) -> list[str]:
    """What the panel's wrapper adds to its fragment (charts PR C2): the title
    narrowed beside the open button, and the button, which opens the chart's
    viewer."""
    return (_override("chart_title_width", [f"max_width = {SMALL[chart.kind].title_w}"])
            + _override("chart_open", ["te_chart_open_button = {",
                                       f"\tonclick = \"[GetVariableSystem.Set('te_popup', '{popup_key(chart)}')]\"",
                                       "}"]))


def size_overrides(chart: Chart, size: Size, text: str) -> list[str]:
    """The blockoverrides the chart needs at the size beyond its fragment: each
    the fragment doesn't carry whose value differs from te_history_chart's
    defaults (SMALL's monthly row, and TITLE_W), and at SMALL the open button
    beside the title."""
    dims, default = size[chart.kind], SMALL["monthly"]
    carried = set(re.findall(r'blockoverride "(\w+)"', text))
    out: list[str] = []
    if "plot_size" not in carried and dims.frame != default.frame:
        out += _override("plot_size", [f"size = {{ {dims.frame[0]} {dims.frame[1]} }}"])
    if "plot_layouts" not in carried and (dims.plot, dims.bar_h) != (default.plot, default.bar_h):
        out += _override("plot_layouts", plot_layouts(dims, RANGES[chart.range]))
    if "chart_text_width" not in carried and dims.text_w != default.text_w:
        out += _override("chart_text_width", [f"max_width = {dims.text_w}"])
    if "empty_width" not in carried and dims.empty_w != default.empty_w:
        out += _override("empty_width", [f"max_width = {dims.empty_w}"])
    if size is SMALL:
        if {"chart_title_width", "chart_open"} & carried:
            raise ValueError(f"{chart.id}: a fragment leaves chart_title_width and chart_open to the generator")
        out += open_overrides(chart)
    elif "chart_title_width" not in carried and dims.title_w != TITLE_W:
        out += _override("chart_title_width", [f"max_width = {dims.title_w}"])
    return out


def render_chart(chart: Chart, size: Size) -> str:
    """The chart's te_history_chart instance at the size, dedented."""
    text = substitute(fragment(chart), chart, size)
    lines = text.split("\n")
    extra = size_overrides(chart, size, text)
    if extra:
        lines = lines[:-1] + [f"\t{ln}" for ln in extra] + lines[-1:]
    if size is not SMALL:
        lines = [ln for ln in lines if not ln.lstrip().startswith("#")]
    return "\n".join(lines)


def wrapper(chart: Chart, size: Size) -> list[str]:
    body = render_chart(chart, size).split("\n")
    return ([f"type {wrapper_name(chart, size)} = flowcontainer {{", "\tparentanchor = hcenter", ""]
            + [f"\t{ln}" if ln else "" for ln in body] + ["}"])


# --- the file -------------------------------------------------------------------

HEADER = [
    "### AUTO-GENERATED by scripts/generators/gen_te_history_charts.py from its CHARTS registry",
    "### and the fragments in scripts/generators/te_history_charts/. Do not edit.",
    "### Each history chart as two wrapper types: te_hist_<id>, the panel's size, which the",
    "### chart's section instances where the chart sits, and te_hist_<id>_large, the",
    "### full-screen viewer's. Each is a plain flowcontainer holding the chart's",
    "### te_history_chart instance inline (gotcha #37). The large one leaves out the chart's",
    "### comments, which describe the panel's size. How to add a chart: the generator's",
    "### docstring and docs/systems/mod_systems/history_charts.md.",
    "",
]


def _validate() -> None:
    if len(BY_ID) != len(CHARTS):
        raise ValueError("chart ids are unique")
    used: dict[str, set[str]] = {s: set() for s in SYSTEMS}
    for c in CHARTS:
        if c.kind not in KINDS:
            raise ValueError(f"{c.id}: kind {c.kind!r} isn't one of {KINDS}")
        if c.range not in RANGES:
            raise ValueError(f"{c.id}: range {c.range!r} isn't in RANGES")
        if (c.kind == "monthly") != (c.range == "te_hist_range"):
            raise ValueError(f"{c.id}: a monthly chart reads te_hist_range, an annual one its own range")
        if c.fragment not in fragments(c.system):
            raise ValueError(f"{c.id}: no fragment {c.fragment} in {c.system}.gui.in")
        used[c.system].add(c.fragment)
    for s in SYSTEMS:
        unused = set(fragments(s)) - used[s]
        if unused:
            raise ValueError(f"{s}.gui.in: fragments no chart uses: {sorted(unused)}")


def render() -> str:
    _validate()
    lines = list(HEADER) + ["types te_history_charts_generated_types", "{"]
    for i, chart in enumerate(CHARTS):
        for size in SIZES:
            if i or size is not SMALL:
                lines.append("")
            if size is SMALL:
                lines.append(f"\t### {chart.id}: {chart.system}, {chart.kind}")
            lines += [f"\t{ln}" if ln else "" for ln in wrapper(chart, size)]
    lines.append("}")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    data = BOM + render().encode("utf-8")
    if "--check" in argv:
        if not GUI_OUT.exists() or GUI_OUT.read_bytes() != data:
            print(f"stale: {GUI_OUT} (run python3 scripts/generators/gen_te_history_charts.py)")
            return 1
        return 0
    GUI_OUT.write_bytes(data)
    return 0


if __name__ == "__main__":
    sys.exit(main())
