"""Tests for event_image_audit (issue #353)."""

import os
import tempfile
import unittest

import event_image_audit as eia


class EventImageAuditTests(unittest.TestCase):
    def _mod(self, events: dict[str, str]):
        """Build a temp mod tree from {relative path under events/: contents}.
        Returns the mod root."""
        td = tempfile.mkdtemp()
        for rel, content in events.items():
            p = os.path.join(td, "events", rel)
            os.makedirs(os.path.dirname(p), exist_ok=True)
            with open(p, "w", encoding="utf-8-sig") as f:
                f.write(content)
        return td

    def _ids(self, mod):
        return {f.event_id for f in eia.audit(mod).flags}

    def test_visible_event_without_image_is_flagged(self):
        mod = self._mod({"e.txt": "namespace = my\nmy.1 = {\n\ttype = country_event\n}\n"})
        self.assertEqual(self._ids(mod), {"my.1"})

    def test_event_with_texture_is_clean(self):
        mod = self._mod(
            {"e.txt": 'my.1 = {\n\tevent_image = { texture = "gfx/x.dds" }\n}\n'}
        )
        self.assertEqual(self._ids(mod), set())

    def test_event_with_video_is_clean(self):
        mod = self._mod({"e.txt": 'my.1 = {\n\tevent_image = { video = "x" }\n}\n'})
        self.assertEqual(self._ids(mod), set())

    def test_multi_block_conditional_image_is_clean(self):
        # The religion-gated ladder form: several event_image blocks, each with
        # its own trigger. Any one of them satisfies the rule.
        mod = self._mod(
            {
                "e.txt": "my.1 = {\n"
                "\tevent_image = {\n"
                "\t\ttrigger = { religion = rel:jewish }\n"
                '\t\tvideo = "a"\n'
                "\t}\n"
                "\tevent_image = {\n"
                '\t\tvideo = "b"\n'
                "\t}\n"
                "}\n"
            }
        )
        self.assertEqual(self._ids(mod), set())

    def test_hidden_event_is_exempt(self):
        mod = self._mod({"e.txt": "my.1 = {\n\thidden = yes\n}\n"})
        self.assertEqual(self._ids(mod), set())

    def test_alternate_gui_window_is_exempt(self):
        # Vanilla's pattern: a layout with no image panel plus a portrait.
        mod = self._mod(
            {
                "e.txt": "my.1 = {\n"
                "\tgui_window = event_window_1char_tabloid\n"
                "\tleft_icon = scope:romeo\n"
                "}\n"
            }
        )
        self.assertEqual(self._ids(mod), set())

    def test_left_icon_alone_is_exempt(self):
        mod = self._mod({"e.txt": "my.1 = {\n\tleft_icon = scope:x\n}\n"})
        self.assertEqual(self._ids(mod), set())

    def test_merge_directive_overrides_are_skipped(self):
        # A REPLACE:/INJECT: override inherits vanilla's art, which we can't see.
        mod = self._mod(
            {
                "e.txt": "REPLACE:vanilla.1 = {\n\ttype = country_event\n}\n"
                "INJECT:vanilla.2 = {\n\ttype = country_event\n}\n"
            }
        )
        self.assertEqual(self._ids(mod), set())

    def test_reviewed_comment_suppresses(self):
        mod = self._mod(
            {"e.txt": "my.1 = { # REVIEWED 2026-09-21: intentionally artless\n}\n"}
        )
        result = eia.audit(mod)
        self.assertEqual(len(result.flags), 1)
        ex = result.flags[0].exemption
        self.assertIsNotNone(ex)
        self.assertEqual(ex["date"], "2026-09-21")
        self.assertEqual(ex["rationale"], "intentionally artless")

    def test_nested_braces_do_not_leak_between_events(self):
        # my.1's option block must not make my.2's image count for my.1.
        mod = self._mod(
            {
                "e.txt": "my.1 = {\n\toption = { name = my.1.a }\n}\n"
                'my.2 = {\n\tevent_image = { video = "x" }\n}\n'
            }
        )
        self.assertEqual(self._ids(mod), {"my.1"})

    def test_coverage_counts(self):
        mod = self._mod(
            {
                "e.txt": "my.1 = {\n}\n"
                "my.2 = {\n\thidden = yes\n}\n"
                'my.3 = {\n\tevent_image = { video = "x" }\n}\n'
                "my.4 = {\n\tgui_window = w\n}\n"
            }
        )
        cov = eia.audit(mod).coverage
        self.assertEqual(cov["events_defined"], 4)
        self.assertEqual(cov["visible"], 3)
        self.assertEqual(cov["alt_art"], 1)
        self.assertEqual(cov["imageless"], 1)

    def test_missing_events_dir_is_empty_result(self):
        result = eia.audit(tempfile.mkdtemp())
        self.assertEqual(result.flags, [])

    def test_report_renders_both_sections(self):
        mod = self._mod(
            {
                "e.txt": "my.1 = {\n}\n"
                "my.2 = { # REVIEWED 2026-09-21: on purpose\n}\n"
            }
        )
        report = eia.render_report(eia.audit(mod), mod)
        self.assertIn("## Unreviewed", report)
        self.assertIn("`my.1`", report)
        self.assertIn("## REVIEWED-suppressed", report)
        self.assertIn("on purpose", report)

    def test_report_clean_state(self):
        mod = self._mod({"e.txt": 'my.1 = {\n\tevent_image = { video = "x" }\n}\n'})
        self.assertIn("No unreviewed imageless events", eia.render_report(eia.audit(mod), mod))

    def test_real_mod_tree_is_clean(self):
        """The shipped mod must have no unreviewed imageless events.

        Mirrors the CI `--strict` gate so a local `unittest` run catches a
        regression without needing the audit's CLI.
        """
        repo = os.path.dirname(os.path.abspath(__file__))
        if not os.path.isdir(os.path.join(repo, "events")):
            self.skipTest("no events/ directory beside the audit")
        unreviewed = [f for f in eia.audit(repo).flags if not f.exemption]
        self.assertEqual(
            unreviewed,
            [],
            "imageless events: " + ", ".join(f.event_id for f in unreviewed),
        )


if __name__ == "__main__":
    unittest.main()
