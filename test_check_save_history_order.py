"""Tests for scripts/analysis/check_save_history_order.py (the #356 save checker).

The checker reads a Victoria 3 save's binary `gamestate` by pattern-matching two
structures and stepping over a fixed number of token bytes to reach each value.
Those step counts were hand-derived from one save; a single wrong offset makes
the whole file resolve to "0 sample containers" and the check passes vacuously,
which is exactly how the first draft failed. These tests pin them by building a
synthetic `.v3` byte for byte and asserting the values come back out.

They also pin what fails: a store out of order, live or `frozen` (stopped
recording). A frozen one used to pass, being unreachable; National Info shows
another country's charts, so it fails now, and the old-save repair
te_repair_history_order sorts every store once. `frozen` is still printed, one
month (or, for Demographics' yearly te_dg_hist, one year) of slack, because a
store can miss the current step depending on where its pulse sits relative to
the save. te_dg_hist is checked too, on its own clock.

Run: .venv/bin/python test_check_save_history_order.py
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
import check_save_history_order as csho  # noqa: E402

FIXED_POINT = 100000

# Clausewitz binary tokens this fixture emits, named as the checker's docstring
# describes them.
EQUALS = b'\x01\x00'
OPEN = b'\x03\x00'
CLOSE = b'\x04\x00'
I32 = b'\x0c\x00'
QUOTED = b'\x0f\x00'
U32 = b'\x14\x00'
I64 = b'\x9c\x02'
VAR_NAME = b'\x84\x03'
VAR_TYPE = b'\x85\x03'
VALUE_WRAPPER = b'\xf0\x00'
REF_KIND = b'\xe1\x00'
REF_ID = b'\xdb\x00'
KIND_VALUE = b'\xd2\x02'
KIND_CONTAINER = b'\x60\x03'
CONTAINER_BODY = b'\x55\x05'
LIST_ITEM = b'\x52\x03'


def _string(text):
    raw = text.encode('ascii')
    return QUOTED + struct.pack('<H', len(raw)) + raw


def _container(container_id, month_index):
    """One script container carrying a single `te_hist_i` variable."""
    return (
        U32 + struct.pack('<I', container_id) + EQUALS + OPEN
        + CONTAINER_BODY + EQUALS + OPEN
        + VAR_NAME + EQUALS + _string('te_hist_i')
        + VAR_TYPE + EQUALS + I32 + struct.pack('<i', 0)
        + VALUE_WRAPPER + EQUALS + OPEN + REF_KIND + EQUALS + KIND_VALUE
        + REF_ID + EQUALS + I64 + struct.pack('<q', month_index * FIXED_POINT)
        + CLOSE + CLOSE + CLOSE
    )


def _sample_list(container_ids, name='te_hist'):
    """One `name` variable list, in the given order."""
    out = _string(name)
    for container_id in container_ids:
        out += (
            LIST_ITEM + EQUALS + OPEN
            + REF_KIND + EQUALS + KIND_CONTAINER
            + REF_ID + EQUALS + I64 + struct.pack('<q', container_id)
            + CLOSE
        )
    return out + CLOSE


def _save(stores, dg_stores=()):
    """Write a synthetic .v3: 24-byte header, then a zip holding `gamestate`.

    `stores` is a list of [(container_id, month_index), ...] in list order;
    `dg_stores` the same for Demographics' `te_dg_hist`, a year in te_hist_i.
    """
    containers = b''
    lists = b''
    for name, group in (('te_hist', stores), ('te_dg_hist', dg_stores)):
        for store in group:
            for container_id, month_index in store:
                containers += _container(container_id, month_index)
            lists += _sample_list([container_id for container_id, _ in store], name)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.writestr('gamestate', containers + lists)

    handle = tempfile.NamedTemporaryFile(suffix='.v3', delete=False)
    handle.write(b'SAV01030deadbeef00005ba\n' + buf.getvalue())
    handle.close()
    return handle.name


def _run(stores, dg_stores=()):
    """Return (out_of_order_count, printed_output)."""
    path = _save(stores, dg_stores)
    out = io.StringIO()
    with redirect_stdout(out):
        broken = csho.check_save(path)
    return broken, out.getvalue()


NOW = 1868 * 12 + 7  # 1868.08, the month the real save was verified against


def _ordered(first_id, newest_month, count=10):
    months = range(newest_month - count + 1, newest_month + 1)
    return list(zip(range(first_id, first_id + count), months))


def _rotated(first_id, newest_month, count=10, split=5):
    """Chronological samples, listed as [the newest `split`][the older rest].

    This is the exact shape `remove_list_variable` leaves behind: one break,
    both halves internally ascending.
    """
    chronological = _ordered(first_id, newest_month, count)
    return chronological[split:] + chronological[:split]


class BinaryDecodingTests(unittest.TestCase):
    """The hand-derived token offsets: wrong by one and nothing resolves."""

    def test_month_indices_and_list_order_round_trip(self):
        store = _rotated(1, NOW)
        blob = csho.read_gamestate(_save([store]))

        months = csho.month_index_by_container(blob)
        self.assertEqual(months, {cid: month for cid, month in store})

        lists = csho.sample_lists(blob)
        self.assertEqual(len(lists), 1)
        _, ids = lists[0]
        self.assertEqual(ids, [cid for cid, _ in store])

    def test_every_store_is_found_not_just_the_first(self):
        blob = csho.read_gamestate(_save([_ordered(1, NOW), _ordered(50, NOW)]))
        self.assertEqual(len(csho.sample_lists(blob)), 2)
        self.assertEqual(len(csho.month_index_by_container(blob)), 20)

    def test_a_save_with_no_history_resolves_to_nothing(self):
        blob = csho.read_gamestate(_save([]))
        self.assertEqual(csho.sample_lists(blob), [])
        self.assertEqual(csho.month_index_by_container(blob), {})


class ClassificationTests(unittest.TestCase):
    """Any store out of order fails; a frozen one is labelled as such."""

    def test_ordered_stores_pass(self):
        broken, out = _run([_ordered(1, NOW), _ordered(50, NOW)])
        self.assertEqual(broken, 0)
        self.assertIn('ascending=True', out)
        self.assertNotIn('ascending=False', out)

    def test_live_store_out_of_order_fails(self):
        broken, out = _run([_ordered(1, NOW), _rotated(50, NOW)])
        self.assertEqual(broken, 1)
        self.assertIn('break@', out)
        self.assertNotIn('frozen', out)

    def test_frozen_store_out_of_order_fails(self):
        # 100 months behind the newest month anywhere in the save: a country
        # that stopped recording, so it never evicts and never re-sorts. National
        # Info shows its charts, so it fails, labelled frozen.
        broken, out = _run([_ordered(1, NOW), _rotated(50, NOW - 100)])
        self.assertEqual(broken, 1)
        self.assertIn('frozen', out)
        self.assertIn('break@', out)
        self.assertIn('te_repair_history_order', out)

    def test_a_frozen_store_in_order_passes(self):
        broken, out = _run([_ordered(1, NOW), _ordered(50, NOW - 100)])
        self.assertEqual(broken, 0)
        self.assertNotIn('frozen', out)

    def test_one_month_behind_is_live(self):
        # The slack is exactly one month: a store that missed only the current
        # month is still being written to.
        broken, out = _run([_ordered(1, NOW), _rotated(50, NOW - 1)])
        self.assertEqual(broken, 1)
        self.assertNotIn('frozen since', out)

    def test_two_months_behind_is_frozen(self):
        broken, out = _run([_ordered(1, NOW), _rotated(50, NOW - 2)])
        self.assertEqual(broken, 1)
        self.assertIn('frozen since', out)

    def test_the_save_clock_comes_from_the_newest_store_not_each_store(self):
        # A lone out-of-order store defines its own newest month, so it is live.
        broken, out = _run([_rotated(1, NOW)])
        self.assertEqual(broken, 1)
        self.assertNotIn('frozen since', out)


YEAR = 1868


class DemographicsStoreTests(unittest.TestCase):
    """te_dg_hist, one sample a census year, read by the same patterns on its
    own clock (a year, not a month index)."""

    def test_its_lists_are_found_apart_from_the_monthly_ones(self):
        blob = csho.read_gamestate(_save([_ordered(1, NOW)], [_ordered(100, YEAR)]))
        self.assertEqual(len(csho.sample_lists(blob)), 1)
        self.assertEqual(len(csho.sample_lists(blob, 'te_dg_hist')), 1)
        _, ids = csho.sample_lists(blob, 'te_dg_hist')[0]
        self.assertEqual(ids, list(range(100, 110)))

    def test_an_ordered_store_passes_beside_the_monthly_ones(self):
        # its years are far below the monthly store's month indices: its own clock, so not frozen
        broken, out = _run([_ordered(1, NOW)], [_ordered(100, YEAR)])
        self.assertEqual(broken, 0)
        self.assertIn('te_dg_hist', out)
        self.assertNotIn('frozen', out)

    def test_one_out_of_order_fails(self):
        broken, out = _run([_ordered(1, NOW)], [_ordered(100, YEAR), _rotated(200, YEAR)])
        self.assertEqual(broken, 1)
        self.assertIn('te_dg_hist', out)
        self.assertIn('break@', out)
        self.assertIn(f'break@4: {YEAR} -> {YEAR - 9}', out, 'years, not months')

    def test_its_frozen_store_out_of_order_fails(self):
        broken, out = _run([_ordered(1, NOW)], [_ordered(100, YEAR), _rotated(200, YEAR - 20)])
        self.assertEqual(broken, 1)
        self.assertIn('frozen since', out)


class MonthFormattingTests(unittest.TestCase):
    def test_month_index_renders_as_year_dot_month(self):
        self.assertEqual(csho.fmt_month(1868 * 12 + 7), '1868.08')
        self.assertEqual(csho.fmt_month(1836 * 12), '1836.01')
        self.assertEqual(csho.fmt_month(1845 * 12 + 11), '1845.12')


if __name__ == '__main__':
    unittest.main()
