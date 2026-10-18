"""Tests for scripts/analysis/econ_save_series.py (the economy growth sim's save reader, issue #1034).

The reader decodes 1.14.5 binary saves from token numbers worked out by hand. A
wrong number doesn't crash anything: a field just stops resolving and reads as
absent, or a fixed-point value reads as a float and comes out as garbage. These
tests build the binary layout byte by byte and check the values come back out.
They need neither Victoria 3 nor a save.

Run: .venv/bin/python -m unittest test_econ_save_series -v
"""

import io
import struct
import tempfile
import unittest
import zipfile
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


if __name__ == "__main__":
    unittest.main()
