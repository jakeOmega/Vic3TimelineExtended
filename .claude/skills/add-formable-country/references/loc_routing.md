# Localization routing for new formables

`organize_loc.py` rewrites every `localization/english/te_*.yml` from scratch on each run, sorted alphabetically and bucketed by `categorize_key`. Any key that doesn't match a registered prefix lands in MISCELLANEOUS or CONCEPTS. The mod auto-runs `organize_loc.py` after every `POST /reload`, so introducing a new tag without updating this rule means your loc keys drift on the first reload.

## Current FORMABLE_COUNTRIES rule

In `organize_loc.py` `categorize_key` (around line 270, just after the IDEOLOGIES check):

```python
if (
    key.startswith("dyn_c_")
    or key.startswith("dp_unify_")
    or key.startswith("dp_leadership_")
    or key in {
        "AFU", "INM", "EAF", "EUN", "UNA",
        "AFU_ADJ", "INM_ADJ", "EAF_ADJ", "EUN_ADJ", "UNA_ADJ",
    }
):
    return "FORMABLE_COUNTRIES"
```

## Adding a new tag

When introducing tag `XYZ`:

1. Append `"XYZ"` and `"XYZ_ADJ"` to the `key in { … }` set in the rule above. The `dyn_c_*` and `dp_*` prefixes catch the dynamic-name and diplomatic-play keys automatically — only the bare-tag display keys need an explicit entry.

2. Run `python3 organize_loc.py --dry-run` and confirm `te_formable_countries_l_english.yml` shows the expected key delta. Then run `python3 organize_loc.py` for real.

## Known routing quirks

- **`dp_*_tooltip` keys land in UNUSED.** `organize_loc.py`'s unused-key detector walks the codebase for explicit references; tooltip keys are referenced only implicitly by the engine via diplomatic-play DSL conventions, so the detector misses them. They still ship (engine loads any l_english.yml regardless of file name) and the engine resolves them at runtime — just sorted into `te_unused_l_english.yml` instead of the formable file. Optional fix: add a `find_diplomatic_play_keys` function to organize_loc.py modeled on `find_diplo_action_keys` (around line 130) that scans `common/diplomatic_plays/*.txt` and adds the `_tooltip`, `_desc`, `_tooltip_desc` companions to the `used_keys` set. Then the routing rule already handles them via the `dp_unify_` / `dp_leadership_` prefix.

- **`TAG:` (without `_ADJ`) used as the default fallback name.** When no dynamic-name entry's trigger matches, the engine displays the tag's bare loc (e.g. `AFU:0 "African Union"`). Always ship this even if all your dynamic-name entries have wide triggers — there will eventually be an edge case (anarchy law, decentralized country type, missing leader) where none fires.

- **`name = TAG_ADJ` on a dynamic-name entry without a corresponding `_ADJ` loc** silently displays as `[BLANK]` in tooltips. If reusing the bare tag adjective (e.g. `adjective = AFU_ADJ`), make sure `AFU_ADJ:0 "African"` exists.

## File destination

All keys above land in `localization/english/te_formable_countries_l_english.yml`. Hand-editing that file is fine for adding new keys; they'll be re-sorted on the next `organize_loc.py` run. Don't bother trying to preserve a custom order — it's destroyed on every reload.

## Categorization order matters

`categorize_key` is a long if/elif chain. Order it so that the FORMABLE_COUNTRIES rule beats any earlier rule that would also match. The `dp_*` keys would match the broad `if any(s in key for s in ["diplo", ...]): return "DIPLOMACY"` check at the bottom — but only if FORMABLE_COUNTRIES doesn't fire first. Currently FORMABLE_COUNTRIES sits above DIPLOMACY in the function, so the `dp_unify_` / `dp_leadership_` prefix wins. Don't move it.
