# Local Climate

Part of the [mod systems reference](../mod_systems.md), which indexes every system.

Spec: `docs/superpowers/specs/2026-11-01-local-climate-design.md`; plan: `docs/superpowers/plans/2026-11-01-local-climate.md`.

## The Climate Record

- **What:** each land state region's climate where most of its people live, six figures per region. Every piece of a split region reads the region's record, since the values are keyed on `state_region`.
- **Fields** (`scripts/generators/data/local_climate.csv`; the generated values in brackets):
  - `summer_mean_c` (`te_climate_summer_mean`): the warmest month's mean temperature, °C.
  - `summer_humidity` (`te_climate_summer_humidity`): that month's dew point as a class, 0 dry (under 10 °C), 1 moderate (10–16), 2 humid (16–20), 3 oppressive (over 20).
  - `winter_mean_c` (`te_climate_winter_mean`): the coldest month's mean, °C.
  - `aridity` (`te_climate_aridity`): water for settlement, 0 ample, 1 limited (Köppen BS), 2 scarce (Köppen BW). A great river whose valley holds the main settled area counts as ample, so the Nile valley is 0; a desert whose settled area a lesser river or a large oasis waters is 1 (Lima, Isfahan); a desert of small oases and wells is 2 (Ghardaia). Ruled 2026-11-01 when the eight agents' rows were merged.
  - `malaria` (`te_climate_malaria`): malaria as of 1836, from history rather than vanilla's traits. 0 none, 1 seasonal or local, 2 endemic. Local ague in a region's lowland counts as 1 (the Sologne, the unregulated Rhine plain, the Mälaren basin), as do the Hungarian plain and the Yangtze lowland's vivax.
  - `latitude` (`te_climate_latitude`): signed degrees of the reference place.
  - `ref_place` and `reason`: the place the figures describe and a short note on the climate. CSV only, never shown in game.
- **Neutral defaults:** a region with no row (one a vanilla patch adds) reads summer 15, winter 15 and zero for the rest, which costs no comfort, and `te_climate_has_record` is 0.
- **Generator:** `scripts/generators/gen_local_climate.py` writes `common/script_values/local_climate_generated.txt` (one if-chain on `state_region` per field). `--check` exits 1 when the committed file is stale; `--plausibility` lists rows worth a second look (a warm winter at a high latitude, a cool tropical highland, oppressive humidity with scarce water). Re-run after editing the CSV.
- **Checks** (`test_local_climate.py`): every land region of the mod's `map_data/state_regions/` (not `99_seas.txt`) has exactly one row, in map order; values in range (summer −10…45, winter −50…30, winter ≤ summer); vanilla's `state_trait_malaria` needs malaria ≥ 1 and `state_trait_severe_malaria` needs 2; a `state_trait_*_desert` needs aridity ≥ 1. Perth and Adelaide sit in desert-trait regions, so they get 1. Where vanilla's trait is plainly wrong, the mod takes it away rather than bend the record: Fiji and Tonga, which had no malaria, lose Severe Malaria through `state_trait_config.json`'s `-state_trait_x` entries.
- **Production:** the 2026-11-01 table was filled by eight subagents from climate normals for each region's main settled area, then validated and spot-checked. Fifteen anchor rows (Georgia, West Bengal, the Home Counties, Île-de-France, Catalonia, Lazio, Lower Andalusia, the Sahara, Arizona, Yakutsk, Massachusetts, Ohio, Florida, Middle Egypt, Moscow) are the calibration's fixed points.

## The Local Climate Tile

- **Where:** a `state_panel_status_item_small` in `gui/states_panel.gui` after Migration Crowding, always shown; its contents are the type `te_state_climate_tile` in `gui/te_state_panel_widgets.gui`.
- **Rows** (`te_state_climate_row`: 80 px of label, 76 of value, since "Humidity" and "Seasonal" overrun the standard tile rows): Summer (°C), Humidity (Dry, Moderate, Humid, Sultry), Winter (°C), Water (Ample, Limited, Scarce), Malaria (None, Seasonal, Endemic). The words come from nested `SelectLocalization` on the class. A region with no row shows `TE_STATE_CLIMATE_NO_DATA` instead.
- **Concept:** `concept_local_climate` ("Local Climate"). The name is never bare "Climate", which the global warming panels, the Market panel's Climate tab and the player guide's chapter 15 already use.
- **Placeholder art:** the tile and the concept use vanilla's `gfx/interface/icons/state_trait_icons/tropical_climate.dds`. The final icon should show a thermometer beside a sun and a snowflake, at `gfx/interface/icons/state_status_icons/local_climate.dds`.
- **Loc:** `TE_STATE_CLIMATE_*` and `te_state_climate_*` in `te_miscellaneous_l_english.yml`; the words are `TE_CLIMATE_HUMIDITY_0`–`3`, `TE_CLIMATE_WATER_0`–`2` and `TE_CLIMATE_MALARIA_0`–`2`.
- **Play-test list:** `docs/testing/local-climate-playtest.md`.
