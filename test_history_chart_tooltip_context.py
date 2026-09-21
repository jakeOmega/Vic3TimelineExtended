# -*- coding: utf-8 -*-
"""A history-chart bar tooltip renders with ONLY the bar's own data context.

`gui/journal_entry_widgets/te_history_chart.gui` draws one item per stored
month over `datamodel = "[JournalEntry.GetCountry.MakeScope.GetList('te_hist')]"`
and gives each item `datacontext = "[Scope.GetScriptContainer]"`. A loc string
rendered as that item's `tooltip` gets a **fresh** data-context set holding the
item's own `ScriptContainer` and nothing else — the `JournalEntry` context the
datamodel itself was resolved against is gone by then.

A loc key that reaches `JournalEntry` from a bar tooltip therefore renders as
nothing and logs four lines per frame per bar:

    New data types does not contain a 'JournalEntry' data context
    No context supplied (Use SetDataContext), wanted context of type
      'JournalEntry' for 'JournalEntry.GetCountry.MakeScope '
    Promote 'SetRoot' returned nullptr, in 'GuiScope.SetRoot( ... ).End '
    Data error in loc string 'te_hist_tt_markers'

That is invisible in the UI (the section simply does not appear) and expensive
in the log: 2,239 of those in debug.log in two and a half minutes of hovering,
mirrored again in error.log, rotated all six generations of both. `te_hist_tt_markers` and `te_hist_tt_ch_markers`
both had it, which silently broke the marker tooltip on nine of the eleven
charts. Both now root their scripted-GUI call at `GetPlayer.MakeScope` — the
handlers never read the country root, they only read `scope:te_hist_sample`.

This test is the guard: no loc key reachable from a `bar_tooltip` blockoverride
may reference a data context the bar does not have.
"""

import glob
import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

# Data roots a bar tooltip may use: the item's own context, plus the globals
# that need no context at all. Anything else has to come from a widget further
# up the tree and will not be there.
ALLOWED_ROOTS = {
    "ScriptContainer",  # the month's sample container — the item's datacontext
    "GuiScope",         # scope builder, needs no context of its own
    "GetPlayer",        # global
    "GetScriptedGui",   # global
    "GetStaticModifier",  # global
    "GetDefine",        # global
    "Concept",          # global
    "SelectLocalization",  # loc helper, not a data context
    "AddLocalizationIf",
    "Localize",
    "Concatenate",
}

_LOC_LINE = re.compile(r'\s*([A-Za-z0-9_.]+):\d*\s+"(.*)"\s*$')
_REF = re.compile(
    r"\$([A-Za-z0-9_.]+)\$"
    r"|SelectLocalization\s*\([^,]+,\s*'([^']+)'\s*,\s*'([^']+)'"
    r"|AddLocalizationIf\s*\([^,]+,\s*'([^']+)'"
)
# Every identifier that STARTS a `.`-chain inside a `[ ... ]` block is a data
# context the render has to supply. Matching only the one right after the `[`
# is not enough: the bug this test exists for had `JournalEntry` buried in
# `GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope )`, four tokens in.
_BRACKET = re.compile(r"\[([^\]]*)\]")
_QUOTED = re.compile(r"'[^']*'")
_CHAIN_ROOT = re.compile(r"(?<![A-Za-z0-9_.'])([A-Za-z][A-Za-z0-9_]*)\s*\.")
_BAR_TOOLTIP = re.compile(
    r'blockoverride\s+"bar_tooltip"\s*\{\s*tooltip\s*=\s*"([A-Za-z0-9_.]+)"'
)


def _load_loc():
    vals = {}
    pattern = os.path.join(REPO, "localization", "english", "**", "*.yml")
    for path in glob.glob(pattern, recursive=True):
        with open(path, encoding="utf-8-sig") as fh:
            for line in fh:
                m = _LOC_LINE.match(line.rstrip("\n"))
                if m:
                    vals[m.group(1)] = m.group(2)
    return vals


def _bar_tooltip_keys():
    keys = set()
    pattern = os.path.join(REPO, "gui", "journal_entry_widgets", "*.gui")
    for path in glob.glob(pattern):
        with open(path, encoding="utf-8-sig") as fh:
            keys.update(_BAR_TOOLTIP.findall(fh.read()))
    return keys


def _data_roots(value):
    """Data contexts a loc value's `[ ... ]` expressions ask the render for."""
    roots = set()
    for segment in _BRACKET.findall(value):
        roots.update(_CHAIN_ROOT.findall(_QUOTED.sub("''", segment)))
    return roots


def _closure(key, vals):
    """Every loc key `key` can pull in, through $splices$ and SelectLocalization."""
    seen, stack = set(), [key]
    while stack:
        cur = stack.pop()
        if cur in seen:
            continue
        seen.add(cur)
        for m in _REF.finditer(vals.get(cur, "")):
            stack.extend(g for g in m.groups() if g and g in vals)
    return seen


class HistoryChartTooltipContextTests(unittest.TestCase):
    def setUp(self):
        self.vals = _load_loc()
        self.bar_keys = _bar_tooltip_keys()

    def test_the_sweep_actually_finds_the_bar_tooltips(self):
        """Guard the guard: a regex that silently matches nothing proves nothing."""
        self.assertGreaterEqual(
            len(self.bar_keys), 6,
            "found almost no bar_tooltip blockoverrides — the .gui shape changed "
            "and this test is no longer checking anything",
        )
        for key in self.bar_keys:
            self.assertIn(
                key, self.vals, f"bar tooltip {key!r} has no localization entry"
            )

    def test_bar_tooltips_only_use_contexts_the_bar_has(self):
        offenders = []
        for key in sorted(self.bar_keys):
            for reached in sorted(_closure(key, self.vals)):
                for root in _data_roots(self.vals.get(reached, "")):
                    if root not in ALLOWED_ROOTS:
                        offenders.append((key, reached, root))
        self.assertEqual(
            offenders, [],
            "a history-chart bar tooltip reaches a data context the bar does not "
            "have; it will render as nothing and spam the log every frame. "
            "Offenders as (bar tooltip, loc key that reaches it, missing root): "
            f"{offenders}",
        )


if __name__ == "__main__":
    unittest.main()
