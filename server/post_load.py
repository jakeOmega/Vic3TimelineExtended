"""The post-load chain: the rosters a reload runs (`POST_LOAD_REGENERATORS`,
then `POST_LOAD_AUDITS`), which of them need the vanilla files, and the
runner that calls each in turn, collects its warnings and re-parses the mod
when a generator rewrote it. Moved out of mod_state_server.py unchanged
(#1537); `_load_mod_state` there calls `_run_post_load_generators`.

`scripts/analysis/check_post_load_rosters.py`, `test_audit_registry.py` and the
audit tests read the two rosters out of this file with `ast`.

A server module holds code only (server/__init__.py says why): the state the
chain writes (`_post_load_warnings`, `_post_load_wrote_files`,
`_post_load_reparsed`) stays in mod_state_server and is read as `srv.<name>`
through `server_state()` at call time, and so are the two rosters wherever a
test patches them there. mod_state_server re-exports every name below.
"""
import hashlib
import importlib
import os
import time
import traceback
from typing import Optional

from server import server_state


# Idempotent transformers run after ModState loads on startup and /reload.
# Each module must expose `regenerate(mod_state)` and finish in well under a
# second. Set VIC3_SKIP_POST_LOAD_GENERATORS=1 to disable while iterating on
# one of these scripts. Failures are logged and skipped — they don't block
# server startup. The /reload?engine_only=true path bypasses _load_mod_state
# entirely, so these don't run there.
# File-rewriting generators. They regenerate mod content on disk from configs
# + vanilla data, so running them mid-audit dirties the working tree.
POST_LOAD_REGENERATORS = [
    ("pop_needs_curves",              "pop_needs_curves"),
    ("apply_ideologies",              "apply_ideologies"),
    ("ig_feminism",                   "ig_feminism"),
    ("pm_costs",                      "pm_costs"),
    ("resources",                     "resources"),
    ("gen_pb_principle_unlock_descs", "gen_pb_principle_unlock_descs"),
    ("gen_un_button_descs",           "gen_un_button_descs"),
    ("gen_carbon_capture_pms",        "gen_carbon_capture_pms"),
    ("gen_law_consistency",           "gen_law_consistency"),
    ("gen_company_building_cleanup",  "scripts.generators.gen_company_building_cleanup"),
    ("gen_covert_tech_theft",         "scripts.generators.gen_covert_tech_theft"),
    ("gen_seabed_basins",             "scripts.generators.gen_seabed_basins"),
    ("gen_launch_windows",            "scripts.generators.gen_launch_windows"),
    ("gen_solar_sites",               "scripts.generators.gen_solar_sites"),
    ("gen_space_fleets",              "scripts.generators.gen_space_fleets"),
    ("gen_culture_merges",            "scripts.generators.gen_culture_merges"),
    ("organize_loc",                  "organize_loc"),
    ("gen_event_inventory",           "gen_event_inventory"),
    # Keep LAST: prepend UTF-8 BOM to any mod .txt the generators above (or a
    # hand-authored file) left without one, so the engine stops warning. It's a
    # file-rewriting generator, so it lives here (not in POST_LOAD_AUDITS) and
    # is skipped on audits_only / mod_only fast reloads. (#148)
    ("bom_normalizer",                "bom_normalizer"),
]


# Read-only audits that surface findings without writing files. Safe to run
# repeatedly mid-audit (see POST /reload?audits_only=true).
POST_LOAD_AUDITS = [
    ("event_magnitude_audit",         "event_magnitude_audit"),
    ("modifier_visibility_audit",     "modifier_visibility_audit"),
    ("kill_character_audit",          "kill_character_audit"),
    ("loc_coverage_audit",            "loc_coverage_audit"),
    ("gui_reference_audit",           "gui_reference_audit"),
    ("concept_reference_audit",       "concept_reference_audit"),
    ("localization_accessor_audit",   "localization_accessor_audit"),
    ("mod_structure_audit",           "mod_structure_audit"),
    ("load_order_audit",              "load_order_audit"),
    ("loc_render_audit",              "loc_render_audit"),
    ("any_limit_audit",               "any_limit_audit"),
    ("iterator_limit_audit",          "iterator_limit_audit"),
    ("modifier_multiplier_var_audit", "modifier_multiplier_var_audit"),
    ("je_multiplier_scope_audit",    "je_multiplier_scope_audit"),
    ("pm_employment_audit",           "pm_employment_audit"),
    ("orphaned_event_audit",          "orphaned_event_audit"),
    ("effect_trigger_validity_audit", "effect_trigger_validity_audit"),
    ("duplicate_key_audit",           "duplicate_key_audit"),
    ("modifier_field_audit",          "modifier_field_audit"),
    ("attitude_key_audit",            "attitude_key_audit"),
    ("event_image_audit",             "event_image_audit"),
    ("treaty_leverage_side_audit",    "treaty_leverage_side_audit"),
    ("event_context_audit",           "event_context_audit"),
    ("trigger_event_cycle_audit",     "trigger_event_cycle_audit"),
    ("silent_variable_audit",         "silent_variable_audit"),
    ("prev_scope_audit",              "prev_scope_audit"),
    ("container_timed_variable_audit", "container_timed_variable_audit"),
    ("je_immediate_reset_audit",      "je_immediate_reset_audit"),
    ("script_loc_reference_audit",    "script_loc_reference_audit"),
    ("empty_effect_audit",            "empty_effect_audit"),
    ("change_variable_clamp_audit",   "change_variable_clamp_audit"),
    ("building_scope_variable_audit", "building_scope_variable_audit"),
    ("variable_guard_audit",          "variable_guard_audit"),
    ("principle_tier_audit",          "principle_tier_audit"),
    ("prestige_good_roster_audit",    "prestige_good_roster_audit"),
    ("amendment_reachability_audit",  "amendment_reachability_audit"),
    ("ideology_lawgroup_audit",       "ideology_lawgroup_audit"),
    ("roster_membership_audit",      "roster_membership_audit"),
    ("script_argument_audit",         "script_argument_audit"),
    ("modifier_duration_audit",       "modifier_duration_audit"),
    ("loc_script_value_audit",        "loc_script_value_audit"),
    ("loc_root_context_audit",        "loc_root_context_audit"),
    ("texture_reference_audit",       "texture_reference_audit"),
    ("long_tooltip_audit",            "long_tooltip_audit"),
    ("hidden_modifier_audit",         "hidden_modifier_audit"),
    ("button_reason_audit",           "button_reason_audit"),
    ("faith_scene_audit",             "faith_scene_audit"),
    ("sol_fraction_audit",            "sol_fraction_audit"),
    ("delayed_event_trigger_audit",   "delayed_event_trigger_audit"),
]


POST_LOAD_GENERATORS = POST_LOAD_REGENERATORS + POST_LOAD_AUDITS


# Regenerators that read vanilla game FILES under <base_game_path>/game rather
# than ModState's parsed vanilla, so vanilla_parsed/ cannot stand in for them.
# With no game files on disk (a cloud session running from vanilla_parsed/)
# they are skipped, and the reload says so: run blind, apply_ideologies would
# rewrite common/ideologies/modified.txt as a bare header and the rest would
# crash. gen_law_consistency and pm_costs are not here: they read only parsed
# vanilla (law and ideology structure, goods prices), taken from
# `mod_state.base_parsers`, so they run either way and reproduce their
# committed outputs from the snapshot byte for byte (#624).
VANILLA_FILE_REGENERATORS = frozenset({
    "pop_needs_curves",
    "apply_ideologies",
    "ig_feminism",
    "resources",
})


# Regenerators that run without vanilla files but also write outputs cut from
# raw vanilla text. Without usable files the chain calls
# `regenerate(mod_state, vanilla_files=False)`, which leaves those outputs as
# committed; the reload warning names them. {label: those outputs}.
PARTIAL_VANILLA_FILE_REGENERATORS = {
    "pm_costs": (
        "docs/engine/commented_vanilla_pms.txt",
        "docs/engine/commented_vanilla_military_units.txt",
    ),
}


# Return-dict keys whose nonzero values indicate "actionable issue surfaced
# by this generator." Audits use a small set of conventional names; if a new
# audit invents one, add it here so the warning fires automatically. A bool
# True counts (it is an int): texture_reference_audit's `catalog_stale` says
# the committed asset catalog no longer matches the install, so CI resolves
# against stale vanilla until `--bootstrap` reruns.
_POST_LOAD_WARN_KEYS = ("unreviewed", "hard_fails", "catalog_stale")


# How many trailing traceback lines a failure warning carries. Enough to name
# the raising frame without dumping the whole stack into every reload response.
_POST_LOAD_TRACEBACK_TAIL_LINES = 6


# Subtrees and suffixes the file-writing generators can touch. Snapshotted
# before/after the regenerator chain to detect writers that ran after the parse.
# map_data/ is deliberately out: `resources` rewrites state_regions there, but
# ModState registers no entity type for it, so a write can't stale the parse and
# re-parsing wouldn't pick it up. docs/engine/ is audit output, not mod content.
_WRITER_WATCH_DIRS = ("common", "events", "localization")


_WRITER_WATCH_SUFFIXES = (".txt", ".yml")


def _failure_warning(label: str, module_name: str, exc: BaseException) -> dict:
    """Shape a crashed post-load step as a reload warning entry."""
    tail = traceback.format_exc().rstrip().splitlines()[-_POST_LOAD_TRACEBACK_TAIL_LINES:]
    return {
        "label": label,
        "module": module_name,
        "error": f"{type(exc).__name__}: {exc}",
        "traceback_tail": "\n".join(tail),
    }


def _snapshot_mod_text_files(root: Optional[str] = None) -> dict:
    """Map mod-relative path -> content digest for every tracked text file the
    post-load regenerators could rewrite.

    Content-hashed rather than stat-compared on purpose: several generators
    (apply_ideologies, pop_needs_curves, …) rewrite their output file
    unconditionally, so mtime/size alone would report a write on every single
    reload and trigger a pointless re-parse. ~350 files / ~10 MB, so both
    snapshots together cost well under a second. Unreadable files are skipped.
    """
    srv = server_state()
    root = root or srv.mod_path
    snapshot: dict = {}
    for sub in _WRITER_WATCH_DIRS:
        base = os.path.join(root, sub)
        if not os.path.isdir(base):
            continue
        for dirpath, dirnames, filenames in os.walk(base):
            dirnames[:] = [d for d in dirnames if d != ".git"]
            for file_name in filenames:
                if not file_name.endswith(_WRITER_WATCH_SUFFIXES):
                    continue
                file_path = os.path.join(dirpath, file_name)
                try:
                    with open(file_path, "rb") as fh:
                        digest = hashlib.blake2b(fh.read(), digest_size=16).hexdigest()
                except OSError:
                    continue
                rel = os.path.relpath(file_path, root).replace(os.sep, "/")
                snapshot[rel] = digest
    return snapshot


def _changed_files(before: dict, after: dict) -> list:
    """Mod-relative paths whose content differs between two snapshots."""
    changed = {p for p, digest in after.items() if before.get(p) != digest}
    changed |= {p for p in before if p not in after}
    return sorted(changed)


def _reparse_mod_after_writes(mod_state) -> Optional[dict]:
    """Re-parse the mod side ONCE after the file-writing generators wrote, so
    the read-only audits in the same chain evaluate what was just generated
    (rather than the pre-generation parse) and /raw + /localize serve it without
    a second reload.

    Called at most once per _run_post_load_generators — it never re-runs the
    generators, so there is no loop. Returns a warning dict on failure, else
    None.
    """
    srv = server_state()
    t0 = time.monotonic()
    try:
        mod_state.reload_mod(srv.mod_paths)
        # Rebuild loc the same way _load_mod_state's mod_only path does:
        # cached vanilla snapshot, then the mod layers on top.
        if srv._VANILLA_LOC_CACHE is not None:
            mod_state.localization = dict(srv._VANILLA_LOC_CACHE)
            mod_state._reverse_loc = None
        for loc_dir in [
            os.path.join(srv.mod_path, "localization", "english"),
            os.path.join(srv.mod_path, "localization", "english", "replace"),
        ]:
            if os.path.isdir(loc_dir):
                mod_state.add_localization(loc_dir)
        srv._tech_unlocks_index_cache = None
        srv._company_catalog_cache = None
        srv._party_catalog_cache = None
        srv._state_history_cache = None
        srv._overlap_state_cache.clear()
        srv._invalidate_call_index()
        srv._last_validation_report = None
        srv._annotator_compute_cache.clear()
    except Exception as exc:  # noqa: BLE001
        srv.logger.exception("[post-load] re-parse after generator writes FAILED")
        return _failure_warning(
            "post_load_reparse", "mod_state_server._reparse_mod_after_writes", exc
        )
    srv.logger.info(
        f"[post-load] re-parsed mod state after generator writes "
        f"({time.monotonic() - t0:.1f}s)"
    )
    return None


def _run_generator_chain(mod_state, generators, *, vanilla_files=True) -> None:
    """Import and run each (label, module) in order, appending both actionable
    findings and hard failures to _post_load_warnings. One bad generator never
    stops the chain. With `vanilla_files=False` a PARTIAL_VANILLA_FILE_REGENERATORS
    member is told so (`regenerate(mod_state, vanilla_files=False)`)."""
    srv = server_state()
    for label, module_name in generators:
        t0 = time.monotonic()
        try:
            mod = importlib.import_module(module_name)
            regenerate = getattr(mod, "regenerate", None)
            if not callable(regenerate):
                raise AttributeError(
                    f"module {module_name!r} has no callable `regenerate` "
                    f"(POST_LOAD_GENERATORS contract)"
                )
            partial = not vanilla_files and label in PARTIAL_VANILLA_FILE_REGENERATORS
            summary = regenerate(mod_state, vanilla_files=False) if partial else regenerate(mod_state)
            elapsed = time.monotonic() - t0
            warn_counts = {}
            if isinstance(summary, dict):
                for key in _POST_LOAD_WARN_KEYS:
                    val = summary.get(key)
                    if isinstance(val, int) and val > 0:
                        warn_counts[key] = val
            if warn_counts:
                # Compose the warning line in a way that's easy to grep
                # ([post-load WARN] is the marker) and that names every
                # actionable counter, not just the first.
                detail = ", ".join(f"{k}={v}" for k, v in warn_counts.items())
                srv.logger.warning(
                    f"[post-load WARN] {label} surfaced issues: {detail} "
                    f"(see the audit's report under docs/engine/)"
                )
                srv._post_load_warnings.append({
                    "label": label,
                    "module": module_name,
                    "counts": warn_counts,
                    "summary": summary,
                })
            else:
                # Coverage counts (files audited, references checked, …) live
                # here rather than in the committed reports, where they would
                # re-diff on every PR that adds a file.
                counts = ""
                if isinstance(summary, dict):
                    counts = "".join(
                        f" {k}={v}" for k, v in summary.items()
                        if isinstance(v, int) and not isinstance(v, bool)
                    )
                srv.logger.info(f"[post-load] {label} ok ({elapsed:.2f}s){counts}")
        except Exception as exc:  # noqa: BLE001
            # An ImportError, a crash inside regenerate(), or a missing
            # `regenerate` used to be logged and forgotten, so POST /reload
            # still answered `{"status": "reloaded"}` with no warnings while a
            # whole audit had silently not run. Record it as a warning. (#242)
            srv.logger.exception(f"[post-load] {label} FAILED — continuing")
            srv._post_load_warnings.append(_failure_warning(label, module_name, exc))


def _run_post_load_generators(mod_state, *, audits_only=False, vanilla_files=True):
    """Run the post-load chain. `vanilla_files=False` (no usable vanilla game
    files; see _vanilla_files_unusable_reason) drops VANILLA_FILE_REGENERATORS,
    keeps PARTIAL_VANILLA_FILE_REGENERATORS off their raw-vanilla outputs, and
    records one `vanilla_files_missing` warning naming everything skipped —
    including generate_docs, which _load_mod_state skips for the same reason."""
    srv = server_state()
    srv._post_load_warnings = []
    srv._post_load_wrote_files = []
    srv._post_load_reparsed = False
    regenerators = srv.POST_LOAD_REGENERATORS
    if not vanilla_files:
        regenerators = [
            (label, module) for label, module in srv.POST_LOAD_REGENERATORS
            if label not in VANILLA_FILE_REGENERATORS
        ]
        skipped = ["generate_docs"] + (
            [] if audits_only else
            [label for label, _ in srv.POST_LOAD_REGENERATORS if label in VANILLA_FILE_REGENERATORS]
        )
        partial = {} if audits_only else {
            label: list(outputs)
            for label, outputs in PARTIAL_VANILLA_FILE_REGENERATORS.items()
        }
        detail = (
            f"{srv._vanilla_files_unusable_reason() or 'vanilla game files unusable'}, "
            f"so skipped {', '.join(skipped)}: they read those files "
            "directly, and vanilla_parsed/ holds only the parsed data. "
            "Their outputs on disk were left as they were, not regenerated."
        )
        if partial:
            detail += (
                " Also left as committed (cut from raw vanilla text; the rest of "
                "the generator ran from parsed vanilla): "
                + "; ".join(f"{label}: {', '.join(outs)}" for label, outs in partial.items())
                + "."
            )
        srv._post_load_warnings.append({
            "label": "vanilla_files_missing",
            "detail": detail,
            "skipped": skipped,
            "partially_skipped": partial,
        })
        srv.logger.warning(f"[post-load WARN] {srv._post_load_warnings[-1]['detail']}")
    if os.environ.get("VIC3_SKIP_POST_LOAD_GENERATORS"):
        srv.logger.info("[post-load] skipped via VIC3_SKIP_POST_LOAD_GENERATORS")
        return
    if audits_only:
        # No file-writing generators run, so nothing can invalidate the parse.
        srv._run_generator_chain(mod_state, srv.POST_LOAD_AUDITS)
    else:
        before = srv._snapshot_mod_text_files()
        srv._run_generator_chain(mod_state, regenerators, vanilla_files=vanilla_files)
        srv._post_load_wrote_files = _changed_files(before, srv._snapshot_mod_text_files())
        if srv._post_load_wrote_files:
            srv.logger.info(
                f"[post-load] regenerators rewrote {len(srv._post_load_wrote_files)} "
                f"file(s): {', '.join(srv._post_load_wrote_files[:5])}"
                + (" …" if len(srv._post_load_wrote_files) > 5 else "")
            )
            failure = _reparse_mod_after_writes(mod_state)
            if failure:
                srv._post_load_warnings.append(failure)
            else:
                srv._post_load_reparsed = True
        srv._run_generator_chain(mod_state, srv.POST_LOAD_AUDITS)
    if srv._post_load_warnings:
        labels = ", ".join(w["label"] for w in srv._post_load_warnings)
        failures = sum(1 for w in srv._post_load_warnings if "error" in w)
        srv.logger.warning(
            f"[post-load WARN] {len(srv._post_load_warnings)} post-load step(s) "
            f"surfaced actionable issues ({failures} crashed): {labels}"
        )
