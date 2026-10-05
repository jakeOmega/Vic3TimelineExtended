"""Small, fail-closed reader for the alternate banking buttons' numeric rules.

Preserves repeated if/add keys. It only supports the arithmetic and trigger
subset used by this simulation; new script syntax raises rather than vanishing.
"""
from __future__ import annotations

import operator
from pathlib import Path

from paradox_file_parser import ParadoxFileParser


def parse(source: str) -> list:
    tokens = iter(ParadoxFileParser().tokenize(source))

    def body() -> list:
        out = []
        for key in tokens:
            if key == "}":
                return out
            op, value = next(tokens), next(tokens)
            if op not in ("=", "?=", "<", "<=", ">", ">=", "!=", "=="):
                raise ValueError(f"unsupported banking script operator {op}")
            out.append((key.strip('"'), op, body() if value == "{" else value.strip('"')))
        return out

    return body()


def definitions(path: Path) -> dict:
    return {key: body for key, _, body in parse(path.read_text(encoding="utf-8-sig"))}


def field(body: list, name: str):
    return next(value for key, _, value in body if key == name)


class Rules:
    def __init__(self, root: Path):
        self.buttons = definitions(root / "common/scripted_buttons/banking_alt_economy_buttons.txt")
        self.triggers = definitions(root / "common/scripted_triggers/market_triggers.txt")
        self.triggers.update(definitions(root / "common/scripted_triggers/banking_policy_triggers.txt"))
        self.values = definitions(root / "common/script_values/extra_script_values.txt")

    def check(self, body: list, read, mode: str = "AND") -> bool:
        answers = []
        for key, op, value in body:
            if key in ("AND", "OR", "NOT"):
                answer = self.check(value, read, key)
            elif key in ("je:je_banking_cycle", "custom_tooltip"):
                answer = self.check([item for item in value if item[0] != "text"], read)
            elif key in self.triggers:
                answer = self.check(self.triggers[key], read) == (value == "yes")
            elif key == "has_modifier":
                answer = read("has_modifier:" + value)
            elif key == "has_law":
                answer = read("has_law:" + value.removeprefix("law_type:"))
            elif value in ("yes", "no"):
                answer = bool(read(key)) == (value == "yes")
            else:
                lhs, rhs = read(key), self.number(value, read)
                answer = {"=": operator.eq, "==": operator.eq, "!=": operator.ne,
                          "<": operator.lt, "<=": operator.le,
                          ">": operator.gt, ">=": operator.ge}[op](lhs, rhs)
            answers.append(answer)
        if mode == "NOT":
            return not any(answers)
        return any(answers) if mode == "OR" else all(answers)

    def number(self, value, read) -> float:
        if isinstance(value, list):
            return self.evaluate(value, read)
        try:
            return float(value)
        except ValueError:
            if value in self.values:
                return self.evaluate(self.values[value], read)
            return float(read(value))

    def evaluate(self, body: list, read, initial: float = 0.0) -> float:
        result, chain_done = initial, False
        for key, _, value in body:
            if key in ("if", "else_if", "else"):
                if key == "if":
                    chain_done = False
                run = not chain_done and (key == "else" or self.check(field(value, "limit"), read))
                if run:
                    chain_done = True
                    result = self.evaluate([item for item in value if item[0] != "limit"], read, result)
            elif key == "round":
                if value != "yes":
                    raise ValueError("unsupported round instruction")
                result = math_round(result)
            else:
                x = self.number(value, read)
                if key == "value":
                    result = x
                elif key == "add":
                    result += x
                elif key == "subtract":
                    result -= x
                elif key == "multiply":
                    result *= x
                elif key == "divide":
                    result /= x
                elif key == "min":
                    result = max(result, x)  # Clausewitz min is a LOWER bound
                elif key == "max":
                    result = min(result, x)
                else:
                    raise ValueError(f"unsupported banking numeric rule {key}")
        return result


def math_round(value: float) -> float:
    # Transfer amounts are positive; engine-style nearest integer, not bankers' rounding.
    return float(int(value + 0.5))
