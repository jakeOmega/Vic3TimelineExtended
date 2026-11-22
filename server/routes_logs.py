"""The game-log routes: GET /logs, /logs/sessions, /logs/<family> and
/logs/<family>/diff. Moved out of mod_state_server.py unchanged (#1537).

A route module holds code only (server/__init__.py says why): the state these
routes read stays in mod_state_server and is read as `srv.<name>` through
`server_state()` at call time. mod_state_server re-exports every name below.
"""
import os
from collections import defaultdict

from server import server_state


class LogRoutes:
    """GET /logs and its sub-routes. A mixin of ModStateHandler."""

    # ---- game logs --------------------------------------------------------
    def _logs(self, parts, params):
        """GET /logs                       — index of available logs.
        GET /logs/sessions                — cluster log files into launch sessions.
        GET /logs/<family>                — entries for the latest gen.
        GET /logs/<family>?gen=N          — backup gen.
        GET /logs/<family>?summary=true   — category histogram + top repeats.
        GET /logs/<family>/diff[?against=N]
        GET /logs/<family>?q=&file=&source=&category=&since=
        GET /logs/<family>?dedupe=&dedupe_key=&limit=&offset=&raw=
        GET /logs/<family>?mod_only=true|false|unknown
            — true (default for error/debug): keep only entries with at least
              one mod-style script path in `files`.
            — false (default elsewhere): keep all entries.
            — unknown: keep entries unless they're tagged as a registered
              vanilla bug or registered vanilla noise. Includes mod-path
              entries AND entries with empty `files` whose origin can't be
              confirmed vanilla — useful for catching engine errors that
              surface from vanilla cpp source (no mod path attached) but
              are actually caused by mod content (e.g. unregistered concept
              refs, malformed loc).
        GET /logs/<family>?vanilla_bugs=show|hide|only
            — tag (default) / drop / keep-only entries that match a vanilla bug
            registered in docs/vanilla/vanilla_known_bugs.md.
        GET /logs/<family>?mod_noise=show|hide|only
            — same shape, but for mod-side cosmetic entries registered in
            docs/audits/mod_known_noise.md (these are NOT vanilla bugs; they're mod
            issues filtered for triage cleanliness but cross-linked to
            docs/audits/open_issues.md so they remain actionable).
            Tagged entries get a `vanilla_bug_ref: {title, section, kind}`
            field; `kind` is "vanilla", "vanilla_noise", "mod_low_priority"
            or "watch". A watch-list entry (the registry's "Watch list"
            section) is tagged and never hidden: its ref carries a `check`
            line saying what tells a mod cause from vanilla's.
            Use `?vanilla_bugs=hide&mod_noise=hide` for a fully-clean triage
            view, or `?mod_only=unknown` to surface uncategorized engine
            entries that the canonical filters hide.
        GET /logs/<family>?debug_log=show|hide|only
            — keep (default) / drop / keep-only script `debug_log` output
              (category `debug_log`: every `jomini_effect_impl.cpp` line,
              including the `debug_log_scopes` dump). Triage hides it; read
              probe and trace lines with `?debug_log=only&q=TE_`.
        """
        srv = server_state()
        from game_log_reader import (
            list_logs, parse_log, filter_mod_only, filter_external_mods, filter_entries,
            filter_debug_log,
            dedupe, summarize, diff_against_backup, cluster_sessions,
            load_vanilla_bug_registry, load_mod_noise_registry, tag_vanilla_bugs,
            gui_injected_scope_names, tag_gui_injected_scopes, apply_known_noise_modes,
            vanilla_gui_file_names, mod_gui_references, untag_mod_gui_fetches, new_mod_gui_warnings,
        )

        vanilla_bugs_doc = os.path.join(srv.mod_path, "docs", "vanilla", "vanilla_known_bugs.md")
        mod_noise_doc = os.path.join(srv.mod_path, "docs", "audits", "mod_known_noise.md")
        _, vb_by_basename, vb_by_source, _ = load_vanilla_bug_registry(vanilla_bugs_doc)
        _, mn_by_basename, mn_by_source, _ = load_mod_noise_registry(mod_noise_doc)

        def _apply_mod_only_mode(entries, mode):
            """Tristate filter on `mod_only` parameter.

            - 'true'    → keep entries with at least one mod-style script path
                          in `files` (today's default for error/debug).
            - 'false'   → keep all entries.
            - 'unknown' → keep entries unless they're tagged with a
                          `vanilla_bug_ref` of kind 'vanilla' or
                          'vanilla_noise'. Includes mod-path entries AND
                          entries with empty `files` whose origin can't be
                          confirmed vanilla. Surfaces engine errors that
                          come from vanilla cpp source (no mod path attached)
                          but are caused by mod content — e.g. unregistered
                          concept references, malformed loc, custom-loc
                          references to undeclared keys.

            Other values (incl. typos) fall through as 'false' / no filter.

            Caller must invoke `_apply_known_noise_tagging` first so that
            `vanilla_bug_ref` is populated when `mode == 'unknown'`.
            """
            if mode == "true":
                return filter_mod_only(entries)
            if mode == "unknown":
                kept = []
                for e in entries:
                    ref = e.vanilla_bug_ref
                    if ref is not None and ref.get("kind") in ("vanilla", "vanilla_noise"):
                        continue
                    kept.append(e)
                return kept
            return entries

        # What a tagging pass could not do, added to every reply that tagged.
        tagging_limits: dict = {}

        def _apply_known_noise_tagging(entries, vanilla_mode, mod_noise_mode):
            """Tag entries against both registries, then apply per-kind modes (show|hide|only).

            Two-pass tagging: vanilla registry first, then mod-noise registry on
            entries that didn't match vanilla, then the GUI-injected scopes
            (`Event target 'X' is used but is never set` for an X a mod .gui
            or loc string sets with AddScope; open_issues.md L14). Once tagged,
            an entry's vanilla_bug_ref.kind tells us which mode applies.
            Last, a GUI data-context failure under a source-only vanilla entry
            loses its tag when the mod's own GUI reaches the key or data type
            it names (#1269); the entry then carries `mod_gui_context`. Where
            that pass could not do all of it (no game install), the reply
            says why under `mod_gui_untagging`.
            """
            # mod_root: a `- stack: vanilla only` entry skips stacks with a mod frame (#863).
            tag_vanilla_bugs(entries, vb_by_basename, vb_by_source, mod_root=srv.mod_path)
            tag_vanilla_bugs(entries, mn_by_basename, mn_by_source, mod_root=srv.mod_path)
            tag_gui_injected_scopes(entries, gui_injected_scope_names([
                os.path.join(srv.mod_path, "gui"),
                os.path.join(srv.mod_path, "localization", "english"),
            ]))
            mod_gui = mod_gui_references(srv.mod_path, vanilla_gui_file_names(srv.base_game_path))
            for warning in new_mod_gui_warnings(mod_gui):  # once per process
                srv.logger.warning("/logs: %s", warning)
            if mod_gui.warnings:
                tagging_limits["mod_gui_untagging"] = list(mod_gui.warnings)
            untag_mod_gui_fetches(entries, mod_gui, (vb_by_source, mn_by_source), mod_root=srv.mod_path)

            return apply_known_noise_modes(entries, vanilla_mode, mod_noise_mode)

        if not parts:
            include_mp = (params.get("mp_sessions") or ["false"])[0].lower() == "true"
            infos = list_logs(srv.game_logs_path, include_mp_sessions=include_mp)
            grouped: dict = defaultdict(list)
            for info in infos:
                grouped[info.family].append(info.to_dict())
            return {
                "logs_dir": srv.game_logs_path,
                "families": dict(sorted(grouped.items())),
                "session_count_hint": len(cluster_sessions(infos)),
            }

        if parts[0] == "sessions":
            include_mp = (params.get("mp_sessions") or ["false"])[0].lower() == "true"
            infos = list_logs(srv.game_logs_path, include_mp_sessions=include_mp)
            return {"sessions": cluster_sessions(infos)}

        family = parts[0]
        action = parts[1] if len(parts) > 1 else None
        gen = int((params.get("gen") or ["0"])[0])
        infos = list_logs(srv.game_logs_path)
        match = None
        for info in infos:
            if info.family == family and info.generation == gen:
                match = info
                break
        if match is None:
            raise srv.NotFound(f"{family} (gen={gen})")

        # Diff endpoint
        if action == "diff":
            against = int((params.get("against") or ["1"])[0])
            against_match = next(
                (i for i in infos if i.family == family and i.generation == against),
                None,
            )
            if against_match is None:
                raise srv._EndpointError({"error": f"No {family}.{against}.log to diff against"}, 404)
            mod_only_mode = (params.get("mod_only") or ["true"])[0].lower()
            default_external = "false" if family in ("error", "debug") else "true"
            include_external = (params.get("include_external") or [default_external])[0].lower() == "true"
            vanilla_bugs_mode = (params.get("vanilla_bugs") or ["show"])[0].lower()
            mod_noise_mode = (params.get("mod_noise") or ["show"])[0].lower()
            debug_log_mode = (params.get("debug_log") or ["show"])[0].lower()
            current_entries = parse_log(match.path)
            against_entries = parse_log(against_match.path)
            # Tag noise first so the mod_only=unknown filter can examine
            # vanilla_bug_ref. The vanilla_bugs/mod_noise modes also apply
            # their own drop/only filtering inside this call.
            current_entries = _apply_known_noise_tagging(current_entries, vanilla_bugs_mode, mod_noise_mode)
            against_entries = _apply_known_noise_tagging(against_entries, vanilla_bugs_mode, mod_noise_mode)
            current_entries = _apply_mod_only_mode(current_entries, mod_only_mode)
            against_entries = _apply_mod_only_mode(against_entries, mod_only_mode)
            if not include_external:
                current_entries = filter_external_mods(current_entries)
                against_entries = filter_external_mods(against_entries)
            current_entries = filter_debug_log(current_entries, debug_log_mode)
            against_entries = filter_debug_log(against_entries, debug_log_mode)
            return {
                "current": match.to_dict(),
                "against": against_match.to_dict(),
                "diff": diff_against_backup(current_entries, against_entries),
                **tagging_limits,
            }

        # Raw / parsed entries
        entries = parse_log(match.path)
        # mod_only default: true for error/debug, false for the rest
        default_mod_only = "true" if family in ("error", "debug") else "false"
        mod_only_mode = (params.get("mod_only") or [default_mod_only])[0].lower()
        # Tag entries that match docs/vanilla/vanilla_known_bugs.md and docs/audits/mod_known_noise.md,
        # then optionally drop or keep-only by kind. Modes per param: show (default —
        # tag, keep visible), hide, only.
        #   ?vanilla_bugs=hide → drops vanilla / vanilla_noise tagged entries
        #   ?mod_noise=hide    → drops mod_low_priority tagged entries
        # Use both with `hide` for a fully-clean triage view; use `only` on either
        # for an audit of "what's currently being filtered".
        # Tagging is applied BEFORE mod_only so the `mod_only=unknown` mode can
        # examine `vanilla_bug_ref` on each entry.
        vanilla_bugs_mode = (params.get("vanilla_bugs") or ["show"])[0].lower()
        mod_noise_mode = (params.get("mod_noise") or ["show"])[0].lower()
        entries = _apply_known_noise_tagging(entries, vanilla_bugs_mode, mod_noise_mode)
        entries = _apply_mod_only_mode(entries, mod_only_mode)
        # include_external default: drop known third-party-mod spam (Statistics, ...)
        # from error/debug, keep it for everything else.
        default_external = "false" if family in ("error", "debug") else "true"
        include_external = (params.get("include_external") or [default_external])[0].lower() == "true"
        if not include_external:
            entries = filter_external_mods(entries)
        entries = filter_debug_log(entries, (params.get("debug_log") or ["show"])[0].lower())
        entries = filter_entries(
            entries,
            q=(params.get("q") or [None])[0],
            file_glob=(params.get("file") or [None])[0],
            source=(params.get("source") or [None])[0],
            category=(params.get("category") or [None])[0],
            since=(params.get("since") or [None])[0],
        )
        if (params.get("summary") or ["false"])[0].lower() == "true":
            return {"file": match.to_dict(), **summarize(entries), **tagging_limits}

        if (params.get("raw") or ["false"])[0].lower() == "true":
            limit = int((params.get("limit") or ["1000"])[0])
            offset = int((params.get("offset") or ["0"])[0])
            chunk = entries[offset: offset + limit]
            text = "\n".join(
                f"[{e.time}][{e.source}]: {e.message}" if e.time else e.message
                for e in chunk
            )
            return {"file": match.to_dict(), "raw": text, "count": len(chunk), **tagging_limits}

        do_dedupe = (params.get("dedupe") or ["true"])[0].lower() == "true"
        if do_dedupe:
            dedupe_key = (params.get("dedupe_key") or ["message+file"])[0]
            deduped = dedupe(entries, key=dedupe_key)
            limit = int((params.get("limit") or ["1000"])[0])
            offset = int((params.get("offset") or ["0"])[0])
            return {
                "file": match.to_dict(),
                "deduped": True,
                "total_unique": len(deduped),
                "entries": deduped[offset: offset + limit],
                **tagging_limits,
            }
        limit = int((params.get("limit") or ["1000"])[0])
        offset = int((params.get("offset") or ["0"])[0])
        chunk = entries[offset: offset + limit]
        return {
            "file": match.to_dict(),
            "deduped": False,
            "total": len(entries),
            "entries": [e.to_dict() for e in chunk],
            **tagging_limits,
        }
