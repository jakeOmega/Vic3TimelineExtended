"""Tests for the nightly audit target selector's doc-affinity greedy selection.

Focuses on `select_targets()`: seed identity, clustering behavior, outlier
override, empty-docs handling, determinism, and budget enforcement. The
per-file base score (`score_candidate`) is patched in most tests to strip the
random jitter and pin scores to the audit state, so assertions are
deterministic.
"""

import random
import sys
import unittest
from datetime import date as Date
from pathlib import Path
from unittest.mock import patch

REPO_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import nightly_audit_select as nas
from nightly_audit_select import (
    FILE_CAP,
    INTENTIONALLY_NOT_EXCLUDED,
    LINE_BUDGET,
    NEW_DOC_PENALTY,
    RECENT_FINDINGS_CAP,
    area_and_docs,
    days_since,
    detect_registry_drift,
    select_targets,
)


def _state(entries):
    return {"version": 1, "files": entries}


def _candidates(specs):
    """specs: list of (rel_path, line_count). Returns the (abs, rel, n) tuples
    select_targets expects."""
    return [(Path("/nonexistent") / rel, rel, n) for rel, n in specs]


def _no_jitter_score(rel, state, today, rng):
    """score_candidate stand-in that strips the rng jitter so base scores are
    pinned to (days_since_last_audited + findings_boost)."""
    fs = state.get("files", {}).get(rel, {})
    days = days_since(fs.get("last_audited"), today)
    findings = fs.get("recent_findings", 0) or 0
    return float(days) + min(findings, RECENT_FINDINGS_CAP) * 0.5


# --------------------------------------------------------------------------- #
# Sanity: doc mappings the tests rely on
# --------------------------------------------------------------------------- #

class DocMappingSanityTest(unittest.TestCase):
    """The clustering tests assume specific path → docs mappings. If
    `_DOC_MAPPING_RAW` changes, these assertions fail loudly so the tests can
    be updated alongside the mapping rather than silently misbehaving."""

    def test_social_tensions_event_docs(self):
        _, docs = area_and_docs("events/social_tensions_events.txt")
        self.assertIn("docs/guides/event_creation_guide.md", docs)
        self.assertIn("docs/vanilla/vanilla_politics_reference.md", docs)

    def test_movement_event_shares_docs_with_social_tensions(self):
        _, docs_a = area_and_docs("events/social_tensions_events.txt")
        _, docs_b = area_and_docs("events/movement_events.txt")
        self.assertEqual(set(docs_a), set(docs_b))

    def test_technology_introduces_new_doc(self):
        _, docs_event = area_and_docs("events/social_tensions_events.txt")
        _, docs_tech = area_and_docs("common/technology/foo.txt")
        self.assertTrue(set(docs_tech) - set(docs_event))

    def test_gfx_asset_has_empty_docs(self):
        _, docs = area_and_docs("gfx/portraits/extra.asset")
        self.assertEqual(docs, [])


# --------------------------------------------------------------------------- #
# Selection behavior
# --------------------------------------------------------------------------- #

class SelectTargetsTest(unittest.TestCase):
    def setUp(self):
        self.today = Date(2026, 5, 16)
        # Strip jitter so base scores are reproducible per (rel, state).
        patcher = patch.object(nas, "score_candidate", side_effect=_no_jitter_score)
        patcher.start()
        self.addCleanup(patcher.stop)

    # ----- seed -------------------------------------------------------------

    def test_seed_is_highest_base_score(self):
        """The first pick must be the highest base-score candidate — the
        penalty doesn't apply on the seed, so a many-doc stale file beats a
        zero-doc fresh file."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 100),
            ("common/laws/00_laws.txt", 100),
        ])
        state = _state({
            "events/social_tensions_events.txt": {"last_audited": "2025-01-01"},
            "common/laws/00_laws.txt": {"last_audited": "2026-05-15"},
        })
        targets = select_targets(cands, state, self.today, random.Random(0))
        self.assertEqual(targets[0]["path"], "events/social_tensions_events.txt")

    # ----- clustering -------------------------------------------------------

    def test_post_seed_prefers_shared_docs(self):
        """After the seed picks an events file, another events file (zero new
        docs) beats an equally-stale technology file (one new doc)."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 100),
            ("events/movement_events.txt", 100),
            ("common/technology/foo.txt", 100),
        ])
        state = _state({
            # Seed clearly stalest.
            "events/social_tensions_events.txt": {"last_audited": "2026-05-10"},  # 6d
            # Same staleness as tech — clustering decides the tiebreak.
            "events/movement_events.txt": {"last_audited": "2026-05-14"},          # 2d
            "common/technology/foo.txt": {"last_audited": "2026-05-14"},           # 2d
        })
        targets = select_targets(cands, state, self.today, random.Random(0))
        order = [t["path"] for t in targets]
        self.assertEqual(order[0], "events/social_tensions_events.txt")
        self.assertEqual(order[1], "events/movement_events.txt")
        self.assertEqual(order[2], "common/technology/foo.txt")

    # ----- outlier override -------------------------------------------------

    def test_stale_outlier_breaks_cluster_when_gap_exceeds_penalty(self):
        """A different-area file should still be picked over a cluster member
        when its staleness gap exceeds NEW_DOC_PENALTY * new_doc_count."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 100),  # seed: 30d
            ("events/movement_events.txt", 100),          # 2d, 0 new docs → eff 2
            ("common/technology/foo.txt", 100),           # 10d, 1 new doc → eff 5
        ])
        state = _state({
            "events/social_tensions_events.txt": {"last_audited": "2026-04-16"},  # 30d
            "events/movement_events.txt": {"last_audited": "2026-05-14"},          # 2d
            "common/technology/foo.txt": {"last_audited": "2026-05-06"},           # 10d
        })
        # Sanity: penalty=5, so tech eff = 10 - 5*1 = 5 > movement eff = 2.
        self.assertGreater(10 - NEW_DOC_PENALTY * 1, 2)

        targets = select_targets(cands, state, self.today, random.Random(0))
        order = [t["path"] for t in targets]
        self.assertEqual(order[0], "events/social_tensions_events.txt")
        self.assertEqual(order[1], "common/technology/foo.txt")
        self.assertEqual(order[2], "events/movement_events.txt")

    def test_cluster_holds_when_outlier_gap_is_small(self):
        """Symmetric to the override test: a small staleness gap (< penalty)
        does NOT let the outlier break the cluster."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 100),  # seed: 30d
            ("events/movement_events.txt", 100),          # 3d, 0 new docs → eff 3
            ("common/technology/foo.txt", 100),           # 6d, 1 new doc → eff 1
        ])
        state = _state({
            "events/social_tensions_events.txt": {"last_audited": "2026-04-16"},
            "events/movement_events.txt": {"last_audited": "2026-05-13"},
            "common/technology/foo.txt": {"last_audited": "2026-05-10"},
        })
        targets = select_targets(cands, state, self.today, random.Random(0))
        self.assertEqual(targets[1]["path"], "events/movement_events.txt")

    # ----- empty docs -------------------------------------------------------

    def test_empty_docs_file_incurs_no_penalty(self):
        """A file with empty docs (gfx scaffolding, generic common/ fallback)
        should compete on base score alone — the marginal-doc penalty is
        5 * 0 = 0."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 100),  # seed: 5d
            ("gfx/portraits/extra.asset", 100),           # 4d, 0 docs → eff 4
            ("common/technology/foo.txt", 100),           # 4d, 1 new doc → eff -1
        ])
        state = _state({
            "events/social_tensions_events.txt": {"last_audited": "2026-05-11"},
            "gfx/portraits/extra.asset": {"last_audited": "2026-05-12"},
            "common/technology/foo.txt": {"last_audited": "2026-05-12"},
        })
        targets = select_targets(cands, state, self.today, random.Random(0))
        order = [t["path"] for t in targets]
        self.assertEqual(order[1], "gfx/portraits/extra.asset")

    # ----- determinism ------------------------------------------------------

    def test_same_inputs_produce_same_selection(self):
        """select_targets must be deterministic given identical inputs (the
        random.Random instance is its only randomness source)."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 100),
            ("events/movement_events.txt", 100),
            ("common/technology/foo.txt", 100),
            ("common/laws/00_laws.txt", 100),
            ("gfx/portraits/extra.asset", 100),
        ])
        state = _state({})  # all files cold-start
        a = select_targets(cands, state, self.today, random.Random(42))
        b = select_targets(cands, state, self.today, random.Random(42))
        self.assertEqual(
            [t["path"] for t in a],
            [t["path"] for t in b],
        )

    # ----- budget / cap -----------------------------------------------------

    def test_line_budget_respected(self):
        """Total selected lines must not exceed LINE_BUDGET (except when the
        seed alone exceeds it — the huge-file fallback)."""
        # 10 files at 400 lines each = 4000, well over the 2500 budget.
        cands = _candidates([
            (f"events/social_tensions_events.txt", 400),
            (f"events/movement_events.txt", 400),
            (f"events/economic_events.txt", 400),
            (f"events/un_overview_events.txt", 400),
            (f"events/space_events.txt", 400),
            (f"events/nuclear_events.txt", 400),
            (f"events/decolonization_events.txt", 400),
            (f"events/repeatable_events.txt", 400),
            (f"common/laws/00_laws.txt", 400),
            (f"common/technology/foo.txt", 400),
        ])
        state = _state({})
        targets = select_targets(cands, state, self.today, random.Random(0))
        total = sum(t["lines"] for t in targets)
        # First pick is allowed to exceed alone (huge-file fallback); here no
        # single file does. All picks must fit collectively.
        self.assertLessEqual(total, LINE_BUDGET)

    def test_file_cap_respected(self):
        """No more than FILE_CAP targets, regardless of remaining budget."""
        # 20 small files — line budget would allow all of them.
        cands = _candidates([
            (f"events/social_tensions_events.txt", 50),
        ] + [(f"events/movement_events_{i}.txt", 50) for i in range(25)])
        state = _state({})
        targets = select_targets(cands, state, self.today, random.Random(0))
        self.assertLessEqual(len(targets), FILE_CAP)

    def test_huge_seed_taken_even_if_over_budget(self):
        """If the highest-scoring candidate alone exceeds LINE_BUDGET, the
        seed pick is still taken (sliced) — never returning zero targets."""
        cands = _candidates([
            ("events/social_tensions_events.txt", 10_000),  # >> budget, will slice
        ])
        state = _state({})
        targets = select_targets(cands, state, self.today, random.Random(0))
        self.assertEqual(len(targets), 1)
        self.assertIsNotNone(targets[0]["line_range"])


# --------------------------------------------------------------------------- #
# Registry drift
# --------------------------------------------------------------------------- #

class RegistryDriftTest(unittest.TestCase):
    """Integration tests against the real `docs/auto_generated_files.md` and the
    in-script `EXCLUDED_GLOBS` / `INTENTIONALLY_NOT_EXCLUDED` lists. These flag
    drift the moment a hand-authored input directory enters the registry
    without a matching classification entry — the noise issue #75 surfaced."""

    def test_company_types_classified_as_intentional_input(self):
        """Registry lists `common/company_types/*.txt` as input to
        gen_company_building_cleanup.py. It must remain audit-eligible (it's
        hand-authored data, not generator output), so it belongs in
        INTENTIONALLY_NOT_EXCLUDED — not EXCLUDED_GLOBS."""
        self.assertIn("common/company_types/*.txt", INTENTIONALLY_NOT_EXCLUDED)

    def test_no_unclassified_registry_drift(self):
        """`detect_registry_drift()` must return an empty `drift_added` list:
        every registry-listed audit-relevant path is either in EXCLUDED_GLOBS
        (wholly generator-managed, skip) or INTENTIONALLY_NOT_EXCLUDED (partial
        or input-only, keep auditing). A non-empty list means a new generator
        landed without classification — fix by adding the path to whichever
        list applies."""
        drift_added, _ = detect_registry_drift()
        self.assertEqual(
            drift_added,
            [],
            msg=(
                f"Unclassified entries in docs/auto_generated_files.md: {drift_added}. "
                "Add each to EXCLUDED_GLOBS (if generator-output) or INTENTIONALLY_NOT_EXCLUDED "
                "(if generator-input/partially-managed) in scripts/nightly_audit_select.py."
            ),
        )


if __name__ == "__main__":
    unittest.main()
