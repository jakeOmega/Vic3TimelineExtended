"""Tests for scripts/analysis/tax_code_save_report.py (a country's tax code from a save, and a per-group diff).

The fixture test_fixtures/tax_code_save/plain_small.v3 is a hand-written excerpt in the plain-text save syntax
(copied from the owner's debug-mode saves: `data={ {` / `} {` / `} }` around variable entries, a value saved with
no `identity` line when it is zero, `identity` = value x 1e5, `list={ { name=... item={ type=... identity=... } } }`,
`}<tabs>key={` on one line). No save on disk held a `te_tax_*` variable when it was written, so the variable
names and values are made up from the schema; GBR (id 1) holds a full code, FRA (id 2) a small one, GER (id 0) none.

Run: .venv/bin/python test_tax_code_save_report.py
"""

import contextlib
import glob
import io
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "analysis"))
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
sys.path.insert(0, str(ROOT))

import check_save_history_order as csho  # noqa: E402
import gen_tax_code as gen  # noqa: E402
import save_country_probe as scp  # noqa: E402
import tax_code_save_report as tcr  # noqa: E402
import test_save_country_probe as tscp  # noqa: E402
import test_tax_code_state as tstate  # noqa: E402

FIXTURE = ROOT / "test_fixtures" / "tax_code_save" / "plain_small.v3"
GROUPS = ("enacted code", "packages", "draft and bill", "obligations and trust", "AI state", "drift counters", "history")


def run(*argv):
    """(exit code, stdout) of tax_code_save_report.main."""
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = tcr.main([str(a) for a in argv])
    return code, out.getvalue()


def section(text, group):
    """The lines under `== group ==`, up to the next section."""
    lines = text.splitlines()
    start = lines.index(f"== {group} ==")
    out = []
    for line in lines[start + 1:]:
        if line.startswith("== "):
            break
        out.append(line)
    return out


def verdicts(text, tag):
    """{group: verdict} from a diff's block for `tag` (the lines after its heading)."""
    lines = text.splitlines()
    start = next(i for i, line in enumerate(lines) if line.startswith(f"{tag} (id"))
    found = {}
    for line in lines[start + 1:]:
        if not line.startswith("  "):
            break
        for group in GROUPS:
            m = re.match(rf"  {re.escape(group)}\s+(same|changed|missing on [AB])\b", line)
            if m:
                found[group] = m.group(1)
    return found


def edited_copy(tmp, old, new, count=1):
    """A copy of the fixture with `old` replaced by `new` (the first `count` times)."""
    text = FIXTURE.read_text(encoding="utf-8")
    assert old in text, old
    path = Path(tmp) / "edited.v3"
    path.write_text(text.replace(old, new, count), encoding="utf-8", newline="\n")
    return path


def token_entry(name, identity=None):
    lines = [f"\t\t\t\tflag={name}", "\t\t\t\tdata={", "\t\t\t\t\ttype=value"]
    if identity is not None:
        lines.append(f"\t\t\t\t\tidentity={identity}")
    lines.append("\t\t\t\t}")
    return "\n".join(lines)


class TextScannerTests(unittest.TestCase):
    def test_reads_variables_of_both_tax_countries(self):
        save = tcr.read_save(FIXTURE)
        self.assertEqual(save.kind, "text")
        self.assertEqual(sorted(save.countries), [1, 2])
        self.assertEqual({c.tag for c in save.countries.values()}, {"GBR", "FRA"})
        gbr = save.countries[1]
        self.assertEqual(gbr.vars["te_tax_en_wage"], 6.0)
        self.assertEqual(gbr.vars["te_tax_en_cons_exp"], 22050.0)
        self.assertEqual(gbr.vars["te_tax_en_wage_exp"], -1.0)        # a negative sentinel
        self.assertEqual(gbr.vars["te_tax_migration_discrepancy"], 0.0)  # zero is saved with no identity line
        self.assertEqual(save.countries[2].vars["te_tax_en_wage"], 4.0)

    def test_variables_are_not_mixed_between_countries(self):
        save = tcr.read_save(FIXTURE)
        self.assertNotIn("te_tax_ai_offers", save.countries[2].vars)
        self.assertNotIn("te_tax_bl_wage", save.countries[2].vars)

    def test_other_variables_and_flags_read_too(self):
        gbr = tcr.read_save(FIXTURE).countries[1]
        self.assertEqual(gbr.vars["te_tp_version"], 1.0)
        self.assertEqual(gbr.vars["slavery_recently_abolished"], "boolean:1")

    def test_variable_lists(self):
        gbr = tcr.read_save(FIXTURE).countries[1]
        self.assertEqual(gbr.lists["te_tp_records"], ["container#2", "container#3"])
        self.assertEqual(gbr.lists["te_tax_en_relief_states"], ["state#5", "state#456"])
        self.assertEqual(gbr.lists["te_tax_pa_relief_states"], ["state#5"])

    def test_native_settings_and_carrier_amendments(self):
        save = tcr.read_save(FIXTURE)
        gbr, fra = save.countries[1].native, save.countries[2].native
        self.assertEqual(gbr["tax_level"], "medium")
        self.assertEqual(gbr["taxed_goods"], ["liquor", "tea"])
        self.assertEqual(gbr["amendments"], {"wage": 6, "div": 4, "land": 12, "head": 4, "cons": 3})
        self.assertEqual(fra["tax_level"], "low")
        self.assertEqual(fra["amendments"], {"wage": 4})      # the unrelated amendment on another law is ignored

    def test_wanted_countries_only(self):
        save = tcr.read_save(FIXTURE, want=lambda cid, tag: tag == "FRA")
        self.assertEqual([c.tag for c in save.countries.values()], ["FRA"])

    def test_a_crlf_copy_reads_the_same(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "crlf.v3"
            path.write_bytes(FIXTURE.read_bytes().replace(b"\n", b"\r\n"))
            crlf = tcr.read_save(path)
        plain = tcr.read_save(FIXTURE)
        self.assertEqual({c: (v.tag, v.vars, v.lists, v.native) for c, v in crlf.countries.items()},
                         {c: (v.tag, v.vars, v.lists, v.native) for c, v in plain.countries.items()})
        self.assertEqual(crlf.date, plain.date)

    def test_game_date(self):
        self.assertEqual(tcr.read_save(FIXTURE).date, "1836.3.1")

    def test_brace_counting_ignores_quoted_braces(self):
        self.assertEqual(tcr.brace_delta(b"\t\t\t} {"), 0)
        self.assertEqual(tcr.brace_delta(b"\t\t\t\t}\t\t\t\tgovernment_slaves={"), 0)
        self.assertEqual(tcr.brace_delta(b"\t\t\t}\t\t}"), -2)
        self.assertEqual(tcr.brace_delta(b'\tname="a { b"'), 0)
        self.assertEqual(tcr.brace_delta(b"\t\tdata={ {"), 2)

    def test_a_save_with_no_tax_code_has_no_countries(self):
        text = FIXTURE.read_text(encoding="utf-8").replace("te_tax_", "te_xxx_")
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "off.v3"
            path.write_text(text, encoding="utf-8", newline="\n")
            self.assertEqual(tcr.read_save(path).countries, {})
            code, out = run(path)
        self.assertEqual(code, 0)
        self.assertIn("no country holds tax-code state", out)


class ReportTests(unittest.TestCase):
    def setUp(self):
        self.code, self.out = run(FIXTURE, "--country", "GBR")

    def test_exit_code_and_sections(self):
        self.assertEqual(self.code, 0)
        found = [line[3:-3] for line in self.out.splitlines() if line.startswith("== ")]
        self.assertEqual(found[:7], list(GROUPS))

    def test_enacted_rates_print_as_index_and_rate(self):
        lines = "\n".join(section(self.out, "enacted code"))
        self.assertRegex(lines, r"Wage tax\s+index 6\s+rate 15%")
        self.assertRegex(lines, r"Dividend tax\s+index 4\s+rate 10%")
        self.assertRegex(lines, r"Rural assessment\s+index 12\s+rate 0\.3\b")       # not a percentage
        self.assertRegex(lines, r"Head tax\s+index 4\s+rate 0\.2\b")
        self.assertRegex(lines, r"Consumption tax rate\s+index 3\s+rate 15%")

    def test_rates_use_the_generators_steps(self):
        # index x step, from gen_tax_code.INSTRUMENTS: nothing in the tool restates a step
        for inst in gen.INSTRUMENTS:
            self.assertEqual(tcr.fmt_rate(inst, 2), tcr.fmt_rate(inst, 2))
        wage = next(i for i in gen.INSTRUMENTS if i.key == "wage")
        self.assertEqual(tcr.fmt_rate(wage, 1), "2.5%")
        self.assertEqual(tcr.fmt_rate(wage, 0), "0%")

    def test_enacted_code_sunset_and_successor(self):
        lines = "\n".join(section(self.out, "enacted code"))
        self.assertRegex(lines, r"Consumption tax rate.*since 1836\.02.*sunset 1837\.07.*then index 2")
        self.assertRegex(lines, r"Wage tax.*sunset —")

    def test_enacted_code_goods_relief_and_native_state(self):
        lines = "\n".join(section(self.out, "enacted code"))
        self.assertRegex(lines, r"taxed goods.*liquor.*tea")
        self.assertNotIn("luxury_clothes", lines.split("taxed goods")[1].split("\n")[0])
        self.assertRegex(lines, r"agricultural relief\s+25%")
        self.assertRegex(lines, r"regional relief\s+50%.*state#5.*state#456")
        self.assertRegex(lines, r"native tax level\s+medium")
        self.assertRegex(lines, r"carrier amendments.*Wage tax 6")

    def test_package_slot_prints_due_month_as_year_dot_month(self):
        lines = "\n".join(section(self.out, "packages"))
        self.assertRegex(lines, r"slot a\s+awaiting\s+due 1836\.07")
        self.assertRegex(lines, r"wage 7.*sunset 1837\.07")
        self.assertRegex(lines, r"slot b\s+free")

    def test_stale_payload_of_a_free_slot_is_labelled_unread(self):
        lines = "\n".join(section(self.out, "packages"))
        self.assertRegex(lines, r"slot b\s+free.*unread payload")
        self.assertNotIn("wage 9", lines)

    def test_history_ring_prints_newest_first_with_kind_names(self):
        lines = [line for line in section(self.out, "history") if line.strip()]
        kinds = [re.search(r"\b(sunset|approved|commenced|migrated)\b", line).group(1) for line in lines]
        self.assertEqual(kinds, ["sunset", "approved", "commenced", "migrated"])     # h2, h1, h8 (wrapped), h7
        self.assertTrue(lines[0].lstrip().startswith("1836.06"))
        self.assertIn("wage", lines[0])           # a sunset names its instrument
        self.assertIn("slot b", lines[1])

    def test_draft_and_bill(self):
        lines = "\n".join(section(self.out, "draft and bill"))
        self.assertRegex(lines, r"draft\s+closed")
        self.assertRegex(lines, r"bill\s+open.*revision 2.*major")
        self.assertRegex(lines, r"wage 8.*sunset after 12 months")
        self.assertRegex(lines, r"rural_folk\s+score 35.*committed")
        self.assertRegex(lines, r"landowners\s+score -40.*red line")

    def test_obligations_and_trust(self):
        lines = "\n".join(section(self.out, "obligations and trust"))
        self.assertRegex(lines, r"o1\s+bound.*institution level.*schools level 2 to 3.*to rural_folk.*deadline 1837\.01.*slot a")
        self.assertRegex(lines, r"trust.*rural_folk\s+\+1.*1836\.02")
        self.assertRegex(lines, r"devout\s+-2")

    def test_ai_state_by_prefix(self):
        lines = "\n".join(section(self.out, "AI state"))
        self.assertIn("te_tax_ai_cooldown = 22036", lines)      # no table row says it is a month: printed raw
        self.assertRegex(lines, r"te_tax_ai_last_month = 1836\.03")   # a `_month` token is decoded
        self.assertIn("te_tax_ai_offers", lines)

    def test_drift_counters(self):
        lines = "\n".join(section(self.out, "drift counters"))
        self.assertIn("te_tax_drift_goods", lines)
        self.assertRegex(lines, r"drift counted\s+yes")      # sync version equals the code version

    def test_header(self):
        head = self.out.splitlines()[0]
        self.assertIn("GBR", head)
        self.assertIn("id 1", head)
        self.assertIn("plain-text", head)
        self.assertIn("1836.3.1", head)
        self.assertRegex(self.out, r"schema 1.*code version 3")

    def test_plain_text_save_is_never_reported_as_ironman_or_corrupt(self):
        self.assertNotIn("ironman", self.out)
        self.assertNotIn("corrupt", self.out)
        code, out = run(FIXTURE)
        self.assertNotIn("corrupt", out)

    def test_decoded_views_consume_their_tokens_and_the_rest_are_listed(self):
        # what a view decodes is not listed again
        for name in ("te_tax_en_wage_since", "te_tax_h3_kind", "te_tax_o1_deadline", "te_tax_pa_wage", "te_tax_bl_wage_sun",
                     "te_tax_trust_devout_month", "te_tax_sup_rural_folk", "te_tax_en_g_tea"):
            self.assertNotIn(name, self.out)
        # a group with no view lists every token, and so does the leftover of one with a view
        self.assertRegex(self.out, r"te_tax_snap_month = 1836\.03")
        self.assertRegex(self.out, r"te_tax_fisc_deficit = 1")
        self.assertRegex("\n".join(section(self.out, "enacted code")), r"te_tax_xver_goods = 1")

    def test_a_token_no_table_lists_is_printed_under_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            old = "\t\t\t\tflag=te_tp_version\n"
            path = edited_copy(tmp, old, token_entry("te_tax_zz_new", 300000) + "\n\t\t\t} {\n" + old)
            _, out = run(path, "--country", "GBR")
        self.assertEqual(section(out, "other"), ["  te_tax_zz_new = 3"])
        self.assertNotIn("te_tp_version", out)         # only te_tax_ names are the tax code's


class CommandLineTests(unittest.TestCase):
    def test_runs_as_a_script(self):
        done = subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "analysis" / "tax_code_save_report.py"), str(FIXTURE), "--country", "FRA"],
            capture_output=True, text=True, check=False)
        self.assertEqual(done.returncode, 0, done.stderr)
        self.assertIn("Tax code: FRA (id 2)", done.stdout)
        self.assertRegex(done.stdout, r"Wage tax\s+index 4\s+rate 10%")

    def test_a_save_that_is_not_a_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            junk = Path(tmp) / "junk.v3"
            junk.write_bytes(b"SAV0103" + b"\x00" * 64)
            code, out = run(junk)
        self.assertEqual(code, 1)
        self.assertIn("ironman or corrupt", out)        # only a file that is neither text nor zip says so

    def test_country_reference_values_print(self):
        country = tcr.Country(1, "XYZ", {"te_tax_ref": ("country", 5), "te_tax_en_wage": 2.0}, {"te_tax_en_relief_states": ["state#1"]})
        self.assertEqual(country.tokens(), {"te_tax_ref": "country#5", "te_tax_en_wage": 2.0, "te_tax_en_relief_states": ("state#1",)})


class CountrySelectionTests(unittest.TestCase):
    def test_tag_is_case_insensitive(self):
        self.assertEqual(run(FIXTURE, "--country", "gbr")[1], run(FIXTURE, "--country", "GBR")[1])

    def test_id(self):
        code, out = run(FIXTURE, "--country", "2")
        self.assertEqual(code, 0)
        self.assertIn("FRA (id 2)", out)

    def test_name(self):
        code, out = run(FIXTURE, "--country", "great britain")
        self.assertEqual(code, 0)
        self.assertIn("GBR (id 1)", out)

    def test_unknown_country(self):
        code, out = run(FIXTURE, "--country", "XYZ")
        self.assertEqual(code, 1)
        self.assertIn("no country", out)

    def test_country_without_tax_code(self):
        code, out = run(FIXTURE, "--country", "GER")
        self.assertEqual(code, 0)
        self.assertIn("holds no tax-code variables", out)

    def test_no_country_lists_the_countries_holding_a_code(self):
        code, out = run(FIXTURE)
        self.assertEqual(code, 0)
        self.assertRegex(out, r"GBR\s+1\b")
        self.assertRegex(out, r"FRA\s+2\b")
        self.assertNotIn("GER", out)
        self.assertIn("--country", out)


class DiffTests(unittest.TestCase):
    def test_identical_saves_are_the_same_in_every_group(self):
        code, out = run("--diff", FIXTURE, FIXTURE, "--country", "GBR")
        self.assertEqual(code, 0)
        self.assertEqual(verdicts(out, "GBR"), {g: "same" for g in GROUPS})
        self.assertIn("no tax-code change", out)

    def test_one_changed_token_changes_exactly_its_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            # te_tax_en_wage 6 -> 7: the first `identity=600000` after the flag
            text = FIXTURE.read_text(encoding="utf-8")
            marker = "flag=te_tax_en_wage\n\t\t\t\tdata={\n\t\t\t\t\ttype=value\n\t\t\t\t\tidentity=600000"
            self.assertIn(marker, text)
            other = edited_copy(tmp, marker, marker.replace("600000", "700000"))
            code, out = run("--diff", FIXTURE, other, "--country", "GBR")
        self.assertEqual(code, 0)
        found = verdicts(out, "GBR")
        self.assertEqual(found["enacted code"], "changed")
        self.assertEqual({g: v for g, v in found.items() if g != "enacted code"}, {g: "same" for g in GROUPS if g != "enacted code"})
        self.assertRegex(out, r"enacted code\s+changed.*te_tax_en_wage 6 -> 7")
        self.assertNotIn("no tax-code change", out)

    def test_changed_bill_token_is_in_its_group(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = "flag=te_tax_bl_rev\n\t\t\t\tdata={\n\t\t\t\t\ttype=value\n\t\t\t\t\tidentity=200000"
            other = edited_copy(tmp, marker, marker.replace("200000", "300000"))
            _, out = run("--diff", FIXTURE, other, "--country", "GBR")
        found = verdicts(out, "GBR")
        self.assertEqual([g for g, v in found.items() if v == "changed"], ["draft and bill"])

    def test_a_group_present_on_one_side_only_is_missing_on_the_other(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = FIXTURE.read_text(encoding="utf-8")
            stripped = Path(tmp) / "no_ai.v3"
            stripped.write_text(text.replace("te_tax_ai_", "te_xxx_ai_"), encoding="utf-8", newline="\n")
            _, out_a = run("--diff", stripped, FIXTURE, "--country", "GBR")
            _, out_b = run("--diff", FIXTURE, stripped, "--country", "GBR")
        self.assertEqual(verdicts(out_a, "GBR")["AI state"], "missing on A")
        self.assertEqual(verdicts(out_b, "GBR")["AI state"], "missing on B")

    def test_a_country_in_one_save_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            text = FIXTURE.read_text(encoding="utf-8")
            # FRA loses its code (id 2's variables renamed away), GBR stays
            head, tail = text.split("\n2={\n", 1)
            fra, rest = tail.split("\n}\n\t}\n}\n", 1)
            other = Path(tmp) / "no_fra.v3"
            other.write_text(head + "\n2={\n" + fra.replace("te_tax_", "te_xxx_") + "\n}\n\t}\n}\n" + rest, encoding="utf-8", newline="\n")
            _, out = run("--diff", FIXTURE, other)
        self.assertEqual(verdicts(out, "FRA")["enacted code"], "missing on B")
        self.assertEqual(verdicts(out, "GBR"), {g: "same" for g in GROUPS})

    def test_diff_needs_two_saves_through_the_flag(self):
        with self.assertRaises(SystemExit):
            with contextlib.redirect_stderr(io.StringIO()):
                tcr.main(["--diff", str(FIXTURE)])


class SchemaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.schema = tcr.load_schema()

    def test_every_schema_token_lands_in_exactly_one_known_group(self):
        country, _ = tstate.schema_tokens()
        self.assertGreater(len(country), 500)
        misses = [name for name in country if not self.schema.claimed(name)]
        self.assertEqual(misses, [])
        for name in country:
            self.assertIn(self.schema.group_of(name), GROUPS, name)

    def test_family_to_group(self):
        group = self.schema.group_of
        self.assertEqual(group("te_tax_en_wage"), "enacted code")
        self.assertEqual(group("te_tax_pver_goods"), "enacted code")
        self.assertEqual(group("te_tax_en_g_tea"), "enacted code")
        self.assertEqual(group("te_tax_customs_held"), "enacted code")
        self.assertEqual(group("te_tax_now"), "enacted code")
        self.assertEqual(group("te_tax_pa_wage_exp"), "packages")
        self.assertEqual(group("te_tax_pb_due0"), "packages")
        self.assertEqual(group("te_tax_dr_on"), "draft and bill")
        self.assertEqual(group("te_tax_bl_on"), "draft and bill")
        self.assertEqual(group("te_tax_bl_prom_devout_kind"), "draft and bill")
        self.assertEqual(group("te_tax_o3_deadline"), "obligations and trust")
        self.assertEqual(group("te_tax_trust_devout_month"), "obligations and trust")
        self.assertEqual(group("te_tax_drift_level"), "drift counters")
        self.assertEqual(group("te_tax_sync_version"), "drift counters")
        self.assertEqual(group("te_tax_h_head"), "history")
        self.assertEqual(group("te_tax_h5_kind"), "history")

    def test_families_described_in_prose_only_get_a_group_too(self):
        group = self.schema.group_of
        self.assertEqual(group("te_tax_sup_devout"), "draft and bill")
        self.assertEqual(group("te_tax_sr_devout_mat"), "draft and bill")
        self.assertEqual(group("te_tax_com_devout_rev"), "draft and bill")
        self.assertEqual(group("te_tax_off_devout_kind"), "draft and bill")
        self.assertEqual(group("te_tax_cretry_imp_tea"), "drift counters")
        self.assertEqual(group("te_tax_snap_gdp"), "caches")
        self.assertEqual(group("te_tax_fisc_surplus"), "caches")

    def test_ai_state_by_prefix_without_a_schema_row(self):
        self.assertEqual(self.schema.group_of("te_tax_ai_anything_new"), "AI state")
        self.assertEqual(self.schema.group_of("te_tax_ai_cooldown"), "AI state")

    def test_unknown_token_goes_to_other(self):
        self.assertEqual(self.schema.group_of("te_tax_totally_new"), "other")

    def test_new_table_row_and_new_heading_need_no_code_change(self):
        doc = (ROOT / "docs" / "systems" / "tax_code_schema.md").read_text(encoding="utf-8")
        doc += (
            "\n### AI legislation\n\n| Variable | Meaning | Sentinel |\n|---|---|---|\n"
            "| `te_tax_ai_next_<key>` | the next instrument the AI moves | -1 |\n"
            "\n### Sparkle ledger\n\n| Variable | Meaning | Sentinel |\n|---|---|---|\n"
            "| `te_tax_sparkle_<ig>` | a made-up per-group token | 0 |\n"
            "| `te_tax_sparkle_total`, `te_tax_sparkle_last` | made-up totals | 0 |\n"
        )
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "schema.md"
            path.write_text(doc, encoding="utf-8")
            schema = tcr.load_schema(path)
        self.assertEqual(schema.group_of("te_tax_ai_next_wage"), "AI state")
        self.assertEqual(schema.group_of("te_tax_sparkle_devout"), "Sparkle ledger")
        self.assertEqual(schema.group_of("te_tax_sparkle_last"), "Sparkle ledger")
        self.assertEqual(self.schema.group_of("te_tax_sparkle_devout"), "other")      # absent from the real doc
        self.assertIn("Sparkle ledger", schema.groups())

    def test_groups_are_ordered_standard_first(self):
        self.assertEqual(list(self.schema.groups())[:7], list(GROUPS))

    def test_history_kind_names(self):
        names = self.schema.kind_names
        self.assertEqual(sorted(names), list(range(1, 19)))
        self.assertEqual(names[1], "commenced")
        self.assertEqual(names[2], "sunset")                # not in HISTORY_KIND_KEYS: a sunset names its instrument
        self.assertEqual(names[5], "migrated")
        self.assertEqual(names[6], "approved")
        self.assertEqual(names[7], "repaired")              # the generator's name, not the doc's "civil-war repair"
        self.assertEqual(names[15], "customs_adopted")

    def test_kind_numbers_agree_with_the_generator(self):
        self.assertEqual(set(gen.HISTORY_KIND_KEYS) | {2}, set(self.schema.kind_names))
        for number, key in gen.HISTORY_KIND_KEYS.items():
            self.assertEqual(self.schema.kind_names[number], key.removeprefix("te_tax_hist_kind_"))

    def test_obligation_enums_come_from_the_doc(self):
        self.assertEqual(self.schema.obligation_states[1], "pending")
        self.assertEqual(self.schema.obligation_states[7], "bound")
        self.assertEqual(self.schema.obligation_states[3], "maintaining")
        self.assertEqual(self.schema.obligation_states[4], "fulfilled")
        self.assertEqual(self.schema.obligation_kinds[1], "institution level")
        self.assertEqual(self.schema.obligation_kinds[4], "fiscal balance outcome")

    def test_state_names(self):
        self.assertEqual(self.schema.package_states, {1: "awaiting", 2: "held_conflict", 3: "held_missed"})


class DecodingTests(unittest.TestCase):
    def test_month(self):
        self.assertEqual(tcr.fmt_month(22033), "1836.02")      # year x 12 + month, January = 0
        self.assertEqual(tcr.fmt_month(22032), "1836.01")
        self.assertEqual(tcr.fmt_month(22043), "1836.12")
        self.assertEqual(tcr.fmt_month(-1), "—")
        self.assertEqual(csho.fmt_month(22033), tcr.fmt_month(22033))

    def test_history_ring_wraps_and_skips_empty_entries(self):
        vars_ = {"te_tax_h_head": 2.0}
        for n, (month, kind) in {7: (100.0, 5.0), 8: (101.0, 1.0), 1: (103.0, 6.0), 2: (105.0, 2.0)}.items():
            vars_[f"te_tax_h{n}_month"], vars_[f"te_tax_h{n}_kind"] = month, kind
        for n in (3, 4, 5, 6):
            vars_[f"te_tax_h{n}_month"], vars_[f"te_tax_h{n}_kind"] = -1.0, 0.0
        self.assertEqual([e["n"] for e in tcr.history_entries(vars_)], [2, 1, 8, 7])

    def test_empty_ring(self):
        self.assertEqual(tcr.history_entries({"te_tax_h_head": 0.0}), [])
        self.assertEqual(tcr.history_entries({}), [])


class PlainTextMessageTests(unittest.TestCase):
    def test_read_gamestate_says_plain_text(self):
        with self.assertRaises(ValueError) as caught:
            csho.read_gamestate(FIXTURE)
        message = str(caught.exception)
        self.assertIn("plain-text", message)
        self.assertIn("tax_code_save_report", message)
        self.assertNotIn("ironman or corrupt", message)

    def test_an_unreadable_file_still_says_so(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "junk.v3"
            path.write_bytes(b"SAV0103" + b"\x00" * 64)
            with self.assertRaises(ValueError) as caught:
                csho.read_gamestate(path)
        self.assertIn("ironman or corrupt", str(caught.exception))

    def test_history_order_main_explains_instead_of_a_traceback(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = csho.main([str(FIXTURE)])
        self.assertEqual(code, 1)
        self.assertIn("plain-text", out.getvalue())

    def test_probe_main_explains_instead_of_a_traceback(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = scp.main([str(FIXTURE), "--tag", "GBR"])
        self.assertEqual(code, 1)
        self.assertIn("plain-text", out.getvalue())
        self.assertNotIn("ironman or corrupt", out.getvalue())


def binary_save(tmp, variables_by_cid):
    """A binary .v3 holding one country per entry; lists go in as ('state', ids) pairs."""
    countries = []
    for cid, (tag, variables, lists) in variables_by_cid.items():
        countries.append(tscp.country(cid, tag, variables=variables, lists=lists))
    path = tscp.write_save(countries)
    target = Path(tmp) / "binary.v3"
    shutil.move(path, target)
    return target


class BinarySaveTests(unittest.TestCase):
    VARS = {
        "te_tax_schema": 1, "te_tax_code_version": 2, "te_tax_now": 22034, "te_tax_en_wage": 6,
        "te_tax_en_wage_exp": -1, "te_tax_en_wage_since": 22032, "te_tax_pa_on": 1, "te_tax_pa_due": 22038,
        "te_tax_pa_state": 1, "te_tax_pa_wage": 7, "te_tax_h_head": 1, "te_tax_h1_month": 22033,
        "te_tax_h1_kind": 5, "te_tax_ai_cooldown": 22040, "unrelated_var": 3,
    }
    LISTS = {"te_tax_en_relief_states": ("state", [5, 456]), "te_tp_records": ("container", [2])}

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = binary_save(self.tmp.name, {tscp.SPAIN: ("SPA", self.VARS, self.LISTS), 5: ("FRA", {"unrelated": 1}, None)})

    def test_read_save_through_the_probe_decoder(self):
        save = tcr.read_save(self.path)
        self.assertEqual(save.kind, "binary")
        self.assertEqual(list(save.countries), [tscp.SPAIN])
        spa = save.countries[tscp.SPAIN]
        self.assertEqual(spa.tag, "SPA")
        self.assertEqual(spa.vars["te_tax_en_wage"], 6.0)
        self.assertEqual(spa.vars["te_tax_en_wage_exp"], -1.0)
        self.assertEqual(spa.lists["te_tax_en_relief_states"], ["state#5", "state#456"])
        self.assertEqual(list(spa.lists), ["te_tax_en_relief_states"])      # the probe's var filter trims the rest
        self.assertEqual(spa.native, {})

    def test_report(self):
        code, out = run(self.path, "--country", "SPA")
        self.assertEqual(code, 0)
        self.assertIn("binary", out.splitlines()[0])
        self.assertRegex("\n".join(section(out, "enacted code")), r"Wage tax\s+index 6\s+rate 15%")
        self.assertRegex("\n".join(section(out, "packages")), r"slot a\s+awaiting\s+due 1836\.07")
        self.assertRegex("\n".join(section(out, "history")), r"1836\.02\s+migrated")
        self.assertIn("te_tax_ai_cooldown", "\n".join(section(out, "AI state")))
        self.assertIn("not read from a binary save", out)

    def test_country_by_slot_number(self):
        code, out = run(self.path, "--country", str(tscp.SPAIN))
        self.assertEqual(code, 0)
        self.assertIn("SPA", out)

    def test_diff_of_binary_saves(self):
        other_vars = dict(self.VARS, te_tax_en_wage=7)
        with tempfile.TemporaryDirectory() as tmp2:
            other = binary_save(tmp2, {tscp.SPAIN: ("SPA", other_vars, self.LISTS)})
            _, out = run("--diff", self.path, other, "--country", "SPA")
        found = verdicts(out, "SPA")
        self.assertEqual([g for g, v in found.items() if v == "changed"], ["enacted code"])

    def test_list_change_shows_in_the_diff(self):
        with tempfile.TemporaryDirectory() as tmp2:
            other = binary_save(tmp2, {tscp.SPAIN: ("SPA", self.VARS, {"te_tax_en_relief_states": ("state", [5])})})
            _, out = run("--diff", self.path, other, "--country", "SPA")
        self.assertEqual(verdicts(out, "SPA")["enacted code"], "changed")
        self.assertIn("te_tax_en_relief_states", out)


REAL = next(iter(glob.glob("/mnt/c/Users/*/OneDrive/Documents/Paradox Interactive/Victoria 3/save games/temp.v3")), None)


@unittest.skipUnless(REAL, "the owner's temp.v3 (a plain-text save with te_tp_* probe variables) is not on this machine")
class RealPlainTextSaveTests(unittest.TestCase):
    """Cheap insurance that the hand-written fixture matches what the engine writes. Structural only: the owner
    overwrites temp.v3, so no value of it is pinned."""

    def test_the_scanner_reads_real_engine_output(self):
        save = tcr.read_save(REAL, require_tax=False)
        probes = [c for c in save.countries.values() if any(k.startswith("te_tp_") for k in c.vars)]
        if not probes:
            self.skipTest("temp.v3 no longer holds te_tp_* probe variables")
        self.assertGreater(len(save.countries), 100)
        country = probes[0]
        self.assertRegex(save.date, r"^\d+\.\d+\.\d+$")
        self.assertRegex(country.tag, r"^[A-Z0-9]{3}$")
        self.assertTrue(any(isinstance(v, float) for k, v in country.vars.items() if k.startswith("te_tp_")))
        for name, items in country.lists.items():
            for item in items:
                self.assertRegex(item, r"^\w+#\d+$", name)
        self.assertIn(country.native["tax_level"], ("very_low", "low", "medium", "high", "very_high"))
        goods = country.native.get("taxed_goods", [])
        self.assertTrue(all(re.fullmatch(r"[a-z_]+", g) for g in goods), goods)


if __name__ == "__main__":
    unittest.main()
