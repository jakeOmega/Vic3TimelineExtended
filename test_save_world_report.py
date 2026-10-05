"""Tests for scripts/analysis/save_world_report.py (treaty, technology, building and PM-churn counts from a save).

The report decodes a save's binary `gamestate` by token numbers worked out by
hand on 1.14.5 saves, and a plain-text save by the key names the engine writes
there. A wrong token number fails silently: the record stops matching and the
world reads as having no treaties, or a tech list reads as empty. These tests
build one small world twice, as a binary `.v3` byte by byte and as a text
`.v3`, and require both to decode to the same counts. They also pin the
judgement calls: what a churn "change" and a "reversal" are, how a swap pairs
by PM group, which treaty articles are the mod's, and how the mod's INJECT:
and REPLACE: blocks layer over vanilla's snapshot. No save or game install is
needed.

Run: .venv/bin/python test_save_world_report.py
"""

import io
import json
import struct
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "scripts" / "analysis"))
import save_world_report as swr  # noqa: E402

EQ, OPEN, CLOSE = b"\x01\x00", b"\x03\x00", b"\x04\x00"
I32, U32, BOOL, STR, F64 = b"\x0c\x00", b"\x14\x00", b"\x0e\x00", b"\x0f\x00", b"\x67\x01"


def tok(n):
    return struct.pack("<H", n)


def u32(n):
    return U32 + struct.pack("<I", n)


def i32(n):
    return I32 + struct.pack("<i", n)


def string(text):
    raw = text.encode("ascii")
    return STR + struct.pack("<H", len(raw)) + raw


def kv(key, value):
    return tok(key) + EQ + value


def block(*parts):
    return OPEN + b"".join(parts) + CLOSE


def record(rid, *parts, key=U32):
    return key + struct.pack("<I", rid) + EQ + block(*parts)


def fixed_f64(value):
    """A progress value as the game writes it: the f64 token around an i64 fixed point x 1e5."""
    return F64 + struct.pack("<q", round(value * 1e5))


def hours(year, month, day):
    return swr.date_hours(f"{year}.{month}.{day}")


GER, GBR, FRA, CEY_A, CEY_B = 1, 2, 16777219, 4, 16777221  # two objects share CEY
NONE = 0xFFFFFFFF
DATE = hours(2015, 6, 1)


# ------------------------------------------------------------ one world, two formats
ARTICLES = [  # id, type, treaty, source, target
    (10, "joint_military_exercises", 100, NONE, NONE),
    (11, "joint_military_exercises", 101, NONE, NONE),
    (12, "alliance", 101, NONE, NONE),
    (13, "trade_privilege", 102, GER, FRA),
    (14, "joint_military_exercises", 103, NONE, NONE),
    (15, "goods_transfer", 102, FRA, GER),
    (16, "goods_transfer", 102, FRA, GER),
]
TREATIES = [(100, GER, GBR), (101, GER, FRA), (102, GER, FRA), (103, GBR, CEY_B)]
TECHS = [  # country, researching, (tech, progress), acquired
    (GER, "tech_e2_b", ("tech_e2_b", 1234.5), ["tech_e1_a", "tech_e1_b", "tech_e2_a"]),
    (GBR, None, None, ["tech_e1_a", "tech_e1_b"]),
    (FRA, "tech_e1_b", ("tech_e1_b", 50.0), ["tech_e1_a"]),
]
BUILDINGS = [  # id, type, level, state, pms, retool (start, end) or None
    (500, "building_port", 2, 7, ["pm_basic_port", "pm_no_ferries"], (DATE - 24 * 10, DATE + 24 * 1810)),
    (501, "building_port", 1, 8, ["pm_no_ferries", "pm_anchorage"], None),
    (502, "building_farm", 5, 7, ["pm_simple"], (DATE - 24 * 2000, DATE - 24 * 180)),  # ended, still listed
]


def binary_gamestate(buildings=BUILDINGS, date=DATE):
    out = [tok(0x55AD) + EQ + block(kv(0x058F, i32(1)), kv(0x3245, i32(date)))]  # the meta block opens the gamestate
    for cid, tag in ((GER, "GER"), (GBR, "GBR"), (FRA, "FRA"), (CEY_A, "CEY"), (CEY_B, "CEY")):
        out.append(record(cid, kv(0x07DD, string(tag)), kv(0x1234, i32(0))))
    for aid, typ, treaty, src, tgt in ARTICLES:
        extra = kv(0x60D4, block(u32(src) + EQ + i32(0))) if src != NONE else b""
        out.append(record(aid, kv(0x2F11, string(typ)), kv(0x57D6, u32(treaty)), kv(0x60C9, u32(src)),
                          kv(0x321F, u32(tgt)), extra))
    # a war goal naming an article: a reference, not an article record
    out.append(kv(0x311C, block(kv(0x2F11, string("trade_privilege")), kv(0x60C7, u32(GER)))))
    # a record opening like a treaty (name block first) that is not one
    out.append(record(102, kv(0x001B, block(kv(0x0010, string("decoy")))), kv(0x0011, i32(3))))
    for tid, first, second in TREATIES:
        out.append(record(tid, kv(0x001B, block(kv(0x0010, string("treaty name")))), kv(0x32CF, u32(first)),
                          kv(0x32D0, u32(second)), kv(0x60CB, i32(DATE - 24 * 30)), kv(0x60CA, i32(1825))))
    # blocks that open like a technology record but are something else
    out.append(record(900, kv(0x2840, u32(GER)), kv(0x00E1, string("je_something"))))
    for n, (cid, researching, progress, acquired) in enumerate(TECHS):
        parts = [kv(0x2840, u32(cid))]
        if researching:
            parts.append(kv(0x53B1, string(researching)))
        if progress:
            parts.append(kv(0x5BAC, block(block(kv(0x31A9, string(progress[0])), kv(0x2A4F, fixed_f64(progress[1])),
                                                kv(0x5443, BOOL + b"\x00")))))
        parts.append(kv(0x5BAD, block(*(string(t) for t in acquired))))
        out.append(record(800 + n, *parts))
        out.append(record(950 + n, kv(0x2840, u32(cid)), kv(0x00E1, string("combat_unit"))))
    for bid, typ, level, state, pms, retool in buildings:
        mods = b""
        if retool:
            mods = kv(0x333B, block(kv(0x0D00, block(block(kv(0x000B, u32(0)), kv(0x0C1F, string("pm_retooling")),
                                                             kv(0x0CF8, i32(retool[0])), kv(0x0CF9, i32(retool[1])))))))
        key = I32 if bid % 2 else U32  # both header key bytes occur
        out.append(record(bid, kv(0x27F8, string(typ)), kv(0x3A52, i32(level)), kv(0x2AB2, BOOL + b"\x01"),
                          kv(0x01B7, u32(state)), kv(0x5925, block(*(string(p) for p in pms))), mods, key=key))
    return b"".join(out)


def binary_save(path, gamestate):
    data = io.BytesIO()
    with zipfile.ZipFile(data, "w") as archive:
        archive.writestr("gamestate", gamestate)
    Path(path).write_bytes(b"SAV010300000000000000000" + data.getvalue())


def text_date(h):
    return swr.fmt_hours(h)


def text_save(path, buildings=BUILDINGS, date=DATE):
    lines = ["SAV0100000000000000000000", "meta_data={", f"\tgame_date={text_date(date)}", "}",
             f"date={text_date(date)}", "country_manager={", "\tdatabase={"]
    for cid, tag in ((GER, "GER"), (GBR, "GBR"), (FRA, "FRA"), (CEY_A, "CEY"), (CEY_B, "CEY")):
        lines += [f"{cid}={{", "\tvariables={ data={ {", "\t\tflag=x", "\t} } }", f'\tdefinition="{tag}"',
                  # a nested record that starts at column 0, as the engine writes some
                  "\thistory={", "77={", "\tdate=1836.1.1", "}", "\t}", "}"]
    lines += ["\t}", "\tnext_id=5", "}", "treaty_article_manager={", "\tdatabase={"]
    for aid, typ, treaty, src, tgt in ARTICLES:
        lines += [f"{aid}={{", f"\tarticle={typ}", f"\ttreaty={treaty}", f"\tsource_country={src}",
                  f"\ttarget_country={tgt}"]
        if src != NONE:
            lines += ["\tcurrent_contraventions={", f"\t\t{src}=0", "\t}"]
        lines.append("}")
    lines += ["\t}", "}", "treaty_manager={", "\tdatabase={"]
    for tid, first, second in TREATIES:
        lines += [f"{tid}={{", "\tname={", "\t\tdynamic={", "\t\t\tdynamic_name=x", "\t\t}", "\t}",
                  f"\tfirst_country={first}", f"\tsecond_country={second}",
                  f"\tentered_into_force_on={text_date(DATE - 24 * 30)}", "\tbinding_period=1825", "}"]
    lines += ["999=none", "\t}", "}", "technology={", "\tdatabase={"]
    for n, (cid, researching, progress, acquired) in enumerate(TECHS):
        lines += [f"{800 + n}={{", f"\tcountry={cid}"]
        if researching:
            lines.append(f"\tresearch_technology={researching}")
        if progress:
            lines += ["\tprogressed_technologies={ {", f"\t\t\ttechnology={progress[0]}",
                      f"\t\t\tprogress={progress[1]}", "\t\t\tis_researched=no", "\t\t} }"]
        lines += [f"\tacquired_technologies={{ {' '.join(acquired)} }}", "}"]
    lines += ["\t}", "}", "building_manager={", "\tdatabase={"]
    for bid, typ, level, state, pms, retool in buildings:
        lines += [f"{bid}={{", f"\tbuilding={typ}", f"\tlevels={level}", "\tactive=yes", f"\tstate={state}",
                  "\tinput_goods={", "\t\tgoods={", "\t\t\t7={ value=1 }", "\t\t}", "\t}",
                  "\tproduction_methods={ " + " ".join(f'"{p}"' for p in pms) + " }"]
        if retool:
            lines += ["\ttimed_modifiers={", "\t\tmodifiers={ {", "\t\t\t\tid=0", "\t\t\t\tmodifier=pm_retooling",
                      f"\t\t\t\tstart_date={text_date(retool[0])}", f"\t\t\t\tend_date={text_date(retool[1])}",
                      "\t\t\t} }", "\t\tnext_id=1", "\t}"]
        lines.append("}")
    lines += ["\t}", "}", "amendment_manager={", "}"]
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8-sig" if path.suffix == ".txt" else "utf-8")


def fake_repo(root):
    """A checkout with a vanilla snapshot and mod files: two eras, one unresearchable tech, port PM groups."""
    snap = root / "vanilla_parsed" / "common"
    write(snap / "technologies.json", json.dumps({
        "tech_e1_a": ["=", {"era": ["=", "era_1"]}],
        "tech_e1_b": ["=", {"era": ["=", "era_1"]}],
        "tech_e1_x": ["=", {"era": ["=", "era_1"], "can_research": ["=", "no"]}],
        "tech_e2_a": ["=", {"era": ["=", "era_2"]}],
    }))
    write(root / "common" / "technology" / "technologies" / "era_2.txt",
          "tech_e2_b = {\n\tera = era_2\n\tcan_research = { always = yes }\n}\n")
    write(snap / "treaty_articles.json", json.dumps({a: ["=", {}] for a in
                                                     ("alliance", "trade_privilege", "goods_transfer")}))
    write(root / "common" / "treaty_articles" / "extra.txt",
          "joint_military_exercises = {\n\tkind = mutual\n}\nINJECT:alliance = { x = y }\n")
    write(snap / "buildings.json", json.dumps({
        "building_port": ["=", {"production_method_groups": ["=", ["pmg_port", "pmg_old"]]}],
        "building_farm": ["=", {"production_method_groups": ["=", ["pmg_farm"]]}],
    }))
    write(snap / "pm_groups.json", json.dumps({
        "pmg_port": ["=", {"production_methods": ["=", ["pm_anchorage", "pm_basic_port"]]}],
        "pmg_old": ["=", {"production_methods": ["=", ["pm_gone"]]}],
        "pmg_farm": ["=", {"production_methods": ["=", ["pm_simple"]]}],
    }))
    write(root / "common" / "buildings" / "b.txt",
          "REPLACE:building_port = {\n\tproduction_method_groups = { pmg_port pmg_ferries }\n}\n")
    write(root / "common" / "production_method_groups" / "g.txt",
          "INJECT:pmg_port = { production_methods = { pm_modern_port } }\n"
          "pmg_ferries = { production_methods = { pm_no_ferries pm_ferries } }\n")
    return swr.Reference(offline=True, repo=root)


class WorldTests(unittest.TestCase):
    """The same world, saved binary and as text, decodes to the same reports."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.ref = fake_repo(root / "repo")
        cls.binary, cls.text = root / "world.v3", root / "world_text.v3"
        binary_save(cls.binary, binary_gamestate())
        text_save(cls.text)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def reports(self, fn, *args):
        out = []
        for path in (self.binary, self.text):
            world = swr.World(path)
            try:
                report = fn(world, self.ref, *args)
            finally:
                world.close()
            json.dumps(report)  # --json must not choke
            out.append(report)
        return out

    def same(self, fn, *args):
        binary, text = self.reports(fn, *args)
        self.assertEqual((binary["format"], text["format"]), ("binary", "text"))
        for r in (binary, text):
            del r["format"], r["save"]
        self.assertEqual(binary, text)
        return binary

    def test_date(self):
        for path in (self.binary, self.text):
            world = swr.World(path)
            self.assertEqual(world.date, "2015.6.1")
            world.close()

    def test_treaties(self):
        r = self.same(swr.treaties_report, ["joint_military_exercises", "goods_transfer"], 10)
        self.assertEqual(r["warnings"], [], "the war goal's article is a reference, not a missed record")
        self.assertEqual((r["articles"], r["treaties"]), (7, 4))
        rows = {t["type"]: t for t in r["types"]}
        jme = rows["joint_military_exercises"]
        self.assertTrue(jme["mod"])
        self.assertFalse(rows["alliance"]["mod"], "an INJECT: of a vanilla article is not a mod article")
        self.assertEqual((jme["articles"], jme["treaties"], jme["only"], jme["directed"]), (3, 3, 2, 0))
        self.assertEqual(jme["pact_same_treaty"], 1)
        self.assertEqual(jme["pact_between_pair"], 1, "GER-FRA hold an alliance; GER-GBR and GBR-CEY do not")
        self.assertEqual(rows["trade_privilege"]["pact_between_pair"], 1, "the pact sits in another treaty")
        self.assertEqual(r["compositions"][0], {"articles": ["joint_military_exercises"], "treaties": 2})
        holders = {h["country"]: h for h in r["holders"]["joint_military_exercises"]}
        self.assertEqual({k: v["articles"] for k, v in holders.items()}, {"GER": 2, "GBR": 2, "FRA": 1, "CEY#5": 1})
        goods = {h["country"]: (h["as_source"], h["as_target"]) for h in r["holders"]["goods_transfer"]}
        self.assertEqual(goods, {"FRA": (2, 0), "GER": (0, 2)})

    def test_techs(self):
        r = self.same(swr.techs_report, "tech_e1_b", 15)
        self.assertEqual(r["countries"], 3)
        self.assertEqual(r["unresearchable"], ["tech_e1_x"])
        eras = {e["era"]: e for e in r["eras"]}
        self.assertEqual((eras["era_1"]["techs"], eras["era_1"]["researchable"]), (3, 2))
        self.assertEqual(eras["era_1"]["complete"], 2, "tech_e1_x, which nobody can research, is not required")
        self.assertEqual((eras["era_2"]["complete"], eras["era_2"]["touched"]), (0, 1))
        self.assertEqual(r["highest_era"], {"era_1": 2, "era_2": 1})
        top = r["top"][0]
        self.assertEqual((top["country"], top["acquired"], top["by_era"]), ("GER", 3, {"era_1": 2, "era_2": 1}))
        self.assertEqual(top["researching"], "tech_e2_b")
        self.assertAlmostEqual(top["progress"], 1234.5, msg="the f64-token progress is an i64 fixed point")
        self.assertEqual(r["tech"]["holders"], ["GBR", "GER"])
        self.assertEqual(r["tech"]["researching"], [{"country": "FRA", "progress": 50.0}])

    def test_buildings(self):
        r = self.same(swr.buildings_report, "building_port", 25)
        self.assertEqual((r["buildings"], r["retooling"], r["retool_ended"]), (3, 1, 1))
        self.assertEqual(r["retool_span_days"], {"1820": 2})
        port = r["type"]
        self.assertEqual((port["buildings"], port["retooling"], port["group_source"]), (2, 1, "files"))
        groups = {g["group"]: [p["pm"] for p in g["pms"]] for g in port["groups"]}
        self.assertEqual(groups, {"pmg_ferries": ["pm_no_ferries"], "pmg_port": ["pm_anchorage", "pm_basic_port"]})

    def test_churn_across_formats(self):
        later = [(500, "building_port", 2, 7, ["pm_modern_port", "pm_ferries"], None)] + BUILDINGS[1:]
        root = Path(self.tmp.name)
        binary_save(root / "later.v3", binary_gamestate(later, DATE + 24 * 30))
        text_save(root / "later_text.v3", later, DATE + 24 * 30)
        for first, second in ((self.binary, root / "later.v3"), (self.text, root / "later_text.v3"),
                              (self.binary, root / "later_text.v3")):
            r = swr.churn_report([second, first], self.ref, None, 15)  # given newest first: sorted by date
            self.assertEqual([s["date"] for s in r["saves"]], ["2015.6.1", "2015.7.1"])
            self.assertEqual((r["changes"], r["reversals"]), (1, 0))
            self.assertEqual({(s["from"], s["to"], s["group"]) for s in r["switches"]},
                             {("pm_basic_port", "pm_modern_port", "pmg_port"),
                              ("pm_no_ferries", "pm_ferries", "pmg_ferries")})
            json.dumps(r)


class CoverageTests(unittest.TestCase):
    """A record the header regex misses is a WARNING, not a quietly smaller count."""

    def test_an_article_record_keyed_otherwise_is_reported(self):
        blob = (record(1, kv(0x2F11, string("alliance")), kv(0x57D6, u32(9)))
                + record(2, kv(0x2F11, string("alliance")), kv(0x57D6, u32(9)), key=I32)
                + kv(0x311C, block(kv(0x2F11, string("alliance")))))  # a reference: not counted
        warnings = []
        self.assertEqual(len(swr.binary_articles(blob, warnings)), 1)
        self.assertEqual(warnings, ["1 article records missed or unparsed; 1 decoded"])

    def test_an_acquired_list_outside_a_technology_record_is_reported(self):
        blob = (record(1, kv(0x2840, u32(GER)), kv(0x5BAD, block(string("a"))))
                + record(2, kv(0x0001 + 0x2840, u32(GER)), kv(0x5BAD, block(string("b")))))
        warnings = []
        self.assertEqual(len(swr.binary_techs(blob, warnings)), 1)
        self.assertEqual(len(warnings), 1)


class TextReaderTests(unittest.TestCase):
    TEXT = (b"head=1\nsection={\n\tother={\n1={\n\tbuilding=wrong\n}\n\t}\n\tdatabase={\n"
            b"5={\n\tkeep=a\n\tskip={\n3={\n\tkeep=nested\n}\n\t}\n\tlist={ \"x\" y }\n}\n"
            b"6={ keep=b }\n7=none\n\t}\n}\nnext={\n\tdatabase={\n8={\n\tkeep=c\n}\n\t}\n}\n")

    def entries(self, section, keep=None):
        with tempfile.TemporaryFile() as handle:
            handle.write(self.TEXT)
            handle.flush()
            import mmap
            mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
            try:
                return list(swr.text_entries(mapped, section, keep))
            finally:
                mapped.close()

    def test_entries_of_the_database_only(self):
        self.assertEqual(self.entries(b"section"), [
            (5, [("keep", "a"), ("skip", [("3", [("keep", "nested")])]), ("list", [(None, "x"), (None, "y")])]),
            (6, [("keep", "b")]),
        ])

    def test_keep_skips_other_keys_and_their_blocks(self):
        self.assertEqual(self.entries(b"section", {b"keep"}), [(5, [("keep", "a")]), (6, [("keep", "b")])])

    def test_two_readers_at_once(self):
        with tempfile.TemporaryFile() as handle:
            handle.write(self.TEXT)
            handle.flush()
            import mmap
            mapped = mmap.mmap(handle.fileno(), 0, access=mmap.ACCESS_READ)
            first = swr.text_entries(mapped, b"next")
            self.assertEqual(next(swr.text_entries(mapped, b"section"))[0], 5)
            self.assertEqual(list(first), [(8, [("keep", "c")])], "each reader keeps its own position")
            mapped.close()


class ChurnTests(unittest.TestCase):
    """A change is a building whose PM set differs; a reversal re-adds a PM an earlier change removed."""

    def test_definitions(self):
        snaps = [
            {1: ("port", ["a", "x"]), 2: ("port", ["b", "y"]), 3: ("port", ["a"])},
            {1: ("port", ["b", "x"]), 2: ("port", ["y", "b"]), 4: ("port", ["a"])},   # 2: order only; 3 gone, 4 new
            {1: ("port", ["a", "x"]), 2: ("port", ["c", "y"]), 4: ("port", ["b"])},
            {1: ("port", ["c", "x"]), 2: ("port", ["b", "y"]), 4: ("port", ["b"])},
        ]
        changes, steps = swr.churn(snaps)
        self.assertEqual(steps, [(2, 1), (3, 3), (3, 2)])
        summary = [(step, bid, sorted(rem), sorted(add), rev) for step, bid, _, rem, add, rev in changes]
        self.assertEqual(summary, [
            (0, 1, ["a"], ["b"], False),
            (1, 1, ["b"], ["a"], True),    # back to a
            (1, 2, ["b"], ["c"], False),
            (1, 4, ["a"], ["b"], False),
            (2, 1, ["a"], ["c"], False),   # c is new to building 1, though a went before
            (2, 2, ["c"], ["b"], True),
        ])

    def test_pairing(self):
        groups = {"a1": "g1", "a2": "g1", "b1": "g2", "b2": "g2"}
        self.assertEqual(swr.pair_switches({"a1", "b1"}, {"a2", "b2"}, groups), [("a1", "a2", "g1"), ("b1", "b2", "g2")])
        self.assertEqual(swr.pair_switches({"p"}, {"q"}, {}), [("p", "q", None)], "a lone swap needs no groups")
        self.assertEqual(swr.pair_switches({"p", "r"}, {"q", "s"}, {}), [("p+r", "q+s", None)])
        self.assertEqual(swr.pair_switches({"a1", "p"}, {"a2"}, groups), [("a1", "a2", "g1"), ("p", "-", None)])


class ValueTests(unittest.TestCase):
    def test_dates_round_trip(self):
        for text in ("1836.1.1", "2015.6.1", "2016.12.31", "2073.6.6"):
            self.assertEqual(swr.fmt_hours(swr.date_hours(text)), text)
        self.assertEqual(swr.date_hours("2046.1.22.12") - swr.date_hours("2046.1.22"), 12)

    def test_fixed_point_from_the_f64_token(self):
        raw = struct.pack("<q", 75673662310)  # 756736.6231 x 1e5
        misread = struct.unpack("<d", raw)[0]
        self.assertAlmostEqual(swr.fixed_point(misread), 756736.6231)
        self.assertEqual(swr.fixed_point("48.1192"), 48.1192, "a text save writes the decimal")

    def test_gamestate_date(self):
        blob = tok(0x55AD) + EQ + block(kv(0x058F, i32(1)), kv(0x3245, i32(DATE)))
        self.assertEqual(swr.fmt_hours(swr.gamestate_hours(blob)), "2015.6.1")
        self.assertIsNone(swr.gamestate_hours(b"\x00" * 64))

    def test_top_level_fields_lists_and_scalars(self):
        text = ("a = { era = era_1 production_methods = { x \"y\" { nested } z } }\n"
                "INJECT:b = { trigger = { era = era_9 } era = era_2 }\n# c = { era = era_3 }\n")
        self.assertEqual(swr.top_level_fields(text, "era"), {"a": "era_1", "b": "era_2"})
        self.assertEqual(swr.top_level_fields(text, "production_methods"), {"a": ["x", "y", "z"]})
        self.assertEqual(swr.top_level_names(text), ["a", "b"])


class ServerTests(unittest.TestCase):
    def test_a_dead_server_falls_back_to_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            ref = fake_repo(Path(tmp))
            ref.server = "http://127.0.0.1:9"  # discard port: refused at once
            eras, source = ref.tech_eras()
            self.assertIn("vanilla_parsed", source)
            self.assertEqual(eras["tech_e2_b"], "era_2")
            self.assertEqual(ref.pm_groups("building_port")[1], "files")
            self.assertFalse(ref._server_up)

    def test_replace_drops_vanilla_groups_and_inject_adds(self):
        with tempfile.TemporaryDirectory() as tmp:
            groups, source = fake_repo(Path(tmp)).pm_groups("building_port")
            self.assertEqual(source, "files")
            self.assertEqual(groups, {"pm_anchorage": "pmg_port", "pm_basic_port": "pmg_port",
                                      "pm_modern_port": "pmg_port", "pm_no_ferries": "pmg_ferries",
                                      "pm_ferries": "pmg_ferries"})


class CheckoutTests(unittest.TestCase):
    """This checkout's own reference data, where the snapshot is committed."""

    def test_eras_and_mod_articles(self):
        ref = swr.Reference(offline=True)
        if not (ref.snapshot / "technologies.json").is_file():
            self.skipTest("no vanilla_parsed snapshot")
        eras, _ = ref.tech_eras()
        self.assertEqual(eras.get("sericulture"), "era_1")
        self.assertIn("sericulture", ref.unresearchable())
        self.assertTrue(any(e == "era_12" for e in eras.values()), "the mod's late eras are read")
        mod = ref.mod_articles()
        self.assertIn("joint_military_exercises", mod)
        self.assertNotIn("alliance", mod)


if __name__ == "__main__":
    unittest.main()
