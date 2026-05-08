# Steam Workshop description (draft)

Paste the contents of the fenced block below into the Steam Workshop description field. Steam Workshop renders BBCode, not Markdown.

Inline `[i]>>> TODO image — ...[/i]` lines flag where to drop screenshots before publishing. Replace each with `[img]<steam-hosted-url>[/img]` (or delete if the slot isn't worth filling).

```bbcode
[h1]Vic3TimelineExtended[/h1]

[i]A large content mod for Victoria 3 that pushes the timeline past 1936 into the 20th century, the modern era, and a speculative near-future. Banking cycles, climate change, the space race, the United Nations, decolonization — playable, opt-in, and woven into the existing economy.[/i]

[i]>>> TODO hero image[/i]

[hr][/hr]

[h1]At a glance[/h1]
[list]
[*]161 new technologies across 7 new eras (eras 6–12)
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

[b]Free Market Construction[/b] — Construction sectors output a [i]construction[/i] good that auto-placed sites consume; states bid on it like any other good, and cost scales with GDP per capita so poorer nations can catch up. Based on TOGFan's mod (credited below).

[b]Banking Cycle[/b] — A seven-phase cycle: [b]panic → downturn → stagnation → stable → expansion → boom → frenzy[/b]. Speculative bubbles, contagion through trade, and policy levers fitted to your economy type. Time your construction spree to ride a Boom; don't tip Frenzy into Panic with debt on the books.

[i]>>> TODO image — Banking Cycle JE[/i]

[b]Space Race[/b] — Eight competitive milestones from suborbital flight to solar-system colonization, with 34 globally contested colony sites. Pick safe (slow, low failure) or ambitious (fast, costly setbacks). Plant the first flag on Mars and the world-first bonus is permanent — or watch a rival do it.

[i]>>> TODO image — Space Race JE[/i]

[b]Global Warming[/b] — Emissions and temperature tracked against a 4°C threshold; tiers trigger climate events and scaling penalties. Eight policy toggles — carbon tax, renewables, adaptation, transit, divestment, and more — let you slow warming or adapt to it.

[b]United Nations[/b] — Found or join an IGO with an authority bar, Security Council vetoes, specialized agencies (UNESCO, IAEA, WHO), and 16 vote topics. Sanctions, peacekeeping, and non-proliferation become real diplomatic tools — the Council seat is something rivals will fight to deny you.

[i]>>> TODO image — UN panel[/i]

[b]Nuclear Weapons[/b] — Race to the bomb or pursue disarmament. World-first grants permanent prestige; treaties can pause programs; deterrence is modeled diplomatically.

[b]Decolonization[/b] — Colonies hold a stability bar shaped by investment, garrisons, assimilation, or planned release. Hold the empire together by force or stage a managed handover that preserves your foreign assets — independence is coming either way.

[b]Covert Warfare[/b] — Cyber and espionage operations: election interference, financial subversion, infrastructure sabotage, communications disruption. Manage operation slots, funding, and detection risk; defend with digital sovereignty.

[b]Cultural Hegemony[/b] — A 0–100% global cultural share derived from prestige, art, living standards, tech leadership, and monuments. Hollywood-style soft power — your films and universities pull migration and bend rivals' ideologies.

[b]Social Movements[/b] — Civil rights, feminism, LGBTQ+, environmentalism, secularization, augmentation, digital rights, and the post-scarcity transition — mostly event chains, with journal entries for the ones that warrant tracked mechanics.

[i]>>> TODO image — Civil Rights JE[/i]

[h2]Smaller systems with their own pull[/h2]

[b]Tourism[/b] — Turn Hawaii or the French Riviera into a global destination. Pollution, infrastructure, and air-travel capacity gate how much demand you can capture; a coal-fired industrial state is a hard sell to the world's vacationers.

[b]Strategic Reserves[/b] — Stockpile oil, grain, and critical materials in dedicated hubs while supplies are cheap. When the war hits or the embargo lands, the reserve drains into your market instead of letting prices spike.

[b]Migration crowding[/b] — Density penalties on overcrowded states. Dump migrants into one hub and housing and political backlash hit; spreading the inflow keeps things stable.

[b]Standard-of-living expectations[/b] — Pops remember the last good year. A long boom raises the bar they measure against, so a dip after sustained prosperity hurts more than the same dip from baseline.

[b]Intelligence sharing[/b] — Defensive-pact members get bonuses against covert ops targeting any member, so blocs and IGOs become defensively meaningful even in peacetime.

[h2]Personal play opt-ins[/h2]

[b]Heir Education[/b] — Spend 15 years molding a successor: discipline, foreign study, committee assignments. Inherit the trait stack you built when they take office.

[b]Custom Religion[/b] — Build your own religion via a wizard: tenets, taboos, governance posture. Plugs into the ideology system like real-world religions.

[b]Universal aptitude traits[/b] — Optional trait pool that broadens which characters can surface as exceptional.

[b]World War[/b] — Off by default; an opt-in escalation system for great-power campaigns that want a 1914- or 1939-style war as a coherent endgame.

[hr][/hr]

[h1]Laws and ideologies[/h1]

[i]>>> TODO image — Laws panel[/i]

The law tree spans the full timeline. From an 1850s start you already get new monetary systems, criminal-justice models, IP regimes, inheritance, family policy, and a new ministry layer. Mid-game adds financial regulation, expanded minority and LGBTQ+ rights ladders, antitrust regimes, and updated rules of war. Late-game and speculative branches handle privacy vs. surveillance, internet governance, AI policy, cryptocurrency, genetic modification, UBI, and direct democracy — the back end of the tree, not the whole pitch.

The ideology system is rebuilt to support these laws, with new factions like environmentalists, anti-colonialists, optimist transhumanists, corporates, and a custom-religion family.

[hr][/hr]

[h1]Compatibility[/h1]

[b]Heavy override — incompatible with:[/b] ideology overhauls (vanilla ideologies replaced), PM overhauls (~60 vanilla PMs replaced), map mods (state-region data overridden), UI mods touching the same 20 vanilla panels (last-loading wins).

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
