"""Evaluate shipped nuclear risk values and family weights, without copied tuning.

Two-week crisis benchmarks and peace-decade expectations. This is a fixed-posture
model: incident choices, damage, diplomacy and AI feedback are not simulated.
An unheld order is a dispatched launch, not a guaranteed hit or conventional war.
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


class RiskModel:
    def __init__(self, root=ROOT):
        self.values = {k: v for k, _, v in parse_script(root / "common/script_values/nuclear_deterrence_values.txt")}
        self.triggers = {k: v for k, _, v in parse_script(root / "common/scripted_triggers/nuclear_deterrence_triggers.txt")}
        effects = {k: v for k, _, v in parse_script(root / "common/scripted_effects/nuclear_deterrence_effects.txt")}
        self.families = next(v for k, _, v in effects["nd_fire_incident"] if k == "random_list")
        events = {k: v for k, _, v in parse_script(root / "events/nuclear_incident_events.txt")}
        accident = next(v for k, _, v in events["nuclear_incident.30"] if k == "immediate")
        self.accident_draw = next(v for k, _, v in accident if k == "random_list")

    def number(self, value, posture):
        if isinstance(value, list):
            return self.arithmetic(value, posture)
        if value.startswith("var:nd_"):
            return getattr(posture, value[7:])
        if value == "nd_own_danger_band":
            return min(3, posture.danger // 25)
        if value in self.values:
            return self.number(self.values[value], posture)
        return float(value)

    def condition(self, clauses, p):
        answers = []
        for key, op, value in clauses:
            if key in ("OR", "AND", "NOT"):
                parts = [self.condition([part], p) for part in value]
                answer = any(parts) if key == "OR" else all(parts)
                if key == "NOT":
                    answer = not all(parts)
            elif key == "has_variable":
                name = value.removeprefix("nd_")
                answer = getattr(p, name, False) if name in ("punished_skeptic", "concealed_incident") else hasattr(p, name)
            elif key == "has_technology_researched":
                answer = {"satellite_communications": p.satellite_communications, "ICBMs": p.icbms}.get(value, True)
            elif key == "any_scope_diplomatic_pact":
                answer = False  # no covert comms disruption in these scenarios
            elif key == "nd_has_plausible_attacker":
                answer = p.plausible_attacker == (value == "yes")
            elif key == "nd_crisis_stage_at_least":
                answer = p.stage >= int(value[0][2])
            elif key == "is_at_war":
                answer = p.war == (value == "yes")
            elif key in self.triggers:
                answer = self.condition(self.triggers[key], p) == (value == "yes")
            else:
                left, right = self.number(key, p), self.number(value, p)
                answer = {"=": left == right, ">=": left >= right, "<=": left <= right,
                          ">": left > right, "<": left < right}[op]
            answers.append(answer)
        return all(answers)

    def arithmetic(self, clauses, p, initial=0):
        result, branch_taken = initial, False
        for key, _, value in clauses:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    branch_taken = False
                limit = next((v for k, _, v in value if k == "limit"), [])
                if (key == "if" or not branch_taken) and self.condition(limit, p):
                    result = self.arithmetic([x for x in value if x[0] != "limit"], p, result)
                    branch_taken = True
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

    def weights(self, p):
        weights = {}
        for weight, _, effects in self.families:
            family = next(v[0][2] for k, _, v in effects if k == "nd_log_incident")
            modifiers = next((v for k, _, v in effects if k == "modifier"), [])
            weights[family] = self.arithmetic(modifiers, p, float(weight))
        return weights

    def unheld_share(self, p):
        weights = self.weights(p)
        warning_automatic = p.authority == 3 or (p.authority == 2 and (p.war or p.stage >= 3))
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
        return dangerous / sum(weights.values()) * (1 - self.number("nd_hold_chance", p) / 100)

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
    print("\nWorld exposure (routine readiness, safeguards 3, central control):")
    p = Posture(safeguards=3)
    _, any_incident, incidents, _ = model.peace(p, years)
    for countries in (1, 2, 8, 20):
        print(f"{countries:2} powers: P(any meaningful incident)={1-(1-any_incident)**countries:.1%}; expected={countries*incidents:.2f}")


if __name__ == "__main__":
    main()
