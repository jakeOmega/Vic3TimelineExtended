# -*- coding: utf-8 -*-
"""State-input treaty articles: the state's effects follow the treaty.

Free Port Concession, Minority Protection, Religious Mission Rights and
Demilitarized Zone put a static modifier and a variable on the state they name.
The article's on_break / on_withdrawal remove them, but a treaty can end
without either doing so (a party annexed), and the state can change hands while
the treaty stands. A player who annexed Belgium kept a free port in Flanders
with no treaty behind it. So the state is checked against the treaty: monthly
and on a change of owner, te_sync_state_treaty_articles clears a state no
longer conceded under an in-force article, and te_restore_state_treaty_articles
puts the effects back when it returns to its conceder
(common/scripted_effects/treaty_article_effects.txt).

Each article has one apply and one clear effect, called by its own hooks and by
both checks. These tests keep a new state-input article, or a new effect on one,
from skipping that wiring: the engine reports none of it.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))

EFFECTS = os.path.join(REPO, "common", "scripted_effects", "treaty_article_effects.txt")
TRIGGERS = os.path.join(REPO, "common", "scripted_triggers", "misc_triggers.txt")
ON_ACTIONS = os.path.join(REPO, "common", "on_actions", "extra_on_actions.txt")
ARTICLES_DIR = os.path.join(REPO, "common", "treaty_articles")

# article -> (apply effect, clear effect, the variable the sync gates on)
ARTICLES = {
    "free_port_concession": ("te_free_port_state_apply", "te_free_port_state_clear", "has_free_port"),
    "minority_protection": ("te_minority_protection_state_apply", "te_minority_protection_state_clear", "has_minority_protection"),
    "religious_mission_rights": ("te_religious_mission_state_apply", "te_religious_mission_state_clear", "religious_mission_country"),
    "demilitarized_zone": ("te_demilitarized_zone_state_apply", "te_demilitarized_zone_state_clear", "has_demilitarized_zone"),
}


def _read(path):
    with open(path, encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _body(text, name, start=0):
    """The body of the first ``name = { ... }`` block at or after ``start``."""
    m = re.compile(r"(?<![\w.:])" + re.escape(name) + r"\s*=\s*\{").search(text, start)
    if m is None:
        raise AssertionError(f"{name} not found")
    depth = 0
    for i in range(m.end() - 1, len(text)):
        if text[i] == "{":
            depth += 1
        elif text[i] == "}":
            depth -= 1
            if depth == 0:
                return text[m.end():i]
    raise AssertionError(f"{name} is not closed")


def _top_level(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
    if m is None:
        raise AssertionError(f"{name} not found at top level")
    return _body(text, name, m.start())


def _article_texts():
    """{article name: its block} for every mod treaty article."""
    out = {}
    for fn in sorted(os.listdir(ARTICLES_DIR)):
        if not fn.endswith(".txt"):
            continue
        text = _read(os.path.join(ARTICLES_DIR, fn))
        for m in re.finditer(r"^(\w+)\s*=\s*\{", text, re.M):
            out[m.group(1)] = _body(text, m.group(1), m.start())
    return out


def _modifiers_added(block):
    names = re.findall(r"add_modifier\s*=\s*\{\s*name\s*=\s*(\w+)", block)
    names += re.findall(r"add_modifier\s*=\s*(\w+)", block)
    return set(names)


class StateInputArticleRoster(unittest.TestCase):
    def test_every_state_input_article_is_registered(self):
        articles = _article_texts()
        state_input = {
            name for name, body in articles.items()
            if "required_inputs" in body
            and re.search(r"\bstate\b", _body(body, "required_inputs"))
        }
        self.assertEqual(
            state_input, set(ARTICLES),
            "a treaty article with a state input must get an apply/clear pair and "
            "a branch in te_sync_state_treaty_articles and te_restore_state_treaty_articles",
        )


class ArticleHooksUseTheHelpers(unittest.TestCase):
    def setUp(self):
        self.articles = _article_texts()

    def test_hooks_call_apply_and_clear(self):
        for article, (apply, clear, _var) in ARTICLES.items():
            body = self.articles[article]
            with self.subTest(article=article):
                self.assertIn(apply, _body(body, "on_entry_into_force"))
                self.assertIn(clear, _body(body, "on_break"))
                self.assertIn(clear, _body(body, "on_withdrawal"))

    def test_no_state_modifier_written_outside_the_helpers(self):
        for article in ARTICLES:
            body = self.articles[article]
            with self.subTest(article=article):
                for hook in ("on_entry_into_force", "on_break", "on_withdrawal"):
                    hook_body = _body(body, hook)
                    self.assertNotRegex(hook_body, r"\b(add|remove)_modifier\b", hook)
                    self.assertNotRegex(hook_body, r"\b(set|remove)_variable\b", hook)


class ApplyAndClearAgree(unittest.TestCase):
    def setUp(self):
        self.effects = _read(EFFECTS)

    def test_clear_undoes_apply(self):
        for article, (apply, clear, var) in ARTICLES.items():
            apply_body = _top_level(self.effects, apply)
            clear_body = _top_level(self.effects, clear)
            with self.subTest(article=article):
                added = _modifiers_added(apply_body)
                self.assertTrue(added, f"{apply} adds no modifier")
                removed = set(re.findall(r"remove_modifier\s*=\s*(\w+)", clear_body))
                self.assertLessEqual(added, removed, f"{clear} leaves a modifier {apply} adds")
                self.assertRegex(apply_body, r"set_variable\s*=\s*(\{\s*name\s*=\s*)?" + var + r"\b")
                self.assertRegex(clear_body, r"remove_variable\s*=\s*" + var + r"\b")

    def test_free_port_clear_also_drops_the_tariff_modifiers(self):
        clear_body = _top_level(self.effects, "te_free_port_state_clear")
        for name in ("free_port_tariff_import_modifier", "free_port_tariff_export_modifier"):
            self.assertRegex(clear_body, r"remove_modifier\s*=\s*" + name + r"\b")


class SyncAndRestoreCoverEveryArticle(unittest.TestCase):
    def setUp(self):
        self.effects = _read(EFFECTS)

    def test_sync_checks_each_article_against_its_treaty(self):
        sync = _top_level(self.effects, "te_sync_state_treaty_articles")
        branches = re.findall(r"\bif\s*=\s*\{", sync)
        self.assertEqual(len(branches), len(ARTICLES))
        for article, (_apply, clear, var) in ARTICLES.items():
            with self.subTest(article=article):
                pattern = (
                    r"has_variable\s*=\s*" + var + r"\b.*?"
                    r"te_state_article_concession_in_force\s*=\s*\{\s*ARTICLE_TYPE\s*=\s*"
                    + article + r"\s*\}.*?" + clear + r"\s*=\s*yes"
                )
                self.assertRegex(sync, re.compile(pattern, re.S))

    def test_restore_reapplies_each_article(self):
        restore = _top_level(self.effects, "te_restore_state_treaty_articles")
        for article, (apply, _clear, var) in ARTICLES.items():
            with self.subTest(article=article):
                self.assertRegex(restore, r"has_type\s*=\s*" + article + r"\b")
                pattern = (
                    r"limit\s*=\s*\{\s*has_type\s*=\s*" + article + r"\s*\}.*?"
                    r"NOT\s*=\s*\{\s*has_variable\s*=\s*" + var + r"\s*\}.*?" + apply + r"\b"
                )
                self.assertRegex(restore, re.compile(pattern, re.S))

    def test_concession_trigger_reads_the_treaty(self):
        triggers = _read(TRIGGERS)
        concedes = _top_level(triggers, "te_country_concedes_state_article")
        for needle in (
            r"any_scope_treaty",
            r"any_scope_article",
            r"has_type\s*=\s*\$ARTICLE_TYPE\$",
            r"source_country\s*=\s*scope:te_saci_source",
            r"input_state\s*=\s*scope:te_saci_state",
        ):
            self.assertRegex(concedes, needle)
        self.assertIn("te_country_concedes_state_article", _top_level(triggers, "te_state_article_concession_in_force"))


class Wiring(unittest.TestCase):
    def setUp(self):
        self.on_actions = _read(ON_ACTIONS)

    def _listed_in(self, hook):
        names = set()
        for m in re.finditer(r"^" + hook + r"\s*=\s*\{", self.on_actions, re.M):
            names |= set(re.findall(r"\w+", _body(_body(self.on_actions, hook, m.start()), "on_actions")))
        return names

    def test_monthly_state_pulse_runs_the_sync(self):
        self.assertIn("te_state_treaty_article_sync_on_action", self._listed_in("on_monthly_pulse_state"))
        effect = _body(_top_level(self.on_actions, "te_state_treaty_article_sync_on_action"), "effect")
        self.assertRegex(effect, r"te_sync_state_treaty_articles\s*=\s*yes")

    def test_owner_change_syncs_then_restores(self):
        self.assertIn("te_state_treaty_article_owner_change_on_action", self._listed_in("on_state_owner_change"))
        effect = _body(_top_level(self.on_actions, "te_state_treaty_article_owner_change_on_action"), "effect")
        sync = effect.find("te_sync_state_treaty_articles")
        restore = effect.find("te_restore_state_treaty_articles")
        self.assertNotEqual(sync, -1)
        self.assertGreater(restore, sync)


if __name__ == "__main__":
    unittest.main()
