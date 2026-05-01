"""Annotator registry: a tiny mechanism for enriching entity entries with
audit-derived metadata (PM balance flags, future combat-unit power tiers,
building cost tiers, etc.).

An annotator is a `(name, entity_type) -> compute(repo_root) -> {entity_id: fields}`
record. It's registered at import time by whichever module owns the metric
(e.g. `pm_balance_lib` registers `("balance", "ProductionMethods")`).

Consumers — primarily the mod state server's `route()` post-processor and
the tech balance audit script — call `apply_to_response(...)` to walk a
response tree and merge annotator-produced fields into any entity entry
shaped like `{"type": <etype>, "id": <eid>, ...}`. Entries that don't
carry both keys are skipped.

The registry is intentionally not a plugin system — it's a Python dict and
a couple of helpers. Keep it that way.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Iterable


@dataclass
class Annotator:
    name: str               # short identifier used in ?annotate=<name>
    entity_type: str        # mod_parsers key, e.g. "ProductionMethods"
    fields: list[str]       # field names this annotator adds to entries
    description: str        # one-line, surfaced via GET /annotators
    compute: Callable[[Path], dict[str, dict]] = field(repr=False)
        # repo_root -> {entity_id: {field_name: value, ...}}


# Module-level registry. Keyed by (entity_type, name) so multiple annotators
# can target the same entity type with different metric flavors.
_REGISTRY: dict[tuple[str, str], Annotator] = {}


def register(annotator: Annotator) -> None:
    """Add (or replace) an annotator in the registry. Last-wins on duplicate
    `(entity_type, name)` keys — the contract assumes a single owning module
    per metric."""
    _REGISTRY[(annotator.entity_type, annotator.name)] = annotator


def get(name: str, entity_type: str) -> Annotator | None:
    return _REGISTRY.get((entity_type, name))


def list_for(entity_type: str) -> list[Annotator]:
    """All annotators registered for a given entity type."""
    return [a for (et, _), a in _REGISTRY.items() if et == entity_type]


def all_registered() -> list[Annotator]:
    return list(_REGISTRY.values())


def snapshot_registry_for_test() -> dict[tuple[str, str], Annotator]:
    """Test-only: capture the current registry contents. Pair with
    `restore_registry_for_test()` in tearDown to make sure tests that mutate
    the registry don't leak across modules."""
    return dict(_REGISTRY)


def restore_registry_for_test(snapshot: dict[tuple[str, str], Annotator]) -> None:
    """Test-only: replace registry contents with `snapshot`."""
    _REGISTRY.clear()
    _REGISTRY.update(snapshot)


def clear_registry_for_test() -> None:
    """Test-only: drop every registration. Pair with restore_* to put it back.

    Prefer the snapshot/restore helpers — calling this without restoring
    will break tests in other modules that depend on production
    registrations (e.g. `pm_balance_lib.balance`).
    """
    _REGISTRY.clear()


def tag(entries: Iterable[dict], entity_type: str) -> Iterable[dict]:
    """Set `type=entity_type` on each entry that doesn't already declare one.

    Idempotent. Returns the original iterable for chaining. Mutates entries
    in place when they're dicts (the typical case)."""
    for e in entries:
        if isinstance(e, dict):
            e.setdefault("type", entity_type)
    return entries


# ---------------------------------------------------------------------------
# Response post-processor
# ---------------------------------------------------------------------------

def _resolve_requested(requested: str | Iterable[str]) -> list[str] | None:
    """Normalize the ?annotate= param into a list of names, or None for 'all'."""
    if isinstance(requested, str):
        if requested.strip() == "all":
            return None
        names = [s.strip() for s in requested.split(",") if s.strip()]
    else:
        names = [s.strip() for s in requested if s and s.strip()]
    if any(n == "all" for n in names):
        return None
    return names


def _annotators_for(entity_type: str, requested: list[str] | None) -> list[Annotator]:
    """Pick the annotators to apply for a given entity type."""
    if requested is None:
        return list_for(entity_type)
    out = []
    for name in requested:
        a = get(name, entity_type)
        if a is not None:
            out.append(a)
    return out


def annotate_entries(
    entity_type: str,
    entries: Iterable[dict],
    requested: str | Iterable[str],
    repo_root: Path,
    cache: dict[tuple[str, str], dict] | None = None,
) -> None:
    """Mutate `entries` in place, adding fields from each requested annotator
    that's registered for `entity_type`.

    `requested` is the ?annotate= param value: comma-list of names, an
    iterable of names, or the literal `"all"` to expand to every registered
    annotator for the given type. Unknown names are silently skipped — the
    "future-proof" path is `?annotate=all`, which picks up newcomers
    automatically.

    `cache` (optional) is a caller-owned dict keyed by `(annotator.name,
    entity_type)` that stores `compute()` results so a single request only
    runs each compute once.
    """
    names = _resolve_requested(requested)
    annotators = _annotators_for(entity_type, names)
    if not annotators:
        return

    if cache is None:
        cache = {}

    for ann in annotators:
        key = (ann.name, ann.entity_type)
        if key not in cache:
            cache[key] = ann.compute(repo_root)
        per_id = cache[key]
        for e in entries:
            if not isinstance(e, dict):
                continue
            eid = e.get("id")
            if eid is None:
                continue
            extra = per_id.get(eid)
            if extra:
                e.update(extra)


def apply_to_response(
    response: Any,
    requested: str | Iterable[str],
    repo_root: Path,
    cache: dict[tuple[str, str], dict] | None = None,
) -> Any:
    """Recursively walk a response tree and annotate any entry shaped like
    `{type: ..., id: ..., ...}` according to `requested`.

    Returns `response` (mutated in place). Lists, dicts, and nested
    combinations are all walked. Non-container values are no-ops.
    """
    if cache is None:
        cache = {}

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            etype = node.get("type")
            eid = node.get("id")
            if isinstance(etype, str) and eid is not None:
                annotate_entries(etype, [node], requested, repo_root, cache)
            for v in node.values():
                _walk(v)
        elif isinstance(node, list):
            for v in node:
                _walk(v)

    _walk(response)
    return response
