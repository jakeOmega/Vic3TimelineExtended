"""Mod calls to vanilla's lobby-appeasement wrappers pass a factor the lobby accepts.

`change_appeasement` takes only a factor the lobby type lists for the sign of
the amount: `appeasement_factors_pro` for a gain, `appeasement_factors_anti`
for a loss (vanilla `common/political_lobbies/00_political_lobbies.txt`;
`docs/guides/scripting_best_practices.md` § `change_appeasement`'s
`appeasement_special_events_*` Factor). Anything else is skipped, and the
engine's error line passes through vanilla's `00_lobby_effects.txt`, where a
registry entry once hid five mod options that had the signs reversed.

The country-lobby lists below are vanilla 1.14.5's. When the game is installed,
`test_table_matches_vanilla` checks them against the game files.
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent

# Factors each country lobby type accepts, by the sign of the amount.
COUNTRY_LOBBY_FACTORS = {
    "lobby_pro_country": {
        "pro": {
            "appeasement_relations_increased", "appeasement_trade_agreement_formed",
            "appeasement_alliance_formed", "appeasement_defensive_pact_formed",
            "appeasement_military_assistance_started", "appeasement_foreign_investment_agreement_formed",
            "appeasement_rivalry_ended", "appeasement_embargo_ended",
            "appeasement_orchestrate_coup_ended", "appeasement_special_events_positive",
        },
        "anti": {
            "appeasement_relations_decreased", "appeasement_trade_agreement_broken",
            "appeasement_alliance_broken", "appeasement_defensive_pact_broken",
            "appeasement_military_assistance_broken", "appeasement_foreign_investment_agreement_broken",
            "appeasement_rivalry_declared", "appeasement_embargo_declared",
            "appeasement_diplomatic_demand_made", "appeasement_diplomatic_play_started",
            "appeasement_orchestrate_coup_started", "appeasement_special_events_negative",
        },
    },
    # Close to a mirror of the pro-country lobby, but not quite: no military
    # assistance factors, and the rival/prestige-rank ones are its own.
    "lobby_anti_country": {
        "pro": {
            "appeasement_relations_decreased", "appeasement_trade_agreement_broken",
            "appeasement_alliance_broken", "appeasement_defensive_pact_broken",
            "appeasement_foreign_investment_agreement_broken", "appeasement_rivalry_declared",
            "appeasement_rival_surpassed", "appeasement_embargo_declared",
            "appeasement_diplomatic_demand_made", "appeasement_diplomatic_play_started",
            "appeasement_overtook_in_prestige_rank", "appeasement_orchestrate_coup_started",
            "appeasement_special_events_negative",
        },
        "anti": {
            "appeasement_relations_increased", "appeasement_trade_agreement_formed",
            "appeasement_alliance_formed", "appeasement_defensive_pact_formed",
            "appeasement_foreign_investment_agreement_formed", "appeasement_rivalry_ended",
            "appeasement_embargo_ended", "appeasement_overtaken_in_prestige_rank",
            "appeasement_orchestrate_coup_ended", "appeasement_special_events_positive",
        },
    },
}

WRAPPER_RE = re.compile(
    r"add_lobby_appeasement_from_diplomacy_(?:unidirectional|bidirectional)\s*=\s*\{([^{}]*)\}"
)


def _arg(block, name):
    m = re.search(r"\b%s\s*=\s*(\S+)" % name, block)
    return m.group(1) if m else None


def wrapper_calls():
    """(path, line, factor, pro_amount, anti_amount) for every mod call of the country wrappers."""
    for path in sorted(list(ROOT.glob("events/**/*.txt")) + list(ROOT.glob("common/**/*.txt"))):
        text = path.read_text(encoding="utf-8-sig", errors="replace")
        for m in WRAPPER_RE.finditer(text):
            block = m.group(1)
            yield (
                path.relative_to(ROOT).as_posix(),
                text.count("\n", 0, m.start()) + 1,
                _arg(block, "FACTOR"),
                _arg(block, "PRO_AMOUNT"),
                _arg(block, "ANTI_AMOUNT"),
            )


def _side(amount):
    return "pro" if float(amount) > 0 else "anti"


class LobbyAppeasementFactorTests(unittest.TestCase):
    def test_wrapper_calls_use_an_accepted_factor(self):
        calls = list(wrapper_calls())
        self.assertGreater(len(calls), 20, "the scan found too few calls; did the wrapper get renamed?")
        problems = []
        for path, line, factor, pro, anti in calls:
            for lobby, amount in (("lobby_pro_country", pro), ("lobby_anti_country", anti)):
                if amount is None or not re.fullmatch(r"-?\d+(\.\d+)?", amount):
                    problems.append(f"{path}:{line}: {lobby} amount {amount!r} is not a literal; check it by hand")
                    continue
                if float(amount) == 0:
                    continue
                side = _side(amount)
                if factor not in COUNTRY_LOBBY_FACTORS[lobby][side]:
                    problems.append(
                        f"{path}:{line}: {factor} with {lobby} amount {amount} needs the {side} list; "
                        "the engine rejects it (reverse the signs, or name the other factor)"
                    )
        self.assertEqual(problems, [])

    def test_table_matches_vanilla(self):
        try:
            from path_constants import base_game_path
            vanilla = Path(base_game_path) / "game/common/political_lobbies/00_political_lobbies.txt"
        except Exception:  # path_constants could not resolve the install
            raise unittest.SkipTest("no Victoria 3 install")
        if not vanilla.is_file():
            raise unittest.SkipTest("no Victoria 3 install")
        text = vanilla.read_text(encoding="utf-8-sig")
        for lobby, sides in COUNTRY_LOBBY_FACTORS.items():
            start = re.search(r"(?m)^%s = \{" % lobby, text).end()
            nxt = re.search(r"(?m)^lobby_\w+ = \{", text[start:])
            body = text[start: start + nxt.start()] if nxt else text[start:]
            for side, factors in sides.items():
                listed = re.search(r"appeasement_factors_%s = \{([^}]*)\}" % side, body)
                self.assertIsNotNone(listed, f"{lobby} has no appeasement_factors_{side}")
                self.assertEqual(set(listed.group(1).split()), factors, f"{lobby} {side}")


if __name__ == "__main__":
    unittest.main()
