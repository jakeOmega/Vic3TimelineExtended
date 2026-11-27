# Company icons: in-game checks

What the next play-test should look at in company icons. In-game checks do not gate a merge (CLAUDE.md, "In-game checks:
self-checks and the play-test list"): each PR adds its own section, newest last, and a fixed item is struck through with
the commit that fixed it.

## Four icons re-exported at 256×256 (#246)

`american_google`, `japanese_toyota`, `korean_samsung` and `russian_rosatom` (`gfx/interface/icons/company_icons/historical_company_icons/`)
were DXT5 textures of 250×256, 256×213, 256×134 and 256×255, which the engine warns about at load (`gfx_dds_loader.cpp:442`,
"Block compressed texture … does not have a height and width that are a multiple of 4") and which a square icon slot
stretched. Each is now its original pixels, unscaled, centered on a 256×256 transparent canvas, written uncompressed.

| Check | How | Expected | If not |
|---|---|---|---|
| The load warning is gone | After a launch, `python3 scripts/analysis/log_triage.py`, or grep `debug.log` for `historical_company_icons` | No `Block compressed texture` line for any of the four | A line still names one: the deployed copy is stale (`./scripts/deploy.sh --apply`) |
| They look right | A company's panel, and the list of companies to found, in a late game where a leading economy has founded or can found Google, Toyota, Samsung or Rosatom (each needs late technology and a high production rank) | Each logo at its true shape, centered, with no dark fringe; Samsung's banner reads as a flat oval, no longer stretched tall | An icon shows cropped or offset: the slot crops instead of scaling, so pad to the slot's shape instead |
