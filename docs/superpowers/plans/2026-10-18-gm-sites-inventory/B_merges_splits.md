> Survey of branch feat/gm-sites-world-wealth at 823dc25c (2026-10-18), read-only. Line numbers drift as the plan lands; search by name.

# Inventory B: shadows, merges, split pieces, the one-off repair (2026-10-18, read-only survey of feat/gm-sites-world-wealth)

Legend: ME=common/scripted_effects/gm_monument_effects.txt, MT=common/scripted_triggers/gm_monument_triggers.txt, MV=common/script_values/gm_monument_values.txt, GV=common/script_values/gm_values.txt, E=common/scripted_effects/gm_effects.txt, TE=common/scripted_effects/gm_trophy_effects.txt, EV=events/monument_events.txt, REG=test_grand_monument_registry.py

Building-level readers: gm_state_level (GV:114), gm_state_primary_levels (MV:39), gm_state_unexplained_levels (MV:243), gm_state_levels_short (MV:270), gm_state_shadow_levels (MV:229); snapshot gm_state_split_short (MV:289). Records-only: gm_mon_levels (MV:14), gm_state_secondary_levels (MV:24).

## 1. Shadows and merges (#936)
- gm_shadow_monthly ME:1273 — drops shadows of regions with no owned state; orphan region → .31; drops stale (split exemption 1322-1323); writes shadow for every gm_seen state with a building. REWRITE: drop split exemption; add site shadows.
- gm_state_write_shadow ME:1342 — create/refresh: links, gm_tr_levels, dedication, 24 records via gm_sh_mirror, gm_sh_short/_passes, piece/split mirrors (1432-1433); gated dedicated + no gm_restore_pm/gm_ceremony_pending/gm_rebuilding. REWRITE: levels from records + starting-grandeur record; drop short notes, piece mirrors, gm_rebuilding gate; dedicated-only gate blocks site shadows.
- gm_sh_mirror ME:1445, gm_sh_drop ME:1459, gm_state_drop_shadow ME:1477 — KEEP.
- gm_state_adopt_orphans ME:1492 — waits a day while a building in region has gm_rebuilding (1497, 1530); repairs places of secondaries; gm_monument_pass; gm_sh_settle_region. REWRITE: drop rebuild waits.
- gm_sh_settle_region ME:1542 — landmark orphans first; try_raise then settle_one. REWRITE.
- gm_sh_try_raise ME:1585 — raises onto region's unrecorded building with most unexplained levels. REWRITE: unrecorded finished building, or state with no primary.
- gm_sh_settle_one ME:1617 — piece_home → whole_of_piece → beside (by unexplained) → was_split/rejoin → lost; skips while rebuilding. REWRITE: only "beside, or primary if none".
- gm_sh_adopt_beside ME:1686 — retag gm_monument, list moves, state/owner lists, caps gm_tr_levels at gm_sh_room, strips piece notes, .20, merge self-check. REWRITE: no cap; put surviving finished building back to level 1.
- gm_state_raise_orphan ME:1735 — adopt_beside + gm_state_raise_secondary (calls gm_clear_state) + restore dedication + write shadow. KEEP shape (one of two pinned shadow writers).
- gm_sh_lost ME:1747 — log, self-check, drop. REWRITE or GO.
- gm_sh_log_numbers ME:1848 — REWRITE.
- gm_mon_repair_origin ME:1873 — re-homes a secondary whose state is gone, by unexplained levels. REWRITE: gm_tr_repair_places' most-populous rule, or the state with a recorded monument.
- gm_monument_merge_self_check (monument_merge_kept) ME:2304 — REWRITE: what the engine does with two level-1 buildings / two sites.
- gm_sh_is_orphan MT:569, gm_sh_orphan_of MT:577 — KEEP.
- gm_state_merge_pending MT:589 — REWRITE: no gm_seen, or a finished building above level 1.
- gm_state_unrecorded MT:617 — KEEP (comment ref monument_triggers.txt:154).
- gm_state_takes_orphan_beside MT:628 — REWRITE: any recorded primary.
- gm_state_was_split MT:638, gm_state_levels_readable MT:648 — GO.
- gm_state_shadow_levels / unexplained_levels / levels_short / split_short MV:229/243/270/289 — GO.
- gm_sh_log_levels/found/buildings MV:310/318/326 — found GO, others keep if used; gm_sh_log_piece/lacked/lacking/put_back MV:337-367 GO.
- monument_events.31 EV:1689 — KEEP. gm_state_level GV:114 — KEEP.

## 2. Split pieces — all GO (spec §3.7)
gm_state_split_pending MT:668; gm_state_split_whole MT:689 (revolutionary/secessionist + civil_war_origin_country check at MT:699-717 is the part worth salvaging for "rebels' part gets nothing"; Paris Commune fallback gm_sh_short_passes relies on a shortfall); gm_state_take_split_identity ME:1929; gm_state_forget_split ME:2027; gm_state_forget_split_notes ME:2061; gm_state_split_piece_home ME:2074; gm_sh_rejoin ME:1771; gm_state_piece_takes_whole ME:2128; gm_sh_piece_takes_whole ME:2161; gm_state_piece_whole_gone MT:726 / split_piece_gone MT:747 / whole_merged_into_piece MT:766; piece_whole_abroad MT:782 / split_piece_abroad MT:792 / gm_sh_piece_home MT:806 / gm_sh_whole_of_piece MT:818; self-checks ME:2333 (monument_split_rejoined), ME:2360 (gate), ME:2378 (monument_split_identity); log values MV:382/390/398; display GV:196 gm_disp_is_piece, GV:207 gm_disp_has_piece, MV:371 gm_state_disp_split_levels, gm_custom_loc.txt:3066-3096 (gm_piece_where, gm_split_where); loc te_miscellaneous_l_english.yml:3556-3557, 3591-3594, 3796-3797; GUI te_state_panel_widgets.gui:672-693, grand_monuments_widget.gui:1390-1399.
gm_repair_after_civil_war E:1412 — KEEP.

## 3. One-off repair — all GO (markers OLD-SAVE REPAIR (#936) at ME:2196, ME:2418, MT:827, MV:406)
gm_short_repair_monthly ME:2214; gm_state_short_repair ME:2263; gm_state_short_unexplained MT:836; gm_state_short_ready MT:861; self-check monument_short_repair ME:2423; log values MV:410-456. test_old_save_repairs.py docstring mentions a scheduled reminder for 2026-12-17 (may go stale).

## 4. Monthly pass + hooks
on_monthly_pulse → gm_monument_monthly_on_action → gm_monument_monthly (gm_monument_on_actions.txt:9-19). Order in gm_monument_monthly (ME:28): gm_sig_seed_monthly; (if secondaries) each gm_monuments container: gm_tr_repair_places (→ gm_mon_repair_origin), picture, signature backfill, first sight, ageing, stale orders → .30; gm_monument_pass; gm_short_repair_monthly (76, GO); gm_shadow_monthly (82, pinned last).
Owner change: on_state_owner_change → gm_state_owner_change_on_action (needs building) → gm_state_changed_hands (monument_events_on_actions.txt:239-253; E:1340): adopts orphans when merge_pending (1343-1346); contest branch gated merge_pending=no and split_pending=no (1383-1384) — REWRITE.
Civil war won: te_civil_war_on_won (te_civil_war_on_actions.txt:124) → gm_repair_after_civil_war — KEEP.

## 5. Callers outside (what breaks on delete)
E:411-418 gm_clear_state (drop_shadow keep; forget_split + gm_split_rejected go); E:431 gm_state_monthly (split identity self-check go); E:491-521 gm_state_monthly no-building branch (whole_merged_into_piece → rewrite site for "put back at level 1"); E:744-765 gm_country_refresh (merge_pending → .29 rewrite; split/piece branches go; place for "remove records-less finished building in rebels' part"); E:1219 gm_check_contests (keep); E:1340 changed_hands; EV:67-90 .1 (merge_pending rewrite; piece_whole_gone go); EV:1644-1666 .29 (adopt rewrite; split branches go); EV:27-32 header; TE:271 gm_state_tr_remove_whole (keep); TE:956-964 gm_tr_repair_places (rewrite); monument_triggers.txt:327 gm_state_has_new_levels (goes); shared: ME:757 gm_state_raise_secondary, TE:624 gm_state_tr_take_records_from_moving, TE:560 gm_state_tr_add_levels (9 callers; rejoin/piece/repair at ME:1838, 2188, 2290; other 6 retired by §3.3).
gm_rebuilding dependencies here: ME:1350, 1497, 1530, 1622; MT:736, 863.
Docs pinned by tests: ageing-playtest.md must keep (or tests drop) "monument_merge_kept", "monument_split_rejoined", "Mughal", "monument_split_identity", "A revolt that wins", "A secession that wins", "monument_short_repair", "A piece's card and row"; mod_systems.md must keep "gm_shadow"; scripting_best_practices.md:769 (revolt split engine fact) keep.

## 6. Tests
MergeShadowTests REG:5008 (SHADOW_EFFECTS tuple 5016; test_the_shadow_is_written_only_by_the_pass_and_a_raise — exactly two writers; CONTAINER_RECORDS REG:4449 also used by FreezeTests, SwapTests, SignatureRecordTests; test_adoption_comes_before_founding_beside pins exact refresh string incl. split branch; ...). SplitPieceTests REG:5409, SplitPieceLineTests REG:5660, ShortRepairTests REG:5739 — go. LandmarkReviewFixTests.test_demolition_ends_a_landmark_without_records (~REG:3905) pins gm_state_monthly else-block incl. whole_merged_into_piece. Keep-pinned hook bodies: ContestTests (changed_hands, civil_war_winner_adopts, monthly_check), ReviewFixTests.test_a_cession_clears_the_commission_mark, TypedNameTests.test_a_naming_is_never_orphaned, MultiMonumentDataTests (3 on gm_monument_monthly), ReviewFixes20261016Tests.test_a_change_of_owner_lists_the_secondaries_again, AgeingTests.test_secondaries_age_in_the_pass_and_trophies_never, SecondaryFitTests.test_first_sight, SecondaryContestTests (2), FinalReviewFixTests.test_a_stale_order_is_run_again, SignatureRecordTests.test_the_backfill_and_its_callers, SignatureSpecialTests.test_old_saves; test_grand_monument_trophies.py RouteTests.test_the_former_owner_is_stamped, AlsoStandingHereTests.test_a_secondarys_picture_catches_up_each_month.

## 7. Surprises
1. REG:5846 has `if __name__ == "__main__": unittest.main()` mid-file: `python3 test_grand_monument_registry.py` silently skips SignatureTableTests..DedicateButtonTests. Use `python -m unittest test_grand_monument_registry`.
2. Merge settle targets are almost all chosen by unexplained-levels ordering; only plumbing survives.
3. gm_sh_lost loses meaning with records only.
4. Salvage MT:699-717 revolutionary/secessionist + civil_war_origin_country for "rebels' part gets nothing"; Paris Commune (vanilla-event country) needs another signal.
5. take_split_identity and raise_orphan both go through gm_clear_state; removing forget_split from gm_clear_state only together with split code.
6. test_old_save_repairs.py reminder for 2026-12-17.
7. Shadows skip undedicated primaries / ceremony pending — now must shadow sites too.
