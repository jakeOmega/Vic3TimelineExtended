# Steam Workshop description (draft)

Paste the contents of the fenced block below into the Steam Workshop description field. Steam Workshop renders BBCode, not Markdown.

Inline `[i]>>> TODO image — ...[/i]` lines flag where to drop screenshots or event-image renders before publishing. Replace each with `[img]<steam-hosted-url>[/img]` (or delete if the slot isn't worth filling). All suggestions stick to two image types — actual mechanic screenshots and event illustrations — so the page reads as "real game" rather than concept art.

```bbcode
[h1]Vic3TimelineExtended[/h1]

[i]A large content mod for Victoria 3 that pushes the timeline past 1936 into the 20th century, the modern era, and a speculative near-future. Banking cycles, climate change, the space race, the United Nations, decolonization, post-scarcity politics — playable, opt-in, and woven into the existing economy.[/i]

[i]The arc runs from gilded-age industry into a late-21st-century crossroads: post-scarcity abundance on one branch, a 4 °C climate brink on the other, and most playthroughs landing somewhere between.[/i]

[i]>>> TODO image — Hero event-image render that captures the modern/future sweep. Strongest candidates: a Saturn V / lunar-landing space-race image, a flooded-coastline or wildfire climate image, or a UN-founding scene. Pick whichever best matches the timeline framing in the italic above.[/i]

[hr][/hr]

[h1]At a glance[/h1]
[list]
[*]161 new technologies across 7 new eras (eras 6–12), reaching toward the 22nd century
[*]13 new goods (consumer electronics, robotics, advanced materials, launch capacity, tourism, and others) plus the production-method chains to make and consume them
[*]Around 40 new wonders and megastructures, plus new system-specific buildings (strategic reserve hubs, resettlement camps, free-market construction sites, state youth centers, military bases) and roughly 280 company-unique flavor buildings tied to new companies and charters
[*]Many vanilla buildings gain new production methods that consume and produce the new goods, so the existing economy plugs into the new content rather than running parallel to it
[*]100+ new laws across post-scarcity, surveillance, monetary systems, AI governance, climate policy, genetic modification, criminal justice, and direct democracy
[*]27 new treaty articles, 14 new decrees, 9 new formable countries
[*]Hundreds of new events and roughly 15,000 lines of new English localization
[*]13 toggleable game rules so you can mix-and-match the major systems
[/list]

[hr][/hr]

[h1]New systems[/h1]

[b]Free Market Construction[/b] — Construction sectors no longer produce country construction points directly. They output a [i]construction[/i] good that auto-placed construction sites consume to do the actual building, so states bid on construction the way they bid on any other good. Construction cost scales with GDP per capita, so wealthy nations pay more and poorer nations can catch up rather than being permanently priced out. Based on TOGFan's Free Market Construction mod (credited below); extended here and integrated with the rest of the mod's systems.

[b]Banking Cycle[/b] — A seven-phase boom/bust cycle: [b]panic → downturn → stagnation → stable → expansion → boom → frenzy[/b]. Speculative bubbles, contagion through trade and adjacency, and policy levers tailored to your economy type — central-bank tools for market economies, planning tools for command economies, council directives for cooperatives.

[i]>>> TODO image — Mechanic screenshot of the Banking Cycle journal entry mid-cycle: phase indicator visible (ideally on a non-stable phase like Boom or Downturn), with the policy buttons and progress bar in frame. The phase chain in the bullet above pays off if a player can see one phase rendered in-game.[/i]

[b]Global Warming[/b] — Global emissions and temperature are tracked against a 4°C threshold. Temperature tiers trigger climate events and scaling penalties. Eight policy toggles (carbon tax, renewable investment, adaptation, emission standards, reforestation, public transit, divestment, green building codes) let you slow warming or adapt to it.

[b]Space Race[/b] — Eight competitive milestones from suborbital flight to solar-system colonization, with 34 globally contested colony sites across five stages. Choose safe (slow, low failure) or ambitious (fast, costly setbacks) approaches. World-first bonuses are permanent. Ties into the UN, private companies, tourism, and several wonder buildings.

[i]>>> TODO image — Mechanic screenshot of the Space Race JE showing milestone progress and the contested-site map (a mid-game shot with a couple of milestones claimed by other countries reads more dramatic than an empty starting state). Alternative: an event image from a launch / landing event if no clean JE shot is available.[/i]

[b]United Nations[/b] — Found or join an IGO with an authority bar, Security Council vetoes, specialized agencies (UNESCO, IAEA, WHO, etc.), and 16 vote topics. Sanctions, peacekeeping, humanitarian aid, and non-proliferation become real diplomatic tools.

[i]>>> TODO image — Mechanic screenshot of the UN panel: authority bar, Security Council seats, and ideally an active vote / resolution in progress so the IGO reads as load-bearing rather than cosmetic. Bonus if a specialized agency tab is visible.[/i]

[b]Cultural Hegemony[/b] — A 0–100% global cultural share derived from prestige, art production, living standards, tech leadership, and monuments. Hegemony pressures rivals' ideologies and pulls migration — soft power as a first-class lever.

[b]Covert Warfare[/b] — Cyber and espionage operations: election interference, financial subversion, infrastructure sabotage, communications disruption. Manage operation slots, funding levels, and detection risk; defend with digital sovereignty.

[b]Nuclear Weapons[/b] — Race to build the bomb or pursue disarmament. World-first grants permanent prestige and innovation. Treaties can pause programs; deterrence is modeled diplomatically.

[b]Decolonization[/b] — Overseas colonies maintain a stability bar; investment, military presence, cultural assimilation, or planned release determine outcomes. Independence triggers an optional nationalization choice for foreign assets.

[b]Social Movements[/b] — Civil rights, second-wave feminism, LGBTQ+ struggle, environmentalism, secularization, mental-health awareness, human augmentation, digital rights, and the post-scarcity transition are all modeled — most through event chains, with journal entries for the ones that warrant a tracked mechanic.

[i]>>> TODO image — Mechanic screenshot of the Civil Rights JE showing the support progress bar plus the pro/anti/coopt policy buttons. The button grid is one of the more visually distinctive UI surfaces in the mod. Alternative: an event image from one of the movement event chains (feminist / LGBTQ+ / environmental).[/i]

[b]Opt-in extras[/b] — Heir education (shape a successor over 15 years), custom religion (build your own religion via a wizard), world war (ideological-tension escalation, off by default), and universal aptitude traits.

[b]Quieter mechanical layers[/b] — Tourism (state-scoped tourism economy), migration crowding (density penalties on overcrowded states), strategic reserves (stockpile critical goods in a hub building), standard-of-living expectations lag (people remember the last good year), and intelligence-sharing defense bonuses.

[hr][/hr]

[h1]Laws and ideologies[/h1]

[i]>>> TODO image — Mechanic screenshot of the laws panel filtered to a uniquely-modern lawgroup (cryptocurrency / surveillance / AI governance / post-scarcity) so the visible options are obviously not vanilla. Alternative: a single-law detail view for a flagship law like Universal Basic Income or Mass Surveillance.[/i]

The law tree extends well past vanilla's late-game into speculative governance: post-scarcity policy (augmentation, intellectual property, inheritance), surveillance vs. privacy, monetary systems (commodity, fiat, cryptocurrency), AI governance, climate policy, genetic modification, criminal justice models, language policy, and direct-democracy options.

The ideology system is rebuilt to support these laws, with new factions like environmentalists, anti-colonialists, optimist transhumanists, corporates, and a full custom-religion family covering economic and governance axes.

[hr][/hr]

[h1]Compatibility[/h1]

[b]Heavy override — avoid pairing with these mod types:[/b]
[list]
[*]All vanilla ideologies are replaced — incompatible with other ideology overhauls
[*]Around 60 vanilla production methods are replaced — incompatible with other PM overhauls
[*]20 vanilla GUI panels are modified (states, building browser, production methods, military, treaties, market, politics, power blocs, tooltip, right-click menu) — last-loading wins, so pair carefully with other UI mods
[*]All state-region map data is overridden — incompatible with map mods
[/list]

[b]Light override — generally safe:[/b] the mod uses Vic3's INJECT directive throughout to extend (rather than replace) vanilla pop needs, principles, modifiers, and on-actions. Most content mods that don't touch the same vanilla files should coexist without issue, though INJECTs can produce odd interactions if another mod changes the underlying mechanical assumptions.

[b]Recommended load order:[/b] load this mod [b]last[/b] so its GUIs and ideology system win.

[hr][/hr]

[h1]A note on AI-generated content[/h1]

This mod contains AI-generated event images and some AI-generated flavor text. If that's a deal-breaker, please skip — no hard feelings. If you'd like to [b]replace AI-generated content with hand-written text or hand-drawn art[/b], contributions are very welcome. Open an issue or PR on the repo and your work can land directly in the mod.

[hr][/hr]

[h1]Bugs and feedback[/h1]

This mod is large and has many systems interacting at once. Bugs, balance issues, and strange interactions are very likely. [b]Detailed bug reports[/b] — what you did, what you expected, what happened, ideally with a snippet from your [i]error.log[/i] or [i]debug.log[/i] and a save file — are enormously useful. Vague reports are still better than none, so don't let "I can't pin it down" stop you from posting.

[hr][/hr]

[h1]Credits[/h1]

[list]
[*][url=https://steamcommunity.com/sharedfiles/filedetails/?id=3257202613]Free Market Construction[/url] by [b]TOGFan[/b] — basis and inspiration for this mod's construction-market subsystem. Highly recommended on its own if you'd like just that mechanic without the rest of the timeline extension.
[/list]
```
