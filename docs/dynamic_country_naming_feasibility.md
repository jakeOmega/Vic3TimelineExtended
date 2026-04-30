# Dynamic Country Naming Feasibility

## Why this question matters

When a culture splits into multiple new or breakaway states (Korea →
North/South, Germany → East/West, Yemen → North/South, Vietnam →
North/South, China → ROC/PRC), the player and the AI need a way to
disambiguate them in the UI without seeing two countries called "Germany"
on the map. Dynamic country names are vanilla's mechanism for this — a
country can resolve to one of several names depending on its current
state. This doc evaluates whether that mechanism can express the kind of
"another country of the same culture exists" rule we'd need.

## Vanilla mechanism (1.13)

Defined per-tag in `common/dynamic_country_names/`. Format (per the
vanilla `dynamic_country_names.md` spec):

```
TAG = {
    dynamic_country_name = {
        name = dyn_c_some_name_loc_key
        adjective = dyn_c_some_name_adj_loc_key
        is_main_tag_only = yes  # default no
        priority = 10           # default 0; higher wins ties
        trigger = { … }         # country-scope scripted trigger
    }
    # multiple dynamic_country_name blocks per tag are allowed
}
```

When the engine resolves a country's name, it walks every
`dynamic_country_name` for that tag, evaluates the `trigger` in country
scope, and picks the highest-priority match. Falls back to the static
country definition's name if no dynamic name matches.

`is_main_tag_only = yes` restricts a name to the canonical owner of the
definition — useful for "this is what we call the primary German state,
not its breakaway". Without it, any country with this tag (e.g. via
release) can use the name.

The trigger is a normal country-scope scripted trigger. Vanilla examples
gate on monarchy/republic, presence of journal entries, primary culture,
ideology of the leader, etc. (See vanilla KOR's "Joseon" / "Empire of
Korea" / "Republic of Korea" / "Democratic People's Republic" alternates
in `00_dynamic_country_names.txt`.)

## What works out of the box

Vanilla's existing trigger language is enough to express:

- "Country has a monarchy / republic / council republic" (governance fork)
- "Country's leader has an ideology" (left/right fork)
- "Country has a specific journal entry / law / decree active"
- "Country's primary culture is X"
- "Country owns a specific state region" (geographic fork — useful for
  "the half that holds Berlin/Seoul/Hanoi")

For most historical splits, **trigger gating on government type +
ideology** does the work. The "Empire of Korea / DPRK / Republic of
Korea" pattern in vanilla shows this idiom — the same TAG resolves to
different names based on its laws and ideology, with no awareness of
whether another Korea exists.

## What would require new wiring

The cleanest "Germany B exists, so call us Germany A" rule needs
*existence-of-another-country* logic inside the trigger:

```
trigger = {
    any_country = {
        primary_culture = root.primary_culture
        NOT = { this = root }
    }
}
```

I did not find any vanilla `dynamic_country_name` block that uses
`any_country` (or any cross-country iteration) inside its trigger. That
doesn't prove the engine rejects it — vanilla just doesn't need it,
because the same problem is solved by giving each side its own static
tag (PRK + KOR; DDR + GER; NVN + SVN). But it does mean **we'd be
exercising untested ground if we relied on it**.

Two possible workarounds if `any_country` doesn't work in the trigger:

**A. Cache the result in a country variable.** A yearly (or post-tag-creation)
on-action loops every country, sets `var:has_other_same_culture_country`
on each, and the dynamic name reads `has_variable = ...` (which is
plain country scope, definitely supported in triggers). One frame of
staleness per year, but the player won't notice.

**B. Use country flags.** When a tag is created via `create_country`
or `form_decolonized_country`, the creator can `set_country_flag` on
both itself and the new country reflecting the split. The dynamic name
trigger reads `has_country_flag`. More explicit per-event wiring; less
general.

## Edge cases the implementation has to address

| Case | Concern |
|------|---------|
| Re-unification (one absorbs the other) | The variable / flag must be cleared when the other country dies. Use `on_country_destroyed` or refresh during the same yearly loop. |
| Re-creation via release event | Flag-based approach must re-fire on release; variable-based recomputes at the next yearly tick. |
| Multi-split (3+ countries of same culture) | Plain "another exists" is enough for naming; the dyn-name set just needs to enumerate the geographic / ideological options. The trigger primitive scales. |
| AI-formed countries with non-historical names | Falls through to the static definition unless we cover the case in the dynamic name set. Default fallback is fine. |
| Player-formed unification country (e.g. "Greater Germany") | Use formation events to set the unified flag explicitly; clear all per-state flags. |

## Recommended structure when implementing

- One file: `common/dynamic_country_names/te_breakaway_country_names.txt`.
- Per culture (or per tag set), enumerate the dynamic names with
  triggers gating on:
  1. Whether a specific other-tag is alive (cleanest, where it applies).
  2. Whether a same-culture country other than self exists (general
     case; uses workaround **A** above).
  3. Government / ideology fork of the country itself (handles cases
     where multiple same-culture countries pick different governments
     and we want them named accordingly).
- Cultures most likely to need entries first: Korean, German, Vietnamese,
  Chinese, Yemeni, Cyprus-Greek/Turkish, Bengali (BAN/IND post-partition),
  Punjabi, Kashmiri.

## Recommendation

The vanilla mechanism handles 80% of the cases without new code. The
remaining "another country of the same culture exists" rule is plausibly
expressible inside the trigger (the trigger language doesn't restrict
country iteration), but **vanilla provides no precedent**. If a quick
test of `any_country = { … }` inside a `dynamic_country_name.trigger`
fails to compile or evaluate as expected, fall back to the on-action +
country variable workaround — that pattern is well-established in this
mod (see `cultural_hegemony_effects.txt` for similar yearly bookkeeping).

The actual implementation is a separate task once a culture priority
list is agreed.
