"""The engine-docs routes: GET /engine-docs and its sub-routes (origin,
usage, loc-functions, <type>, <type>/<name>), and GET /dev-docs, vanilla's
developer reference docs. Moved out of mod_state_server.py unchanged (#1537,
stage 1; /dev-docs in stage 2).

The code moved; the state did not. Everything module-level that these
functions read or rebind (`engine_docs`, `engine_docs_source_label`,
`pattern_index`, `dev_reference_docs`, `base_game_path`, `_BASE_COMMON`, the
`_LOC_FUNCTION_INDEX` and `_USAGE_TARGET_RE_CACHE` caches, the `_LOC_EXPR_RE`
the GUI index shares)
stays defined in mod_state_server and is read through `server_state()` at
call time, never imported into this module, so a reload's rebinding and a
test's `mock.patch.object(mod_state_server, ...)` reach it as before. The
error classes come from there too, so do_GET's `except` clauses match them
however the server file was run (see server/__init__.py).
mod_state_server re-exports every name below.
"""
import difflib
import os
import re
import shutil
import subprocess

from server import server_state

_LOC_IDENT_RE = re.compile(r"[a-zA-Z_][a-zA-Z0-9_]*")
# Identifier "kind" classification:
# - "scope":    all-uppercase keyword (ROOT, SCOPE, THIS, PREV, ...).
# - "method":   appears only after a `.` in vanilla (e.g. GetName, GetDesc).
# - "function": appears at expression start (e.g. GetStaticModifier, Concept).
# - "accessor": lowercase-then-CamelCase (sCharacter, sState — "string getters").


def _is_function_like_ident(ident: str) -> bool:
    """Filter tokens to function-like identifiers — those carrying at least one
    uppercase letter. Excludes lowercase-only keys like `concept_homeland`."""
    return bool(ident) and any(c.isupper() for c in ident)


def _build_loc_function_index() -> dict:
    """Scan vanilla loc + GUI files for `[...]` expressions, tokenize the
    function-like identifiers, and return an index of name -> usage stats.

    Cached after first build (call `_get_loc_function_index` from endpoints).
    Single-pass over ~16 MB of text; ~2-4s on WSL+NTFS.
    """
    srv = server_state()
    index: dict[str, dict] = {}
    max_examples_per_token = 8

    scan_roots = [
        os.path.join(srv.base_game_path, "game", "localization", "english"),
        os.path.join(srv.base_game_path, "game", "gui"),
    ]
    exts = {".yml", ".gui"}

    for root in scan_roots:
        if not os.path.isdir(root):
            continue
        for dirpath, _dirs, files in os.walk(root):
            for fname in files:
                ext = os.path.splitext(fname)[1].lower()
                if ext not in exts:
                    continue
                path = os.path.join(dirpath, fname)
                rel = os.path.relpath(path, srv.base_game_path).replace(os.sep, "/")
                try:
                    with open(path, "r", encoding="utf-8", errors="replace") as f:
                        for line_no, line in enumerate(f, start=1):
                            if "[" not in line:
                                continue
                            for m in srv._LOC_EXPR_RE.finditer(line):
                                expr = m.group(0)  # full `[...]`
                                body = m.group(1)
                                # Tokenize identifiers; classify position.
                                # We track first-seen kind heuristically:
                                # method if previous char is `.`, else opener.
                                for tm in _LOC_IDENT_RE.finditer(body):
                                    ident = tm.group(0)
                                    if not _is_function_like_ident(ident):
                                        continue
                                    prev_char = body[tm.start() - 1] if tm.start() > 0 else ""
                                    is_method = prev_char == "."
                                    entry = index.get(ident)
                                    if entry is None:
                                        if ident.isupper() and len(ident) >= 2:
                                            kind = "scope"
                                        elif ident[0].islower():
                                            kind = "accessor"
                                        elif is_method:
                                            kind = "method"
                                        else:
                                            kind = "function"
                                        entry = {
                                            "count": 0,
                                            "kind": kind,
                                            "examples": [],
                                            "first_seen": f"{rel}:{line_no}",
                                        }
                                        index[ident] = entry
                                    entry["count"] += 1
                                    if len(entry["examples"]) < max_examples_per_token:
                                        # Avoid duplicate expressions among examples.
                                        if not any(
                                            e["expression"] == expr for e in entry["examples"]
                                        ):
                                            entry["examples"].append({
                                                "file": rel,
                                                "line": line_no,
                                                "expression": expr,
                                            })
                except OSError:
                    continue
    return index


def _get_loc_function_index() -> dict:
    """Return the cached loc-function index, building it on first access."""
    srv = server_state()
    if srv._LOC_FUNCTION_INDEX is None:
        srv._LOC_FUNCTION_INDEX = _build_loc_function_index()
    return srv._LOC_FUNCTION_INDEX


def _engine_docs_find_usage(
    target: str,
    *,
    limit: int = 5,
    include_defs: bool = False,
    context_before: int = 1,
    context_after: int = 3,
) -> dict:
    """Scan vanilla `common/` for real-world call sites of `target` (a trigger,
    effect, or modifier name). Returns context-bracketed snippets with file:line.

    Default filter excludes column-0 `target = {` (definition) and matches inside
    `common/trigger_localization/` (engine-side display-label cross-references,
    not script calls). Set `include_defs=true` to disable filtering.

    Backend: ripgrep when available (fast, ~1-2s across vanilla); Python
    `os.walk` otherwise. Either way the result is capped at `limit`.
    """
    srv = server_state()
    if not target or not re.match(r"^[a-z][a-z0-9_]*$", target):
        return {
            "name": target,
            "error": "Invalid target name (expected snake_case identifier).",
            "uses": [],
        }

    if not os.path.isdir(srv._BASE_COMMON):
        return {
            "name": target,
            "error": f"Vanilla common dir not found: {srv._BASE_COMMON}",
            "uses": [],
        }

    # Cache the per-target regex used to filter "call-site" lines from "match
    # within a longer identifier". A call site has the identifier as a whole
    # word followed by whitespace and an operator (= < > <= >= !=) or `{`.
    pat = srv._USAGE_TARGET_RE_CACHE.get(target)
    if pat is None:
        pat = re.compile(
            r"(^|[^A-Za-z0-9_])" + re.escape(target) + r"\s*(=|<|>|!=|<=|>=|\{)"
        )
        srv._USAGE_TARGET_RE_CACHE[target] = pat

    # Prefer system grep (always available, ~5-10x faster than Python walk on
    # WSL+NTFS). Fall back to ripgrep, then Python walk.
    raw_matches: list[tuple[str, int, str]] = []  # (relpath, line_no, line)
    grep_path = shutil.which("grep")
    rg_path = shutil.which("rg")
    backend = "python"
    try:
        if grep_path or rg_path:
            if grep_path:
                cmd = [
                    grep_path, "-rn", "-w",
                    "--include=*.txt",
                    "--exclude-dir=trigger_localization",
                    target, srv._BASE_COMMON,
                ]
                backend = "grep"
            else:
                cmd = [
                    rg_path, "-n", "-w", "-t", "txt",
                    "--max-count", "30",
                    "--no-heading", "--no-messages",
                    target, srv._BASE_COMMON,
                ]
                backend = "ripgrep"
            proc = subprocess.run(cmd, capture_output=True, text=True, timeout=20)
            for raw in proc.stdout.splitlines():
                # Format: "<absolute_path>:<line_no>:<line>"
                head, _, rest = raw.partition(":")
                line_no_str, _, line = rest.partition(":")
                try:
                    line_no = int(line_no_str)
                except ValueError:
                    continue
                rel = os.path.relpath(head, srv._BASE_COMMON)
                raw_matches.append((rel, line_no, line))
        else:
            for root, _dirs, files in os.walk(srv._BASE_COMMON):
                for fname in files:
                    if not fname.endswith(".txt"):
                        continue
                    path = os.path.join(root, fname)
                    try:
                        with open(path, "r", encoding="utf-8", errors="replace") as f:
                            for i, line in enumerate(f, start=1):
                                if target in line:
                                    rel = os.path.relpath(path, srv._BASE_COMMON)
                                    raw_matches.append((rel, i, line.rstrip("\n")))
                    except OSError:
                        continue
    except subprocess.TimeoutExpired:
        return {
            "name": target,
            "error": "Timed out scanning vanilla common/. Try a more specific name.",
            "uses": [],
        }
    except Exception as e:
        return {
            "name": target,
            "error": f"Scan failed: {e}",
            "uses": [],
        }

    # Filter to call sites (not definitions or label cross-references).
    filtered: list[tuple[str, int, str]] = []
    for rel, line_no, line in raw_matches:
        if not include_defs:
            if rel.startswith("trigger_localization" + os.sep):
                # Engine-side trigger-localization cross-references — not calls.
                continue
            if line.lstrip() != line and (line.lstrip().startswith(target + " ")
                                          or line.lstrip().startswith(target + "=")):
                # Indented call site — good.
                pass
            elif line.startswith(target):
                # Column-0 line starting with the name is almost always a definition.
                # Filter unless include_defs is set.
                continue
        if not pat.search(line):
            continue
        filtered.append((rel, line_no, line))
        if len(filtered) >= limit * 4:  # surface a few extras pre-dedupe-by-file
            break

    # Diversify across files: prefer first hit per file before repeating one file.
    by_file: dict[str, list[tuple[int, str]]] = {}
    for rel, line_no, line in filtered:
        by_file.setdefault(rel, []).append((line_no, line))
    diversified: list[tuple[str, int, str]] = []
    while len(diversified) < limit and any(by_file.values()):
        for rel in list(by_file.keys()):
            if not by_file[rel]:
                continue
            line_no, line = by_file[rel].pop(0)
            diversified.append((rel, line_no, line))
            if len(diversified) >= limit:
                break

    # Read context around each chosen match.
    uses = []
    for rel, line_no, line in diversified:
        abs_path = os.path.join(srv._BASE_COMMON, rel)
        snippet_lines: list[str] = []
        try:
            with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
                all_lines = f.readlines()
            start = max(1, line_no - context_before)
            end = min(len(all_lines), line_no + context_after)
            for i in range(start, end + 1):
                marker = ">" if i == line_no else " "
                snippet_lines.append(f"{marker} {i:5}: {all_lines[i - 1].rstrip()}")
        except OSError:
            snippet_lines = [f"  {line_no}: {line.rstrip()}"]
        uses.append({
            "file": rel,
            "line": line_no,
            "snippet": "\n".join(snippet_lines),
        })

    return {
        "name": target,
        "total_call_sites_scanned": len(filtered),
        "returned": len(uses),
        "backend": backend,
        "uses": uses,
    }


def _group_similar_entries(entries: list[dict]) -> tuple[list[dict], list[dict]]:
    """Group modifier entries by pattern_index (§3).

    Falls back to returning everything as ungrouped if the pattern engine
    hasn't been initialized (e.g. server is starting up).
    """
    srv = server_state()
    if not srv.pattern_index:
        return [], list(entries)

    grouped_names: set[str] = set()
    grouped_entries: list[dict] = []
    name_to_entry = {e.get("name", ""): e for e in entries}

    for pattern, members in srv.pattern_index.items():
        member_names = sorted(members.keys())
        if not member_names:
            continue
        # Use the first concrete entry as the example for description/scope/mask
        first_value = member_names[0]
        first_name = pattern.replace(srv._pattern_token(pattern), first_value)
        example = name_to_entry.get(first_name) or next(iter(members.values()))
        full_member_names = []
        for v in member_names:
            full_name = pattern.replace(srv._pattern_token(pattern), v)
            grouped_names.add(full_name)
            full_member_names.append(full_name)
        grouped_entries.append({
            "pattern": pattern,
            "count": len(member_names),
            "members": full_member_names,
            "description": example.get("description", "") if isinstance(example, dict) else "",
            "scopes": example.get("scopes", []) if isinstance(example, dict) else [],
            "mask": example.get("mask", "") if isinstance(example, dict) else "",
        })

    ungrouped = [e for e in entries if e.get("name") not in grouped_names]
    return grouped_entries, ungrouped



class EngineDocsRoutes:
    """ModStateHandler's /engine-docs handler (a mixin: the dispatcher calls
    `self._engine_docs`, and tests call `ModStateHandler._engine_docs`)."""

    def _engine_docs(self, parts, params):
        """GET /engine-docs                      - list available doc types
        GET /engine-docs/<type>               - list entries of a type, capped
                                                at ?limit=N (default 500);
                                                `count` is the filtered total,
                                                `returned` / `truncated` say
                                                whether `entries` holds all of it
        GET /engine-docs/<type>/<name>        - the entry named <name> in that
                                                type (full entry), or 404 with
                                                `did_you_mean` and the other
                                                types that define <name>
        GET /engine-docs/<type>?q=<search>    - search entries
        GET /engine-docs/<type>?scope=<scope> - filter by scope
        GET /engine-docs/<type>?mask=<mask>   - filter by mask (modifiers only)
        GET /engine-docs/<type>?origin=mod|vanilla|unknown - filter by origin tag
        GET /engine-docs/<type>?group=true    - group similar entries
        GET /engine-docs/origin/<name>        - which doc type(s) define <name>,
                                                with the full schema entry
                                                (description, example, traits,
                                                reads, scopes, targets, …).
                                                Replaces ad-hoc grep when checking
                                                "does this trigger exist? what
                                                scope? what's the syntax?".
        GET /engine-docs/usage/<name>         - real-world call sites of <name>
                                                from vanilla `common/`. Returns
                                                file:line + a 4-line snippet per
                                                hit. Definitions and trigger-
                                                localization labels are filtered
                                                out by default. Params:
                                                  limit=N (default 5)
                                                  before=N / after=N (context)
                                                  include_defs=true (keep all)
                                                Useful when the docs don't cover
                                                a trigger or you want canonical
                                                argument shapes from real script.
        GET /engine-docs/loc-functions        - index of data-system loc
                                                functions (GetStaticModifier,
                                                GetValueWithBreakdownFor,
                                                Concept, AddTextIf, …) found by
                                                scanning vanilla loc + GUI for
                                                `[...]` expressions. Sorted by
                                                count desc. Params:
                                                  q=<substring>
                                                  kind=function|method|scope|accessor
                                                  min_count=N
                                                  limit=N (default 100)
                                                  include_examples=true
        GET /engine-docs/loc-functions/<name> - single function with up to 8
                                                vanilla `[...]` example
                                                expressions and file:line of
                                                first sighting. Use when
                                                researching the canonical loc
                                                idiom for a feature.
        """
        srv = server_state()
        if not parts:
            return {
                "available_types": list(srv.engine_docs.keys()),
                "counts": {k: len(v) for k, v in srv.engine_docs.items()},
                "source_label": srv.engine_docs_source_label,
            }

        # /engine-docs/origin/<name> — disambiguation lookup with full schema
        if parts[0] == "origin":
            if len(parts) < 2:
                raise srv.BadRequest("Usage: /engine-docs/origin/<name>")
            target = parts[1]
            hits = []
            # Fields surfaced per match. Common to all entry types: name, origin.
            # Trigger/effect: description, example, traits, reads, scopes, targets.
            # Modifier: mask, display_name, defined_in, is_*_flags.
            # custom-localization / on-action / event-target: type-specific subset.
            _surfaced_fields = (
                "description", "example", "traits", "reads",
                "scopes", "targets",
                "defined_in", "is_script_only", "is_boolean",
                "mask", "display_name",
                "mod_redeclares", "mod_redeclared_in", "mod_script_only",
                "input_scopes", "output_scopes",
            )
            for dtype, entries in srv.engine_docs.items():
                for e in entries:
                    if e.get("name") == target:
                        match = {
                            "type": dtype,
                            "origin": e.get("origin", "unknown"),
                        }
                        for k in _surfaced_fields:
                            if k in e and e[k] not in (None, "", [], {}):
                                match[k] = e[k]
                        hits.append(match)
            return {
                "name": target,
                "found": len(hits) > 0,
                "matches": hits,
            }

        # /engine-docs/loc-functions[/<name>] — index of loc-rendering function
        # tokens discovered by scanning vanilla loc + GUI files for `[...]`
        # expressions. Surfaces the data-system functions the engine exposes
        # (GetStaticModifier, GetValueWithBreakdownFor, GetNameNoFormatting,
        # Concept, AddTextIf, …) which are not in any vanilla doc — they have
        # to be reverse-engineered from real-world usage.
        if parts[0] == "loc-functions":
            index = _get_loc_function_index()
            if len(parts) >= 2:
                name = parts[1]
                entry = index.get(name)
                if entry is None:
                    return {"name": name, "found": False, "examples": []}
                limit = int(params.get("limit", ["8"])[0])
                return {
                    "name": name,
                    "found": True,
                    "kind": entry["kind"],
                    "count": entry["count"],
                    "first_seen": entry["first_seen"],
                    "examples": entry["examples"][:limit],
                }
            # Listing: q substring filter, min_count cutoff, kind filter, limit.
            query = params.get("q", [""])[0]
            min_count = int(params.get("min_count", ["0"])[0])
            kind_filter = params.get("kind", [""])[0].lower()
            limit = int(params.get("limit", ["100"])[0])
            include_examples = params.get("include_examples", ["false"])[0].lower() in (
                "true", "1", "yes"
            )
            rows = []
            for ident, entry in index.items():
                if query and query.lower() not in ident.lower():
                    continue
                if entry["count"] < min_count:
                    continue
                if kind_filter and entry["kind"] != kind_filter:
                    continue
                row = {
                    "name": ident,
                    "kind": entry["kind"],
                    "count": entry["count"],
                }
                if include_examples:
                    row["example"] = entry["examples"][0]["expression"] if entry["examples"] else ""
                rows.append(row)
            rows.sort(key=lambda r: (-r["count"], r["name"]))
            return {
                "total_distinct_functions": len(index),
                "filtered": len(rows),
                "returned": min(len(rows), limit),
                "entries": rows[:limit],
            }

        # /engine-docs/usage/<name> — find real-world usages in vanilla common/.
        # Returns context-bracketed call sites (definition lines and label
        # cross-references in scripted_triggers/trigger_localization are filtered
        # out — usages are always indented inside a block, definitions are at
        # column 0).
        if parts[0] == "usage":
            if len(parts) < 2:
                raise srv.BadRequest("Usage: /engine-docs/usage/<name>?limit=N&include_defs=true")
            target = parts[1]
            limit = int(params.get("limit", ["5"])[0])
            include_defs = params.get("include_defs", ["false"])[0].lower() in ("true", "1", "yes")
            context_before = int(params.get("before", ["1"])[0])
            context_after = int(params.get("after", ["3"])[0])
            usage = _engine_docs_find_usage(
                target,
                limit=limit,
                include_defs=include_defs,
                context_before=context_before,
                context_after=context_after,
            )
            # The scanner reports failures in-band; over HTTP they are a
            # status, not a 200 body. (#254)
            if isinstance(usage, dict) and "error" in usage:
                err = usage["error"]
                if err.startswith("Invalid target name"):
                    # Whole payload, so the body keeps `name` / `uses`. (#254)
                    raise srv._EndpointError(usage, 400)
                if err.startswith("Vanilla common dir not found"):
                    raise srv._ServiceNotReady(usage, 503)
                raise srv._EndpointError(usage, 500)
            return usage

        doc_type = parts[0]
        if doc_type not in srv.engine_docs:
            raise srv.NotFound(f"Unknown engine doc type: {doc_type}. Available: {list(srv.engine_docs.keys())}")

        entries = srv.engine_docs[doc_type]

        # /engine-docs/<type>/<name> — one entry of that type. Used to fall
        # through to the unfiltered listing, silently dropping <name> (#326).
        if len(parts) > 2:
            raise srv.BadRequest(
                f"Usage: /engine-docs/{doc_type}/<name> (one name segment)."
            )
        if len(parts) == 2:
            name = parts[1]
            matches = [e for e in entries if e.get("name") == name]
            if not matches:
                raise srv.NotFound(
                    f"{doc_type}/{name}",
                    did_you_mean=difflib.get_close_matches(
                        name, [e.get("name", "") for e in entries], n=5, cutoff=0.6
                    ),
                    defined_in_types=[
                        t for t, es in srv.engine_docs.items()
                        if t != doc_type and any(e.get("name") == name for e in es)
                    ],
                    hint="GET /engine-docs/origin/<name> searches every doc type; "
                         "/engine-docs/usage/<name> finds vanilla call sites.",
                )
            # A list: event-targets repeats some names (one entry per scope form).
            return {"type": doc_type, "name": name, "found": True, "matches": matches}
        query = params.get("q", [""])[0].lower()
        scope_filter = params.get("scope", [""])[0].lower()
        mask_filter = params.get("mask", [""])[0].lower()
        origin_filter = params.get("origin", [""])[0].lower()
        do_group = params.get("group", ["false"])[0].lower() in ("true", "1", "yes")
        limit = int(params.get("limit", ["500"])[0])

        # Apply filters
        filtered = entries
        if query:
            filtered = [
                e for e in filtered
                if query in e.get("name", "").lower()
                or query in e.get("description", "").lower()
                or query in e.get("display_name", "").lower()
            ]
        if scope_filter:
            filtered = [
                e for e in filtered
                if scope_filter in [s.lower() for s in e.get("scopes", [])]
                or scope_filter in [s.lower() for s in e.get("input_scopes", [])]
                or scope_filter in [s.lower() for s in e.get("output_scopes", [])]
            ]
        if mask_filter:
            filtered = [
                e for e in filtered
                if mask_filter in e.get("mask", "").lower()
            ]
        if origin_filter:
            filtered = [
                e for e in filtered
                if e.get("origin", "unknown").lower() == origin_filter
            ]

        # Grouping
        if do_group:
            grouped, ungrouped = _group_similar_entries(filtered)
            return {
                "type": doc_type,
                "grouped_patterns": grouped,
                "ungrouped_count": len(ungrouped),
                "ungrouped": ungrouped[:limit],
                "truncated": len(ungrouped) > limit,
            }

        # `count` is the filtered total; `entries` is capped at `limit`, so a
        # client scanning it must check `truncated` (#326).
        page = filtered[:limit]
        return {
            "type": doc_type,
            "count": len(filtered),
            "returned": len(page),
            "truncated": len(page) < len(filtered),
            "entries": page,
        }

    # ---- developer reference docs -----------------------------------------
    def _dev_docs(self, parts, params):
        """GET /dev-docs                       - list available docs by directory
        GET /dev-docs/<directory>           - get all docs in a directory
        GET /dev-docs/<dir>/<file>          - get specific doc content
        GET /dev-docs?q=<search>            - search doc contents
        """
        srv = server_state()
        query = params.get("q", [""])[0].lower()

        if not parts and not query:
            # List all docs grouped by directory
            by_dir: dict[str, list] = {}
            for path, doc in srv.dev_reference_docs.items():
                d = doc["directory"]
                if d not in by_dir:
                    by_dir[d] = []
                by_dir[d].append({"filename": doc["filename"], "path": path, "size": doc["size"]})
            return {
                "directories": sorted(by_dir.keys()),
                "count": len(srv.dev_reference_docs),
                "docs_by_directory": {k: by_dir[k] for k in sorted(by_dir.keys())},
            }

        if not parts and query:
            # Search across all docs
            results = []
            for path, doc in srv.dev_reference_docs.items():
                if query in doc["content"].lower():
                    # Find matching lines for context
                    matching_lines = []
                    for i, line in enumerate(doc["content"].splitlines(), 1):
                        if query in line.lower():
                            matching_lines.append({"line": i, "text": line.rstrip()})
                    results.append({
                        "path": path,
                        "directory": doc["directory"],
                        "match_count": len(matching_lines),
                        "matches": matching_lines[:20],
                    })
            return {"query": query, "count": len(results), "results": results}

        # /dev-docs/<path...> — reconstruct path from parts
        req_path = "/".join(parts)

        # Exact match
        if req_path in srv.dev_reference_docs:
            doc = srv.dev_reference_docs[req_path]
            return {"path": doc["path"], "directory": doc["directory"], "content": doc["content"]}

        # Try as directory — list all docs in that dir
        matches = {
            p: d for p, d in srv.dev_reference_docs.items()
            if d["directory"] == req_path or d["directory"].startswith(req_path + "/")
        }
        if matches:
            docs = []
            for p, d in matches.items():
                docs.append({"path": p, "filename": d["filename"], "size": d["size"]})
            # If only one doc in the directory, return its content directly
            if len(docs) == 1:
                single = srv.dev_reference_docs[docs[0]["path"]]
                return {"path": single["path"], "directory": single["directory"], "content": single["content"]}
            return {"directory": req_path, "count": len(docs), "docs": docs}

        raise srv.NotFound(f"No dev doc found for: {req_path}")
