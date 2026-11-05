"""gui/00_te_law_effects.gui (scripts/generators/gen_law_effects_gui.py):
vanilla's law tooltips and change-law panel, with a taxation law's effects
text, which prices its revenue at every tax level, behind a hover."""
from __future__ import annotations

from pathlib import Path
import re
import sys
import unittest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import gen_law_effects_gui as gen  # noqa: E402


def _read(path):
    return Path(path).read_text(encoding="utf-8-sig")


def _loc():
    keys = {}
    for path in (ROOT / "localization" / "english").glob("*_l_english.yml"):
        for line in _read(path).splitlines():
            m = re.match(r'\s+([\w.]+):\d*\s+"(.*)"\s*$', line)
            if m:
                keys[m.group(1)] = m.group(2)
    return keys


def _type(lines, name):
    start, end = gen.type_span(lines, name)
    return lines[start:end + 1]


def _costly(line):
    return "GetEffectDesc(" in line or "GetDeltaEffectDesc(" in line


def _unmod(lines):
    """The lines with every MOD block taken out, stripped of indentation."""
    out, inside = [], False
    for line in lines:
        if line.strip().startswith(gen.MOD_OPEN):
            inside = True
        elif line.strip() == gen.MOD_CLOSE:
            inside = False
        elif not inside:
            out.append(line.strip())
    return out


class GeneratedFileTest(unittest.TestCase):

    def test_the_committed_file_is_the_generators_output(self):
        raw = gen.OUT.read_bytes()
        self.assertTrue(raw.startswith(b"\xef\xbb\xbf"))
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf\xef\xbb\xbf"))
        self.assertEqual(raw[3:].decode("utf-8"), gen.generated_gui(),
                         "run python3 scripts/generators/gen_law_effects_gui.py")

    def test_only_marked_blocks_differ_from_vanilla(self):
        mod = _read(gen.OUT).split("\n")
        for fixture, _, types in gen.SOURCES:
            vanilla = _read(gen.FIXTURES / fixture).split("\n")
            for name, *_ in types:
                with self.subTest(type=name):
                    self.assertEqual(_unmod(_type(mod, name)), [line.strip() for line in _type(vanilla, name)])

    def test_every_effects_text_is_hidden_for_a_taxation_law(self):
        """Each GetEffectDesc and GetDeltaEffectDesc call sits in a container
        whose own `visible` hides it for a taxation law, and every call
        vanilla's types make is still there."""
        lines = _read(gen.OUT).split("\n")
        hidden_line = f'visible = "[Not({gen.IS_TAX})]"'
        stack, calls = [], 0
        for line in lines:
            if line.strip() == hidden_line and stack:
                stack[-1] = True
            if _costly(line):
                calls += 1
                self.assertIn(True, stack, line.strip())
            for _ in range(line.count("{") - line.count("}")):
                stack.append(False)
            for _ in range(line.count("}") - line.count("{")):
                stack.pop()
        vanilla = 0
        for fixture, _, types in gen.SOURCES:
            fixture_lines = _read(gen.FIXTURES / fixture).split("\n")
            vanilla += sum(1 for name, *_ in types for line in _type(fixture_lines, name) if _costly(line))
        self.assertEqual(calls, vanilla)

    def test_a_taxation_law_shows_the_header_and_the_line(self):
        """Each effects text has its line for a taxation law, under the same
        header vanilla's text has (one copy hidden for it, one shown), and
        the comparison view's too where vanilla has one."""
        lines = _read(gen.OUT).split("\n")

        def widget(i):
            """The lines of the widget whose property is line i."""
            indent = len(lines[i]) - len(lines[i].lstrip("\t"))
            start = next(j for j in range(i, -1, -1) if lines[j].rstrip().endswith("{")
                         and len(lines[j]) - len(lines[j].lstrip("\t")) == indent - 1)
            return [line.strip() for line in lines[start:i + 1]]

        def for_tax(i):
            """The widget's own `visible` shows it for a taxation law only."""
            return any(line.startswith('visible = "') and gen.IS_TAX in line and f"Not({gen.IS_TAX})" not in line
                       for line in widget(i))

        expected, headers = {}, {"DATA_LAW_EFFECTS_HEADER": 0, "DATA_LAW_DELTA_EFFECTS_HEADER": 0}
        for _, _, types in gen.SOURCES:
            for _, _, link, delta_link in types:
                expected[link] = expected.get(link, 0) + 1
                headers["DATA_LAW_EFFECTS_HEADER"] += 2
                if delta_link:
                    expected[delta_link] = expected.get(delta_link, 0) + 1
                    headers["DATA_LAW_DELTA_EFFECTS_HEADER"] += 2
        self.assertTrue(headers["DATA_LAW_DELTA_EFFECTS_HEADER"], "vanilla's comparison view went: update the test")
        for text, count in list(expected.items()) + list(headers.items()):
            with self.subTest(text=text):
                sites = [i for i, line in enumerate(lines) if line.strip() == f'text = "{text}"']
                self.assertEqual(len(sites), count)
                shown_for_tax = [i for i in sites if for_tax(i)]
                self.assertEqual(len(shown_for_tax), count if text in expected else count // 2)

    def test_a_taxation_law_keeps_the_view_toggle(self):
        """The selected law's All effects / Comparative effects toggle shows
        for a taxation law too: a copy shown only for one, its `visible`
        building no text."""
        lines = _read(gen.OUT).split("\n")
        start, end = gen.type_span(lines, "selected_or_enacting_law_content")
        body = [line.strip() for line in lines[start:end + 1]]
        self.assertEqual(body.count('text = "DATA_LAW_DELTA_EFFECTS_BUTTON"'), 2)
        self.assertIn(f'visible = "[{gen.IS_TAX}]"', body)

    def test_it_defines_the_constants_it_uses(self):
        gui = _read(gen.OUT)
        defined = set(re.findall(r"^(@\w+)\s*=", gui, re.M))
        self.assertLessEqual(set(re.findall(r"@\w+", gui)) - {"@"}, defined)

    def test_the_file_name_loads_first(self):
        # CMF's naming for type redefinitions (gotcha #30)
        self.assertTrue(gen.OUT.name.startswith("00_"))


class LocalizationTest(unittest.TestCase):
    """Each link's hover builds the effects text for the law's country, the
    player's own or (another country's law) the law's."""

    def test_each_link_opens_its_text(self):
        loc = _loc()
        for link, function, country in (("te_law_tax_effects", "GetEffectDesc", "GetPlayer.Self"),
                                        ("te_law_tax_effects_country", "GetEffectDesc", "Law.GetCountry.Self"),
                                        ("te_law_tax_delta_effects", "GetDeltaEffectDesc", "GetPlayer.Self")):
            with self.subTest(link=link):
                label = "te_law_tax_delta_effects_label" if "delta" in link else "te_law_tax_effects_label"
                self.assertIn(f"#tooltip:[Law.GetTooltipTag],{link}_tt ", loc[link])
                self.assertIn(f"${label}$", loc[link])
                self.assertEqual(loc[f"{link}_tt"], f"[Law.GetLawType.{function}({country})]")
                self.assertTrue(loc[label])


class DriftTest(unittest.TestCase):
    """generated_gui() raises, naming what moved, when a vanilla patch moves
    the effects widgets, rather than writing a wrong file."""

    @classmethod
    def setUpClass(cls):
        cls.tooltips = _read(gen.FIXTURES / "custom_tooltip.gui")

    def _raises(self, old, new):
        self.assertEqual(self.tooltips.count(old), 1, old)
        with self.assertRaises(ValueError) as ctx:
            gen.generated_gui({"custom_tooltip.gui": self.tooltips.replace(old, new)})
        return str(ctx.exception)

    def test_a_widget_between_header_and_text_raises(self):
        old = ('\t\t\t\ttext = "DATA_LAW_EFFECTS_HEADER"\n\t\t\t}\n\n\t\t\tcustom_tooltip_textbox_with_empty_line = {\n'
               '\t\t\t\tvisible = "[Not(StringIsEmpty(Law.GetLawType.GetEffectDesc(GetPlayer.Self)))]"')
        new = old.replace("\t\t\t}\n\n", "\t\t\t}\n\n\t\t\twidget = { size = { 1 1 } }\n\n", 1)
        self.assertIn("FancyTooltip_Law", self._raises(old, new))

    def test_a_changed_country_raises(self):
        old = '\t\t\t\ttext = "[Law.GetLawType.GetEffectDesc(Country.Self)]"'
        self.assertIn("FancyTooltip_LawWithCountryContext",
                      self._raises(old, old.replace("Country.Self", "GetPlayer.Self")))

    def test_a_missing_type_raises(self):
        self.assertIn("FancyTooltip_LawWithCountryContext",
                      self._raises("\ttype FancyTooltip_LawWithCountryContext = ", "\ttype Renamed = "))


if __name__ == "__main__":
    unittest.main()
