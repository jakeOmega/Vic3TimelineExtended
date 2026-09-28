"""Tests for scripts/analysis/save_country_probe.py (per-country save dump and diff).

The probe decodes a Victoria 3 save's binary `gamestate` from token numbers worked
out by hand on real 1.14 saves. A wrong number does not crash anything: a key
simply stops resolving and the country reads as having no variables, which looks
like an answer. These tests pin the layout by building a synthetic `.v3` byte by
byte and asserting the values come back out, and pin the one piece of judgement
the tool makes — recognising a civil war that has ended, whichever side won, and
reporting what the survivor did with the loser's variables. Laws add a second
failure mode that looks like an answer: a law put in the wrong group, which the
depth-aware law-file reader exists to prevent, hides or invents a conflict.

Run: .venv/bin/python test_save_country_probe.py
"""

import io
import struct
import sys
import tempfile
import unittest
import zipfile
from contextlib import redirect_stdout
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / 'scripts' / 'analysis'))
import save_country_probe as scp  # noqa: E402

EQ = b'\x01\x00'
OPEN = b'\x03\x00'
CLOSE = b'\x04\x00'
I32 = b'\x0c\x00'
BOOL = b'\x0e\x00'
STR = b'\x0f\x00'
U32 = b'\x14\x00'
I64 = b'\x9c\x02'


def tok(n):
    return struct.pack('<H', n)


def string(text):
    raw = text.encode('ascii')
    return STR + struct.pack('<H', len(raw)) + raw


def variable(name, value):
    """One entry of a country's variable block.

    value: a number (script value), ('country', id), 'flag', or 0 (saved with no value).
    """
    if value == 'flag':
        wrapper = tok(scp.KEY_KIND) + EQ + tok(0x0500)
    elif isinstance(value, tuple):
        wrapper = tok(scp.KEY_KIND) + EQ + tok(scp.KIND_COUNTRY) + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', value[1])
    elif value == 0:
        wrapper = tok(scp.KEY_KIND) + EQ + tok(scp.KIND_VALUE)
    else:
        wrapper = (
            tok(scp.KEY_KIND) + EQ + tok(scp.KIND_VALUE)
            + tok(scp.KEY_VAL) + EQ + I64 + struct.pack('<q', round(value * scp.FIXED))
        )
    return (
        OPEN + tok(scp.KEY_NAME) + EQ + string(name)
        + tok(scp.KEY_DATA) + EQ + OPEN + wrapper + CLOSE + CLOSE
    )


def country(cid, tag, flags=(), variables=None, modifiers=()):
    body = b''.join(tok(f) + EQ + BOOL + bytes([1]) for f in flags)
    body += tok(scp.KEY_DEF) + EQ + string(tag)
    if variables:
        body += (
            tok(scp.KEY_VARS) + EQ + OPEN + tok(scp.KEY_DATA) + EQ + OPEN
            + b''.join(variable(k, v) for k, v in variables.items())
            + CLOSE + CLOSE
        )
    if modifiers:
        body += modifier_block(modifiers)
    return U32 + struct.pack('<I', cid) + EQ + OPEN + body + CLOSE


def modifier_block(modifiers):
    entries = b''.join(
        OPEN + tok(0x000B) + EQ + U32 + struct.pack('<I', i)
        + tok(scp.KEY_MODNAME) + EQ + string(m)
        + tok(0x0CF8) + EQ + I32 + struct.pack('<i', 1000) + CLOSE
        for i, m in enumerate(modifiers)
    )
    return tok(scp.KEY_MODS) + EQ + OPEN + tok(scp.KEY_MODLIST) + EQ + OPEN + entries + CLOSE + CLOSE


def record(rid, type_name, owner, active=None, modifiers=()):
    """A journal-entry-shaped record; other databases (combat units) share this shape."""
    out = U32 + struct.pack('<I', rid) + EQ + OPEN + tok(scp.KEY_KIND) + EQ + string(type_name)
    out += scp.JE_OWNER + struct.pack('<I', owner)
    if active is not None:
        out += scp.JE_ACTIVE + bytes([active])
    if modifiers:
        out += modifier_block(modifiers)
    return out + CLOSE


def law(rid, name, owner, active=False, since=None, replaced=None, enacting=None, mark=False):
    """One country-law record. An inactive law is saved with no active key at all."""
    out = U32 + struct.pack('<I', rid) + EQ + OPEN + tok(scp.KEY_LAW_TYPE) + EQ + string(name)
    out += tok(scp.KEY_OWNER) + EQ + U32 + struct.pack('<I', owner)
    if active:
        out += tok(scp.KEY_ACTIVE) + EQ + BOOL + b'\x01'
    if mark:  # 0x5fac, undecoded; must not upset the walk
        out += tok(0x5FAC) + EQ + BOOL + b'\x01'
    if since is not None:
        out += tok(scp.KEY_LAW_SINCE) + EQ + I32 + struct.pack('<i', since)
    if replaced:
        out += tok(scp.KEY_LAW_REPLACED) + EQ + string(replaced)
    if enacting is not None:
        out += tok(scp.KEY_LAW_ENACTING) + EQ + I32 + struct.pack('<i', enacting)
    return out + CLOSE


def law_db(*records):
    """The law database; a free slot (`<id> = 0x0165`) sits among the records, as in real saves."""
    free = U32 + struct.pack('<I', 999) + EQ + tok(0x0165)
    body = records[0] + free + b''.join(records[1:]) if records else free
    return tok(scp.KEY_LAW_DB) + EQ + OPEN + tok(scp.KEY_DATABASE) + EQ + OPEN + body + CLOSE + CLOSE


def hours(year, month, day):
    days = (year + 5000) * 365 + sum(scp.MONTHS[: month - 1]) + day - 1
    return days * 24


def write_save(countries, records=(), date=(2003, 11, 18)):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('gamestate', b''.join(countries) + b''.join(records))
        archive.writestr('meta', b'\x45\x32' + EQ + I32 + struct.pack('<i', hours(*date)))
    handle = tempfile.NamedTemporaryFile(suffix='.v3', delete=False)
    handle.write(b'SAV01030deadbeef00005ba\n' + buf.getvalue())
    handle.close()
    return handle.name


ORIGINAL, REBEL, SPAIN = 5, 0x0100005A, 37
HOLDER, REVOLT = scp.FLAG_TAG_HOLDER, scp.FLAG_REVOLUTIONARY


class DecodingTests(unittest.TestCase):
    """The hand-derived token numbers: wrong by one and nothing resolves."""

    def setUp(self):
        self.path = write_save(
            [
                country(ORIGINAL, 'GER', flags=[HOLDER], modifiers=['nuclear_power', 'un_dues_modifier'], variables={
                    'nuclear_weapon_stockpile': 16,
                    'nuclear_weapons_program_funding': 0,
                    'nd_crisis_last_opponent': ('country', SPAIN),
                    'nd_warning_suspect': ('country', 999),
                    'nuclear_weapon_events.21': 'flag',
                }),
                country(SPAIN, 'SPA', flags=[HOLDER], variables={'nd_doctrine': 3}),
            ],
            records=[
                record(1, 'je_nuclear_program', ORIGINAL, active=1, modifiers=['nd_upkeep_cost']),
                record(2, 'je_strategic_reserve', ORIGINAL, active=0),
                record(3, 'slave_owner_paranoia', ORIGINAL, active=1),
                record(4, 'combat_unit_type_armored_infantry', ORIGINAL),
            ],
        )

    def test_country_block_decodes(self):
        save = scp.Save(self.path, scp.Filters(tags=['GER']))
        recs = save.select()
        self.assertEqual(list(recs), [ORIGINAL])
        rec = recs[ORIGINAL]
        self.assertEqual(rec['tag'], 'GER')
        self.assertEqual(rec['flags'], {HOLDER: 1})
        self.assertIsNone(rec['warning'], 'block must end exactly at the next header')
        self.assertEqual(rec['vars']['nuclear_weapon_stockpile'], 16.0)
        self.assertEqual(rec['vars']['nuclear_weapons_program_funding'], 0.0, 'a zero is saved with no value')
        self.assertEqual(rec['vars']['nd_crisis_last_opponent'], ('country', SPAIN))
        self.assertEqual(rec['vars']['nuclear_weapon_events.21'], 'flag')
        self.assertEqual(rec['modifiers'], ['nuclear_power', 'un_dues_modifier'])

    def test_journal_keeps_entries_and_drops_other_databases(self):
        found = scp.journal_entries(scp.read_gamestate(self.path))[ORIGINAL]
        self.assertEqual(
            sorted((t, a) for t, a, _ in found),
            [('je_nuclear_program', 1), ('je_strategic_reserve', 0), ('slave_owner_paranoia', 1)],
        )

    def test_journal_shows_running_entries_unless_one_is_named(self):
        rec = scp.Save(self.path, scp.Filters(tags=['GER'])).select()[ORIGINAL]
        self.assertEqual(rec['journal'], [('je_nuclear_program', 1), ('slave_owner_paranoia', 1)])
        rec = scp.Save(self.path, scp.Filters(je='je_strategic_reserve')).select()[ORIGINAL]
        self.assertEqual(rec['journal'], [('je_strategic_reserve', 0)])

    def test_journal_entry_modifiers_decode(self):
        rec = scp.Save(self.path, scp.Filters(tags=['GER'])).select()[ORIGINAL]
        self.assertEqual(rec['journal_modifiers']['je_nuclear_program'], ['nd_upkeep_cost'])
        self.assertNotIn('je_strategic_reserve', rec['journal_modifiers'], 'inactive entries are not decoded')

    def test_country_reference_names_its_tag_or_says_gone(self):
        save = scp.Save(self.path, scp.Filters())
        rec = save.record(ORIGINAL)
        self.assertEqual(scp.fmt_value(rec['vars']['nd_crisis_last_opponent'], save.tags), 'country#37(SPA)')
        self.assertEqual(scp.fmt_value(rec['vars']['nd_warning_suspect'], save.tags), 'country#999(gone)')

    def test_save_date(self):
        self.assertEqual(scp.save_date(self.path), '2003.11.18')


class JournalNameTests(unittest.TestCase):
    """Entries are told from other databases by name; a prefix-less entry missing here would read as absent."""

    def test_every_prefixless_vanilla_entry_is_listed(self):
        snapshot = Path(__file__).resolve().parent / 'vanilla_parsed' / 'common' / 'journal_entries.json'
        if not snapshot.exists():
            self.skipTest('no vanilla_parsed snapshot')
        import json
        keys = json.loads(snapshot.read_text(encoding='utf-8'))
        prefixless = {k for k in keys if not k.startswith('je_')}
        self.assertEqual(prefixless, scp.VANILLA_JE_WITHOUT_PREFIX,
                         'update VANILLA_JE_WITHOUT_PREFIX in save_country_probe.py')

    def test_exact_name_bypasses_the_heuristic(self):
        self.assertTrue(scp.is_journal_type('some_modded_entry', wanted='some_modded_entry'))
        self.assertFalse(scp.is_journal_type('combat_unit_type_armored_infantry'))


class FilterTests(unittest.TestCase):
    def setUp(self):
        self.path = write_save([
            country(ORIGINAL, 'GER', flags=[HOLDER], modifiers=['nuclear_power'],
                    variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 100}),
            country(SPAIN, 'SPA', flags=[HOLDER], variables={'te_bank_gold': 5}),
        ])

    def test_var_filter_selects_and_trims(self):
        recs = scp.Save(self.path, scp.Filters(var='^nuclear_')).select()
        self.assertEqual(list(recs), [ORIGINAL])
        self.assertEqual(recs[ORIGINAL]['vars'], {'nuclear_weapon_stockpile': 16.0})

    def test_modifier_filter(self):
        self.assertEqual(list(scp.Save(self.path, scp.Filters(modifier='^nuclear_power$')).select()), [ORIGINAL])

    def test_byte_probe_never_hides_a_match(self):
        self.assertIsNotNone(scp.Filters._bytes_probe('^te_bank_(gold|silver)$'))
        self.assertIsNone(scp.Filters._bytes_probe('^a$|^b$'), 'inner anchors cannot be applied to raw bytes')
        both = scp.Save(self.path, scp.Filters(var='^te_bank_gold$')).select()
        self.assertEqual(set(both), {ORIGINAL, SPAIN})


GOV, CRIME = 'lawgroup_governance_principles', 'lawgroup_criminal_justice'
GROUPS = {
    'law_monarchy': GOV,
    'law_presidential_republic': GOV,
    'law_punishment_focused_criminal_justice': CRIME,
    'law_penal_labor_camps': CRIME,
    'law_restorative_justice': CRIME,
}


class LawDecodingTests(unittest.TestCase):
    """Law records: active is the presence of 0x2ab2, groups come from the law files, not the save."""

    def setUp(self):
        self.path = write_save(
            [country(ORIGINAL, 'GER', flags=[HOLDER]), country(SPAIN, 'SPA', flags=[HOLDER])],
            records=[law_db(
                law(1, 'law_presidential_republic', ORIGINAL, active=True, since=hours(1882, 9, 4),
                    replaced='law_monarchy', mark=True),
                law(2, 'law_monarchy', ORIGINAL, since=hours(1836, 1, 1)),
                law(3, 'law_punishment_focused_criminal_justice', ORIGINAL, active=True, since=hours(1836, 1, 1)),
                law(4, 'law_penal_labor_camps', ORIGINAL),
                law(5, 'law_restorative_justice', ORIGINAL, enacting=hours(2003, 10, 1)),
                law(6, 'law_mystery_a', ORIGINAL, active=True),
                law(7, 'law_monarchy', SPAIN, active=True, since=hours(1836, 1, 1)),
                law(8, 'law_punishment_focused_criminal_justice', SPAIN, active=True, since=hours(1836, 1, 1)),
                law(9, 'law_penal_labor_camps', SPAIN, active=True, since=hours(2020, 2, 1)),
                law(10, 'law_mystery_a', SPAIN, active=True),
                law(11, 'law_mystery_b', SPAIN, active=True),
            )],
        )

    def save(self, **filters):
        return scp.Save(self.path, scp.Filters(**filters), GROUPS)

    def test_records_decode_by_key(self):
        recs, warning = scp.law_records(scp.read_gamestate(self.path))
        self.assertIsNone(warning, 'every law-type key in the gamestate is inside the database')
        self.assertEqual(len(recs), 11, 'the free slot is skipped')
        by = {(r['country'], r['law']): r for r in recs}
        self.assertEqual(by[ORIGINAL, 'law_presidential_republic'], {
            'law': 'law_presidential_republic', 'country': ORIGINAL, 'active': True,
            'since': hours(1882, 9, 4), 'replaced': 'law_monarchy', 'enacting': None,
        })
        monarchy = by[ORIGINAL, 'law_monarchy']
        self.assertFalse(monarchy['active'], 'no 0x2ab2 means inactive')
        self.assertEqual(monarchy['since'], hours(1836, 1, 1), 'an inactive law keeps its date')
        self.assertIsNone(by[ORIGINAL, 'law_penal_labor_camps']['since'])
        self.assertEqual(by[ORIGINAL, 'law_restorative_justice']['enacting'], hours(2003, 10, 1))

    def test_record_holds_only_active_laws_sorted_by_group(self):
        rec = self.save(tags=['GER']).select()[ORIGINAL]
        self.assertEqual([(x['group'], x['law']) for x in rec['laws']], [
            (CRIME, 'law_punishment_focused_criminal_justice'),
            (GOV, 'law_presidential_republic'),
            (None, 'law_mystery_a'),
        ])
        self.assertEqual(rec['enacting'], ('law_restorative_justice', hours(2003, 10, 1)))

    def test_law_filter_matches_name_or_group(self):
        recs = self.save(law='^law_penal_labor_camps$').select()
        self.assertEqual(list(recs), [SPAIN], 'GER holds the law only inactive')
        self.assertEqual([x['law'] for x in recs[SPAIN]['laws']], ['law_penal_labor_camps'])
        recs = self.save(law='^lawgroup_criminal_justice$').select()
        self.assertEqual(set(recs), {ORIGINAL, SPAIN})
        self.assertEqual([x['law'] for x in recs[SPAIN]['laws']],
                         ['law_penal_labor_camps', 'law_punishment_focused_criminal_justice'])

    def test_laws_flag_prints_only_laws_and_marks_a_clash(self):
        out = io.StringIO()
        with redirect_stdout(out):
            scp.report(self.path, scp.Filters(tags=['SPA'], laws=True), GROUPS)
        text = out.getvalue()
        self.assertIn('laws, active (5):', text)
        self.assertIn(f'{CRIME}: law_penal_labor_camps (since 2020.2.1); '
                      'law_punishment_focused_criminal_justice (since 1836.1.1)  <- 2 ACTIVE IN ONE GROUP', text)
        self.assertIn('?: law_mystery_a; law_mystery_b\n', text, 'unknown-group laws are listed, never marked')
        self.assertNotIn('variables', text)

    def test_conflicts(self):
        save = self.save()
        found = scp.law_conflicts(save.active_laws, GROUPS)
        self.assertEqual(list(found), [SPAIN], 'two laws with no known group are not a conflict')
        self.assertEqual([r['law'] for r in found[SPAIN][CRIME]],
                         ['law_penal_labor_camps', 'law_punishment_focused_criminal_justice'])

    def test_conflict_report(self):
        out = io.StringIO()
        with redirect_stdout(out):
            count = scp.conflict_report(self.path, scp.Filters(), GROUPS)
        text = out.getvalue()
        self.assertEqual(count, 1)
        self.assertIn('2 countries with active laws (8 laws), 1 with two or more active in one group', text)
        self.assertIn(f'SPA id={SPAIN}: {CRIME}: law_penal_labor_camps (since 2020.2.1); '
                      'law_punishment_focused_criminal_justice (since 1836.1.1)', text)
        self.assertIn(f'by group: {CRIME} 1', text)
        self.assertIn('by law set: law_penal_labor_camps + law_punishment_focused_criminal_justice 1', text)
        self.assertIn('by the date the newer law became active: 2020.2.1 1', text)
        self.assertIn('not checked, no known group (2): law_mystery_a, law_mystery_b', text)
        with redirect_stdout(io.StringIO()):
            self.assertEqual(scp.conflict_report(self.path, scp.Filters(tags=['GER']), GROUPS), 0)

    def test_diff_reports_laws_turning_on_and_off(self):
        after = write_save(
            [country(ORIGINAL, 'GER', flags=[HOLDER]), country(SPAIN, 'SPA', flags=[HOLDER])],
            records=[law_db(
                law(1, 'law_presidential_republic', ORIGINAL, active=True, since=hours(1882, 9, 4),
                    replaced='law_monarchy'),
                law(3, 'law_punishment_focused_criminal_justice', ORIGINAL, active=True, since=hours(1836, 1, 1)),
                law(4, 'law_penal_labor_camps', ORIGINAL, active=True, since=hours(2003, 11, 2)),
                law(6, 'law_mystery_a', ORIGINAL),
            )],
        )
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(self.path, after, scp.Filters(tags=['GER']), GROUPS)
        text = out.getvalue()
        self.assertIn(f'+law law_penal_labor_camps (since 2003.11.2) [{CRIME}]', text)
        self.assertIn('-law law_mystery_a [?]', text)
        self.assertNotIn('law_presidential_republic', text, 'an unchanged law is not a change')

    def test_no_law_database_is_a_warning_not_an_empty_answer(self):
        path = write_save([country(ORIGINAL, 'GER')])
        save = scp.Save(path, scp.Filters(), GROUPS)
        self.assertEqual(save.active_laws, {})
        self.assertIn('no law database', save.law_warning)

    def test_a_law_record_outside_the_database_is_a_warning(self):
        stray = tok(scp.KEY_LAW_TYPE) + EQ + string('law_monarchy')
        path = write_save([country(ORIGINAL, 'GER')], records=[law_db(law(1, 'law_monarchy', ORIGINAL)), stray])
        self.assertIn('2 law-type keys in the gamestate but 1 law records decoded',
                      scp.law_records(scp.read_gamestate(path))[1])


class LawGroupTests(unittest.TestCase):
    """Law -> group from the law files: only `group` at the law block's own depth counts."""

    TEXT = '''﻿# law_commented = { group = lawgroup_comment    a stray { in a comment
law_a = {
\tgroup = lawgroup_a
\tcan_enact = {
\t\tgroup = lawgroup_nested   # nested: must not win
\t}
\thas_ruling_interest_group = ig_industrialists
}
law_b = {
\tmodifier = { x = 1 }
\tpossible = { OR = { group = lawgroup_deep } }
\tinterest_group = lawgroup_wrong
}
INJECT:law_c = {
\tgroup = lawgroup_c
}
REPLACE:law_d = { group = "lawgroup_d" }
TRY_INJECT:law_e={group=lawgroup_e}
'''

    def test_depth_and_whole_token(self):
        self.assertEqual(scp.law_groups_from_text(self.TEXT), {
            'law_a': 'lawgroup_a',
            'law_c': 'lawgroup_c',
            'law_d': 'lawgroup_d',
            'law_e': 'lawgroup_e',
        })

    def write(self, folder, name, text):
        folder.mkdir(parents=True, exist_ok=True)
        (folder / name).write_text(text, encoding='utf-8-sig')

    def test_mod_layers_over_vanilla(self):
        with tempfile.TemporaryDirectory() as tmp:
            vanilla, mod = Path(tmp) / 'vanilla', Path(tmp) / 'mod'
            self.write(vanilla, '00_a.txt', 'law_x = { group = g_x }\nlaw_y = { group = g_y_old }\n')
            self.write(vanilla, '00_b.txt', 'law_z = { group = g_z }\n')
            self.write(mod, '00_b.txt', 'law_w = { group = g_w }\n')  # replaces vanilla's 00_b.txt
            self.write(mod, 'extra.txt', 'INJECT:law_x = { modifier = { a = 1 } }\nINJECT:law_y = { group = g_y_new }\n')
            self.assertEqual(scp.law_groups(vanilla, None, mod),
                             {'law_x': 'g_x', 'law_y': 'g_y_new', 'law_w': 'g_w'})

    def test_snapshot_stands_in_for_a_missing_install(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            snapshot, mod = Path(tmp) / 'laws.json', Path(tmp) / 'mod'
            snapshot.write_text(json.dumps({
                'law_x': ['=', {'group': ['=', 'g_x'], 'icon': ['=', '"x.dds"']}],
                'law_q': ['=', {'icon': ['=', '"q.dds"']}],
            }), encoding='utf-8')
            self.write(mod, 'm.txt', 'law_m = { group = g_m }\n')
            self.assertEqual(scp.law_groups(Path(tmp) / 'no_install', snapshot, mod), {'law_x': 'g_x', 'law_m': 'g_m'})
            self.assertEqual(scp.law_groups(None, None, mod), {'law_m': 'g_m'}, 'nothing but the mod: no error')

    def test_this_checkout(self):
        """A naive scan gave the mod's group-less INJECT:law_elected_bureaucrats the next block's group."""
        repo = Path(__file__).resolve().parent
        snapshot = repo / 'vanilla_parsed' / 'common' / 'laws.json'
        if not snapshot.exists():
            self.skipTest('no vanilla_parsed snapshot')
        groups = scp.law_groups(None, snapshot, repo / 'common' / 'laws')
        self.assertEqual(groups['law_elected_bureaucrats'], 'lawgroup_bureaucracy')
        self.assertEqual(groups['law_penal_labor_camps'], 'lawgroup_criminal_justice')
        self.assertEqual(groups['law_punishment_focused_criminal_justice'], 'lawgroup_criminal_justice')


class CivilWarTests(unittest.TestCase):
    """The MERGE report, and recognising an ended civil war whichever side won."""

    BEFORE = [
        country(ORIGINAL, 'GER', flags=[HOLDER], modifiers=['nuclear_power'],
                variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 111}),
        country(REBEL, 'GER', flags=[REVOLT], variables={'te_bank_gold': 3}),
    ]

    def test_revolution_won(self):
        before = write_save(self.BEFORE)
        after = write_save([
            country(ORIGINAL, 'GER', variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 111}),
            country(REBEL, 'GER', flags=[HOLDER], variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 3}),
        ], date=(2003, 12, 3))
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(before, after, scp.Filters(tags=['GER']))
        text = out.getvalue()
        self.assertIn(f'MERGE: loser id {ORIGINAL} -> survivor id {REBEL}', text)
        self.assertIn('inherited (the loser\'s only, now on the survivor): 1', text)
        self.assertIn('survivor kept its own 1, took the loser\'s 0', text)
        self.assertIn('the loser\'s own modifiers: 1, also on the survivor now: 0', text)

    def test_merge_counts_the_losers_laws(self):
        before = write_save(
            [country(ORIGINAL, 'GER', flags=[HOLDER]), country(REBEL, 'GER', flags=[REVOLT])],
            records=[law_db(
                law(1, 'law_monarchy', ORIGINAL, active=True),
                law(2, 'law_penal_labor_camps', ORIGINAL, active=True),
                law(3, 'law_presidential_republic', REBEL, active=True),
            )],
        )
        after = write_save(
            [country(ORIGINAL, 'GER'), country(REBEL, 'GER', flags=[HOLDER])],
            records=[law_db(
                law(3, 'law_presidential_republic', REBEL, active=True),
                law(4, 'law_penal_labor_camps', REBEL, active=True),
            )],
        )
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(before, after, scp.Filters(tags=['GER']), GROUPS)
        text = out.getvalue()
        self.assertIn(f'MERGE: loser id {ORIGINAL} -> survivor id {REBEL}', text)
        self.assertIn("the loser's own active laws: 2, also active on the survivor now: 1 ['law_penal_labor_camps']",
                      text)

    def test_loyalists_won(self):
        a = {ORIGINAL: {'flags': {HOLDER: 1}}, REBEL: {'flags': {REVOLT: 1}}}
        z = {ORIGINAL: {'flags': {HOLDER: 1}}}
        self.assertEqual(scp.civil_war_outcome(a, z), (ORIGINAL, REBEL))

    def test_war_still_running_is_not_an_outcome(self):
        a = {ORIGINAL: {'flags': {HOLDER: 1}}, REBEL: {'flags': {REVOLT: 1}}}
        self.assertIsNone(scp.civil_war_outcome(a, a))

    def test_var_filter_keeps_the_pair_together(self):
        """The rebel holds no nuclear variable before the win; it must still be compared."""
        before = write_save(self.BEFORE)
        after = write_save([
            country(REBEL, 'GER', flags=[HOLDER], variables={'nuclear_weapon_stockpile': 16, 'te_bank_gold': 3}),
        ])
        out = io.StringIO()
        with redirect_stdout(out):
            scp.diff(before, after, scp.Filters(var='^nuclear_'))
        self.assertIn(f'MERGE: loser id {ORIGINAL} -> survivor id {REBEL}', out.getvalue())


if __name__ == '__main__':
    unittest.main()
