# Production building icons: in-game checks

What the next play-test should look at in the production buildings' icons. In-game checks do not gate a merge (CLAUDE.md,
"In-game checks: self-checks and the play-test list"): each PR adds its own section, newest last, and a fixed item is
struck through with the commit that fixed it.

## Thirty-nine buildings in vanilla's look (2026-11-27)

A player found the mod's production building icons out of place beside vanilla's. The 39 buildings in
`icon_prompts.py`'s `production_building` category are now vanilla's two layers: a dark, close-up picture of the plant,
regraded to vanilla's measured colour and darkness, under the good's own goods icon in vanilla's place, or the mine's
ore. Five mod goods icons were repainted at an angle in muted colours to match (Industrial Robotics, Software, Consumer Appliances,
Electronic Components, Tourism).

| Check | How | Expected | If not |
|---|---|---|---|
| The set reads as one | The building browser's industry and mining tabs in a late game (or the construction list with the late technologies), mod buildings beside vanilla's at the panel's own size, about 70 px | No mod icon stands out brighter, flatter or busier than its vanilla neighbours; each good sits in the lower right where vanilla's do | One stands out: name it, and re-pick its backdrop (`seed` back to `None` in `icon_prompts.py`) |
| The mines tell apart | The mining tab with several of the fifteen mod mines listed | Each mine's ore is legible and distinct from its neighbours | Two merge: re-describe one ore with a stronger accent colour |
| The repainted goods | The market panel and a building's production method tooltip | The five goods read at goods-list size and sit with vanilla's | One is unclear at small size: re-pick from its candidates |
| Synthetic Clothes Industries' own icon | The building, in the construction list | Its own icon (silk over its plant), no longer the icon it shared with the other synthetics plants | It shows the old icon: the deployed copy is stale (`./scripts/deploy.sh --apply`) |
