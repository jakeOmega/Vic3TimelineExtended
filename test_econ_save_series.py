"""Tests for scripts/analysis/econ_save_series.py (the economy growth sim's save reader, issue #1034).

The reader decodes 1.14.5 binary saves from token numbers worked out by hand. A
wrong number doesn't crash anything: a field just stops resolving and reads as
absent, or a fixed-point value reads as a float and comes out as garbage. These
tests build the binary layout byte by byte and check the values come back out.
They need neither Victoria 3 nor a save.

Run: .venv/bin/python -m unittest test_econ_save_series -v
"""

import io
import json
import struct
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

from scripts.analysis import econ_save_series as S

EQ, OPEN, CLOSE = b"\x01\x00", b"\x03\x00", b"\x04\x00"
FX = S.FX_SCALE
_TMP = tempfile.TemporaryDirectory()


def tearDownModule():
    _TMP.cleanup()


# ---------------------------------------------------------------- binary tokens
def _tok(t):
    return struct.pack("<H", t)


def _fx(v):
    """A fixed-point value: token 0x0167 and the raw i64 (the value x 1e5)."""
    return _tok(0x0167) + struct.pack("<q", v)


def _u32(v):
    return _tok(0x0014) + struct.pack("<I", v)


def _i32(v):
    return _tok(0x000C) + struct.pack("<i", v)


def _i64(v):
    return _tok(0x029C) + struct.pack("<q", v)


def _str(text):
    raw = text.encode("latin1")
    return _tok(0x000F) + struct.pack("<H", len(raw)) + raw


def _kv(key, value):
    """`key = value`, or `key = { ... }` when value is a list of encoded items."""
    if isinstance(value, list):
        return _tok(key) + EQ + OPEN + b"".join(value) + CLOSE
    return _tok(key) + EQ + value


def _obj(items):
    """A bare `{ ... }` block (a queue element, a variable entry)."""
    return OPEN + b"".join(items) + CLOSE


def _block(country_id, items, tag=None):
    """`<u32 id> = { ... }` at offset 0; with a tag, the definition comes first, as in real saves."""
    head = [_kv(0x07DD, _str(tag))] if tag else []
    return _u32(country_id) + EQ + OPEN + b"".join(head + items) + CLOSE


def _variable(name, value):
    wrap = _kv(0x00E1, _tok(0x02D2)) + _kv(0x00DB, _i64(round(value * FX)))
    return _obj([_kv(0x0384, _str(name)), _kv(0x00F0, [wrap])])


def _ring(values, index, count, hours=60599496):
    channel = _obj([_kv(0x06B5, _i32(hours)), _kv(0x020C, _i32(index)), _kv(0x06EE, [_fx(v) for v in values])])
    return _kv(0x3F16, [_kv(0x3F14, _i32(28)), _kv(0x045A, _i32(count)), _kv(0x3F15, [_i32(0) + EQ + channel])])


def _element(state, speed=None, base=None):
    items = [_kv(0x00E1, _str("building_food_industry")), _kv(0x01B7, _u32(state)), _kv(0x2D93, _fx(100 * FX))]
    if speed is not None:
        items += [_kv(0x2E77, _fx(round(speed * FX))), _kv(0x59A1, _fx(round(base * FX)))]
    return _obj(items)


WORKFORCE = {"clerks": 300, "laborers": 500, "peasants": 1000}


def _country_items(ring=((100, 110, 120), 3, 5214), states=(7, 8)):
    """pop_statistics, budget, a gdp ring, two queues, states and two variables."""
    prof = [_i32(15)] + [_i32(S.PROFESSIONS.index(n)) + EQ + _fx(v) for n, v in WORKFORCE.items()]
    pop_stats = _kv(0x330D, [
        _kv(0x573C, _fx(3000)), _kv(0x573D, _fx(800)), _kv(0x573E, _fx(20)),
        _kv(0x5743, _fx(600)), _kv(0x5744, _fx(1000)), _kv(0x5745, _fx(200)),
        _kv(0x574C, prof),
    ])
    budget = _kv(0x3171, [
        _kv(0x3776, _fx(52940356)), _kv(0x5B51, _fx(1913236)), _kv(0x56C3, _fx(4148939733557)),
        _kv(0x33C7, _fx(-168782502625)),
        _kv(0x52D6, [_str("building_food_industry") + EQ + _fx(1142632009),
                     _str("building_textile_mill") + EQ + _fx(4628114067)]),
    ])
    values, index, count = ring
    gov = _kv(0x5720, [_kv(0x567F, [_element(7, 40, 40), _element(8)])])
    private = _kv(0x5721, [_kv(0x567F, [_element(7, 35, 30)])])
    variables = _kv(0x0555, [_kv(0x00F0, [_variable("prior_construction_scaling", 0.666),
                                          _variable("unrelated", 2.0)])])
    return [budget, _ring([v * FX for v in values], index, count), variables, pop_stats,
            _kv(0x09CD, [_u32(s) for s in states]), gov, private]


def _synthetic_country(cid=4, tag="FRA", **kw):
    return _block(cid, _country_items(**kw), tag=tag)


# ---------------------------------------------------------------- save files
def _tmp_file(data, name="save.v3"):
    path = Path(tempfile.mkdtemp(dir=_TMP.name)) / name
    path.write_bytes(data)
    return path


def _zip(entries):
    """Deflated, as the game writes them: a stored text meta would show `meta_data={` to is_text_save's sniff."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    return buf.getvalue()


def _tmp_binary_save(version="1.14.5", gamestate=b""):
    """A 24-byte SAV0105 header, then a zip holding a text `meta` and the gamestate."""
    meta = ('meta_data={\n\tversion="%s"\n}\n' % version).encode()
    return _tmp_file(b"SAV0105" + b"0" * 16 + b"\n" + _zip({"gamestate": gamestate, "meta": meta}))


def _tmp_sav0103(meta):
    """An autosave layout: the meta sits between the header and the zip, its length in header chars 15..23."""
    head = b"SAV0103" + b"0" * 8 + b"%08x" % len(meta) + b"\n"
    return _tmp_file(head + meta + _zip({"gamestate": b""}))


def _binary_meta(version):
    raw = version.encode()
    return _kv(0x55AD, [_kv(0x058F, _i32(1))]) + _tok(0x00EE) + EQ + _tok(0x000F) + struct.pack("<H", len(raw)) + raw


# ---------------------------------------------------------------- Task 1
class TestTokens(unittest.TestCase):
    def test_fx_value_is_fixed_point(self):
        blob = _block(4, [_kv(0x3171, [_kv(0x56C3, _fx(123456789))])])
        rec = S.country_record(blob, 0)
        self.assertAlmostEqual(rec["investment_pool"], 1234.56789)

    def test_ring_unwrapped(self):
        self.assertEqual(S.unwrap_ring([5, 6, 3, 4], index=6, count=4), [3, 4, 5, 6])

    def test_ring_not_wrapped(self):
        self.assertEqual(S.unwrap_ring([1, 2, 3], index=3, count=5214), [1, 2, 3])

    def test_ring_exactly_full(self):
        self.assertEqual(S.unwrap_ring([1, 2, 3, 4], index=4, count=4), [1, 2, 3, 4])

    def test_country_record_fields(self):
        blob = _synthetic_country()   # pop_statistics, budget, a 3-sample gdp ring, two queues
        rec = S.country_record(blob, 0)
        self.assertEqual(rec["workforce"], rec["salaried"] + rec["subsisting"] + rec["unemployed"])
        self.assertEqual(rec["points_weekly"], {"government": 40.0, "private": 35.0})
        self.assertEqual(rec["active_projects"], {"government": 1, "private": 1})
        self.assertEqual(rec["queued_projects"], {"government": 2, "private": 1})
        self.assertEqual(rec["per_project_cap"], 40.0)
        self.assertEqual(rec["gdp_weekly"][-1], rec["gdp"])

    def test_country_record_values(self):
        rec = S.country_record(_synthetic_country(), 0)
        self.assertEqual(rec["tag"], "FRA")
        self.assertEqual(rec["population"], 3820)
        self.assertEqual(rec["workforce"], 1800)
        self.assertEqual((rec["salaried"], rec["subsisting"], rec["unemployed"]), (600, 1000, 200))
        self.assertEqual(list(rec["workforce_by_profession"]), list(S.PROFESSIONS))
        self.assertEqual(rec["workforce_by_profession"]["peasants"], 1000)
        self.assertEqual(rec["workforce_by_profession"]["slaves"], 0)
        self.assertEqual(rec["gdp_weekly"], [100.0, 110.0, 120.0])
        self.assertEqual(rec["gdp_week_index"], 3)
        self.assertAlmostEqual(rec["base_wage"], 529.40356)
        self.assertAlmostEqual(rec["average_productivity"], 19.13236)
        self.assertAlmostEqual(rec["investment_pool"], 41489397.33557)
        self.assertAlmostEqual(rec["pool_spend_weekly"], 1687825.02625)   # stored as the pool's (negative) change
        self.assertEqual(rec["investment_by_type"],
                         {"building_food_industry": 11426.32009, "building_textile_mill": 46281.14067})
        self.assertEqual(rec["states"], [7, 8])
        self.assertEqual(rec["variables"], {"prior_construction_scaling": 0.666, "te_mon_gdp_last_year": None})

    def test_wrapped_ring_in_record(self):          # Review Focus 3: an early save and a wrapped one
        rec = S.country_record(_synthetic_country(ring=((5, 6, 3, 4), 6, 4)), 0)
        self.assertEqual(rec["gdp_weekly"], [3.0, 4.0, 5.0, 6.0])
        self.assertEqual(rec["gdp"], 6.0)

    def test_partial_block_has_absent_sections(self):   # R8: a budget-only block
        rec = S.country_record(_block(4, [_kv(0x3171, [_kv(0x56C3, _fx(1))])]), 0)
        self.assertIsNone(rec["tag"])
        for key in ("population", "workforce", "salaried", "subsisting", "unemployed", "gdp", "gdp_week_index",
                    "base_wage", "per_project_cap"):
            self.assertIsNone(rec[key], key)
        for key in ("workforce_by_profession", "points_weekly", "active_projects", "queued_projects"):
            self.assertEqual(rec[key], {}, key)
        self.assertEqual(rec["gdp_weekly"], [])
        self.assertEqual(rec["states"], [])
        self.assertEqual(rec["variables"], {"prior_construction_scaling": None, "te_mon_gdp_last_year": None})
        self.assertEqual(rec["investment_by_type"], {})

    def test_empty_block(self):
        rec = S.country_record(_block(4, []), 0)
        self.assertIsNone(rec["investment_pool"])
        self.assertEqual(rec["investment_by_type"], {})


class TestSupported(unittest.TestCase):
    def test_text_save_unsupported(self):
        p = _tmp_file(b"SAV0100" + b"0" * 17 + b"meta_data={")
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)

    def test_old_version_unsupported(self):
        p = _tmp_binary_save(version="1.13.9")
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)

    def test_supported_version_passes(self):
        p = _tmp_binary_save(version="1.14.5")
        S.check_supported(p)
        self.assertEqual(S.save_version(p), "1.14.5")

    def test_binary_meta_version_token(self):
        """Real binary meta has no ASCII `version`: the string sits under token 0x00ee."""
        p = _tmp_sav0103(_binary_meta("1.14.5"))
        self.assertEqual(S.save_version(p), "1.14.5")
        S.check_supported(p)

    def test_sav0103_meta_before_zip(self):
        p = _tmp_sav0103(b'meta_data={ version="1.14.4" }')
        self.assertEqual(S.save_version(p), "1.14.4")
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)

    def test_no_zip_unsupported(self):
        p = _tmp_file(b"SAV0105" + b"0" * 16 + b"\n" + b"not a zip at all")
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)

    def test_zip_without_gamestate_unsupported(self):
        meta = b'meta_data={ version="1.14.5" }'
        p = _tmp_file(b"SAV0105" + b"0" * 16 + b"\n" + _zip({"meta": meta}))
        with self.assertRaises(S.UnsupportedSave):
            S.check_supported(p)


# ---------------------------------------------------------------- Task 2 helpers
def _pop(pid, ptype, wf, state, workplace=None, dep=0, wages=0, welfare=0, location_first=True):
    """One pop record. Real saves write workforce and dependents before the location, and the
    workplace (a building id) after it; with location_first=False the location comes after the
    workplace, which only a full parse finds. 0x573b, which is not employment, is written as
    the whole workforce to show it is ignored."""
    budget = _kv(0x4EED, [_fx(round(wages * FX)), _fx(0), _fx(0), _fx(round(welfare * FX))] + [_fx(0)] * 9)
    loc = _kv(0x2819, _u32(state))
    counts = [_kv(0x2FD5, _fx(wf))] if wf else []
    counts += [_kv(0x573A, _fx(dep))] if dep else []
    place = [_kv(0x27DD, _i32(1))] + ([_kv(0x330B, _u32(workplace))] if workplace is not None else [])
    place += [_kv(0x573B, _fx(wf))]
    items = [_kv(0x00E1, _str(ptype))] + counts + ([loc] + place if location_first else place + [loc])
    return _block(pid, items + [budget])


def _pops(rows):
    """rows: (type, workforce, employed, state[, keywords for _pop]).

    The game keeps a pop's employed and unemployed workers in two pops: the employed
    one has a workplace (and takes the wages and dependents), the other has none (and
    takes the welfare). Peasants are one pop with a workplace (a subsistence farm).
    """
    out, pid = [], 1000
    for row in rows:
        ptype, wf, emp, state = row[:4]
        kw = dict(row[4]) if len(row) > 4 else {}
        welfare = kw.pop("welfare", 0)
        parts = [(wf, 1, kw)] if ptype == "peasants" else [(emp, 1, kw), (wf - emp, None, {"welfare": welfare})]
        for size, workplace, extra in parts:
            if size:
                out.append(_pop(pid, ptype, size, state, workplace=workplace, **extra))
                pid += 1
    return b"".join(out)


def _building(bid, btype, levels, state, staffing, employees, sales, cost, pms):
    items = [_kv(0x27F8, _str(btype)), _kv(0x3A52, _i32(levels)), _kv(0x01B7, _u32(state)),
             _kv(0x32ED, _fx(round(staffing * FX))), _kv(0x5607, _fx(employees)),
             _kv(0x2D15, _fx(round(cost * FX))), _kv(0x5606, _fx(round(sales * FX))),
             _kv(0x5925, [_str(pm) for pm in pms])]
    return _block(bid, items)


def _blob_with_countries(ids, extra=b""):
    """A country block per id (tags A00, A01, ...; country 4 is FRA), then pops and buildings for states 7-9."""
    tags = {cid: "FRA" if cid == 4 else "A%02d" % i for i, cid in enumerate(ids)}
    blocks = b"".join(_synthetic_country(cid, tags[cid], states=(7, 8) if cid == 4 else (20 + cid,)) for cid in ids)
    pops = _pops([("peasants", 1000, 0, 7, {"dep": 500}), ("laborers", 500, 300, 7, {"wages": 30.0}),
                  ("clerks", 100, 100, 8, {"wages": 20.0, "location_first": False}),
                  ("laborers", 200, 0, 9, {"welfare": 4.0})])
    buildings = (_building(5001, "building_textile_mill", 3, 7, 2.5, 300, 900.0, 400.0, ["pm_a", "pm_b"])
                 + _building(5002, "building_textile_mill", 2, 8, 2.0, 100, 500.0, 200.0, ["pm_a", "pm_c"])
                 + _building(5003, "building_food_industry", 1, 9, 1.0, 0, 0.0, 0.0, ["pm_d"]))
    return blocks + pops + buildings + extra


def _run_cli(paths, *args):
    out = io.StringIO()
    with redirect_stdout(out):
        rc = S.main([str(p) for p in paths] + list(args))
    return rc, out.getvalue()


def _extract(date, gdp_values, index, states=(7, 8), population=3820, cid=4, tag="FRA", core=True):
    """A minimal per-save extract, the shape extract() writes (JSON-loaded: string keys)."""
    pops = {"7": {"population": population, "workforce": 1500, "peasants": 1000, "employed": 300, "unemployed": 200,
                  "wages_weekly": 30.0, "welfare_weekly": 0.0}}
    buildings = [{"type": "building_textile_mill", "levels": 3, "state": 7, "staffing": 2.5, "employees": 300,
                  "goods_sales": 900.0, "goods_cost": 400.0, "pms": ["pm_a", "pm_b"]},
                 {"type": "building_textile_mill", "levels": 2, "state": 7, "staffing": 2.0, "employees": 100,
                  "goods_sales": 500.0, "goods_cost": 200.0, "pms": ["pm_a", "pm_c"]}]
    rec = {"tag": tag, "population": population, "gdp_weekly": list(gdp_values), "gdp": gdp_values[-1],
           "gdp_week_index": index, "states": list(states), "points_weekly": {"government": 1.0, "private": 2.0}}
    out = {"save": f"s_{date}.v3", "date": date, "version": "1.14.5", "playthrough": "c480d386-0000-0000-0000-000000000000",
           "countries": {str(cid): rec}, "whole": {str(cid): {"states": pops, "buildings": buildings}},
           "core": {}, "world": {"gdp": 10.0 * gdp_values[-1], "population": 10 * population}, "warnings": []}
    if core:
        out["core"][str(cid)] = {"state_ids": [7], "states": pops, "buildings": buildings[:1]}
    return out


# ---------------------------------------------------------------- Task 2
class TestExtract(unittest.TestCase):
    def test_missing_country_is_absent(self):          # Review Focus 2
        out = S.extract_from_blob(_blob_with_countries([4]), "1900.1.1", country_ids=[4, 99])
        self.assertIn(4, out["countries"])
        self.assertNotIn(99, out["countries"])
        self.assertNotIn(99, out["whole"])

    def test_explicit_headers(self):                    # R1: [(offset, id, tag)]
        blob = _block(4, _country_items())
        out = S.extract_from_blob(blob, "1900.1.1", country_ids=[4], headers=[(0, 4, "FRA")])
        self.assertEqual(out["countries"][4]["population"], 3820)
        self.assertEqual(out["countries"][4]["acquired_techs"], [])
        self.assertIsNone(out["countries"][4]["land_law"])

    def test_world_sums_every_block(self):
        out = S.extract_from_blob(_blob_with_countries([4, 5]), "1900.1.1", country_ids=[4])
        self.assertEqual(out["world"], {"gdp": 240.0, "population": 7640})
        self.assertEqual(list(out["countries"]), [4])

    def test_whole_and_core_slices(self):               # R2
        out = S.extract_from_blob(_blob_with_countries([4]), "1900.1.1", country_ids=[4], core={4: {7, 9}})
        whole, core = out["whole"][4], out["core"][4]
        self.assertEqual(sorted(whole["states"]), [7, 8])
        self.assertEqual(sorted(b["state"] for b in whole["buildings"]), [7, 8])
        self.assertEqual(core["state_ids"], [7, 9])
        self.assertEqual(sorted(core["states"]), [7, 9])
        self.assertEqual(sorted(b["state"] for b in core["buildings"]), [7, 9])
        self.assertEqual(whole["states"][8]["employed"], 100)   # found by the full parse (location after employed)

    def test_no_core_without_core_set(self):
        out = S.extract_from_blob(_blob_with_countries([4, 5]), "1900.1.1", country_ids=[4, 5], core={4: {7}})
        self.assertEqual(list(out["core"]), [4])
        self.assertEqual(sorted(out["whole"]), [4, 5])

    def test_pops_by_state_peasants_and_unemployed(self):
        blob = _pops([("peasants", 1000, 0, 7), ("laborers", 500, 300, 7), ("laborers", 200, 200, 8)])
        got = S.pops_by_state(blob, {7})
        self.assertEqual(got[7]["peasants"], 1000)
        self.assertEqual(got[7]["employed"], 300)
        self.assertEqual(got[7]["unemployed"], 200)
        self.assertNotIn(8, got)

    def test_pops_by_state_money_and_population(self):
        blob = _pops([("peasants", 1000, 0, 7, {"dep": 500, "wages": 9.0}),
                      ("laborers", 500, 300, 7, {"dep": 250, "wages": 30.0, "welfare": 2.5}),
                      ("clerks", 100, 100, 7, {"wages": 20.0, "location_first": False}),
                      ("je_not_a_pop", 100, 0, 7)])
        got = S.pops_by_state(blob, {7})[7]
        self.assertEqual(got["population"], 1000 + 500 + 500 + 250 + 100)
        self.assertEqual(got["workforce"], 1600)
        self.assertEqual(got["employed"], 400)
        self.assertAlmostEqual(got["wages_weekly"], 50.0)     # peasants' budget is not wages
        self.assertAlmostEqual(got["welfare_weekly"], 2.5)

    def test_buildings_in(self):
        blob = _blob_with_countries([4])
        got = S.buildings_in(blob, {7})
        self.assertEqual(got, [{"type": "building_textile_mill", "levels": 3, "state": 7, "staffing": 2.5,
                                "employees": 300, "goods_sales": 900.0, "goods_cost": 400.0, "pms": ["pm_a", "pm_b"]}])

    def test_land_law(self):
        laws = (_kv(0x5705, [_kv(0x05AB, [
            _block(1, [_kv(0x2B0A, _str("law_serfdom")), _kv(0x2840, _u32(4)), _kv(0x2AB2, _tok(0x000E) + b"\x01")]),
            _block(2, [_kv(0x2B0A, _str("law_homesteading")), _kv(0x2840, _u32(4))]),
            _block(3, [_kv(0x2B0A, _str("law_monarchy")), _kv(0x2840, _u32(4)), _kv(0x2AB2, _tok(0x000E) + b"\x01")]),
        ])]))
        groups = {"law_serfdom": "lawgroup_land_reform", "law_homesteading": "lawgroup_land_reform",
                  "law_monarchy": "lawgroup_governance_principles"}
        self.assertEqual(S.land_laws(laws, [], groups), {4: "law_serfdom"})

    def test_cli_skips_unsupported(self):                # Review Focus 1
        rc, out = _run_cli([_tmp_file(b"SAV0100" + b"0" * 17 + b"meta_data={")], "--country-id", "4")
        self.assertEqual(rc, 0)
        self.assertIn("skip", out)

    def test_cli_skips_other_version_and_carries_on(self):
        bad, out_path = _tmp_binary_save(version="1.13.9"), Path(_TMP.name) / "raw_skip.json"
        good = _tmp_binary_save(gamestate=_blob_with_countries([4]))
        rc, out = _run_cli([bad, good], "--country-id", "4", "--out", str(out_path))
        self.assertEqual(rc, 0)
        self.assertIn("skip save.v3: game version 1.13.9", out)
        raws = json.loads(out_path.read_text())
        self.assertEqual(len(raws), 1)
        self.assertEqual(raws[0]["countries"]["4"]["population"], 3820)

    def test_cli_core_from_json_extract(self):
        good = _tmp_binary_save(gamestate=_blob_with_countries([4, 5]))
        first, second = Path(_TMP.name) / "core_a.json", Path(_TMP.name) / "core_b.json"
        self.assertEqual(_run_cli([good], "--country-id", "4", "--country-id", "5", "--out", str(first))[0], 0)
        rc, _ = _run_cli([good], "--country-id", "4", "--country-id", "5", "--core-from", str(first),
                         "--core-id", "4", "--out", str(second))
        self.assertEqual(rc, 0)
        raw = json.loads(second.read_text())[0]
        self.assertEqual(raw["core"]["4"]["state_ids"], [7, 8])
        self.assertNotIn("5", raw["core"])


class TestDataset(unittest.TestCase):
    def setUp(self):
        # Weeks 0-3 in the first save, 2-5 in the second; the second's values for weeks 2-3 differ and must win.
        self.early = _extract("1900.1.29", [10.0, 20.0, 30.0, 40.0], index=4)
        self.late = _extract("1900.2.26", [300.0, 400.0, 50.0, 60.0], index=6, states=(7, 8, 9))
        gbr = _extract("1900.1.29", [1.0, 1.0, 1.0, 1.0], index=4, cid=1, tag="GBR", core=False)
        self.early["countries"]["1"] = gbr["countries"]["1"]
        self.early["whole"]["1"] = gbr["whole"]["1"]
        self.ds = S.build_dataset([self.late, self.early])

    def test_points_sorted_and_country_series_ends(self):   # Review Focus 2
        fra = self.ds["countries"]["4"]
        self.assertEqual([p["date"] for p in fra["points"]], ["1900.1.29", "1900.2.26"])
        self.assertEqual(len(self.ds["countries"]["1"]["points"]), 1)
        self.assertEqual(fra["tag_by_date"], {"1900.1.29": "FRA", "1900.2.26": "FRA"})
        self.assertNotIn("gdp_weekly", fra["points"][0])
        self.assertEqual(fra["points"][1]["states"], [7, 8, 9])

    def test_gdp_yearly_later_save_wins(self):
        self.assertEqual(self.ds["countries"]["4"]["gdp_yearly"], {"1900": (10 + 20 + 300 + 400 + 50 + 60) / 6})

    def test_slices(self):
        point = self.ds["countries"]["4"]["points"][0]
        whole, core = point["whole"], point["core"]
        self.assertEqual((whole["population"], whole["workforce"], whole["peasants"]), (3820, 1500, 1000))
        self.assertAlmostEqual(whole["wage_per_worker"], 30.0 / 300)
        self.assertEqual(whole["welfare_per_unemployed"], 0.0)
        mill = whole["buildings_by_type"]["building_textile_mill"]
        self.assertEqual(mill["levels"], 5)
        self.assertEqual(mill["employees"], 400)
        self.assertAlmostEqual(mill["goods_sales"], 1400.0)
        self.assertEqual(mill["pms"], {"pm_a": 5, "pm_b": 3, "pm_c": 2})
        self.assertEqual(core["buildings_by_type"]["building_textile_mill"]["pms"], {"pm_a": 3, "pm_b": 3})
        self.assertNotIn("core", self.ds["countries"]["1"]["points"][0])

    def test_world_core_states_and_playthrough(self):
        self.assertEqual(self.ds["playthrough"], "c480d386")
        self.assertEqual([w["date"] for w in self.ds["world"]], ["1900.1.29", "1900.2.26"])
        self.assertEqual(self.ds["core_states"], {"4": [7]})

    def test_mixed_playthroughs_refused(self):
        self.late["playthrough"] = "deadbeef-0000-0000-0000-000000000000"
        with self.assertRaises(ValueError):
            S.build_dataset([self.early, self.late])

    def test_undated_extract_refused(self):
        self.early["date"] = "?"
        with self.assertRaises(ValueError):
            S.build_dataset([self.early, self.late])

    def test_zero_employed_and_unemployed_stay_finite(self):
        for part in (self.early["whole"]["4"], self.early["core"]["4"]):
            part["states"] = {"7": dict(part["states"]["7"], employed=0, unemployed=0, wages_weekly=0.0)}
        point = S.build_dataset([self.early])["countries"]["4"]["points"][0]
        self.assertEqual((point["whole"]["wage_per_worker"], point["whole"]["welfare_per_unemployed"]), (0.0, 0.0))

    def test_cli_dataset_from_extract_files(self):
        paths = []
        for i, raw in enumerate((self.early, self.late)):
            paths.append(Path(_TMP.name) / f"extract_{i}.json")
            paths[-1].write_text(json.dumps(raw))
        out_path = Path(_TMP.name) / "dataset.json"
        rc, _ = _run_cli(paths, "--dataset", str(out_path))
        self.assertEqual(rc, 0)
        self.assertEqual(json.loads(out_path.read_text()), json.loads(json.dumps(self.ds)))


if __name__ == "__main__":
    unittest.main()
