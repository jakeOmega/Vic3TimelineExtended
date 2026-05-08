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

[i]A large content mod for Victoria 3 that pushes the timeline past 1936 into the 20th century, the modern era, and a speculative near-future. Banking cycles, climate change, the space race, the United Nations, decolonization — playable, opt-in, and woven into the existing economy.[/i]

[hr][/hr]

[h1]At a glance[/h1]
[list]
[*]161 new technologies across 7 new eras (eras 6–12), interwar through far-future
[*]13 new goods plus production-method chains; many vanilla buildings get new PMs that consume and produce them
[*]~40 new wonders and megastructures, plus ~280 company-unique flavor buildings
[*]100+ new laws spanning the timeline, from 1850s monetary/criminal-justice/ministry laws to late-game surveillance, AI, and post-scarcity branches
[*]27 new treaty articles, 14 decrees, 9 new formable countries
[*]Hundreds of new events; ~15,000 lines of new English localization
[*]13 toggleable game rules so you can mix-and-match the major systems
[/list]

[hr][/hr]

[h1]New systems[/h1]

[h2]The big systems[/h2]

[b]Banking Cycle[/b] — A seven-phase cycle: [b]panic → downturn → stagnation → stable → expansion → boom → frenzy[/b]. Speculative bubbles, contagion through trade, and policy levers fitted to your economy type. Time your construction spree to ride a Boom; don't tip Frenzy into Panic with debt on the books.

[b]Space Race[/b] — Eight competitive milestones from suborbital flight to solar-system colonization, with 34 globally contested colony sites. Pick safe (slow, low failure) or ambitious (fast, costly setbacks). Plant the first flag on Mars and the world-first bonus is permanent — or watch a rival do it.

[b]Global Warming[/b] — Track emissions and rising temperatures across six tiers, each triggering climate events and scaling penalties. Eight policy toggles — carbon tax, renewables, adaptation, transit, divestment, and more — let you slow warming or live with it.

[b]United Nations[/b] — Found or join the UN: an authority bar, Security Council vetoes, specialized agencies (UNESCO, IAEA, WHO), and 16 vote topics. Sanctions, peacekeeping, and non-proliferation become real diplomatic tools.

[b]Nuclear Weapons[/b] — Race to the bomb or pursue disarmament. World-first grants permanent prestige; treaties can pause programs; deterrence is modeled diplomatically.

[b]Decolonization[/b] — Colonies hold a stability bar shaped by investment, garrisons, assimilation, or planned release. Hold the empire together by force or stage a managed handover that preserves your foreign assets — independence is coming either way.

[b]Covert Warfare[/b] — Cyber and espionage operations: election interference, financial subversion, infrastructure sabotage, communications disruption. Manage operation slots, funding, and detection risk.

[b]Cultural Hegemony[/b] — A global cultural share built from prestige, art, tech leadership, and monuments — Hollywood-style soft power that pulls migration and bends rivals' ideologies.

[b]Modern Military[/b] — Mix unit types in your formations to earn combined-arms bonuses, with new aviation, missile, and drone formations plus modern ship classes extending the vanilla roster forward.

[b]Social Movements[/b] — Civil rights, feminism, LGBTQ+, environmentalism, secularization, augmentation, digital rights, and the post-scarcity transition — mostly event chains, with journal entries for the ones that warrant tracked mechanics.

[b]Free Market Construction[/b] — Construction sectors output a [i]construction[/i] good that auto-placed sites consume; states bid on it like any other good, and cost scales with GDP per capita so poorer nations can catch up. Based on TOGFan's mod (credited below).

[h2]Smaller systems with their own pull[/h2]

[b]Tourism[/b] — Turn Hawaii or the French Riviera into a global destination. Pollution, infrastructure, and air-travel capacity gate how much demand you can capture; a coal-fired industrial state is a hard sell to the world's vacationers.

[b]Strategic Reserves[/b] — Stockpile oil, grain, and critical materials in dedicated hubs while supplies are cheap. When the war hits or the embargo lands, the reserve drains into your market instead of letting prices spike.

[b]Migration crowding[/b] — Dense states (population vs. arable land) become less attractive to migrants, capping how concentrated populations get naturally. The Ministry of Urban Planning stretches the tolerance so big cities keep absorbing arrivals.

[b]Dynamic homelands[/b] — Homelands aren't fixed by the scenario. As cultural acceptance and population shift, homelands form or dissolve to match — diaspora communities can establish new ones, minorities can lose them.

[b]Standard-of-living expectations[/b] — Pops remember the last good year. A long boom raises the bar they measure against, so a dip after sustained prosperity hurts more than the same dip from baseline.

[b]Power bloc principles[/b] — Extra principles and identities for player-led blocs, with naming variants tied to member composition.

[h2]Tech and megastructures[/h2]

161 new techs span interwar aviation, atomic power, postwar electronics and rocketry, computers, the internet, biotech, AI, fusion, and antimatter. End-game megastructures include space elevators, orbital solar collectors, fusion plants, antimatter facilities, and lunar / Martian / asteroid resettlement colonies.

[h2]Personal play opt-ins[/h2]

Heir Education (15-year successor shaping), Custom Religion (build-your-own wizard), universal aptitude traits, and an off-by-default World War system for 1914- or 1939-style endgames.

[hr][/hr]

[h1]Laws and ideologies[/h1]

The law tree spans the full timeline. From an 1850s start you already get new monetary systems, criminal-justice models, IP regimes, inheritance, family policy, and a new ministry layer. Mid-game adds financial regulation, expanded minority and LGBTQ+ rights ladders, antitrust regimes, and updated rules of war. Late-game and speculative branches handle privacy vs. surveillance, internet governance, AI policy, cryptocurrency, genetic modification, UBI, and direct democracy.

The ideology system is rebuilt to support these laws, with new factions like environmentalists, anti-colonialists, optimist transhumanists, corporates, a custom-religion family, and three new modern parties (Green, Populist, Technocratic).

[hr][/hr]

[h1]Compatibility[/h1]

[b]Heavy override — avoid pairing with:[/b] ideology overhauls (vanilla ideologies replaced), PM overhauls (~60 PMs replaced), map mods (state-regions overridden), UI mods touching the same 20 panels (last-loading wins).

[b]Light override:[/b] uses Vic3's INJECT directive to extend rather than replace vanilla pop needs, principles, modifiers, and on-actions, so most non-overlapping content mods coexist. Load this mod [b]last[/b].

[hr][/hr]

[h1]AI-generated content[/h1]

This mod contains AI-generated event images and some AI-generated flavor text. To replace AI content with hand-written text or hand-drawn art, open an issue or PR on the [url=https://github.com/jakeOmega/Vic3TimelineExtended]GitHub repo[/url].

[hr][/hr]

[h1]Bugs and feedback[/h1]

Bugs and strange interactions are likely in a mod this size. Detailed reports — what you did, what you expected, what happened, with [i]error.log[/i] / [i]debug.log[/i] snippets and a save — help most. Post on the Workshop page or the [url=https://github.com/jakeOmega/Vic3TimelineExtended/issues]issue tracker[/url].

[hr][/hr]

[h1]Links and credits[/h1]
[list]
[*][url=https://github.com/jakeOmega/Vic3TimelineExtended]Source repository[/url] · [url=https://github.com/jakeOmega/Vic3TimelineExtended/issues]Issue tracker[/url]
[*][url=https://steamcommunity.com/sharedfiles/filedetails/?id=3257202613]Free Market Construction[/url] by [b]TOGFan[/b] — basis for the construction-market subsystem; recommended on its own if you want just that mechanic.
[/list]
```
