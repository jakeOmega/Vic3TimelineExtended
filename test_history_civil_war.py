# -*- coding: utf-8 -*-
"""A revolution's winner keeps the nation's history charts (#1477).

The two history stores, te_hist (monthly, te_history_effects.txt) and te_dg_hist
(the census's yearly samples, te_demog_history_effects.txt), are variable lists
of containers parented to the recording country. A winner inherits no list, and
the containers die with the loser, so te_history_repair_after_civil_war
(common/scripted_effects/te_history_civil_war_effects.txt) moves the loser's
older samples to the winner. The engine checks none of the pairings below.
"""

import os
import re
import unittest

REPO = os.path.dirname(os.path.abspath(__file__))


def _read(*parts):
    with open(os.path.join(REPO, *parts), encoding="utf-8-sig") as f:
        return re.sub(r"#[^\n]*", "", f.read())


def _block(text, name):
    m = re.search(r"^" + re.escape(name) + r"\s*=\s*\{", text, re.M)
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


EFFECTS = ("common", "scripted_effects", "te_history_civil_war_effects.txt")
SHARED = ("common", "on_actions", "te_civil_war_on_actions.txt")
ON_ACTIONS = ("common", "on_actions", "te_history_civil_war_on_actions.txt")
HISTORY = ("common", "scripted_effects", "te_history_effects.txt")
DEMOG = ("common", "scripted_effects", "te_demog_history_effects.txt")

# KEY -> what the call must pass, read off the store's own helpers.
STORES = {
    "hist": {"LIST": "te_hist", "TMP": "te_hist_tmp", "TAG": "te_hist_sample",
             "PRUNE": "te_history_prune_samples", "SOURCE": HISTORY},
    "dg": {"LIST": "te_dg_hist", "TMP": "te_dg_hist_tmp", "TAG": "te_dg_hist_sample",
           "PRUNE": "te_demog_history_prune", "SOURCE": DEMOG},
}


def _calls():
    repair = _block(_read(*EFFECTS), "te_history_repair_after_civil_war")
    calls = {}
    for body in re.findall(r"te_history_cw_take_store\s*=\s*\{([^{}]*)\}", repair):
        args = dict(re.findall(r"(\w+)\s*=\s*(\S+)", body))
        calls[args["KEY"]] = args
    return repair, calls


class WiringTests(unittest.TestCase):
    def test_called_from_the_shared_layer_between_resolve_and_clear(self):
        won = _block(_read(*SHARED), "te_civil_war_on_won")
        call = won.index("te_history_repair_after_civil_war = yes")
        self.assertLess(won.index("te_civil_war_resolve_sides = yes"), call)
        self.assertLess(call, won.index("te_civil_war_clear = yes"))

    def test_only_on_a_rebel_win_over_a_dead_loser(self):
        repair, _calls_ = _calls()
        self.assertRegex(
            repair, r"^\s*if\s*=\s*\{\s*limit\s*=\s*\{\s*has_variable\s*=\s*te_cw_rebels_won\s*"
            r"var:te_cw_rebels_won\s*=\s*1\s*scope:te_cw_loser\s*\?=\s*\{\s*is_country_alive\s*=\s*no\s*\}\s*\}")

    def test_the_kept_check_runs_monthly(self):
        text = _read(*ON_ACTIONS)
        self.assertRegex(_block(text, "on_monthly_pulse_country"),
                         r"^\s*on_actions\s*=\s*\{\s*te_history_cw_selfcheck_on_action\s*\}\s*$")
        self.assertIn("te_history_cw_selfcheck_kept = yes", _block(text, "te_history_cw_selfcheck_on_action"))


class StoreTests(unittest.TestCase):
    def test_both_stores_with_their_own_helpers_and_caps(self):
        _repair, calls = _calls()
        self.assertEqual(sorted(calls), sorted(STORES))
        sample_cap = re.search(r"^te_history_sample_cap\s*=\s*(\d+)", _read("common", "script_values", "te_history_values.txt"), re.M)
        caps = {"hist": int(sample_cap.group(1)),
                "dg": int(re.search(r"count\s*>=\s*(\d+)\s+has_tag\s*=\s*te_dg_hist_sample",
                                    _block(_read(*DEMOG), "te_demog_history_prune")).group(1)) - 1}
        for key, want in STORES.items():
            got = calls[key]
            with self.subTest(store=key):
                for arg in ("LIST", "TMP", "TAG", "PRUNE"):
                    self.assertEqual(got[arg], want[arg], arg)
                self.assertEqual(int(got["CAP"]), caps[key])
                self.assertEqual(int(got["OVER"]), caps[key] + 1)
                source = _read(*want["SOURCE"])
                self.assertIsNotNone(re.search(r"^" + want["PRUNE"] + r"\s*=\s*\{", source, re.M), "the pruner exists")
                self.assertIn("tags = { " + ("te_hist " if key == "hist" else "") + want["TAG"] + " }", source)

    def test_a_sample_is_moved_to_the_winner_before_the_list_takes_it(self):
        body = _block(_read(*EFFECTS), "te_history_cw_take_store")
        self.assertRegex(
            body,
            r"limit\s*=\s*\{\s*var:te_hist_i\s*<\s*scope:te_hcw_winner\.var:te_hcw_floor\s*\}\s*"
            r"set_parent\s*=\s*scope:te_hcw_winner\s*save_scope_as\s*=\s*te_hcw_moved\s*"
            r"scope:te_hcw_winner\s*=\s*\{\s*add_to_variable_list\s*=\s*\{\s*name\s*=\s*\$LIST\$\s+target\s*=\s*scope:te_hcw_moved\s*\}")
        # The cap before the sort: the sort reads at most $CAP$ samples.
        self.assertLess(body.index("while = {"), body.index("te_history_cw_sort = {"))

    def test_the_sort_replaces_the_list_only_when_the_copy_is_complete(self):
        body = _block(_read(*EFFECTS), "te_history_cw_sort")
        swap = body.index("clear_variable_list = $LIST$")
        gate = re.search(r"var:te_hcw_n_sorted\s*>\s*0\s*var:te_hcw_n_sorted\s*=\s*var:te_hcw_n_live", body)
        self.assertIsNotNone(gate)
        self.assertLess(gate.end(), swap)
        for helper in ("te_history_cw_sort", "te_history_cw_take_store"):
            with self.subTest(helper=helper):
                for m in re.finditer(r"ordered_in_list\s*=\s*\{", _block(_read(*EFFECTS), helper)):
                    self.assertIn("order_by = te_history_sample_order", _block(_read(*EFFECTS), helper)[m.end():m.end() + 200])


class SelfCheckTests(unittest.TestCase):
    def test_both_lines_say_ok_and_broken_once_a_game(self):
        text = _read(*EFFECTS)
        read = _block(text, "te_history_cw_selfcheck_read")
        kept = _block(text, "te_history_cw_selfcheck_kept")
        for verdict in ("OK", "BROKEN"):
            with self.subTest(verdict=verdict):
                self.assertEqual(read.count(f'"TE_SELF_CHECK {verdict} history_after_civil_war '), 1)
                self.assertEqual(kept.count(f'"TE_SELF_CHECK {verdict} history_after_civil_war_kept '), 1)
        self.assertIn("NOT = { has_global_variable = te_hcw_selfcheck_read_done }", read)
        self.assertEqual(read.count("set_global_variable = te_hcw_selfcheck_read_done"), 2)
        # Judged only for a loser that kept a store.
        self.assertIn("scope:te_cw_loser = { has_variable = te_hist_since_y }", read)
        # The kept check is armed only by an OK and disarms itself.
        self.assertEqual(text.count("name = te_hcw_check_due_i value"), 1)
        self.assertIn("remove_variable = te_hcw_check_due_i", kept)

    def test_the_play_test_list_names_both(self):
        with open(os.path.join(REPO, "docs", "testing", "charts-help-national-info-playtest.md"), encoding="utf-8") as f:
            doc = f.read()
        for name in ("history_after_civil_war", "history_after_civil_war_kept"):
            with self.subTest(name=name):
                self.assertIn(f"`TE_SELF_CHECK … {name}`", doc)


if __name__ == "__main__":
    unittest.main()
