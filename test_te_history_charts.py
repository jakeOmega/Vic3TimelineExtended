"""The history charts: one registry entry per chart, drawn at two sizes (spec
docs/superpowers/specs/2026-11-02-charts-help-national-info-design.md § 4.3).

te_history_chart (gui/journal_entry_widgets/te_history_chart.gui) is the chart
type. Its widths are blocks, so an instance can draw it at another size.
scripts/generators/gen_te_history_charts.py holds each of the 33 charts once,
as a fragment of its instance's text with each size a placeholder, and writes
each as two wrapper types into gui/te_history_charts_generated.gui:
te_hist_<id> at the panel's size (SMALL), which the chart's section instances,
and te_hist_<id>_large at the full-screen viewer's (LARGE).
"""
import glob
import os
import re
import sys
import tempfile
import unittest
from decimal import ROUND_HALF_UP, Decimal
from unittest import mock

REPO = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, REPO)
import gui_tree  # noqa: E402
from gui_test_helpers import _close, _read, _strip_comments, _type_body  # noqa: E402
from scripts.generators import gen_te_history_charts as gen  # noqa: E402
from scripts.generators import gen_te_systems_window as window  # noqa: E402

CHART_GUI = os.path.join(REPO, "gui", "journal_entry_widgets", "te_history_chart.gui")
GENERATED = os.path.join(REPO, "gui", "te_history_charts_generated.gui")
SGUIS = os.path.join(REPO, "common", "scripted_guis")
JE_DIR = os.path.join(REPO, "common", "journal_entries")
ICONS_DOC = os.path.join(REPO, "docs", "systems", "te_systems_window_gui_icons.md")
# The open button's placeholder art: vanilla's (style guide rule 10).
OPEN_ICON = "gfx/interface/buttons/button_icons/areacharts.dds"
# The sections that hold the charts, and so their range buttons.
SECTIONS = {
    "banking": "gui/journal_entry_widgets/banking_history_widget.gui",
    "strategic_reserve": "gui/journal_entry_widgets/strategic_reserve_widget.gui",
    "demographics": "gui/te_demographics_widgets.gui",
    "cultural_hegemony": "gui/journal_entry_widgets/cultural_hegemony_widget.gui",
    "nuclear_weapons": "gui/journal_entry_widgets/nuclear_program_widget.gui",
    "united_nations": "gui/journal_entry_widgets/un_authority_widget.gui",
    "global_warming": "gui/journal_entry_widgets/global_warming_widget.gui",
    "colonial_empire": "gui/journal_entry_widgets/colonial_empire_widget.gui",
}
# Fixed pixels a fragment may hold, the same at both sizes: the zero line's
# thickness and the axis labels' pads (the bars keep 6 px clear of their box).
FIXED = {"size = { 100% 2 }", "position = { 8 6 }", "position = { 8 -6 }"}


def _block_bodies(text, name):
    """The body of each `block "name" { … }` in text, in order."""
    return [text[m.end():_close(text, m.end() - 1)] for m in re.finditer(rf'block "{name}" \{{', text)]


def _override_bodies(text, name):
    """The body of each `blockoverride "name" { … }` in text, in order."""
    return [text[m.end():_close(text, m.end() - 1)] for m in re.finditer(rf'blockoverride "{name}" \{{', text)]


def _unblocked(text, pattern):
    """Each line matching `pattern` that no `block "…" { … }` encloses."""
    out, stack = [], []
    for line in _strip_comments(text).split("\n"):
        if re.search(pattern, line) and not any(stack):
            out.append(line.strip())
        for ch in line:
            if ch == "{":
                stack.append(bool(re.search(r'\bblock "\w+" \{', line)))
            elif ch == "}":
                stack.pop()
    return out


class ChartTypeTest(unittest.TestCase):
    """The chart's own widths are blocks with today's values as their defaults,
    so the panel's charts draw as before and the viewer's can set them."""

    @classmethod
    def setUpClass(cls):
        cls.chart = _type_body(_read(CHART_GUI), "te_history_chart")

    def test_the_title_and_the_legend_each_have_a_width_block(self):
        """The title's width (chart_title_width) and the legend's
        (chart_text_width) are separate blocks, both today's 484 by default:
        the panel's wrapper narrows only the title, beside its open button."""
        for block, font in (("chart_title_width", "chart_title_font"), ("chart_text_width", "chart_legend_font")):
            with self.subTest(block=block):
                self.assertEqual([b.strip() for b in _block_bodies(self.chart, block)], ["max_width = 484"])
                box = self.chart[self.chart.rindex("textbox = {", 0, self.chart.index(f'block "{font}"')):]
                self.assertIn(f'block "{block}"', box[:box.index(f'block "{font}"')], font)

    def test_the_title_shares_a_row_with_the_open_button(self):
        """The title and block "chart_open" sit in one horizontal flowcontainer
        (charts PR C2); the legend stays below it, at the full width."""
        i = self.chart.index('block "chart_open" {}')
        row = self.chart[self.chart.rindex("flowcontainer = {", 0, self.chart.index('block "chart_title_font"')):]
        row = row[:_close(row, row.index("{")) + 1]
        self.assertIn("direction = horizontal", row.split("textbox = {")[0])
        self.assertIn('block "chart_open" {}', row)
        self.assertNotIn('block "chart_legend"', row)
        self.assertEqual(self.chart.count('block "chart_open"'), 1)
        self.assertLess(i, self.chart.index('block "chart_legend"'))

    def test_the_empty_states_width_is_a_block(self):
        self.assertEqual([b.strip() for b in _block_bodies(self.chart, "empty_width")], ["max_width = 420"])
        box = self.chart[self.chart.rindex("textbox = {", 0, self.chart.index('block "empty_text"')):]
        self.assertIn('block "empty_width"', box)

    def test_no_other_literal_width_in_the_type(self):
        """Every pixel width or size the chart draws at is a block an instance
        can override: the text, the empty state, the frame (plot_size) and the
        bars (plot_layouts)."""
        self.assertEqual(_unblocked(self.chart, r"\b(max_width|size) = \{?\s*\d"), [])
        self.assertTrue(_block_bodies(self.chart, "plot_size"))
        self.assertTrue(_block_bodies(self.chart, "plot_layouts"))


class OpenButtonTest(unittest.TestCase):
    """The open button beside each panel chart's title (charts PR C2, spec
    § 4.2): it opens the chart's full-screen viewer, te_popup = chart_<id>."""

    @classmethod
    def setUpClass(cls):
        cls.button = _type_body(_read(CHART_GUI), "te_chart_open_button")

    def test_the_type(self):
        self.assertRegex(_read(CHART_GUI), r"\btype te_chart_open_button = button_icon_round \{")
        self.assertIn('tooltip = "te_chart_open_tt"', self.button)
        self.assertRegex(self.button, r'blockoverride "size" \{\s*size = \{ %d %d \}\s*\}'
                         % (gen.OPEN_BUTTON, gen.OPEN_BUTTON))
        self.assertEqual(gen.OPEN_BUTTON, 24)
        self.assertNotIn("onclick", self.button, "each wrapper sets its own")
        # centred on the title's line, as the row is max(title, 24) tall
        self.assertEqual(re.findall(r"^\t\tparentanchor = (\S+)$", self.button, re.M), ["vcenter"])
        # one visible per widget: the Demographics wrappers put theirs on the instance
        self.assertNotIn("visible", self.button)
        self.assertEqual(sorted(c.system for c in gen.CHARTS if c.entry is None), ["demographics"] * 8)

    def test_its_placeholder_art_is_listed(self):
        """Style guide rule 10: the placeholder (vanilla's area-charts icon)
        is listed in the icons doc with the final art's subject."""
        textures = re.findall(r'texture = "([^"]+)"', self.button)
        self.assertEqual(textures, [OPEN_ICON])
        doc = _read(ICONS_DOC)
        row = next((ln for ln in doc.splitlines() if ln.startswith("| ") and "`te_chart_open_button`" in ln), None)
        self.assertIsNotNone(row, "no row for te_chart_open_button in the icons doc")
        self.assertIn(f"`{OPEN_ICON}`", row)
        self.assertIn("two arrows pointing out from a corner", row.lower())

    def test_every_small_wrapper_opens_its_viewer(self):
        """Each panel chart's wrapper fills chart_open with the button, on its
        own te_popup value, and narrows the title by the button and its gap;
        the viewer's wrapper has neither."""
        text = _read(GENERATED)
        for chart in gen.CHARTS:
            small = _type_body(text, gen.wrapper_name(chart, gen.SMALL))
            large = _type_body(text, gen.wrapper_name(chart, gen.LARGE))
            with self.subTest(chart=chart.id):
                opens = _override_bodies(small, "chart_open")
                self.assertEqual(len(opens), 1)
                self.assertIn("te_chart_open_button = {", opens[0])
                self.assertEqual(re.findall(r'onclick = "(.*)"', opens[0]),
                                 [f"[GetVariableSystem.Set('te_popup', 'chart_{chart.id}')]"])
                # A chart that reads its host's Country (Demographics', drawn for
                # any country in the Census Data window) opens the player's
                # viewer, so its button shows only for the player's own country:
                # the first half of F1.4's two-button slot.
                self.assertEqual(re.findall(r'visible = "(.*)"', opens[0]),
                                 ["[Country.IsLocalPlayer]"] if chart.entry is None else [])
                self.assertEqual([b.strip() for b in _override_bodies(small, "chart_title_width")],
                                 [f"max_width = {484 - gen.OPEN_BUTTON - gen.OPEN_GAP}"])
                self.assertEqual(_override_bodies(large, "chart_open"), [])
                self.assertEqual(_override_bodies(large, "chart_title_width"), [])
                self.assertNotIn("te_chart_open_button", large)
        self.assertEqual(484 - gen.OPEN_BUTTON - gen.OPEN_GAP, 456)


def _code_lines(text):
    """Each line without its comment, whole-line comments dropped."""
    return [ln for ln in _strip_comments(text).split("\n") if ln.strip()]


def _enclosing(lines, i):
    """The lines directly inside the block that holds line i."""
    depth, start = 0, 0
    for j in range(i - 1, -1, -1):
        depth += lines[j].count("}") - lines[j].count("{")
        if depth < 0:
            start = j + 1
            break
    out, depth = [], 0
    for line in lines[start:]:
        if depth == 0:
            out.append(line)
        depth += line.count("{") - line.count("}")
        if depth < 0:
            break
    return out


def _all_fragments():
    return [(s, name, text) for s in gen.SYSTEMS for name, text in gen.fragments(s).items()]


class RegistryTest(unittest.TestCase):
    """One registry entry per chart, its fragment drawn at two sizes (spec § 4.3)."""

    def test_the_33_charts(self):
        self.assertEqual(len(gen.CHARTS), 33)
        counts = {s: sum(c.system == s for c in gen.CHARTS) for s in gen.SYSTEMS}
        self.assertEqual(counts, {"banking": 8, "strategic_reserve": 8, "demographics": 8, "cultural_hegemony": 1,
                                  "nuclear_weapons": 2, "united_nations": 2, "global_warming": 2,
                                  "colonial_empire": 2})
        self.assertEqual(sorted(gen.SYSTEMS), sorted(SECTIONS))

    def test_the_small_size_is_todays(self):
        """SMALL holds the literals the charts drew at before the registry, and
        the chart type's own defaults are its monthly row, so a monthly chart's
        small wrapper needs no size of its own."""
        m, ch, dg = gen.SMALL["monthly"], gen.SMALL["annual"], gen.SMALL["annual_pips"]
        self.assertEqual((m.frame, m.bar_h, m.text_w, m.empty_w), ((496, 96), 84, 484, 420))
        self.assertEqual(gen.bars(m, gen.RANGES["te_hist_range"]), {"1": 40, "5": 8, "20": 2})
        self.assertEqual((ch.frame, ch.bar_h, ch.text_w, ch.empty_w), ((456, 180), 168, 484, 420))
        self.assertEqual(gen.bars(ch, gen.RANGES["ch_model_hist_range"]), {"5": 80, "20": 20, "100": 4})
        self.assertEqual((dg.frame, dg.box_h, dg.bar_h, dg.text_w, dg.empty_w), ((456, 132), 96, 84, 484, 420))
        self.assertEqual(gen.bars(dg, gen.RANGES["te_demog_hist_range"]), {"5": 80, "20": 20, "100": 4})
        digital = gen.BY_ID["mon_policy_digital"]
        self.assertEqual(gen.substitute("${zero_y:0.2}", digital, gen.SMALL), "-23")     # 6 + 0.2 x 84
        self.assertEqual(gen.substitute("${zero_y:0.25}", digital, gen.SMALL), "-27")    # 6 + 0.25 x 84
        # the title, beside the open button: 484 less the button and its gap (charts PR C2)
        self.assertEqual({gen.SMALL[k].title_w for k in gen.KINDS}, {456})
        # the chart type's defaults
        chart = _type_body(_read(CHART_GUI), "te_history_chart")
        self.assertEqual(re.findall(r'block "chart_title_width" \{\s*max_width = (\d+)', chart), ["484"])
        plot = _type_body(_read(CHART_GUI), "te_history_plot")
        self.assertEqual(re.findall(r'block "plot_size" \{\s*size = \{ (\d+) (\d+) \}', chart), [("496", "96")])
        self.assertEqual(re.findall(r'block "bar_size" \{\s*size = \{ (\d+) (\d+) \}', plot), [("2", "84")])
        layouts = chart[chart.index('block "plot_layouts"'):]
        layouts = layouts[:_close(layouts, layouts.index("{")) + 1]
        widths = re.findall(r'size = \{ (\d+) (\d+) \}', layouts)
        self.assertEqual(widths, [("40", "84"), ("8", "84")])   # the full range takes te_history_plot's 2 x 84
        ours = "\n".join(gen.plot_layouts(m, gen.RANGES["te_hist_range"]))
        self.assertEqual(re.findall(r'visible = "(.*)"', layouts), re.findall(r'visible = "(.*)"', ours))
        self.assertEqual(re.findall(r'size = \{ (\d+) (\d+) \}', ours), [("40", "84"), ("8", "84"), ("2", "84")])

    def test_the_small_wrapper_is_its_fragment(self):
        """At SMALL the generator substitutes and adds nothing but the open
        button and the title's width beside it (charts PR C2), and an annual
        chart's fixed width (its text is wider than its frame: ChartWidthTest),
        so the panel's charts are otherwise their fragments' text, as their
        sections had it."""
        for chart in gen.CHARTS:
            with self.subTest(chart=chart.id):
                text = gen.substitute(gen.fragment(chart), chart, gen.SMALL)
                added = gen.size_overrides(chart, gen.SMALL, text)
                width = gen.SMALL[chart.kind].width
                own = [] if width == gen.SMALL["monthly"].width else ['blockoverride "chart_width" {', f"\tminimumsize = {{ {width} -1 }}",
                                               f"\tmaximumsize = {{ {width} -1 }}", "}"]
                self.assertEqual(added, own + gen.open_overrides(chart))
                self.assertEqual(re.findall(r'^blockoverride "(\w+)"', "\n".join(added), re.M),
                                 (["chart_width"] if own else []) + ["chart_title_width", "chart_open"])
                rendered = gen.render_chart(chart, gen.SMALL).split("\n")
                tail = [f"\t{ln}" for ln in added]
                self.assertEqual(rendered[-1 - len(tail):-1], tail)
                self.assertEqual("\n".join(rendered[:-1 - len(tail)] + rendered[-1:]), text)

    def test_no_size_literal_in_a_fragment(self):
        """Every size a fragment draws at is a placeholder: no number left in a
        size, a position, a width or the frame, and no thin cap or floor
        outside ${thin:...} (a value line keeps only its axis's own clamps)."""
        checked = 0
        for system, name, text in _all_fragments():
            lines = _code_lines(text)
            for i, line in enumerate(lines):
                s = line.strip()
                with self.subTest(fragment=name, line=s[:80]):
                    for m in re.finditer(r"\b(size|position) = \{ ([^}]*) \}", s):
                        if m.group(0) in FIXED:
                            continue
                        for token in m.group(2).split():
                            self.assertRegex(token, r"^(\$\{[^}]+\}|\d+%|0)$", m.group(0))
                        checked += 1
                    self.assertNotRegex(s, r"\b(max_width|minimumsize|maximumsize)\b", "a width is the generator's")
                    if s.startswith("value = "):
                        own = _enclosing(lines, i)
                        clamps = {Decimal(v) for v in re.findall(r"^\s*(?:min|max) = (-?[\d.]+)\s*$",
                                                                  "\n".join(own), re.M)}
                        uppers = {Decimal(v) for v in re.findall(
                            r"Min_CFixedPoint\( [^,]+\), '\(CFixedPoint\)(-?[\d.]+)' \)", s)}
                        for v in re.findall(r"\(CFixedPoint\)(-?\d+(?:\.\d+)?)", s):
                            self.assertIn(Decimal(v), clamps | uppers | {Decimal(0)},
                                          f"{v}: a cap or floor outside ${{thin:...}}")
                        checked += 1
        self.assertGreater(checked, 90, "the sweep checked almost nothing")

    def test_a_fragment_holds_no_dollar_but_its_placeholders(self):
        """No $ in the sections, the chart type or the output, so a ${...} in a
        fragment can only be a placeholder; each is one the generator knows."""
        for path in list(SECTIONS.values()) + [os.path.relpath(CHART_GUI, REPO), os.path.relpath(GENERATED, REPO)]:
            self.assertNotIn("$", _read(os.path.join(REPO, path)), path)
        for chart in gen.CHARTS:
            text = gen.fragment(chart)
            known = set(gen.values(chart, gen.SMALL)) | {"thin", "zero_y"}
            with self.subTest(chart=chart.id):
                self.assertEqual(text.count("$"), len(gen.PLACEHOLDER.findall(text)))
                self.assertLessEqual({m.group(1) for m in gen.PLACEHOLDER.finditer(text)}, known)
        with self.assertRaisesRegex(ValueError, "unknown placeholder"):
            gen.substitute("${frmae}", gen.CHARTS[0], gen.SMALL)

    def test_the_bars_fill_the_plot(self):
        """At each size, every range's bars fill the plot exactly (integer
        widths: a remainder goes to the newest bar, history_charts.md), and the
        frame is the plot plus its margins, the bars 6 px clear of their box."""
        for size in gen.SIZES:
            for chart in {c.kind: c for c in gen.CHARTS}.values():
                dims, rng = size[chart.kind], gen.RANGES[chart.range]
                with self.subTest(size=size.name, kind=chart.kind):
                    widths = gen.bars(dims, rng)
                    for value, n in zip(rng.values, rng.samples):
                        self.assertEqual(widths[value] * n, dims.plot)
                    self.assertEqual(dims.frame[0], dims.left + dims.plot + 8)
                    box = dims.box_h if dims.box_h is not None else dims.frame[1]
                    self.assertEqual(box, dims.bar_h + 12)
                    self.assertEqual(dims.frame[1], box + (gen.PIP_LANE if chart.kind == "annual_pips" else 0))
                    self.assertEqual(dims.text_w, dims.frame[0] - 12 if size is gen.LARGE else 484)
                    # the title: beside the open button on the panel, the type's 484 in the viewer
                    self.assertEqual(dims.title_w, 484 - gen.OPEN_BUTTON - gen.OPEN_GAP if size is gen.SMALL else 484)
        self.assertIn("margin_right = 8", _type_body(_read(CHART_GUI), "te_history_plot"))
        self.assertEqual({gen.LARGE[k].plot for k in gen.KINDS}, {1200})   # owner call 7
        with self.assertRaisesRegex(ValueError, "don't divide"):
            gen.bars(gen.Dims(plot=500, left=8, frame=(516, 96), bar_h=84, text_w=0, title_w=0, empty_w=0),
                     gen.RANGES["te_hist_range"])

    def test_the_large_caps_scale(self):
        """A cap or floor in the axis's units draws as many pixels at LARGE:
        x at SMALL, x times the bars' height ratio at LARGE (to CFixedPoint's
        thousandth); a + x keeps a and scales x. The zero lines move with the
        bars: 6 + 0.2 x 336 and 6 + 0.25 x 336."""
        seen = 0
        for chart in gen.CHARTS:
            ratio = Decimal(gen.SMALL[chart.kind].bar_h) / Decimal(gen.LARGE[chart.kind].bar_h)
            for m in re.finditer(r"\$\{thin:([^}]*)\}", gen.fragment(chart)):
                base, _, x = m.group(1).rpartition("+")
                base, x = Decimal(base or 0), Decimal(x)
                with self.subTest(chart=chart.id, thin=m.group(1)):
                    self.assertEqual(Decimal(gen.substitute(m.group(0), chart, gen.SMALL)), base + x)
                    want = (base + x * ratio).quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
                    self.assertEqual(Decimal(gen.substitute(m.group(0), chart, gen.LARGE)), want)
                    self.assertLess(want - base, x)
                seen += 1
        self.assertGreater(seen, 50)
        digital = gen.BY_ID["mon_policy_digital"]
        self.assertEqual(gen.substitute("${zero_y:0.2}", digital, gen.LARGE), "-73")
        self.assertEqual(gen.substitute("${zero_y:0.25}", digital, gen.LARGE), "-90")
        large = gen.render_chart(gen.BY_ID["bank_bubble"], gen.LARGE)
        self.assertIn("'(CFixedPoint)0.5', ScriptContainer", large)    # the floor: 2 of 100 at 84 px
        self.assertIn("'(CFixedPoint)1' )", large)                     # the cap: 4

    def test_the_cycle_chart_thins_its_floor_and_cap(self):
        """te_history_bar_cycle_phase holds its bars' floor and cap as blocks
        (phase_value on all six bars, phase_cover_value on the cover). A chart
        drawing it overrides both with ${thin:...}, or its large size would
        keep a 13 px cap, and the type's seven defaults are those overrides at
        SMALL, so the panel draws as the defaults would."""
        phase = _type_body(_read(os.path.join(REPO, SECTIONS["banking"])), "te_history_bar_cycle_phase")
        defaults = {name: [b.strip() for b in _block_bodies(phase, name)] for name in ("phase_value", "phase_cover_value")}
        self.assertEqual([len(defaults["phase_value"]), len(defaults["phase_cover_value"])], [6, 1])
        users = [c for c in gen.CHARTS if "te_history_bar_cycle_phase = {" in gen.fragment(c)]
        self.assertEqual([c.id for c in users], ["bank_value"])
        for chart in users:
            text = gen.fragment(chart)
            start = text.index("te_history_bar_cycle_phase = {")
            bar = text[start:_close(text, text.index("{", start)) + 1]
            for name, values in defaults.items():
                with self.subTest(chart=chart.id, block=name):
                    m = re.search(rf'blockoverride "{name}" \{{', bar)
                    self.assertIsNotNone(m, f"the fragment leaves {name} to the type's default")
                    body = bar[m.end():_close(bar, m.end() - 1)]
                    self.assertIn("${thin:", body)
                    small = gen.substitute(body, chart, gen.SMALL).strip()
                    self.assertEqual(set(values), {small}, "the type's defaults are the override at SMALL")
                    self.assertNotEqual(gen.substitute(body, chart, gen.LARGE).strip(), small)

    def test_the_large_wrapper_sets_every_size(self):
        """The large wrapper draws at the viewer's size: a monthly chart gains
        the frame, the bars and both widths, an annual one both widths (its
        fragment sizes the frame and the bars), and no comment is left to
        describe the panel's size but a `# world:` line, which marks the read
        under it (the year, which the binding test lets through)."""
        for chart in gen.CHARTS:
            dims = gen.LARGE[chart.kind]
            large = gen.render_chart(chart, gen.LARGE)
            with self.subTest(chart=chart.id):
                self.assertIn(f"size = {{ {dims.frame[0]} {dims.frame[1]} }}", large)
                for w in gen.bars(dims, gen.RANGES[chart.range]).values():
                    self.assertIn(f"size = {{ {w} {dims.bar_h} }}", large)
                self.assertIn(f'blockoverride "chart_text_width" {{\n\t\tmax_width = {dims.text_w}\n\t}}', large)
                self.assertIn(f'blockoverride "empty_width" {{\n\t\tmax_width = {dims.empty_w}\n\t}}', large)
                self.assertFalse([ln for ln in large.split("\n") if ln.lstrip().startswith("#") and not gen.WORLD.match(ln)])
                small = gen.render_chart(chart, gen.SMALL)
                self.assertEqual([ln.strip() for ln in large.split("\n") if gen.WORLD.match(ln)],
                                 [ln.strip() for ln in small.split("\n") if gen.WORLD.match(ln)])
                self.assertEqual(large.count("{"), large.count("}"))
                for name in ("plot_size", "plot_layouts", "chart_text_width", "empty_width"):
                    self.assertEqual(large.count(f'blockoverride "{name}"'), 1, name)

    def test_the_wrappers_are_plain_flowcontainers(self):
        """Each wrapper holds its chart's te_history_chart instance (gotcha #37:
        never a type derived from te_history_plot or te_history_chart) in a
        centered column of the chart's fixed width (ChartWidthTest)."""
        text = _read(GENERATED)
        every = re.findall(r"^\ttype (\w+) = (\w+) \{", text, re.M)
        types = [(n, b) for n, b in every if n.startswith("te_hist_")]
        self.assertEqual([n for n, _ in types],
                         [gen.wrapper_name(c, s) for c in gen.CHARTS for s in gen.SIZES])
        # then the viewer's (charts PR C2): the range rows, the popups and their holder
        self.assertEqual([n for n, _ in every[len(types):]],
                         [gen.range_row_name(v) for v in gen.RANGES] + [gen.popup_name(c) for c in gen.CHARTS]
                         + ["te_chart_popups"])
        self.assertEqual({base for _, base in types}, {"flowcontainer"})
        small = {gen.wrapper_name(c, gen.SMALL): c for c in gen.CHARTS}
        large = {gen.wrapper_name(c, gen.LARGE): c for c in gen.CHARTS}
        for name, _ in types:
            body = _type_body(text, name)
            with self.subTest(wrapper=name):
                width = (gen.SMALL if name in small else gen.LARGE)[small.get(name, large.get(name)).kind].width
                self.assertEqual(body[:body.index("te_history_chart = {")].split(),
                                 ["direction", "=", "vertical", "parentanchor", "=", "hcenter",
                                  "minimumsize", "=", "{", str(width), "-1", "}",
                                  "maximumsize", "=", "{", str(width), "-1", "}"])
                self.assertEqual(body.rstrip()[-1], "}")
                chart = body[body.index("te_history_chart = {"):]
                self.assertEqual(_close(chart, chart.index("{")), len(chart.rstrip()) - 1, "one child")
        # the chart itself is unanchored: its wrapper centers it (ChartWidthTest)
        self.assertNotRegex(_type_body(_read(CHART_GUI), "te_history_chart").split("block \"chart_width\"")[0],
                            r"\bparentanchor\b")
        for path in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True):
            self.assertIsNone(re.search(r"\btype \w+ = te_history_(plot|chart)\b", _read(path)), path)

    def test_every_chart_is_generated(self):
        """No hand-written te_history_chart instance is left in gui/: each
        chart's section instances its small wrapper, once, and no hand-written
        file instances a large one (the viewer's are generated with them)."""
        generated = os.path.normpath(GENERATED)
        hand = {os.path.relpath(p, REPO): _strip_comments(_read(p))
                for p in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)
                if os.path.normpath(p) != generated}
        self.assertGreater(len(hand), 50)
        placed = {}
        for path, text in hand.items():
            self.assertNotIn("te_history_chart = {", text, path)
            for name in re.findall(r"(?<![\w.])(te_hist_\w+) = \{", text):
                placed.setdefault(name, []).append(path)
        self.assertFalse([n for n in placed if n.endswith("_large")], "a large wrapper instanced by hand")
        for chart in gen.CHARTS:
            with self.subTest(chart=chart.id):
                self.assertEqual(placed.get(gen.wrapper_name(chart, gen.SMALL)), [SECTIONS[chart.system]])

    def test_the_registry_names_what_the_viewer_reads(self):
        """Each chart's tab, entry, gate and range, for the viewer (C2): the
        gate is the tab's scripted GUI, scope-free, and holds the entry the
        viewer's GetPlayerJournalEntry reads (gotcha #29)."""
        sguis = "\n".join(_read(p) for p in glob.glob(os.path.join(SGUIS, "*.txt")))
        entries = "\n".join(_read(p) for p in glob.glob(os.path.join(JE_DIR, "*.txt")))
        tabs = {t.key for t in window.TABS}
        for chart in gen.CHARTS:
            with self.subTest(chart=chart.id):
                self.assertIn(chart.system, tabs)
                m = re.search(rf"(?m)^{chart.gate} = \{{", sguis)
                self.assertIsNotNone(m, f"no scripted GUI {chart.gate}")
                body = sguis[m.end():_close(sguis, m.end() - 1)]
                self.assertIn("scope = country", body)
                if chart.entry is None:
                    self.assertEqual(chart.system, "demographics", "only Demographics reads Country")
                else:
                    self.assertRegex(entries, rf"(?m)^{chart.entry} = \{{")
                    self.assertIn(f"has_journal_entry = {chart.entry}", body)
                self.assertIn(chart.range, gen.RANGES)

    def test_each_section_places_its_charts_in_registry_order(self):
        """Each section instances its charts in CHARTS order, so two charts
        swapped in a section (or in the registry) fail here."""
        for system, path in SECTIONS.items():
            text = _strip_comments(_read(os.path.join(REPO, path)))
            names = {gen.wrapper_name(c, gen.SMALL): c.id for c in gen.CHARTS}
            placed = [names[n] for n in re.findall(r"(?<![\w.])(te_hist_\w+) = \{", text) if n in names]
            with self.subTest(system=system):
                self.assertEqual(placed, [c.id for c in gen.CHARTS if c.system == system])

    def test_the_sections_carry_each_charts_own_visible(self):
        """A chart drawn only for some countries (Chart.shown: Banking's
        policy-rate pair, inflation and the exchange rate) keeps that visible
        on its section's instance of the wrapper, exactly; every other
        instance is a bare te_hist_<id> = {}. A visible dropped in a rebinding
        would draw both policy-rate charts, or empty monetary charts under
        banking_system_simplified."""
        self.assertEqual({c.id for c in gen.CHARTS if c.shown},
                         {"mon_policy", "mon_policy_digital", "mon_inflation", "mon_fx"})
        for chart in gen.CHARTS:
            text = _strip_comments(_read(os.path.join(REPO, SECTIONS[chart.system])))
            m = re.search(rf"(?<![\w.]){gen.wrapper_name(chart, gen.SMALL)} = \{{", text)
            body = text[m.end():_close(text, m.end() - 1)].strip()
            with self.subTest(chart=chart.id):
                self.assertEqual(body, f'visible = "[{chart.shown}]"' if chart.shown else "")

    def test_the_entry_and_gate_are_the_charts_own_tabs(self):
        """A chart's gate and entry are its own system's: the gate is the first
        scripted GUI its tab's open test (gen_te_systems_window.TABS) shows on,
        and the entry is the journal entry its tab body mounts (tab_entry's
        GetPlayerJournalEntry; Demographics' body mounts GetPlayer, so None).
        A chart given another system's pair would open its viewer on that
        system's tab and read that system's entry."""
        texts = [_read(p) for p in glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)]
        tabs = {t.key: t for t in window.TABS}
        for chart in gen.CHARTS:
            tab = tabs[chart.system]
            with self.subTest(chart=chart.id):
                self.assertEqual(chart.gate, re.findall(r"GetScriptedGui\('(\w+)'\)\.IsShown", tab.open_)[0])
                (src,) = [x for x in texts if re.search(rf"type {tab.body} = \w+ \{{", x)]
                mount = re.search(r'blockoverride "tab_entry" \{\s*datacontext = "\[(.*)\]"', _type_body(src, tab.body))
                self.assertIsNotNone(mount, f"{tab.body} mounts no entry")
                entry = re.fullmatch(r"GetPlayerJournalEntry\('(\w+)'\)", mount.group(1))
                self.assertEqual(chart.entry, entry.group(1) if entry else None, mount.group(1))
                if entry is None:
                    self.assertEqual(mount.group(1), "GetPlayer")

    def test_the_ranges_are_the_sections_buttons(self):
        """RANGES holds each range variable's three buttons as the sections
        draw them (values, labels, width), so the viewer's row (C2) can be
        theirs."""
        found = {}
        for system, path in SECTIONS.items():
            text = _strip_comments(_read(os.path.join(REPO, path)))
            for m in re.finditer(r"te_history_range_button = \{", text):
                button = text[m.end():_close(text, m.end() - 1)]
                var, value = re.search(r"GetVariableSystem\.Set\(\s*'(\w+)',\s*'(\w+)'\s*\)", button).groups()
                label = re.search(r'text = "(\w+)"', button).group(1)
                width = re.search(r"\bsize = \{ (\d+) 26 \}", button)
                found.setdefault((system, var), []).append((value, label, int(width.group(1)) if width else 72))
        self.assertEqual({var for _, var in found}, set(gen.RANGES))
        for (system, var), buttons in found.items():
            rng = gen.RANGES[var]
            with self.subTest(system=system, range=var):
                self.assertEqual(buttons, [(v, lab, rng.button_w) for v, lab in zip(rng.values, rng.labels)])
                self.assertIn(var, {c.range for c in gen.CHARTS if c.system == system})
        self.assertIn("size = { 72 26 }", _type_body(_read(CHART_GUI), "te_history_range_button"))

    def test_validate(self):
        bad = gen.Chart("x", "banking", "monthly", "bank_value", None, "te_x_sgui", "te_demog_hist_range")
        with mock.patch.object(gen, "CHARTS", gen.CHARTS + [bad]), mock.patch.object(gen, "BY_ID", {}):
            with self.assertRaisesRegex(ValueError, "unique|te_hist_range"):
                gen.render()
        orphan = [c for c in gen.CHARTS if c.id != "gw_share"]
        with mock.patch.object(gen, "CHARTS", orphan), mock.patch.object(gen, "BY_ID", {c.id: c for c in orphan}):
            with self.assertRaisesRegex(ValueError, "no chart uses"):
                gen.render()


# The keys' heights, from their rows: Banking's two lines of fontsize_medium
# (18 px) 1 apart in a 2 px margin, Demographics' one line in a 2 px margin,
# Cultural Hegemony's eight rows of ch_fontsize_row (17 px type, a 22 px line)
# 1 apart.
KEY_HEIGHTS = {"banking": 2 * 18 + 1 + 2 * 2, "demographics": 18 + 2 * 2, "cultural_hegemony": 8 * 22 + 7}


def _loc_values():
    out = {}
    for path in glob.glob(os.path.join(REPO, "localization", "english", "**", "*.yml"), recursive=True):
        for m in re.finditer(r'^ (\w+):\d* "(.*)"\s*$', _read(path), re.M):
            out[m.group(1)] = m.group(2)
    return out


class ViewerTest(unittest.TestCase):
    """Each chart's full-screen viewer (charts PR C2, spec § 4.2): a popup the
    generator writes beside the chart's wrappers, holding the range buttons,
    the large chart and its section's key (the popups' shape and gate:
    test_te_popups.py's ChartPopupTest)."""

    @classmethod
    def setUpClass(cls):
        cls.text = _strip_comments(_read(GENERATED))

    def popup(self, chart):
        return _type_body(self.text, gen.popup_name(chart))

    def test_one_popup_per_chart(self):
        holder = _type_body(self.text, "te_chart_popups")
        self.assertEqual(re.findall(r"^\s*(\w+) = \{\}$", holder, re.M), [gen.popup_name(c) for c in gen.CHARTS])
        self.assertRegex(holder, r"^\s*size = \{ 100% 100% \}")
        for chart in gen.CHARTS:
            body = self.popup(chart)
            with self.subTest(chart=chart.id):
                self.assertRegex(self.text, rf"\btype {gen.popup_name(chart)} = te_ui_popup \{{")
                self.assertEqual(_override_bodies(body, "popup_visible")[0].strip(),
                                 f"visible = \"[GetVariableSystem.HasValue('te_popup', 'chart_{chart.id}')]\"")
                self.assertEqual(gen.popup_key(chart), f"chart_{chart.id}")
                # the range row, the large chart, then the section's key, once each
                names = re.findall(r"^\t*(te_\w+) = \{\}$", _override_bodies(body, "popup_list")[0], re.M)
                key = [gen.KEYS[chart.system][0]] if chart.system in gen.KEYS else []
                self.assertEqual(names, [gen.range_row_name(chart.range), gen.wrapper_name(chart, gen.LARGE)] + key)

    def test_the_title(self):
        """The header is the chart's own title, static text (it sits outside
        the popup's datacontexts; a concept link reads nothing), but for the Strategic Reserve's eight,
        whose shared "Fill by Month" would not say which good: theirs names
        it, spliced from the good's own name."""
        loc = _loc_values()
        for chart in gen.CHARTS:
            key = gen.popup_title(chart)
            with self.subTest(chart=chart.id):
                self.assertEqual(_override_bodies(self.popup(chart), "popup_title")[0].strip(), f'text = "{key}"')
                self.assertIn(key, loc)
                # a concept link reads nothing; any other [ ] would read data
                self.assertNotIn("[", re.sub(r"\[concept_\w+\]", "", loc[key]), "the header reads no data")
                if chart.system == "strategic_reserve":
                    good = dict(chart.params)["good"]
                    self.assertEqual(loc[key], f"$je_strategic_reserve$: ${good}$")
                else:
                    self.assertIn(f'blockoverride "chart_title" {{ text = "{key}" }}'
                                  if chart.system == "cultural_hegemony" else f'text = "{key}"',
                                  gen.fragment(chart))
        self.assertEqual(sorted(gen.POPUP_TITLES), sorted(f"st_res_{g}" for g in gen.ST_RES_GOODS))
        self.assertEqual(loc["te_chart_gone"], "This chart's system is no longer running.")
        self.assertEqual(loc["te_chart_open_tt"], "See this chart at full size.")

    def test_the_size_fits_the_chart_and_the_screen(self):
        """The large frame plus the shell's margins, a scrollbar and the list's
        margin: 1320 wide for a monthly chart, 1360 for an annual one, as tall
        as its rows, and every popup within a 1600 x 900 screen at UI scale 1."""
        sizes = {}
        for chart in gen.CHARTS:
            width, height = gen.popup_size(chart)
            frame = gen.LARGE[chart.kind].frame
            with self.subTest(chart=chart.id):
                self.assertEqual(_override_bodies(self.popup(chart), "popup_size")[0].strip(),
                                 f"size = {{ {width} {height} }}")
                self.assertGreaterEqual(width, frame[0] + 2 * 35 + 2 * 10 + 8)
                # every row, summed here from the layout itself, so the popup
                # needs no scrollbar: the shell (header_pattern's 56,
                # Window_Margins' 18 and 20, the list's 2 x 6), the range row
                # (a 26 px button, the row's 2 x 4), the chart's text (its 2 x 4
                # margin, a 28 px title, two 18 px legend lines, 2 x 2 spacing),
                # the frame, and the key
                rows = [56 + 18 + 20 + 2 * 6, 26 + 2 * 4, 2 * 4 + 28 + 2 * 18 + 2 * 2, frame[1]]
                if chart.system in KEY_HEIGHTS:
                    rows.append(KEY_HEIGHTS[chart.system])
                self.assertGreaterEqual(height, sum(rows) + 4 * (len(rows) - 3))   # 4 px between the list's rows
                self.assertLessEqual((width, height), gen.SCREEN)
                self.assertLessEqual(height, gen.SCREEN[1])
            sizes.setdefault(chart.kind, set()).add(width)
        self.assertEqual(sizes, {"monthly": {1320}, "annual": {1360}, "annual_pips": {1360}})
        self.assertEqual(gen.SCREEN, (1600, 900))

    def test_the_range_rows_are_the_sections_buttons(self):
        """Each row sets the variable, the values and the labels the sections'
        buttons do, at their width, greyed on the same conditions, so the
        viewer opens at the panel's range and changing it changes both."""
        def buttons(text):
            out = []
            for m in re.finditer(r"te_history_range_button = \{", text):
                button = text[m.end():_close(text, m.end() - 1)]
                var, value = re.search(r"GetVariableSystem\.Set\(\s*'(\w+)',\s*'(\w+)'\s*\)", button).groups()
                width = re.search(r"\bsize = \{ (\d+) 26 \}", button)
                enabled = re.sub(r"\s+", "", re.search(r'enabled = "(.*)"', button).group(1))
                out.append((var, value, re.search(r'text = "(\w+)"', button).group(1),
                            int(width.group(1)) if width else 72, enabled))
            return out
        rows = {}
        for var in gen.RANGES:
            rows[var] = buttons(_type_body(self.text, gen.range_row_name(var)))
            self.assertEqual([b[1] for b in rows[var]], list(gen.RANGES[var].values))
            self.assertEqual({b[0] for b in rows[var]}, {var})
        checked = 0
        for system, path in SECTIONS.items():
            found = buttons(_strip_comments(_read(os.path.join(REPO, path))))
            for i in range(0, len(found), 3):
                with self.subTest(system=system, row=i // 3):
                    self.assertEqual(found[i:i + 3], rows[found[i][0]])
                    checked += 1
        self.assertEqual(checked, len(SECTIONS), "a row a section (the Reserve's in te_st_res_good_row)")

    def test_the_keys_are_the_sections(self):
        """The key under a large chart is the type its section shows, so the
        two can't drift: each defined in the section's file and instanced
        there once."""
        self.assertEqual(sorted(gen.KEYS), ["banking", "cultural_hegemony", "demographics"])
        for system, (name, _height) in gen.KEYS.items():
            text = _strip_comments(_read(os.path.join(REPO, SECTIONS[system])))
            with self.subTest(system=system):
                self.assertRegex(text, rf"(?m)^\ttype {name} = flowcontainer \{{")
                self.assertEqual(len(re.findall(rf"(?<![\w.]){name} = \{{\}}", text)), 1)
                self.assertNotIn(f"{name} = {{\n", text, "the instance adds nothing: the type is the key")
        bank = _type_body(_strip_comments(_read(os.path.join(REPO, SECTIONS["banking"]))), "te_banking_hist_marker_key")
        self.assertIn("te_history_marker_legend = {", bank)
        self.assertEqual(bank.count("using = fontsize_medium"), 2)

    def test_a_key_waits_for_the_first_sample(self):
        """Banking's and Demographics' keys hide until the store holds a
        sample, as their sections' instances did before the keys became types
        (the visible moved into the type); Cultural Hegemony's always shows."""
        lists = {"banking": "JournalEntry.GetCountry.MakeScope.GetList('te_hist')",
                 "demographics": "Country.MakeScope.GetList('te_dg_hist')"}
        for system, (name, _height) in gen.KEYS.items():
            body = _type_body(_strip_comments(_read(os.path.join(REPO, SECTIONS[system]))), name)
            own = [ln.strip() for ln in body.split("\n") if re.match(r"^\t\t\w", ln)]   # the type's own lines
            with self.subTest(system=system):
                visibles = [ln for ln in own if ln.startswith("visible = ")]
                if system in lists:
                    self.assertEqual(visibles, [f'visible = "[Not( IsDataModelEmpty( {lists[system]} ) )]"'])
                else:
                    self.assertEqual(visibles, [])
                    self.assertNotIn("visible", body)


def _fixed_width(node):
    """A node's width when its minimumsize and maximumsize fix it, else None:
    a width its content can't change."""
    lo, hi = gui_tree.size(node, "minimumsize"), gui_tree.size(node, "maximumsize")
    return lo[0] if lo and hi and lo[0] == hi[0] else None


def _value(node, key):
    """A node's own property `key`, or None."""
    prop = node.prop(key)
    return prop.value if prop else None


def _named(node, kind, name):
    return [c for c in node.children if c.kind == kind and c.name == name]


class ChartWidthTest(unittest.TestCase):
    """Every chart, and its wrapper, has one fixed width: the frame, or the text
    over it where that is wider (gen.Dims.width). C1's wrapper was a centered
    flowcontainer sized by its content, and the engine centered it at the width
    of the chart's text alone, the plot left out: each chart sat half its
    plot's excess over its text right of the next, and the short-titled ones
    ran out of the panel (Banking's Bubble Pressure 157 px, Demographics' Median
    Age 163; gui_modding_guide.md gotcha #46). With the width fixed, every
    chart in a section shares one left edge, as before the registry."""

    @classmethod
    def setUpClass(cls):
        tree = gui_tree.parse(_read(GENERATED))
        cls.wrappers = {n.name: n for n in tree.walk() if n.kind == "type" and n.name.startswith("te_hist_")}
        types = {n.name: n for n in gui_tree.parse(_read(CHART_GUI)).walk() if n.kind == "type"}
        cls.chart_type, cls.legend = types["te_history_chart"], types["te_history_marker_legend"]

    def each(self):
        """(name, chart, size, wrapper) for every wrapper. Each test opens its
        own subTest on the name: a subTest held open across a yield reports a
        failure as GeneratorExit, at the first wrapper only."""
        for chart in gen.CHARTS:
            for size in gen.SIZES:
                name = gen.wrapper_name(chart, size)
                yield name, chart, size, self.wrappers[name]

    def resolved(self, chart_node, name):
        """The chart instance's blockoverride `name`, else the type's block."""
        found = (_named(chart_node, "blockoverride", name)
                 or [n for n in self.chart_type.walk() if n.kind == "block" and n.name == name])
        self.assertTrue(found, f'neither the chart nor te_history_chart has block "{name}"')
        return found[0]

    def chart(self, wrapper):
        (node,) = [c for c in gui_tree.widgets(wrapper) if c.kind == "te_history_chart"]
        return node

    def test_each_wrapper_is_a_centered_column_of_fixed_width(self):
        """Never centered on a width its content gives it (gotcha #43, #46)."""
        for name, chart, size, wrapper in self.each():
            with self.subTest(wrapper=name):
                self.assertEqual(_value(wrapper, "direction"), "vertical")
                self.assertEqual(_value(wrapper, "parentanchor"), "hcenter")
                self.assertEqual(_fixed_width(wrapper), size[chart.kind].width)

    def test_the_chart_is_as_wide_as_its_wrapper(self):
        """The chart inside is fixed at the same width (block "chart_width"), and
        neither the chart nor its title and legend column is anchored: each sits
        at the left of its parent, so no place in the chain depends on a width
        measured from content (gotcha #43). The wrapper alone centers."""
        for name, _chart, _size, wrapper in self.each():
            with self.subTest(wrapper=name):
                node = self.chart(wrapper)
                self.assertEqual(_fixed_width(self.resolved(node, "chart_width")), _fixed_width(wrapper))
                self.assertIsNone(node.prop("parentanchor"))
        self.assertIsNone(self.chart_type.prop("parentanchor"))
        (column,) = [n for n in gui_tree.widgets(self.chart_type) if n.kind == "flowcontainer"]
        self.assertIsNotNone(column.prop("margin_left"), "the title and legend column")
        self.assertIsNone(column.prop("parentanchor"))
        self.assertIsNone(column.prop("widgetanchor"))

    def test_nothing_in_the_chart_is_wider_than_it(self):
        """The plot, and the title row and the legend in their column, fit the
        width: the plot is never wider than the wrapper, and no text widens it."""
        margin = int(next(n for n in self.chart_type.walk() if n.prop("margin_left")).prop("margin_left").value)
        self.assertEqual(margin, gen.TEXT_MARGIN)
        for name, chart, size, wrapper in self.each():
            with self.subTest(wrapper=name):
                node, width = self.chart(wrapper), size[chart.kind].width
                plot = gui_tree.size(self.resolved(node, "plot_size"))
                self.assertEqual(plot, size[chart.kind].frame)
                self.assertLessEqual(plot[0], width)
                title = int(self.resolved(node, "chart_title_width").prop("max_width").value)
                # the open slot shows one button at a time (test_one_open_button_shows)
                if any(w.kind == "te_chart_open_button" for w in self.open_slot(node)):
                    title += gen.OPEN_GAP + gen.OPEN_BUTTON
                legend = int(self.resolved(node, "chart_text_width").prop("max_width").value)
                self.assertLessEqual(margin + max(title, legend), width)
                self.assertLessEqual(int(self.resolved(node, "empty_width").prop("max_width").value), plot[0])

    def open_slot(self, node):
        """What the chart's "chart_open" slot, beside its title, holds."""
        return [w for o in _named(node, "blockoverride", "chart_open") for w in gui_tree.widgets(o)]

    def test_one_open_button_shows(self):
        """The title's width leaves room for one open button. A slot may hold
        more (F1's own-country and foreign viewers' pair) only if each carries
        a visible, and at most one in a slot may show unconditionally, so the
        row never draws two."""
        for name, _chart, _size, wrapper in self.each():
            with self.subTest(wrapper=name):
                buttons = [w for w in self.open_slot(self.chart(wrapper)) if w.kind == "te_chart_open_button"]
                if len(buttons) > 1:
                    self.assertEqual([b.line for b in buttons if b.prop("visible") is None], [])

    def test_the_types_width_is_the_panels_monthly(self):
        """te_history_chart's own width is SMALL's monthly chart's, the 496 px
        frame, as its other defaults are; the generator overrides it elsewhere."""
        blocks = _named(self.chart_type, "block", "chart_width")
        self.assertEqual(len(blocks), 1, 'te_history_chart has one block "chart_width"')
        self.assertEqual(_fixed_width(blocks[0]), gen.SMALL["monthly"].width)
        self.assertEqual(gen.SMALL["monthly"].width, 496)
        self.assertEqual({k: gen.SMALL[k].width for k in gen.KINDS},
                         {"monthly": 496, "annual": 488, "annual_pips": 488})
        self.assertEqual({k: gen.LARGE[k].width for k in gen.KINDS},
                         {"monthly": 1216, "annual": 1256, "annual_pips": 1256})

    def test_a_sections_charts_share_one_width(self):
        """Centered at one width, a section's charts share one left edge."""
        for system in gen.SYSTEMS:
            for size in gen.SIZES:
                with self.subTest(system=system, size=size.name):
                    self.assertEqual(len({size[c.kind].width for c in gen.CHARTS if c.system == system}), 1)

    def test_the_marker_key_wraps_inside_the_charts(self):
        """Banking's pip key (te_history_marker_legend) is the monthly chart's
        width, so it shares the charts' left edge, and each line wraps inside
        it: at Banking's fontsize_medium the marker's line ran past the panel."""
        width = _fixed_width(self.legend)
        self.assertEqual(width, gen.SMALL["monthly"].width)
        margin = gui_tree.size(self.legend, "margin")[0]
        rows = [n for n in self.legend.walk() if n.kind == "flowcontainer"]
        self.assertEqual(len(rows), 2)
        for row in rows:
            with self.subTest(row=row.line):
                (icon,) = [w for w in gui_tree.widgets(row) if w.kind == "icon"]
                (box,) = [w for w in gui_tree.widgets(row) if w.kind == "textbox"]
                self.assertEqual(_value(box, "multiline"), "yes")
                self.assertEqual(_value(box, "autoresize"), "yes")
                used = gui_tree.size(icon)[0] + int(row.prop("spacing").value) + int(box.prop("max_width").value)
                self.assertLessEqual(2 * margin + used, width)


class GeneratorTest(unittest.TestCase):
    def test_generated_file_is_current(self):
        with open(GENERATED, "rb") as f:
            committed = f.read()
        self.assertTrue(committed.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(committed[3:].startswith(b"\xef\xbb\xbf"))    # exactly one BOM
        self.assertEqual(committed.decode("utf-8-sig"), gen.render(),
                         "stale: run python3 scripts/generators/gen_te_history_charts.py")
        self.assertEqual(gen.main(["--check"]), 0)

    def test_check_fails_on_a_file_without_its_bom(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = gen.Path(tmp) / "generated.gui"
            with mock.patch.object(gen, "GUI_OUT", path):
                path.write_bytes(gen.render().encode("utf-8"))
                self.assertEqual(gen.main(["--check"]), 1)
                path.write_bytes(b"\xef\xbb\xbf" + gen.render().encode("utf-8"))
                self.assertEqual(gen.main(["--check"]), 0)
                path.write_bytes(b"\xef\xbb\xbf\xef\xbb\xbf" + gen.render().encode("utf-8"))
                self.assertEqual(gen.main(["--check"]), 1)


if __name__ == "__main__":
    unittest.main()
