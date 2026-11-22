"""What National Info's binding tests take as given: the systems not bound
yet and the loc keys that are world reads.

Data, not tests: `test_te_system_tab_bodies.py`'s `BindingTest`, `GuardTest` and
`PublicTest` hold the panels to it, and `loc_root_context_audit.py` and
`scripts/analysis/te_rebind_country.py` read it too. It lived in the test file
until #1698, so those two tools imported a test module for it.
"""

# The systems National Info is to show (spec § 6.4) whose panels aren't bound yet: off the binding tests until their
# PR binds them. A system's PR sets its Tab's public=True and deletes its own `"key",` line here, and only that line:
# keep the blank lines, or two parallel PRs' deletions touch and conflict. One still here that passes every check
# fails test_unbound_is_honest, so this list only shrinks. A set() call, not a {...} literal, so it stays a set when
# the last system goes.
UNBOUND = set([








])

# A world read in loc (spec § 6.7): a key a public panel renders that reads the player's copy of what is the same
# for every country (a world list written for players only), with why. Markup marks its world reads with a
# `# world: <why>` line over the read instead. An entry read is never a world read. Each system's PR adds its keys
# to its own heading's dict, one a line, in order, so parallel PRs merge cleanly. A key that more than one system's
# panel reaches goes under Shared, once: test_a_shared_world_key_is_under_shared, and test_a_world_key_is_listed_once
# (two PRs adding it under their own headings would list it twice, and the flat WORLD_LOC would keep only one). A
# key no public or unbound panel renders, or that reads no player, fails test_world_loc_is_live.
# te_rebind_country.py names the other tabs that reach a key.
WORLD_LOC_BY_HEADING: dict[str, dict[str, str]] = {
    # Keys more than one system's panel reaches.
    "Shared": {
        "te_hist_tt_markers": "a chart bar's tooltip has only the bar's context (gotcha #24), and the scripted GUI it "
                              "asks roots on GetPlayer only to have a root: its handler reads scope:te_hist_sample. The "
                              "keys that scripted GUI prints read no root today; one that later reads SCOPE.GetRootScope "
                              "would read the player, and with this key exempt nothing would flag it",
    },
    "Demographics": {
    },
    "Nation (F2)": {
        "state_birth_limit_relief_add": "a modifier type's name, which the engine renders wherever it names the type, "
                                        "mostly with no Country in context (breakdowns, law tooltips, loading tips): "
                                        "GetPlayer is a root, behind vanilla's GetPlayer.IsValid guard, only to ask a "
                                        "game rule, the same for every country (te_demog_custom_loc.txt's header)",
        "state_birth_limit_relief_add_desc": "its description: as state_birth_limit_relief_add",
        "state_demog_womens_work_ratio_add": "a modifier type's name: as state_birth_limit_relief_add",
        "state_demog_womens_work_ratio_add_desc": "its description: as state_birth_limit_relief_add",
        "state_desired_fertility_mult": "a modifier type's name: as state_birth_limit_relief_add",
        "state_desired_fertility_mult_desc": "its description: as state_birth_limit_relief_add",
        "state_fertility_means_add": "a modifier type's name: as state_birth_limit_relief_add",
        "state_fertility_means_add_desc": "its description: as state_birth_limit_relief_add",
        "state_maternal_mortality_mult": "a modifier type's name: as state_birth_limit_relief_add",
        "state_maternal_mortality_mult_desc": "its description: as state_birth_limit_relief_add",
        "state_means_literacy_add": "a modifier type's name: as state_birth_limit_relief_add",
        "state_means_literacy_add_desc": "its description: as state_birth_limit_relief_add",
        "state_sex_ratio_at_birth_add": "a modifier type's name: as state_birth_limit_relief_add",
        "state_sex_ratio_at_birth_add_desc": "its description: as state_birth_limit_relief_add",
        "state_urban_fertility_relief_add": "a modifier type's name: as state_birth_limit_relief_add",
        "state_urban_fertility_relief_add_desc": "its description: as state_birth_limit_relief_add",
        "te_demog_census_off_name_ingame": "those names' custom loc, which asks the Demographics rule "
                                           "(te_demog_cohorts_run)",
        "te_demog_census_off_desc_ingame": "those descriptions' custom loc, which asks the Demographics rule "
                                           "(te_demog_cohorts_run)",
        "te_demog_wf_womens_name_ingame": "a name's custom loc, which asks the Demographics rule (te_demog_effects_run)",
        "te_demog_wf_womens_desc_ingame": "a description's custom loc, which asks the Demographics rule "
                                          "(te_demog_effects_run)",
        "te_demog_wf_womens_desc_full": "that description's text under the rule: a constant "
                                        "(te_demog_k_womens_work_full), read through GetPlayer for a root",
    },
    "Banking (F2)": {
    },
    "Tax Code (F2)": {
    },
    "Grand Monuments (F3)": {
    },
    "Colonial Empire (F3)": {
    },
    "Seabed (F3)": {
    },
    "Cultural Hegemony (F4)": {
    },
    "Nuclear Weapons (F4)": {
    },
    "Space Race (F5)": {
    },
}

# Every world key, with why, whatever its heading.
WORLD_LOC: dict[str, str] = {
    key: why for keys in WORLD_LOC_BY_HEADING.values() for key, why in keys.items()
}


def world_loc_headings() -> dict[str, str]:
    """Each world key and the heading it is listed under (the last, for a key
    listed twice)."""
    return {key: heading for heading, keys in WORLD_LOC_BY_HEADING.items() for key in keys}
