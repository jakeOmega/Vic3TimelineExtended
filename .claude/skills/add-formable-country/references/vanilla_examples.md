# Vanilla examples — country formation

Quotes are verbatim from the vanilla install at the path returned by `path_constants.py.base_game_path`. Re-verify before relying — Paradox patches change line numbers.

## Major formations

`game/common/country_formation/00_major_formables.txt` (full file is short).

### Germany (GER) — geographic_region anchored, dual-monarchy guard
```
GER = {
    geographic_region = geographic_region_greater_germany

    is_major_formation = yes

    unification_play = dp_unify_germany
    leadership_play = dp_leadership_germany

    required_states_fraction = 0.73

    ai_will_do = { has_technology_researched = nationalism }

    possible = {
        OR = {
            has_technology_researched = pan-nationalism
            custom_tooltip = {
                text = je_german_unification_idea_trigger_desc
                has_variable = je_german_unification_idea
            }
        }
        custom_tooltip = {
            text = no_confederation_of_the_rhine_tt
            NOT = { exists = c:RHN }
        }
        custom_tooltip = {
            text = no_dual_or_triple_monarchy_tt
            NOR = {
                has_government_type = gov_dual_monarchy
                has_government_type = gov_triple_monarchy
            }
        }
        NOT = { c:KUK ?= this }
    }

    max_num_formation_candidates = 3
    can_be_formation_candidate = {
        country_rank >= rank_value:major_power
    }

    can_be_unification_target = {
        NOR = {
            has_government_type = gov_dual_monarchy
            has_government_type = gov_triple_monarchy
        }
    }
}
```

### Italy (ITA) — `use_culture_states` + culture-fan candidacy
```
ITA = {
    use_culture_states = yes

    is_major_formation = yes

    unification_play = dp_unify_italy
    leadership_play = dp_leadership_italy

    required_states_fraction = 0.7

    ai_will_do = { has_technology_researched = nationalism }

    possible = {
        OR = {
            country_has_primary_culture = cu:north_italian
            country_has_primary_culture = cu:south_italian
        }
        is_country_type = recognized
        NOR = { c:AUS ?= this   c:KUK ?= this   c:HRE ?= this }
    }

    max_num_formation_candidates = 3
    can_be_formation_candidate = {
        country_rank >= rank_value:minor_power
        NOR = { c:AUS ?= this   c:KUK ?= this   c:HRE ?= this }
        is_country_type = recognized
        any_country_in_italy_old = {
            has_technology_researched = nationalism
            percent = 1
        }
    }
}
```

### Scandinavia (SCA) — minimum candidate threshold (minor_power), all-tech precondition
```
SCA = {
    geographic_region = geographic_region_scandinavia

    is_major_formation = yes

    unification_play = dp_unify_scandinavia
    leadership_play = dp_leadership_scandinavia

    required_states_fraction = 0.7

    ai_will_do = { always = yes }

    possible = {
        OR = {
            country_has_primary_culture = cu:swedish
            country_has_primary_culture = cu:danish
            country_has_primary_culture = cu:norwegian
            country_has_primary_culture = cu:icelandic
        }
    }

    max_num_formation_candidates = 3
    can_be_formation_candidate = {
        country_rank >= rank_value:minor_power
        any_country_in_scandinavia = {
            has_technology_researched = pan-nationalism
            percent = 1
        }
    }
}
```

## Minor formations

`game/common/country_formation/00_formable_countries.txt`.

### Indonesia (IDN) — explicit state list, single tech gate
```
IDN = {
    states = {
        STATE_ACEH STATE_CENTRAL_JAVA STATE_EAST_BORNEO STATE_EAST_JAVA
        STATE_MALAYA STATE_MOLUCCAS STATE_CELEBES STATE_NORTH_BORNEO
        STATE_NORTH_SUMATRA STATE_SOUTH_SUMATRA STATE_SUNDA_ISLANDS
        STATE_WEST_BORNEO STATE_WESTERN_NEW_GUINEA STATE_WEST_JAVA
    }

    required_states_fraction = 0.65

    ai_will_do = { always = yes }

    possible = {
        has_technology_researched = pan-nationalism
    }
}
```

### Poland (POL) — `use_culture_states` + simple
```
PLC = {
    states = {
        STATE_BREST STATE_EAST_GALICIA STATE_GREATER_POLAND
        STATE_LESSER_POLAND STATE_KAUNAS STATE_VILNIUS STATE_MAZOVIA
        STATE_POSEN STATE_VOLHYNIA STATE_WEST_GALICIA STATE_WEST_PRUSSIA
    }
    required_states_fraction = 1
    ai_will_do = { always = yes }
}
```

## Diplomatic plays for major formations

`game/common/diplomatic_plays/00_diplomatic_plays.txt` lines 839-1180-ish.

```
dp_unify_germany = {
    war_goal = unification

    requires_interest_marker = no
    blocked_by_diplomatic_status = no
    add_infamy_for_starting_initiator_wargoals = no

    texture = "gfx/interface/icons/war_goals/unify_germany.dds"

    selectable_in_lens = { always = no }

    possible = {
        NOT = { exists = c:GER }
        NOT = { is_country_type = decentralized }
        has_technology_researched = pan-nationalism
        custom_tooltip = {
            text = no_confederation_of_the_rhine_tt
            NOT = { exists = c:RHN }
        }
    }

    on_weekly_pulse = {} on_war_begins = {} on_war_end = {}
}

dp_leadership_germany = {
    war_goal = unification_leadership

    requires_interest_marker = no
    mirror_war_goal = yes

    texture = "gfx/interface/icons/war_goals/unify_germany.dds"

    selectable_in_lens = { always = no }

    possible = {
        has_technology_researched = nationalism
    }

    on_weekly_pulse = {} on_war_begins = {} on_war_end = {}
}
```

## Generic formation event

`game/events/misc_unifications.txt:1042` — `formation.17`. Auto-fires for any tag NOT on its NOR-list. New mod tags (AFU, INM, EAF, EUN, UNA in this mod) are not on the list, so this event fires for them with the standard "X has emerged as a rising power in [region]" flavor and gives a 20-year prestige modifier + claims via `unification_claims_effect`.

`game/common/scripted_effects/00_scripted_effects.txt:840` — `unification_claims_effect`. Adds claims on every cultural-homeland state not yet owned/claimed, or 5% loyalists if all are owned.

## Existing mod content (this mod, pre-existing convention)

`/home/jakef/src/Vic3TimelineExtended/common/on_actions/fmc_on_actions.txt:143-158` — example of how the mod extends a vanilla `on_xxx` action. Vic3 merges these across files, so adding a new `on_country_formed = { on_actions = { … } events = { … } }` block in any mod file runs alongside vanilla's giant if/else chain.
