# -*- coding: utf-8 -*-
"""Every input a mod treaty article requires has a widget to set and show it.

Vanilla draws a treaty article's input widgets by article *type name*: the
quantity slider in the Add dialog only for `money_transfer`, the goods and
amount only for `goods_transfer`. An article with an input no widget answers
opens an Add dialog with its title, two dividers and a greyed Add button, and
the engine logs nothing. `nuclear_arms_limitation` (`required_inputs =
{ quantity }`) shipped that way.

So for each input of each article under `common/treaty_articles/`, each of the
three places an article's inputs are drawn must hold a branch for it, keyed
either generically (`RequiresInput('<input>')`) or on the article itself
(`HasType('<article>')`):

- the Add dialog's selected-value area (`template article_input_fixed_bottom`
  in `gui/right_click_menu.gui`),
- the draft row (`type article_draft` in `gui/treaty_draft_panel.gui`),
- the signed row (the article input widgets in `gui/treaty_panel.gui`).

A mention inside `Not(...)` excludes an input rather than drawing it, and a
`visible` that also tests `HasKind(...)` belongs to the short-description
textbox, so neither counts. See gotcha #28 in `docs/guides/gui_modding_guide.md`.

Picking an input is another matter. `ArticleDraft.GetValidBuildingTypes` lists a
company's building types, and read with no company it crashes the game; Cede
Colony's picker did, so an article with a `building_type` input and no company
needs a picker of its own.
"""

import glob
import os
import re
import unittest

from paradox_file_parser import ParadoxFileParser

REPO = os.path.dirname(os.path.abspath(__file__))

VISIBLE_RE = re.compile(r'visible\s*=\s*"\[(.*)\]"')


def block(text, opener):
    """The brace block that starts at `opener` (which ends with `{`)."""
    start = text.index(opener) + len(opener)
    depth = 1
    for i in range(start, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[start:i]
    raise ValueError(f"unbalanced block after {opener!r}")


def strip_negations(expr):
    """`expr` with every `Not(...)` call removed, nested parentheses included."""
    out = []
    i = 0
    while i < len(expr):
        if expr.startswith("Not(", i):
            depth = 0
            j = i + 3
            while j < len(expr):
                if expr[j] == "(":
                    depth += 1
                elif expr[j] == ")":
                    depth -= 1
                    if depth == 0:
                        break
                j += 1
            i = j + 1
        else:
            out.append(expr[i])
            i += 1
    return "".join(out)


def drawing_expressions(text):
    """The positive half of every widget `visible` in `text`."""
    exprs = []
    for match in VISIBLE_RE.finditer(text):
        expr = match.group(1)
        if "HasKind(" in expr:
            continue
        exprs.append(strip_negations(expr))
    return exprs


def uncovered(articles, text):
    """(article, input) pairs no expression in `text` draws."""
    exprs = drawing_expressions(text)
    missing = []
    for article, inputs in sorted(articles.items()):
        for key in inputs:
            generic = f"RequiresInput('{key}')"
            named = f"HasType('{article}')"
            if not any(generic in e or named in e for e in exprs):
                missing.append((article, key))
    return missing


def mod_article_inputs():
    parser = ParadoxFileParser()
    for path in sorted(glob.glob(os.path.join(REPO, "common", "treaty_articles", "*.txt"))):
        parser.parse_file(path, apply_directives=False)
    articles = {}
    for name, entry in parser.data.items():
        body = entry[1] if isinstance(entry, tuple) else entry
        if not isinstance(body, dict):
            continue
        inputs = body.get("required_inputs")
        if inputs is None:
            continue
        inputs = inputs[1] if isinstance(inputs, tuple) else inputs
        articles[name] = list(inputs)
    return articles


def read(rel):
    with open(os.path.join(REPO, rel), encoding="utf-8-sig") as f:
        return f.read()


VALID_BUILDING_TYPES = "ArticleDraft.GetValidBuildingTypes"


def enclosing_block(text, pos):
    """The text of the innermost brace block around `pos`."""
    depth = 0
    for start in range(pos, -1, -1):
        if text[start] == "}":
            depth += 1
        elif text[start] == "{":
            if depth == 0:
                break
            depth -= 1
    depth = 0
    for end in range(pos, len(text)):
        if text[end] == "{":
            depth += 1
        elif text[end] == "}":
            if depth == 0:
                return text[start:end]
            depth -= 1
    raise ValueError("unbalanced block")


def strip_comments(text):
    """`text` with each `#` comment blanked, keeping `#` inside quotes (`#b`)."""
    out = []
    for line in text.split("\n"):
        quoted = False
        for i, ch in enumerate(line):
            if ch == '"':
                quoted = not quoted
            elif ch == "#" and not quoted:
                line = line[:i]
                break
        out.append(line)
    return "\n".join(out)


def top_level(block_text):
    """`block_text` without its nested blocks: the widget's own properties."""
    out, depth = [], 0
    for ch in block_text:
        if ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
        elif depth == 0:
            out.append(ch)
    return "".join(out)


def unguarded_valid_building_types(text):
    """Line numbers of GetValidBuildingTypes reads whose widget has no company.

    The engine lists a company's building types there: with no company the
    data is no list, and the game crashes (`This data is likely not a
    container`, then an access violation). Vanilla reads it only in the
    monopoly picker, on a widget whose own datacontext is the company and
    whose own `visible` requires it, so that is the one form accepted: a
    guard on a parent widget is flagged too."""
    text = strip_comments(text)
    lines = []
    for match in re.finditer(re.escape(VALID_BUILDING_TYPES), text):
        own = top_level(enclosing_block(text, match.start())[1:])
        guarded = 'datacontext = "[ArticleDraft.GetCompany]"' in own and any(
            "Company.IsValid" in strip_negations(m.group(1)) for m in VISIBLE_RE.finditer(own)
        )
        if not guarded:
            lines.append(text.count("\n", 0, match.start()) + 1)
    return lines


class TreatyArticleInputWidgetTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.articles = mod_article_inputs()

    def test_parser_finds_the_known_inputs(self):
        self.assertEqual(self.articles.get("nuclear_arms_limitation"), ["quantity"])
        self.assertEqual(self.articles.get("seize_company"), ["company"])

    def test_add_dialog_draws_every_input(self):
        text = block(read("gui/right_click_menu.gui"), "template article_input_fixed_bottom {")
        self.assertEqual(uncovered(self.articles, text), [])

    def test_draft_row_draws_every_input(self):
        text = block(read("gui/treaty_draft_panel.gui"), "type article_draft = vbox {")
        self.assertEqual(uncovered(self.articles, text), [])

    def test_signed_row_draws_every_input(self):
        self.assertEqual(uncovered(self.articles, read("gui/treaty_panel.gui")), [])

    def test_valid_building_types_read_only_with_a_company(self):
        # Cede Colony's picker crashed the game, from a war goal and from the
        # treaty designer alike (2026-10-30).
        found = {}
        for path in sorted(glob.glob(os.path.join(REPO, "gui", "**", "*.gui"), recursive=True)):
            rel = os.path.relpath(path, REPO)
            lines = unguarded_valid_building_types(read(rel))
            if lines:
                found[rel] = lines
        self.assertEqual(found, {})

    def test_unguarded_valid_building_types_is_caught(self):
        bare = 'dynamicgridbox = {\n\tdatamodel = "[ArticleDraft.GetValidBuildingTypes]"\n}'
        self.assertEqual(unguarded_valid_building_types(bare), [2])
        guarded = (
            'dynamicgridbox = {\n\tdatacontext = "[ArticleDraft.GetCompany]"\n'
            '\tvisible = "[Company.IsValid]"\n\tdatamodel = "[ArticleDraft.GetValidBuildingTypes]"\n}'
        )
        self.assertEqual(unguarded_valid_building_types(guarded), [])
        negated = guarded.replace("[Company.IsValid]", "[Not(Company.IsValid)]")
        self.assertEqual(unguarded_valid_building_types(negated), [4])
        nested = (
            'dynamicgridbox = {\n\tdatamodel = "[ArticleDraft.GetValidBuildingTypes]"\n'
            '\twidget = {\n\t\tdatacontext = "[ArticleDraft.GetCompany]"\n\t\tvisible = "[Company.IsValid]"\n\t}\n}'
        )
        self.assertEqual(unguarded_valid_building_types(nested), [2])
        self.assertEqual(unguarded_valid_building_types("# reads ArticleDraft.GetValidBuildingTypes\n"), [])

    def test_building_type_without_company_has_its_own_picker(self):
        # With no company the engine has no list to offer, so such an article
        # needs a picker of its own, named for it in the Add dialog's lists.
        exprs = drawing_expressions(block(read("gui/right_click_menu.gui"), "template article_input_items {"))
        missing = [
            article for article, inputs in sorted(self.articles.items())
            if "building_type" in inputs and "company" not in inputs
            and not any(f"HasType('{article}')" in e for e in exprs)
        ]
        self.assertEqual(missing, [])
        self.assertIn("te_cede_colony", self.articles)

    def test_negated_mention_does_not_count(self):
        text = (
            'visible = "[And(ArticleDraft.RequiresInput(\'goods\'), '
            'Not(ArticleDraft.RequiresInput(\'quantity\')))]"'
        )
        self.assertEqual(uncovered({"x": ["quantity"]}, text), [("x", "quantity")])
        self.assertEqual(uncovered({"x": ["goods"]}, text), [])

    def test_description_textbox_does_not_count(self):
        text = (
            'visible = "[And(Article.HasKind(\'mutual\'), '
            'Article.RequiresInput(\'quantity\'))]"'
        )
        self.assertEqual(uncovered({"x": ["quantity"]}, text), [("x", "quantity")])


if __name__ == "__main__":
    unittest.main()
