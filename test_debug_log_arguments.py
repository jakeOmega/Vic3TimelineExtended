"""No `debug_log` string names a scripted-effect argument.

A `$X$` inside a quoted string isn't substituted reliably. Vanilla 1.14.5 put the value in but dropped the
character before it (`"(kind $KIND$)"` logged `(kind1$)`, `scripting_best_practices.md`, "No `$PARAM$` inside the
string"), and vanilla 1.15 "fixed script arguments being substituted inside quoted strings" without saying which
way. Twenty such lines in twelve helpers printed garbled `TE_SELF_CHECK` names (`nd_trade_$CODE$`) until the 1.15
migration rewrote them to read a record the effect keeps, a literal per argument, or the copies in
`common/scripted_effects/te_debug_log_arg_effects.txt`. This keeps it that way.

One exemption: the 1.15 probe's `TE_PROBE_115 c19_quoted_arg_*` lines
(`common/scripted_effects/te_probe_115_effects.txt`) quote an argument on purpose, to read in game which way 1.15
substitutes it (C19). A string that starts `TE_PROBE_115 c19_` is skipped (`EXEMPT`).

Run: python3 test_debug_log_arguments.py
"""

import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SCAN = ("common", "events")
# debug_log = "<string>": the string runs to its closing quote on the same line
LINE = re.compile(r'\bdebug_log\s*=\s*"([^"\n]*)"')
ARG = re.compile(r"\$[A-Za-z_][A-Za-z0-9_]*\$")
# the C19 probe's lines, which quote an argument to test the substitution itself
EXEMPT = "TE_PROBE_115 c19_"
COPIES = ROOT / "common" / "scripted_effects" / "te_debug_log_arg_effects.txt"


def offenders(root=ROOT):
    """[(relpath, line number, argument)] for every `$X$` inside a debug_log string under common/ and events/."""
    found = []
    for base in SCAN:
        for path in sorted((root / base).rglob("*.txt")):
            for n, line in enumerate(path.read_text(encoding="utf-8-sig", errors="replace").splitlines(), 1):
                if line.lstrip().startswith("#"):
                    continue
                for m in LINE.finditer(line):
                    if m.group(1).startswith(EXEMPT):
                        continue
                    for arg in ARG.findall(m.group(1)):
                        found.append((str(path.relative_to(root)), n, arg))
    return found


class TestDebugLogArguments(unittest.TestCase):
    def test_no_debug_log_string_names_an_argument(self):
        self.assertEqual(offenders(), [], "print a stored record, a literal per argument, or te_log_args_set's copies")

    def test_the_scan_sees_one(self):
        """The check itself: a quoted $X$ is found; a commented-out line, an unquoted argument and the C19 probe's
        line are not."""
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp) / "common" / "scripted_effects"
            d.mkdir(parents=True)
            (Path(tmp) / "events").mkdir()
            (d / "x.txt").write_text(
                'a = {\n'
                '\tdebug_log = "TE_SELF_CHECK OK x_$CODE$ value=[THIS.Var(\'y\').GetValue|0]"\n'
                '\t# debug_log = "old $KEY$"\n'
                '\tset_variable = { name = z value = flag:$KEY$ }\n'
                '\tdebug_log = "fine [GetGlobalVariable(\'te_log_arg_1\').GetFlagName]"\n'
                '\tdebug_log = "TE_PROBE_115 c19_quoted_arg_a kind=$KIND$"\n'
                '}\n', encoding="utf-8")
            self.assertEqual(offenders(Path(tmp)), [("common/scripted_effects/x.txt", 2, "$CODE$")])

    def test_the_copies_cover_their_slots(self):
        """te_log_args_set fills te_log_arg_1..5 and te_log_args_clear removes each, and te_log_value, behind a
        has_global_variable guard (the read that makes them "used" for the engine's parse-time check)."""
        text = COPIES.read_text(encoding="utf-8-sig")
        for n, arg in enumerate("ABCDE", 1):
            self.assertIn(f"set_global_variable = {{ name = te_log_arg_{n} value = flag:${arg}$ }}", text)
        for name in [f"te_log_arg_{n}" for n in range(1, 6)] + ["te_log_value"]:
            self.assertIn(f"if = {{ limit = {{ has_global_variable = {name} }} remove_global_variable = {name} }}",
                          text)


if __name__ == "__main__":
    unittest.main()
