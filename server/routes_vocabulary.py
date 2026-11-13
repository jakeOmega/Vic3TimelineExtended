"""The vocabulary and modifier-pattern routes: GET /vocabularies[/<placeholder>],
/modifier-patterns[/<pattern>], /building-groups[/<id>[/reach]] and the thin
wrappers over a vocabulary (/cultures, /religions, /interest-groups,
/law-groups, /pop-types, /country-ranks, /terrain, /discrimination-traits).
Moved out of mod_state_server.py unchanged (#1537).

A route module holds code only (server/__init__.py says why): the state these
routes read stays in mod_state_server and is read as `srv.<name>` through
`server_state()` at call time. mod_state_server re-exports every name below.
"""
from server import server_state


class VocabularyRoutes:
    """GET /vocabularies, /modifier-patterns, /building-groups and the vocabulary wrappers. A mixin of ModStateHandler."""

    # ---- vocabularies -----------------------------------------------------
    def _vocabularies(self, parts):
        """GET /vocabularies            — full {placeholder: [values]} map.
        GET /vocabularies/<placeholder>  — list for a single placeholder."""
        srv = server_state()
        if not parts:
            return {
                p: {
                    "entity_type": srv.VOCABULARY_TYPES[p],
                    "count": len(values),
                    "values": values,
                }
                for p, values in srv._vocabulary_index().items()
            }
        placeholder = parts[0]
        if placeholder not in srv.VOCABULARY_TYPES:
            raise srv.NotFound(placeholder)
        values = srv._vocabulary_values(placeholder)
        return {
            "placeholder": placeholder,
            "entity_type": srv.VOCABULARY_TYPES[placeholder],
            "count": len(values),
            "values": values,
        }

    def _vocab_endpoint(self, placeholder: str):
        """Convenience endpoint behind /cultures, /religions, etc."""
        srv = server_state()
        values = srv._vocabulary_values(placeholder)
        return {
            "placeholder": placeholder,
            "entity_type": srv.VOCABULARY_TYPES[placeholder],
            "count": len(values),
            "entries": [{"id": v, "name": srv.ms.localize(v)} for v in values],
        }

    def _building_groups(self, parts):
        """GET /building-groups[/<id>[/reach]] (#383)

        Bare: the vocabulary wrapper (`{placeholder, entity_type, count,
        entries: [{id, name}]}`), each real group also carrying `parent_group`
        (merged: after the mod's REPLACE / INJECT), `origin` (vanilla | mod |
        mod-injected, a vanilla group the mod only INJECTs into | mod-replaced,
        one a mod file redefines) and `construction_efficiency_modifier` (whether
        it registers its own building_group_<id>_construction_efficiency_add). The
        prefix-less spellings the vocabulary lists (`manufacturing`) carry
        `alias_of` instead; `group_count` counts the real groups.

        /<id>: that group with `ancestors` (nearest first), `children`,
        `descendants`, the `buildings` directly in it and `mod_definitions`
        (each mod file's line and directive). /<id>/reach: every building a
        building_group_<id>_* modifier applies to, the group's own and its
        descendants'. <id> may be the prefix-less spelling."""
        srv = server_state()
        import building_group_tree as bgt

        groups = (srv.ms.get_data(bgt.ENTITY_TYPE) if srv.ms else None) or {}
        if not groups:
            if parts:
                raise srv.DataNotLoaded(bgt.ENTITY_TYPE)
            return self._vocab_endpoint("bg")
        vanilla_parser = srv.ms.base_parsers.get(bgt.ENTITY_TYPE)
        definitions = bgt.definitions(srv.mod_path)
        tree = bgt.Tree(groups, vanilla_parser.data if vanilla_parser is not None else None,
                        srv.ms.get_data("Buildings"), definitions)

        if not parts:
            out = self._vocab_endpoint("bg")
            for entry in out["entries"]:
                if entry["id"] in groups:
                    entry.update(tree.row(entry["id"]))
                else:
                    entry["alias_of"] = tree.resolve(entry["id"])
            out["group_count"] = len(groups)
            return out

        gid = tree.resolve(parts[0])
        if gid is None or len(parts) > 2 or (len(parts) == 2 and parts[1] != "reach"):
            raise srv.NotFound("/".join(parts))
        out = {"type": bgt.ENTITY_TYPE, "id": gid, "name": srv.ms.localize(gid), **tree.row(gid)}
        if len(parts) == 2:
            reach = tree.reach(gid)
            out.update({
                "groups": [gid, *tree.descendants(gid)],
                "count": len(reach),
                "buildings": [{"id": bid, "name": srv.ms.localize(bid), "building_group": group}
                              for bid, group in reach],
                "note": bgt.REACH_NOTE,
            })
            return out
        out.update({
            "ancestors": tree.ancestors(gid),
            "children": list(tree.children[gid]),
            "descendants": tree.descendants(gid),
            "buildings": [{"id": bid, "name": srv.ms.localize(bid)} for bid in tree.buildings[gid]],
            "mod_definitions": definitions.get(gid, []),
        })
        return out

    # ---- modifier patterns -----------------------------------------------
    def _modifier_patterns(self, parts, params):
        """GET /modifier-patterns                — list all patterns.
        GET /modifier-patterns?source=catalog|discovered|all
        GET /modifier-patterns?expand=<pattern>&<placeholder>=<value>
        GET /modifier-patterns/<pattern>        — detail for one pattern."""
        srv = server_state()
        source_filter = (params.get("source") or ["all"])[0]
        expand_pattern = (params.get("expand") or [None])[0]

        if expand_pattern:
            return self._modifier_pattern_expand(expand_pattern, params)

        catalog_set = {entry["pattern"] for entry in srv.pattern_catalog}
        discovered_set = {d["pattern"] for d in srv.discovered_patterns}
        catalog_meta = {entry["pattern"]: entry for entry in srv.pattern_catalog}
        discovered_meta = {d["pattern"]: d for d in srv.discovered_patterns}
        vocabularies = srv._vocabulary_index()

        if parts:
            pattern = parts[0]
            return self._modifier_pattern_detail(
                pattern, catalog_meta, discovered_meta, vocabularies
            )

        out = []
        for pattern, members in sorted(srv.pattern_index.items()):
            origin = "catalog" if pattern in catalog_set else (
                "discovered" if pattern in discovered_set else "unknown"
            )
            if source_filter != "all" and origin != source_filter:
                continue
            entry_meta = catalog_meta.get(pattern) or discovered_meta.get(pattern) or {}
            placeholder = entry_meta.get("placeholder", "?")
            vocab = entry_meta.get("vocab", placeholder)
            vocab_size = len(vocabularies.get(vocab, []) or [])
            out.append({
                "pattern": pattern,
                "source": origin,
                "placeholder": placeholder,
                "vocab": vocab,
                "members": len(members),
                "vocab_size": vocab_size,
                "missing_count": max(0, vocab_size - len(members)),
            })
        return {"count": len(out), "patterns": out}

    def _modifier_pattern_detail(self, pattern, catalog_meta, discovered_meta, vocabularies):
        srv = server_state()
        if pattern not in srv.pattern_index:
            raise srv.NotFound(pattern)
        members = srv.pattern_index[pattern]
        meta = catalog_meta.get(pattern) or discovered_meta.get(pattern) or {}
        placeholder = meta.get("placeholder", "?")
        vocab_name = meta.get("vocab", placeholder)
        vocab_values = set(vocabularies.get(vocab_name, []) or [])
        present = set(members.keys())
        missing = sorted(vocab_values - present) if vocab_values else []
        origin = "catalog" if pattern in catalog_meta else (
            "discovered" if pattern in discovered_meta else "unknown"
        )
        return {
            "pattern": pattern,
            "source": origin,
            "placeholder": placeholder,
            "vocab": vocab_name,
            "notes": meta.get("notes", ""),
            "members": [
                {"value": v, "name": pattern.replace("{" + placeholder + "}", v),
                 "display_name": entry.get("display_name", ""),
                 "mask": entry.get("mask", "")}
                for v, entry in sorted(members.items())
            ],
            "missing": missing,
            "missing_count": len(missing),
        }

    def _modifier_pattern_expand(self, pattern, params):
        """Instantiate a pattern with a given placeholder value."""
        srv = server_state()
        compiled = srv._compile_pattern(pattern)
        if not compiled:
            raise srv.BadRequest(f"Pattern lacks a {{placeholder}} token: {pattern}")
        prefix, placeholder, suffix = compiled
        value = (params.get(placeholder) or [None])[0]
        if not value:
            raise srv.BadRequest(f"Provide ?{placeholder}=<value>")
        concrete = pattern.replace("{" + placeholder + "}", value)
        members = srv.pattern_index.get(pattern, {})
        existing = members.get(value)
        return {
            "pattern": pattern,
            "placeholder": placeholder,
            "value": value,
            "concrete_name": concrete,
            "exists_in_engine_docs": existing is not None,
            "engine_doc_entry": existing,
        }
