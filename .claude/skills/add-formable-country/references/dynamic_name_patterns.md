# Dynamic country names — patterns and triggers

## Canonical USA block (vanilla)

`game/common/dynamic_country_names/00_dynamic_country_names.txt:2785`. Reproduced in full because it's the cleanest multi-government example.

```
USA = { # United States of America
    dynamic_country_name = {
        name = dyn_c_united_states
        adjective = USA_ADJ
        is_main_tag_only = yes
        priority = 0
        trigger = {
            coa_def_republic_flag_trigger = yes
            NOT = { coa_def_communist_flag_trigger = yes }
            NOT = {
                scope:actor ?= { has_law_or_variant = law_type:law_technocracy }
            }
        }
    }

    dynamic_country_name = {        # priority 1: only when D.C. is the sole state
        name = dyn_c_united_senators
        adjective = USA_ADJ
        priority = 1
        trigger = {
            exists = c:USA
            c:USA ?= {
                any_scope_state = {
                    state_region = { has_variable = district_of_columbia }
                    count > 0
                }
                any_scope_state = {
                    state_region = { NOT = { has_variable = district_of_columbia } }
                    count < 1
                }
            }
        }
    }

    dynamic_country_name = {
        name = dyn_c_united_sovereign_archduchy
        adjective = dyn_c_united_sovereign_archduchy_adj
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_monarchy_flag_trigger = yes }
    }

    dynamic_country_name = {
        name = dyn_c_united_syndicates_of_america
        adjective = USA_ADJ
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_communist_flag_trigger = yes }
    }

    dynamic_country_name = {
        name = dyn_c_united_synods_of_america
        adjective = USA_ADJ
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_theocracy_flag_trigger = yes }
    }

    dynamic_country_name = {
        name = dyn_c_north_american_technate
        adjective = USA_ADJ
        is_main_tag_only = yes
        priority = 0
        trigger = {
            coa_def_republic_flag_trigger = yes
            scope:actor ?= { has_law_or_variant = law_type:law_technocracy }
        }
    }
}
```

Three things to copy:

1. **Default-republic guard.** The default entry checks `coa_def_republic_flag_trigger = yes` AND explicitly excludes communist + technocracy. This avoids both entries firing when (e.g.) a council republic also matches the broad republic trigger. The technocracy NOT is technically redundant (technocracy's law isn't in the republic OR list), but vanilla keeps it for safety.

2. **Priority for second-axis flavor.** The "United Senators" entry uses priority 1 to override the default when its niche conditions match (D.C. only). Use priority 5+ in your skill output for clearer override semantics.

3. **`is_main_tag_only = yes` on every entry.** Subjects with the same tag won't pull these names — they get the base `TAG:` loc instead. Almost always what you want.

## Government trigger reference

| Trigger | Underlying condition | Notes |
|---|---|---|
| `coa_def_republic_flag_trigger` | corporate_state, presidential_republic, parliamentary_republic, council_republic | broad — overlaps with communist |
| `coa_def_communist_flag_trigger` | `law_council_republic` | mutually triggers `coa_def_republic_flag_trigger` |
| `coa_def_fascist_flag_trigger` | (oligarchy OR dictatorship OR fascist_social_monarchy) AND fascist leader/IG | works under monarchy or republic — fascist law doesn't exist as a single category |
| `coa_def_monarchy_flag_trigger` | any monarchy law variant | broad — includes constitutional monarchy |
| `coa_def_absolute_monarchy_flag_trigger` | absolute monarchy variant | narrower; no parliament |
| `coa_def_undemocratic_monarchy_flag_trigger` | non-elected monarchy | narrower than _monarchy_, broader than _absolute_ |
| `coa_def_theocracy_flag_trigger` | `law_theocracy` | |
| `coa_def_technocracy_flag_trigger` | `law_technocracy` | |
| `coa_def_dictatorship_flag_trigger` | dictatorship via coa_dictatorship_trigger | |
| `coa_def_anarchy_flag_trigger` | `law_anarchy` | |
| `coa_def_nihilist_flag_trigger` | state atheism, not theocracy/monarchy | |
| `coa_def_corporate_state_flag_trigger` | `law_corporate_state` | |

Defined in `game/common/scripted_triggers/00_coa_triggers.txt`.

## Worked example — Intermarium (INM)

The mod's INM (Promethean Empire under fascism, drawn from Piłsudski's Intermarium project). Five government variants + one second-axis variant.

```
INM = {
    dynamic_country_name = { # Default
        name = dyn_c_intermarium
        adjective = INM_ADJ
        is_main_tag_only = yes
        priority = 0
        trigger = {
            coa_def_republic_flag_trigger = yes
            NOT = { coa_def_communist_flag_trigger = yes }
            NOT = { coa_def_technocracy_flag_trigger = yes }
        }
    }
    dynamic_country_name = { # Communist
        name = dyn_c_three_seas_socialist_federation
        adjective = dyn_c_three_seas_adj
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_communist_flag_trigger = yes }
    }
    dynamic_country_name = { # Fascist — Promethean Empire (Piłsudski)
        name = dyn_c_promethean_empire
        adjective = dyn_c_promethean_adj
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_fascist_flag_trigger = yes }
    }
    dynamic_country_name = { # 2nd axis: Hungarian-formed monarchy → Crown of Saint Stephen
        name = dyn_c_crown_of_saint_stephen
        adjective = dyn_c_crown_of_saint_stephen_adj
        is_main_tag_only = yes
        priority = 5
        trigger = {
            coa_def_monarchy_flag_trigger = yes
            scope:actor ?= { was_formed_from = HUN }
        }
    }
    dynamic_country_name = { # Generic monarchy fallback
        name = dyn_c_polish_lithuanian_commonwealth
        adjective = dyn_c_commonwealth_adj
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_monarchy_flag_trigger = yes }
    }
    dynamic_country_name = { # Theocracy
        name = dyn_c_catholic_federation_of_three_seas
        adjective = dyn_c_three_seas_adj
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_theocracy_flag_trigger = yes }
    }
    dynamic_country_name = { # Technocracy
        name = dyn_c_three_seas_technical_union
        adjective = dyn_c_three_seas_adj
        is_main_tag_only = yes
        priority = 0
        trigger = { coa_def_technocracy_flag_trigger = yes }
    }
}
```

Loc keys for this example:

```
 INM:0 "Intermarium"
 INM_ADJ:0 "Intermarian"
 dyn_c_intermarium:0 "Intermarium"
 dyn_c_three_seas_adj:0 "Three Seas"
 dyn_c_three_seas_socialist_federation:0 "Federation of Three Seas Soviets"
 dyn_c_promethean_adj:0 "Promethean"
 dyn_c_promethean_empire:0 "Promethean Empire"
 dyn_c_crown_of_saint_stephen:0 "Crown of Saint Stephen"
 dyn_c_crown_of_saint_stephen_adj:0 "Hungarian"
 dyn_c_polish_lithuanian_commonwealth:0 "Polish-Lithuanian Commonwealth"
 dyn_c_commonwealth_adj:0 "Commonwealth"
 dyn_c_catholic_federation_of_three_seas:0 "Catholic Federation of the Three Seas"
 dyn_c_three_seas_technical_union:0 "Three Seas Technical Union"
```

## 2nd-axis flavor patterns

These fire at priority 5 (or higher), beating the priority-0 generic for that government type when their extra condition matches.

| Axis | Trigger | Example use |
|---|---|---|
| Forming country | `scope:actor ?= { was_formed_from = TAG }` | INM-from-Hungary → Crown of Saint Stephen |
| Ruler culture | `scope:actor ?= { ruler ?= { has_culture = cu:X } }` | AU-with-Amhara-ruler → Solomonic African Empire |
| Ruler religion | `scope:actor ?= { ruler ?= { religion = rel:X } }` | BHT-theocracy-Hindu → Hindu Rashtra |
| State religion | `scope:actor ?= { state_religion = rel:X }` | IDN-theocracy-Sunni → Negara Islam Indonesia |
| Owns specific state | `scope:actor ?= { owns_entire_state_region = STATE_X }` | (vanilla HOL/Holstein → Schleswig-Holstein when owning that state) |

When stacking conditions, prefer `scope:actor ?= { … }` — matches vanilla idiom for actor scoping in dynamic-name triggers.

## Anti-patterns to avoid

- **Don't omit `is_main_tag_only`** unless you genuinely want subjects to use the dynamic name (rare).
- **Don't add a trigger that overlaps a vanilla entry without higher priority.** Vanilla IDN has Majapahit (Javan ruler + monarchy) and Srivijaya (Malay/Sumatran ruler + monarchy). A mod entry "Generic Indonesian Monarchy" at priority 0 would file-order race vanilla (which loads first) and never fire. Use higher priority or narrower trigger.
- **Don't use campy names.** Every dynamic name should ground in real history, real political projects, or real linguistic tradition. "Empire of the Penguins" / "Emu Empire" reads as joke content. Examples that work: Promethean Empire (Piłsudski), Solomonic Empire (Ethiopia), Akhand Bharat (Hindu nationalist), Indonesia Raya (real movement), Ujamaa (Nyerere), Three Seas (real Polish geopolitical concept).
- **Don't write loc inline.** Every `name =` and `adjective =` must point to a localization key, even if you'd rather inline a string. The engine doesn't accept inline strings here.
