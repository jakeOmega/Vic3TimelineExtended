"""The Healthcare power bloc principles work through the census (owner, 2026-11-14).

docs/systems/mod_systems/demographics.md, "The Healthcare principles". Technology decides what medicine can do,
so the ladder carries no treatment line; it carries how far medicine reaches (Health Care Access, a level of the
Health System), how fast (Spread of Medicine), Malaria Control, the Family Policy measures' money upkeep and the
late game's Longevity Care Price Fall. With the census off, the absorbed mortality line stands in for access, as
it does on the health laws.
"""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PRINCIPLES = ROOT / "common" / "power_bloc_principles" / "extra_power_bloc_principles.txt"
TYPES = ROOT / "common" / "modifier_type_definitions"

COST = "country_institution_cost_institution_health_system_mult"
SPREAD = "state_medical_diffusion_add"
MALARIA = "state_malaria_control_add"
FAMILY = "country_family_policy_upkeep_mult"
PRICE = "country_longevity_care_price_fall_mult"
ACCESS = "state_health_care_access_add"
ABSORBED = "state_demog_absorbed_mortality_mult"
RECOVERY = "unit_recovery_rate_add"
AID = "power_bloc_can_give_healthcare_aid_bool"

# tier: (member_modifier, institution_modifier a level of the Health System, power_bloc_modifier)
LADDER = {
    1: ({COST: -0.1},
        {RECOVERY: 0.05, ACCESS: 0.005, ABSORBED: -0.005}, {}),
    2: ({COST: -0.2, SPREAD: 0.05},
        {RECOVERY: 0.05, ACCESS: 0.005, ABSORBED: -0.005}, {}),
    3: ({COST: -0.3, SPREAD: 0.05, MALARIA: 0.25, FAMILY: -0.1},
        {RECOVERY: 0.05, ACCESS: 0.01, ABSORBED: -0.01}, {}),
    4: ({COST: -0.4, SPREAD: 0.1, MALARIA: 0.5, FAMILY: -0.2},
        {RECOVERY: 0.05, ACCESS: 0.01, ABSORBED: -0.01}, {AID: 1.0}),
    5: ({COST: -0.5, SPREAD: 0.1, MALARIA: 0.5, FAMILY: -0.3, PRICE: 0.25},
        {RECOVERY: 0.05, ACCESS: 0.015, ABSORBED: -0.015}, {AID: 1.0}),
}
# What the ladder carried until 2026-11-14 and the census has no use for.
DROPPED = ("state_birth_rate_mult", "country_authority_add", "country_loyalism_increases_full_acceptance_mult",
           "country_sol_expectations_target_add")


def _entry(text, name):
    """The top-level `name = { ... }` entry's body, by brace depth, comments dropped."""
    text = re.sub(r"#[^\n]*", "", text)
    start = re.search(rf"(?m)^{re.escape(name)} = \{{", text)
    assert start, name
    depth, i = 1, start.end()
    while depth:
        depth += {"{": 1, "}": -1}.get(text[i], 0)
        i += 1
    return text[start.end():i - 1]


def _block(body, name):
    """{field: value} of the entry's `name = { ... }` block (flat), {} when it has none; `yes` counts 1."""
    found = re.search(rf"(?ms)^\t{name} = \{{(.*?)^\t\}}", body)
    if not found:
        return {}
    return {k: 1.0 if v == "yes" else float(v) for k, v in re.findall(r"(?m)^\s*(\w+) = (\S+)\s*$", found.group(1))}


class TestHealthcarePrinciples(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        text = PRINCIPLES.read_text(encoding="utf-8-sig")
        cls.tiers = {n: _entry(text, f"principle_healthcare_{n}") for n in LADDER}

    def test_each_tier_carries_the_ladder(self):
        for n, (member, institution, bloc) in LADDER.items():
            body = self.tiers[n]
            self.assertEqual(_block(body, "member_modifier"), member, f"tier {n}: member_modifier")
            self.assertEqual(_block(body, "institution_modifier"), institution, f"tier {n}: institution_modifier")
            self.assertEqual(_block(body, "power_bloc_modifier"), bloc, f"tier {n}: power_bloc_modifier")
            self.assertIn("institution = institution_health_system", body, n)

    def test_no_tier_gives_less_than_the_tier_below(self):
        """A tier replaces the one below, so each restates it (scripting_best_practices.md, "Power Bloc Principle
        Tiers Replace the Tier Below"): every line holds or grows in size."""
        for n in range(2, 6):
            for i in (0, 1, 2):
                for field, value in LADDER[n - 1][i].items():
                    self.assertGreaterEqual(abs(LADDER[n][i].get(field, 0.0)), abs(value), f"tier {n}: {field}")

    def test_the_absorbed_line_mirrors_access(self):
        """Access under Full, the same size off deaths outside it: the health laws' pair
        (te_demog_engine_line_injections.txt, modified_health_system.txt)."""
        for n, (_member, institution, _bloc) in LADDER.items():
            self.assertEqual(institution[ABSORBED], -institution[ACCESS], n)

    def test_the_ladder_carries_no_treatment_and_none_of_the_dropped_lines(self):
        for n, body in self.tiers.items():
            self.assertNotRegex(body, r"state_\w+_treatment_add", f"tier {n}: treatment is the technologies'")
            for field in DROPPED:
                self.assertNotIn(field, body, f"tier {n}")

    def test_the_half_point_steps_show(self):
        """Access and the absorbed mortality line show one decimal: a tier's 0.5% a level would read as 0% or 1%."""
        for path, name in ((TYPES / "demographics_modifier_types.txt", ACCESS),
                           (TYPES / "demographics_engine_line_types.txt", ABSORBED)):
            body = _entry(path.read_text(encoding="utf-8-sig"), name)
            self.assertRegex(body, r"\bdecimals = 1\b", name)
            self.assertIn("script_only = yes", body, name)

    def test_family_policy_upkeep_is_registered_as_a_cost(self):
        body = _entry((TYPES / "demographics_modifier_types.txt").read_text(encoding="utf-8-sig"), FAMILY)
        for line in ("color = bad", "percent = yes", "script_only = yes"):
            self.assertIn(line, body)


class TestHealthcareAid(unittest.TestCase):
    """The article tiers IV and V unlock gives its recipient the ladder's pair, flat (owner, 2026-11-14)."""

    ARTICLES = ROOT / "common" / "treaty_articles" / "extra_treaty_articles.txt"

    def test_the_recipient_takes_access_and_the_absorbed_line(self):
        body = _entry(self.ARTICLES.read_text(encoding="utf-8-sig"), "healthcare_aid")
        self.assertEqual(_block(body, "target_modifier"), {
            "country_treaty_leverage_generation_add": 200.0, ACCESS: 0.1, SPREAD: 0.1, ABSORBED: -0.05,
            "state_standard_of_living_add": 1.0})
        self.assertEqual(_block(body, "source_modifier"), {COST: 0.1})

    def test_no_engine_mortality_line_is_left_on_top(self):
        """state_mortality_mult sat on top of the census's rate under Full; with it went its cause tag."""
        body = _entry(self.ARTICLES.read_text(encoding="utf-8-sig"), "healthcare_aid")
        self.assertNotRegex(body, r"\bstate_mortality_mult\b")
        self.assertNotIn("state_death_cause_", body)


if __name__ == "__main__":
    unittest.main()
