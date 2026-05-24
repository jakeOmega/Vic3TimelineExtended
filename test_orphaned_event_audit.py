"""Tests for orphaned_event_audit (issue #147)."""

import os
import tempfile
import unittest

import orphaned_event_audit as oea


class OrphanedEventAuditTests(unittest.TestCase):
    def _mod(self, events: dict[str, str], common: dict[str, str] | None = None):
        """Build a temp mod tree. `events`/`common` map relative file path ->
        contents. Returns the mod root."""
        td = tempfile.mkdtemp()
        for rel, content in events.items():
            p = os.path.join(td, "events", rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(content)
        for rel, content in (common or {}).items():
            p = os.path.join(td, "common", rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(content)
        return td

    def _ids(self, result):
        return {f.event_id for f in result.flags}

    def test_unreferenced_event_is_orphan(self):
        mod = self._mod({"e.txt": "namespace = my\nmy.1 = {\n\ttype = country_event\n}\n"})
        result = oea.audit(mod)
        self.assertIn("my.1", self._ids(result))

    def test_referenced_via_random_events_not_orphan(self):
        mod = self._mod(
            {"e.txt": "my.1 = {\n\ttype = country_event\n}\n"},
            {"on_actions/x.txt": "a = { random_events = {\n\t10 = my.1\n} }\n"},
        )
        self.assertNotIn("my.1", self._ids(oea.audit(mod)))

    def test_referenced_via_trigger_event_both_forms(self):
        mod = self._mod(
            {"e.txt": "my.1 = {\n}\nmy.2 = {\n}\n"},
            {
                "se/x.txt": "f = {\n\ttrigger_event = { id = my.1 }\n"
                "\ttrigger_event = my.2\n}\n"
            },
        )
        self.assertEqual(self._ids(oea.audit(mod)), set())

    def test_loc_keys_do_not_count_as_references(self):
        # The event references only its own loc keys (.t/.d/.a) — still orphan.
        mod = self._mod(
            {
                "e.txt": "my.1 = {\n\ttitle = my.1.t\n\tdesc = my.1.d\n"
                "\toption = { name = my.1.a }\n}\n"
            }
        )
        self.assertIn("my.1", self._ids(oea.audit(mod)))

    def test_self_firing_event_excluded(self):
        mod = self._mod(
            {"e.txt": "my.1 = {\n\tmean_time_to_happen = { months = 6 }\n}\n"}
        )
        result = oea.audit(mod)
        self.assertNotIn("my.1", self._ids(result))
        self.assertEqual(result.coverage["dispatch_required_candidates"], 0)

    def test_reviewed_suppression_partitions_flag(self):
        mod = self._mod(
            {"e.txt": "my.1 = {  # REVIEWED 2026-05-24: fired via dynamic id\n}\n"}
        )
        result = oea.audit(mod)
        flag = next(f for f in result.flags if f.event_id == "my.1")
        self.assertIsNotNone(flag.exemption)
        self.assertEqual(flag.exemption["date"], "2026-05-24")

    def test_replace_inject_definitions_excluded(self):
        # Overrides of vanilla events ride vanilla dispatch we can't see.
        mod = self._mod({"e.txt": "REPLACE:vanilla.1 = {\n}\nINJECT:vanilla.2 = {\n}\n"})
        self.assertEqual(self._ids(oea.audit(mod)), set())

    def test_higher_id_not_substring_matched(self):
        # my.1 referenced; my.10 is a distinct, unreferenced orphan.
        mod = self._mod(
            {"e.txt": "my.1 = {\n}\nmy.10 = {\n}\n"},
            {"on/x.txt": "a = { random_events = { 5 = my.1 } }\n"},
        )
        ids = self._ids(oea.audit(mod))
        self.assertIn("my.10", ids)
        self.assertNotIn("my.1", ids)


if __name__ == "__main__":
    unittest.main()
