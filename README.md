# Vic3TimelineExtended
Mod for Victoria 3 extending timeline

## Game Rules

The following mod systems can be toggled via game rules at game setup:

### Banking System (Default: Enabled)
Controls the banking cycle journal entry and financial regulation system. When enabled, financial regulation laws provide banking intervention tools, momentum effects, and crash chance modifiers that drive the banking cycle. When disabled, the journal entry does not appear, but financial regulation laws still provide standard economic effects (construction cost reductions, infrastructure bonuses, and other non-banking modifiers).

### Global Warming (Default: Enabled)
Controls the global warming journal entry and greenhouse gas tracking system. When enabled, greenhouse gas emissions are tracked globally and climate policies affect temperature rise. When disabled, the journal entry does not appear and emissions tracking is inactive, but environmental policies and events still provide pollution reduction effects as an alternative to greenhouse gas effects.

### World War (Default: Disabled)
Controls the world war journal entry for great powers. When enabled, ideological tensions between great powers can escalate into a global conflict with leadup, active war, and post-war phases. When disabled, the journal entry does not appear and world war events will not fire. World war buttons use direct technology checks (Combined Arms, Mass Media) rather than boolean modifier types.

## Credits

The construction-market subsystem (files prefixed `te_construction_market_*` in `common/` and `events/`, plus the integration in `gui/construction_panel.gui`) was originally based on the third-party **Free Market Construction** mod and has since been substantially rewritten — the price stabilizer, AI buy-target heuristic with bankruptcy-avoidance brake, public/private split via per-building modifier multiplier, geopolitical recalc hooks, and the broader market-driven allocation framing all evolved well past the original. Credit and thanks to that mod's author for the foundation. Identifiers, file layout, and event-namespace shape have been redone to fit this codebase's conventions.
