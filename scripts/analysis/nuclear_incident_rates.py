"""Evaluate shipped nuclear risk values and family weights, without copied tuning.

Two-week crisis benchmarks, peace-decade expectations, and the rework spec's
calibration cases (docs/superpowers/specs/2026-10-28-nuclear-crisis-rework-design.md
§2): an eight-week Acute crisis for each posture of §2.3, a war-year with an
armed enemy, and a peacetime armed-rival pair-year. This is a fixed-posture
model: incident choices other than the AI's government order, damage, diplomacy
and AI feedback are not simulated. An unheld or ordered launch is a dispatched
launch, not a guaranteed hit or conventional war.
"""

import argparse
import math
import re
from dataclasses import dataclass, replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]


def parse_script(path):
    """Keep repeated clauses and their order, which arithmetic requires."""
    source = Path(path).read_text(encoding="utf-8-sig")
    source = re.sub(r'("[^"\n]*")|#[^\n]*', lambda m: m[1] or "", source)
    tokens = iter(re.findall(r'"[^"\n]*"|[{}]|>=|<=|\?=|[=<>]|[^\s{}=<>]+', source))

    def body(nested=False):
        result = []
        for key in tokens:
            if key == "}":
                if not nested:
                    raise ValueError("unexpected closing brace")
                return result
            op = next(tokens)
            value = next(tokens)
            result.append((key, op, body(True) if value == "{" else value.strip('"')))
        if nested:
            raise ValueError("unclosed block")
        return result

    return body()


@dataclass
class Posture:
    readiness: int = 1
    authority: int = 1
    doctrine: int = 2
    safeguards: int = 1
    strain: float = 0
    reliability: float = 60
    danger: int = 0
    stage: int = 0
    readiness_months: int = 0
    war: bool = False
    plausible_attacker: bool = True
    punished_skeptic: bool = False
    concealed_incident: bool = False
    satellite_communications: bool = True
    icbms: bool = True
    war_band: int = 0              # the war's exposure band (nd_war_danger_band) while at war
    talks: bool = False            # the crisis's talks are open
    suspect_readiness: int = 3     # the suspected attacker's readiness
    survivability: float = 50      # stored survivability (nd_survivability)
    survivors: float = 5           # our survivors against the suspect (Task 3's measure)
    ruler: str = "neutral"         # neutral | cautious | aggressive
    regime: str = "neutral"        # neutral | militarist | restraint
    second_warning_source: bool = True   # recon_satellites
    stockpile: float = 10          # our true warheads (nd_stockpile)
    believed_stockpile: float = 10 # the world's estimate of them (nd_believed_stockpile)
    pgm: bool = False              # precision_guided_munitions
    mainframe: bool = True         # mainframe_computers
    enemy: "Posture | None" = None # scope:nd_sv_enemy, for the survivors values


# The rework spec's §2.3 rows: both sides take the same posture.
ACUTE_ROWS = (
    ("Central, safeguards 3", 1, 3),
    ("Central, safeguards 0", 1, 0),
    ("Delegation, safeguards 3", 2, 3),
    ("Launch on Warning, safeguards 3", 3, 3),
    ("Launch on Warning, safeguards 0", 3, 0),
)


class RiskModel:
    def __init__(self, root=ROOT):
        self.values = {k: v for k, _, v in parse_script(root / "common/script_values/nuclear_deterrence_values.txt")}
        self.triggers = {k: v for k, _, v in parse_script(root / "common/scripted_triggers/nuclear_deterrence_triggers.txt")}
        effects = {k: v for k, _, v in parse_script(root / "common/scripted_effects/nuclear_deterrence_effects.txt")}
        self.families = next(v for k, _, v in effects["nd_fire_incident_family"] if k == "random_list")
        events = {k: v for k, _, v in parse_script(root / "events/nuclear_incident_events.txt")}
        accident = next(v for k, _, v in events["nuclear_incident.30"] if k == "immediate")
        self.accident_draw = next(v for k, _, v in accident if k == "random_list")
        self.warning_options = {
            next(v for k, _, v in option if k == "name"): option
            for k, _, option in events["nuclear_incident.1"] if k == "option"}

    def number(self, value, posture):
        if isinstance(value, list):
            return self.arithmetic(value, posture)
        if value.startswith("var:nd_"):
            return getattr(posture, value[7:])
        if value == "nd_own_danger_band":
            return min(3, posture.danger // 25)
        if value == "nd_war_danger_band":
            return posture.war_band if posture.war else 0
        if value == "nd_stockpile":
            return posture.stockpile
        if value == "nd_believed_stockpile":
            return posture.believed_stockpile
        if value in self.values:
            return self.number(self.values[value], posture)
        return float(value)

    # Triggers whose body reads game state the model has no field for: each is
    # answered from the posture. Any other unknown key raises (number() below).
    def posture_trigger(self, key, value, p):
        yes = value == "yes"
        answers = {
            "ruler_is_cautious": lambda: p.ruler == "cautious",
            "ruler_is_aggressive": lambda: p.ruler == "aggressive",
            "nd_regime_is_militarist": lambda: p.regime == "militarist",
            "nd_regime_is_restraint": lambda: p.regime == "restraint",
            "nd_is_armed": lambda: True,
            "nd_forces_assembled": lambda: p.readiness >= 1,
            # No pledge and no Rules of War ban in these scenarios.
            "nd_pledge_permits_strike": lambda: True,
            "nd_war_law_permits_strategic_strike": lambda: True,
            # The shipped doctrine gate in a war: Warfighting always; Flexible or
            # Compellence once the war threatens us (the model's band 3).
            "nd_doctrine_permits_strike": lambda: p.war and (p.doctrine == 5 or (p.doctrine >= 3 and p.war_band >= 3)),
            "nd_vulnerable_to": lambda: p.survivors < 3,
            # The launch under attack (nuclear_incident.1.c): a war with the
            # suspect or an Acute crisis against it, and no No First Use.
            "nd_launch_under_attack_context": lambda: p.war or p.stage >= 3,
            "nd_launch_under_attack_doctrine": lambda: p.doctrine != 1,
            "nd_crisis_talks_open_either": lambda: p.talks,
        }
        if key not in answers:
            return None
        answer = answers[key]()
        return answer if isinstance(value, list) or yes else not answer

    def condition(self, clauses, p, crisis=False):
        answers = []
        for key, op, value in clauses:
            posture = self.posture_trigger(key, value, p)
            if posture is not None:
                answers.append(posture)
                continue
            if key == "custom_tooltip":
                answers.append(self.condition([c for c in value if c[0] != "text"], p, crisis)
                               if isinstance(value, list) else True)
                continue
            if key == "has_war_with":
                answers.append(p.war)
                continue
            if key == "exists" and value == "scope:nd_hold_suspect":
                answers.append(True)  # every benchmark has a suspected attacker
                continue
            if key in ("OR", "AND", "NOT"):
                parts = [self.condition([part], p, crisis) for part in value]
                answer = any(parts) if key == "OR" else all(parts)
                if key == "NOT":
                    answer = not all(parts)
            elif key == "has_variable":
                name = value.removeprefix("nd_")
                answer = getattr(p, name, False) if name in ("punished_skeptic", "concealed_incident") else hasattr(p, name)
            elif key == "has_technology_researched":
                answer = {"satellite_communications": p.satellite_communications, "ICBMs": p.icbms,
                          "recon_satellites": p.second_warning_source, "precision_guided_munitions": p.pgm,
                          "mainframe_computers": p.mainframe}.get(value, True)
            elif key == "any_scope_diplomatic_pact":
                answer = False  # no covert comms disruption in these scenarios
            elif key == "nd_has_plausible_attacker":
                answer = p.plausible_attacker == (value == "yes")
            elif key == "nd_crisis_stage_at_least":
                answer = p.stage >= int(value[0][2])
            elif key == "nd_in_crisis":
                answer = (p.stage >= 1) == (value == "yes")
            elif key == "always":
                answer = crisis if value == "$CRISIS$" else value == "yes"
            elif key == "is_at_war":
                answer = p.war == (value == "yes")
            elif key in self.triggers:
                answer = self.condition(self.triggers[key], p, crisis) == (value == "yes")
            else:
                left, right = self.number(key, p), self.number(value, p)
                answer = {"=": left == right, ">=": left >= right, "<=": left <= right,
                          ">": left > right, "<": left < right}[op]
            answers.append(answer)
        return all(answers)

    def arithmetic(self, clauses, p, initial=0, crisis=False):
        result, branch_taken = initial, False
        for key, _, value in clauses:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    branch_taken = False
                limit = next((v for k, _, v in value if k == "limit"), [])
                if (key == "if" or not branch_taken) and self.condition(limit, p, crisis):
                    result = self.arithmetic([x for x in value if x[0] != "limit"], p, result, crisis)
                    branch_taken = True
                continue
            if key == "scope:nd_sv_enemy":
                result = self.arithmetic(value, p.enemy, result, crisis)
                continue
            if key == "scope:nd_hold_suspect":
                result = self.arithmetic(value, replace(p, readiness=p.suspect_readiness), result, crisis)
                continue
            if key in ("round", "floor"):
                result = math.floor(result + 0.5) if key == "round" else math.floor(result)
                continue
            operand = self.number(value, p)
            if key == "value":
                result = operand
            elif key == "add":
                result += operand
            elif key == "subtract":
                result -= operand
            elif key == "multiply":
                result *= operand
            elif key == "divide":
                result /= operand
            elif key == "min":
                result = max(result, operand)
            elif key == "max":
                result = min(result, operand)
            else:
                raise ValueError(f"unsupported arithmetic: {key}")
        return result

    def probability(self, p):
        """The actual quantized two-stage random roll, not only its nominal value."""
        rate = self.number("nd_incident_weekly_permille", p)
        if rate <= 10:
            return self.number("nd_incident_tenth_permille", p) / 10000
        if rate <= 100:
            return self.number("nd_incident_permille_whole", p) / 1000
        return self.number("nd_incident_weekly_percent", p) / 100

    def family_weights(self, p, crisis):
        weights = {}
        for weight, _, effects in self.families:
            record = next(v for k, _, v in effects if k == "debug_log" and "type=incident" in v)
            family = re.search(r"family=(\w+);", record)[1]
            modifiers = next((v for k, _, v in effects if k == "modifier"), [])
            weights[family] = self.arithmetic(modifiers, p, float(weight), crisis)
        return weights

    def weights(self, p):
        """Each family's share of a meaningful incident: nd_fire_incident picks the
        base or the crisis part of the week's exposure, then a family within it."""
        base = self.number("nd_incident_base_share", p)
        crisis = self.number("nd_incident_crisis_share", p)
        result = {}
        for part, share in ((False, base), (True, crisis)):
            weights = self.family_weights(p, part)
            total = sum(weights.values())
            for family, weight in weights.items():
                result[family] = result.get(family, 0.0) + (
                    share / (base + crisis) * weight / total if share and total else 0.0)
        return result

    @staticmethod
    def warning_is_automatic(p):
        """Delegation executes a warning only in a war with the suspect."""
        return p.authority == 3 or (p.authority == 2 and p.war)

    def unheld_share(self, p):
        """Share of meaningful incidents that end in a launch nobody halted."""
        return self.dangerous_share(p) * (1 - self.number("nd_hold_chance", p) / 100)

    def dangerous_share(self, p):
        """Share of meaningful incidents that start a launch nobody ordered,
        before the chance that someone in the chain halts it."""
        weights = self.weights(p)
        warning_automatic = self.warning_is_automatic(p)
        dangerous = weights["isolated_commander"] + (weights["unconfirmed_warning"] if warning_automatic else 0)
        if p.authority == 4 and (p.war or p.stage >= 3 or (p.readiness == 3 and p.plausible_attacker)):
            total, explosive = 0.0, 0.0
            for base, _, effects in self.accident_draw:
                modifiers = next((v for k, _, v in effects if k == "modifier"), [])
                weight = self.arithmetic(modifiers, p, float(base))
                assignment = next(v for k, _, v in effects if k == "set_variable")
                kind = next(v for k, _, v in assignment if k == "value")
                total += weight
                if kind in ("1", "2"):
                    explosive += weight
            dangerous += weights["weapons_accident"] * explosive / total
        return dangerous / sum(weights.values())

    def option_weight(self, option, p):
        """An option's ai_chance: base, then each modifier's add or factor in order."""
        chance = next((v for k, _, v in option if k == "ai_chance"), [])
        weight = 0.0
        for key, _, value in chance:
            if key == "base":
                weight = float(value)
            elif key == "modifier":
                trigger = next((v for k, _, v in value if k == "trigger"), [])
                if self.condition(trigger, p):
                    for k, _, v in value:
                        if k == "add":
                            weight += float(v)
                        elif k == "factor":
                            weight *= float(v)
        return weight

    def order_chance(self, p):
        """The AI government's chance of giving the launch order (nuclear_incident.1.c)
        once a warning reaches it: zero where the option is not available."""
        order = self.warning_options["nuclear_incident.1.c"]
        trigger = next((v for k, _, v in order if k == "trigger"), [])
        if not self.condition(trigger, p):
            return 0.0
        weights = {name: self.option_weight(option, p) for name, option in self.warning_options.items()}
        total = sum(weights.values())
        return weights["nuclear_incident.1.c"] / total if total else 0.0

    def launch_chance_week(self, p):
        """Chance a week that this side launches without a real attack: an unheld
        launch nobody ordered, or the government's order on a false warning."""
        weights = self.weights(p)
        to_government = 0.0 if self.warning_is_automatic(p) else weights["unconfirmed_warning"]
        return self.probability(p) * (self.unheld_share(p) + to_government * self.order_chance(p))

    def near_miss_ratio(self, p):
        """Launches halted in the chain for each launch that went ahead."""
        launched = self.launch_chance_week(p)
        held = self.probability(p) * self.dangerous_share(p) * self.number("nd_hold_chance", p) / 100
        return held / launched if launched else math.inf

    def pair_chance(self, a, b, weeks):
        """Chance that either side launches at least once over the weeks."""
        quiet = ((1 - self.launch_chance_week(a)) * (1 - self.launch_chance_week(b))) ** weeks
        return 1 - quiet

    def acute_crisis(self, a, b, weeks=8):
        return self.pair_chance(a, b, weeks)

    def war_year(self, a, b, band):
        def at_war(p):
            return replace(p, war=True, war_band=band, stage=0, danger=0)
        return self.pair_chance(at_war(a), at_war(b), 52)

    def peace_pair_year(self, a, b):
        def at_peace(p):
            return replace(p, war=False, war_band=0, stage=0, danger=0)
        return self.pair_chance(at_peace(a), at_peace(b), 52)

    def at_reliability_target(self, p):
        """The posture with reliability where its safeguards put it."""
        return replace(p, reliability=self.number("nd_reliability_target", p))

    def acute_posture(self, authority, safeguards):
        """§2.3's benchmark side: High Alert, an Acute crisis at danger 75+, no strain."""
        return self.at_reliability_target(Posture(readiness=3, authority=authority, safeguards=safeguards,
                                                  danger=80, stage=3))

    def peace(self, p, years):
        quiet, incidents, orders = 1.0, 0.0, 0.0
        for month in range(years * 12):
            p = replace(p, strain=max(0, min(100, p.strain + self.number("nd_strain_step", p))), readiness_months=month + 1)
            p = replace(p, reliability=max(0, min(100, p.reliability + self.number("nd_reliability_step", p))))
            weeks = (month + 1) * 52 // 12 - month * 52 // 12
            chance = self.probability(p)
            quiet *= (1 - chance) ** weeks
            incidents += weeks * chance
            orders += weeks * chance * self.unheld_share(p)
        return p, 1 - quiet, incidents, orders


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--years", type=int, default=10)
    years = parser.parse_args().years
    if years < 1:
        parser.error("--years must be positive")
    model = RiskModel()
    print("Two high-alert countries, two weeks, strain 0, reliability 60, Existential doctrine:")
    for danger in (0, 25, 50, 75, 100):
        p = Posture(readiness=3, danger=danger, stage=3 if danger >= 70 else 2)
        chance = model.probability(p)
        print(f"danger {danger:3}: {chance:.2%}/country/week; any meaningful incident {1 - (1 - chance)**4:.1%}")
    print(f"\nPeace over {years} years, no incident or diplomacy feedback:")
    print("| Readiness | Safeguards | Authority | P(any meaningful incident) | Expected incidents | Unheld launch orders |")
    print("|---|---|---|---|---|---|")
    for readiness in range(4):
        for safeguards in (0, 3):
            for authority in ((1, 2, 3, 4) if readiness >= 2 else (1,)):
                p = Posture(readiness=readiness, safeguards=safeguards, authority=authority)
                _, any_incident, incidents, orders = model.peace(p, years)
                name = ("Recessed", "Routine", "Heightened", "High alert")[readiness]
                print(f"| {name} | {safeguards} | {authority} | {any_incident:.0%} | {incidents:.2f} | {orders:.2f} |")
    print("\nRework spec §2.3: either side launches, eight-week Acute crisis, danger 80, both at High Alert:")
    for label, authority, safeguards in ACUTE_ROWS:
        side = model.acute_posture(authority, safeguards)
        print(f"| {label} | {model.acute_crisis(side, side):.1%} | near misses per launch "
              f"{model.near_miss_ratio(side):.1f} |")
    print("\nRework spec §2.1: either side launches in a war-year, both Central, safeguards 1, High Alert:")
    war_side = model.at_reliability_target(Posture(readiness=3, authority=1, safeguards=1))
    for band in (2, 3):
        print(f"band {band}: {model.war_year(war_side, war_side, band):.1%}")
    peace_side = model.at_reliability_target(Posture(readiness=2, authority=2, safeguards=2))
    print(f"Peacetime armed-rival pair-year, both Delegation, safeguards 2, Heightened: "
          f"{model.peace_pair_year(peace_side, peace_side):.3%}")
    print("\nWorld exposure (routine readiness, safeguards 3, central control):")
    p = Posture(safeguards=3)
    _, any_incident, incidents, _ = model.peace(p, years)
    for countries in (1, 2, 8, 20):
        print(f"{countries:2} powers: P(any meaningful incident)={1-(1-any_incident)**countries:.1%}; expected={countries*incidents:.2f}")


if __name__ == "__main__":
    main()
