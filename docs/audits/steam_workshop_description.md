# Steam Workshop description (draft)

Paste the contents of the fenced block below into the Steam Workshop description field. Steam Workshop renders BBCode, not Markdown.

## Images to add

When you have screenshots ready, paste `[img]<steam-hosted-url>[/img]` at these locations in the BBCode block below:

1. **Hero image** — between the tagline italic and the `[hr]` above "At a glance". Strongest candidates: Saturn V / lunar landing, a flooded-coastline or wildfire climate scene, or a UN founding scene. Pick whichever best matches the timeline framing.
2. **Banking Cycle JE** — after the Banking Cycle bullet. Mid-cycle screenshot with the phase indicator on a non-stable phase (Boom or Downturn) and the policy buttons + progress bar in frame.
3. **Space Race JE** — after the Space Race bullet. Milestone progress and the contested-site map; mid-game with a couple of milestones already claimed by other countries reads more dramatic than an empty start.
4. **UN panel** — after the United Nations bullet. Authority bar, Security Council seats, and ideally an active vote / resolution. Bonus if a specialized agency tab is visible.
5. **Civil Rights JE** — after the Social Movements bullet. Support progress bar plus the pro/anti/coopt policy button grid. Alternative: an event image from a movement event chain (feminist / LGBTQ+ / environmental).
6. **Laws panel** — under the "Laws and ideologies" header. Filtered to a uniquely-modern lawgroup (cryptocurrency / surveillance / AI governance / post-scarcity) so the visible options are obviously not vanilla. Alternative: a single-law detail view for a flagship law like UBI or Mass Surveillance.

```bbcode
[h1]Vic3TimelineExtended[/h1]

[i]A large content mod for Victoria 3 that pushes the timeline past 1936 into the 20th century, the modern era, and a speculative near-future. Banking cycles, climate change, the space race, the UN, decolonization — playable, opt-in, woven into the existing economy.[/i]

[hr][/hr]

[h1]At a glance[/h1]
[list]
[*]161 new technologies across 7 new eras, interwar through far-future
[*]13 new goods plus PM chains
[*]~280 company-unique flavor buildings, plus ~40 wonders and megastructures
[*]100+ new laws across the timeline — from monetary and family-policy early; financial regulation and rights ladders mid-game; to surveillance, AI, post-scarcity late
[*]New combat units, mobilization options, ship classes, treaty articles, decrees, and companies
[*]Hundreds of events; ~15,000 lines of new English localization with concept tooltips and breakdowns
[*]13 toggleable game rules to mix-and-match the major systems
[/list]

[hr][/hr]

[h1]New systems[/h1]

[h2]The big systems[/h2]

[b]Banking Cycle[/b] — A boom-and-bust cycle with speculative bubbles, trade-route contagion, and policy levers fitted to your economy type. Time your spree to the boom; don't let frenzy tip into panic.

[b]Space Race[/b] — Eight competitive milestones from suborbital flight to solar-system colonization. Pick safe or ambitious approaches. Plant the first flag on Mars and the world-first bonus is permanent — or watch a rival do it.

[b]Global Warming[/b] — Track emissions and rising temperatures; events and scaling penalties land as climate degrades. Policy toggles (carbon tax, renewables, adaptation) slow warming or help you adapt, and a treaty article can bind rivals to emissions reductions.

[b]United Nations[/b] — Found or join the UN: an authority bar, Security Council vetoes, specialized agencies (UNESCO, IAEA, WHO), and 16 vote topics. Sanctions, peacekeeping, and non-proliferation become real diplomatic tools.

[b]Nuclear Weapons[/b] — Race to the bomb, build a stockpile, and use it — or pursue disarmament. Strikes deal real damage but bring infamy and risk retaliation; world-first grants permanent prestige; treaties can pause programs.

[b]Decolonization[/b] — Colonies hold a stability bar shaped by investment, garrisons, assimilation, or planned release. Stage a managed handover that preserves your assets, or solidify your hold and keep the empire.

[b]Covert Warfare[/b] — Cyber and espionage operations: election interference, financial subversion, infrastructure sabotage, communications disruption. Manage operation slots, funding, and detection risk.

[b]Cultural Hegemony[/b] — A global cultural share built from prestige, art, tech leadership, and monuments — Hollywood-style soft power that pulls migration, fuels tourism, and bends rivals' ideologies.

[b]Modern Military[/b] — Mix unit types in your formations to earn combined-arms bonuses, with new aviation, missile, and drone formations plus modern ship classes extending the vanilla roster forward.

[b]Social Movements[/b] — Civil rights, feminism, LGBTQ+, environmentalism, secularization, augmentation, digital rights, and the post-scarcity transition — event chains for all of them, with journal entries for the most impactful.

[b]Free Market Construction[/b] — A construction industry produces a construction good at a market-set price; your government picks how much to buy each month. Based on TOGFan's mod (credited below).

[h2]Smaller systems[/h2]

[b]Tourism[/b] — Turn Hawaii or the French Riviera into a global destination. Pollution, turmoil, infrastructure, and air-travel capacity gate how much demand you can capture; coal-fired industrial states are a hard sell to vacationers.

[b]Strategic Reserves[/b] — Stockpile oil, grain, military equipment, and ammunition in dedicated hubs while supplies are cheap. When war hits or embargoes land, the reserve drains into your market rather than letting prices spike.

[b]Migration crowding[/b] — Dense states (population vs. arable land) attract fewer migrants, capping how concentrated populations get naturally. The Ministry of Urban Planning stretches the tolerance so big cities keep absorbing arrivals.

[b]Dynamic homelands[/b] — Homelands aren't fixed by history. As cultural acceptance and population shift, homelands form or dissolve to match — diaspora communities can establish new ones, minorities can lose them.

[b]Standard-of-living expectations[/b] — Pops remember the last good year. A long boom raises the bar they measure against, so a dip after sustained prosperity hurts more than the same dip from baseline.

[b]Power bloc principles[/b] — Extra principles and identities, with naming variants tied to member composition.

[h2]Tech and the era expansion[/h2]

161 new technologies across 7 new eras, the spine of the timeline extension:
[list]
[*]6 (1919–45): aviation, atomics, propaganda, plastics
[*]7 (1946–67): jets, early computing, satellites, antibiotics
[*]8 (1968–87): microchips, environmental science, telecoms
[*]9 (1988–2012): internet, mobile, biotech, global supply chains
[*]10 (today): AI, surveillance, climate adaptation, social media
[*]11 (near future): fusion, gene editing, advanced AI, brain-computer interfaces
[*]12 (far future): antimatter, post-scarcity, space colonization, transhumanism
[/list]

Endgame megastructures include space elevators, orbital solar collectors, and antimatter facilities.

[h2]Personal play opt-ins[/h2]

Heir Education, Custom Religion (player-defined tenets, taboos, and governance), universal aptitude traits, and a World War system. Opt-in to taste.

[hr][/hr]

[h1]Laws and ideologies[/h1]

The law tree spans the full timeline. A small sample: the 19th century gives access to new inheritance, state power, and minority rights. Mid-game adds financial regulation, LGBTQ+ rights ladders, and family and reproductive policy. Late-game handles internet governance, genetic modification, and UBI. New ministries — science, environment, intelligence, urban planning, and more — each pull government in a different direction; build your preferred society.

The ideology system is expanded to support these laws, with new factions (environmentalists, anti-colonialists, transhumanists, business-interest movements) plus three modern parties: Green, Populist, Technocratic.

[hr][/hr]

[h1]Compatibility[/h1]

Vanilla ideologies, ~60 vanilla PMs, state-region map data, and 20 vanilla GUI panels are overridden — avoid pairing with other mods that touch those. Otherwise the mod uses INJECT to extend rather than replace vanilla content, so most non-overlapping mods coexist. Load this mod [b]last[/b].

[hr][/hr]

[h1]Feedback and AI-generated content[/h1]

Bugs and strange interactions are likely in a mod this size. Detailed reports — what you did, what you expected, what happened, with [i]error.log[/i] / [i]debug.log[/i] snippets and a save — help most. Concept tooltips and breakdowns are wired throughout; if a mechanic feels under-explained, that's also useful feedback. Post on the Workshop page or the [url=https://github.com/jakeOmega/Vic3TimelineExtended/issues]issue tracker[/url].

The mod contains AI-generated event images and some AI flavor text. To replace AI content with hand-written text or hand-drawn art, open an issue or PR on the [url=https://github.com/jakeOmega/Vic3TimelineExtended]GitHub repo[/url].

[hr][/hr]

[h1]Links and credits[/h1]
[list]
[*][url=https://github.com/jakeOmega/Vic3TimelineExtended]Source repository[/url]
[*][url=https://steamcommunity.com/sharedfiles/filedetails/?id=3257202613]Free Market Construction[/url] by [b]TOGFan[/b] — basis for the construction-market subsystem; recommended on its own if you want just that mechanic.
[/list]
```
