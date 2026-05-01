"""Unit tests for the annotators registry and response post-processor.

Pure unit — no I/O, no server. Run:
    .venv/bin/python -m unittest test_annotators -v
"""
from __future__ import annotations

import unittest
from pathlib import Path

import annotators


def _fake_compute(returns: dict[str, dict]):
    calls = {"n": 0}

    def compute(repo_root: Path) -> dict[str, dict]:  # noqa: ARG001
        calls["n"] += 1
        return dict(returns)

    return compute, calls


class AnnotatorRegistryTests(unittest.TestCase):
    def setUp(self) -> None:
        # Snapshot any production registrations (e.g. pm_balance_lib's
        # `balance` annotator) so we can restore them after this class's
        # tests mutate the registry.
        self._registry_snapshot = annotators.snapshot_registry_for_test()
        annotators.clear_registry_for_test()
        self.repo_root = Path("/tmp/fake-repo")

    def tearDown(self) -> None:
        annotators.restore_registry_for_test(self._registry_snapshot)

    # ----- registry primitives ------------------------------------------------

    def test_register_and_lookup(self) -> None:
        compute, _ = _fake_compute({"pm_x": {"flag": "OK"}})
        ann = annotators.Annotator(
            name="balance",
            entity_type="ProductionMethods",
            fields=["flag"],
            description="test",
            compute=compute,
        )
        annotators.register(ann)
        self.assertIs(annotators.get("balance", "ProductionMethods"), ann)
        self.assertEqual(
            annotators.list_for("ProductionMethods"), [ann]
        )
        self.assertEqual(annotators.all_registered(), [ann])

    def test_register_last_wins(self) -> None:
        compute_a, _ = _fake_compute({})
        compute_b, _ = _fake_compute({})
        a = annotators.Annotator("balance", "ProductionMethods", ["x"], "first", compute_a)
        b = annotators.Annotator("balance", "ProductionMethods", ["y"], "second", compute_b)
        annotators.register(a)
        annotators.register(b)
        self.assertIs(annotators.get("balance", "ProductionMethods"), b)
        self.assertEqual(len(annotators.all_registered()), 1)

    def test_get_returns_none_when_missing(self) -> None:
        self.assertIsNone(annotators.get("balance", "ProductionMethods"))
        self.assertEqual(annotators.list_for("ProductionMethods"), [])

    # ----- tag() --------------------------------------------------------------

    def test_tag_sets_type_when_missing(self) -> None:
        entries = [{"id": "pm_a"}, {"id": "pm_b"}]
        annotators.tag(entries, "ProductionMethods")
        self.assertTrue(all(e["type"] == "ProductionMethods" for e in entries))

    def test_tag_idempotent(self) -> None:
        entries = [{"id": "x", "type": "Existing"}, {"id": "y"}]
        annotators.tag(entries, "ProductionMethods")
        self.assertEqual(entries[0]["type"], "Existing")
        self.assertEqual(entries[1]["type"], "ProductionMethods")

    def test_tag_skips_non_dicts(self) -> None:
        entries = [{"id": "x"}, "not-a-dict", 42]
        annotators.tag(entries, "ProductionMethods")
        self.assertEqual(entries[0]["type"], "ProductionMethods")
        # The non-dict entries are unchanged.
        self.assertEqual(entries[1], "not-a-dict")
        self.assertEqual(entries[2], 42)

    # ----- apply_to_response: detection -------------------------------------

    def test_apply_to_response_finds_typed_entries(self) -> None:
        compute, calls = _fake_compute({"pm_x": {"flag": "TEST"}})
        annotators.register(annotators.Annotator(
            "balance", "ProductionMethods", ["flag"], "t", compute,
        ))
        response = {
            "results": [
                {"type": "ProductionMethods", "id": "pm_x"},
                {"type": "Laws", "id": "law_y"},  # no annotator registered
                {"id": "no-type"},                # missing type
            ],
            "unrelated": {"foo": "bar"},
        }
        annotators.apply_to_response(response, "balance", Path("/x"))
        self.assertEqual(response["results"][0]["flag"], "TEST")
        self.assertNotIn("flag", response["results"][1])
        self.assertNotIn("flag", response["results"][2])
        self.assertEqual(calls["n"], 1)

    def test_apply_to_response_recurses_into_nested_buckets(self) -> None:
        compute, _ = _fake_compute({"pm_x": {"flag": "TEST"}})
        annotators.register(annotators.Annotator(
            "balance", "ProductionMethods", ["flag"], "t", compute,
        ))
        response = {
            "by_type": {
                "ProductionMethods": [
                    {"type": "ProductionMethods", "id": "pm_x"},
                ],
                "Buildings": [
                    {"type": "Buildings", "id": "b_x"},  # no annotator
                ],
            },
        }
        annotators.apply_to_response(response, "balance", Path("/x"))
        self.assertEqual(
            response["by_type"]["ProductionMethods"][0]["flag"], "TEST"
        )
        self.assertNotIn("flag", response["by_type"]["Buildings"][0])

    def test_apply_to_response_unknown_name_silently_skips(self) -> None:
        compute, calls = _fake_compute({"pm_x": {"flag": "TEST"}})
        annotators.register(annotators.Annotator(
            "balance", "ProductionMethods", ["flag"], "t", compute,
        ))
        response = [{"type": "ProductionMethods", "id": "pm_x"}]
        annotators.apply_to_response(response, "does-not-exist", Path("/x"))
        self.assertNotIn("flag", response[0])
        self.assertEqual(calls["n"], 0)

    def test_apply_to_response_all_runs_every_applicable(self) -> None:
        compute_balance, _ = _fake_compute({"pm_x": {"flag": "OK"}})
        compute_other, _ = _fake_compute({"pm_x": {"tier": "A"}})
        annotators.register(annotators.Annotator(
            "balance", "ProductionMethods", ["flag"], "b", compute_balance,
        ))
        annotators.register(annotators.Annotator(
            "tier", "ProductionMethods", ["tier"], "t", compute_other,
        ))
        # Plus one for a different type that should not fire on this response.
        compute_unused, calls_unused = _fake_compute({"law_y": {"era": "z"}})
        annotators.register(annotators.Annotator(
            "balance", "Laws", ["era"], "u", compute_unused,
        ))
        response = [{"type": "ProductionMethods", "id": "pm_x"}]
        annotators.apply_to_response(response, "all", Path("/x"))
        self.assertEqual(response[0]["flag"], "OK")
        self.assertEqual(response[0]["tier"], "A")
        self.assertEqual(calls_unused["n"], 0)

    def test_apply_to_response_caches_compute(self) -> None:
        compute, calls = _fake_compute({"pm_x": {"flag": "OK"}})
        annotators.register(annotators.Annotator(
            "balance", "ProductionMethods", ["flag"], "t", compute,
        ))
        cache: dict = {}
        response_a = [{"type": "ProductionMethods", "id": "pm_x"}]
        response_b = [{"type": "ProductionMethods", "id": "pm_x"}]
        annotators.apply_to_response(response_a, "balance", Path("/x"), cache=cache)
        annotators.apply_to_response(response_b, "balance", Path("/x"), cache=cache)
        self.assertEqual(calls["n"], 1)

    def test_apply_to_response_handles_non_string_type(self) -> None:
        # Defensive: a `type` that's not a string shouldn't crash or annotate.
        compute, calls = _fake_compute({"pm_x": {"flag": "X"}})
        annotators.register(annotators.Annotator(
            "balance", "ProductionMethods", ["flag"], "t", compute,
        ))
        response = [{"type": 42, "id": "pm_x"}]
        annotators.apply_to_response(response, "balance", Path("/x"))
        self.assertNotIn("flag", response[0])
        self.assertEqual(calls["n"], 0)

    def test_apply_to_response_no_op_when_no_match(self) -> None:
        # No annotators registered for the type at all.
        response = [{"type": "Laws", "id": "law_x"}]
        annotators.apply_to_response(response, "balance", Path("/x"))
        self.assertEqual(response, [{"type": "Laws", "id": "law_x"}])


if __name__ == "__main__":
    unittest.main()
