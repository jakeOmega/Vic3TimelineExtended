# Tech Era Appropriateness Audit (2026-05)

Issue #40. Manual review of 171 mod-added techs against canonical real-world invention/adoption years vs the era they're assigned to.

## Methodology

- Era year ranges per `docs/vanilla/vanilla_technology_reference.md`:

  | Era    | Period                | Half-point |
  |--------|-----------------------|------------|
  | era_6  | 1919 – 1945           | 1932       |
  | era_7  | 1946 – 1967           | 1956       |
  | era_8  | 1968 – 1987           | 1977       |
  | era_9  | 1988 – 2012           | 2000       |
  | era_10 | ~2013 – ~2030         | ~2022      |
  | era_11 | ~2030 – ~2060         | speculative |
  | era_12 | 2060+                 | speculative |

- **Verdict legend:**
  - **OK** — canonical invention/adoption year falls inside the era's window.
  - **OK (boundary)** — year is within 5 years of an era boundary; era choice is defensible either way.
  - **Move to era_N (suggested)** — anchor year is clearly outside the assigned era and inside another. Listed as a suggestion; this audit applies moves only where the mismatch is large AND prerequisite chains remain intact.
  - **N/A (speculative)** — era_11 / era_12 are forward-projected; canonical year doesn't exist. Verdict is based on subject-matter plausibility.

- Borderline cases that span an era boundary are kept where they are unless their *predominant* invention period falls clearly in another era.

- Future eras (era_11, era_12) are reviewed for *thematic* fit (depends-on-X, plausible-given-Y) rather than year fit.

---

## era_6 (1919 – 1945) — 38 techs

| Tech | Canonical year(s) | Verdict |
|---|---|---|
| `bergius_process` | 1913 patent, 1927 industrial | OK (Bergius scaled in era_6) |
| `isoprene` | 1931 neoprene, 1935 Buna | OK |
| `computing_machines` | 1931 differential analyzer → 1941 Z3 → 1945 ENIAC | OK |
| `personal_appliances` | 1920s–30s widespread | OK |
| `rocketry` | V-2 1944; Goddard work 1920s–30s | OK |
| `bombing_aircraft` | WWII strategic bombing 1939–1945 | OK |
| `nuclear_weapons` | 1945 | OK |
| `commercial_aviation` | DC-3 1936, Pan Am 1927 | OK |
| `keynesian_economics` | 1936 (General Theory) | OK |
| `combined_arms` | Blitzkrieg 1939–1940, Soviet deep ops 1936 | OK |
| `modern_materials` | Nylon 1935, Teflon 1938, fiberglass 1936 | OK |
| `modern_tools` | Forklift 1923, pneumatics 1920s | OK |
| `modern_skyscrapers` | Empire State 1931, Chrysler 1930 | OK |
| `advanced_agricultural_statistics` | Fisher 1925–35 (statistical methods); ag census refinement 1930s | OK |
| `modern_automotive_technology` | Coil-spring 1934, hydraulic brakes 1918, independent suspension 1933 | OK |
| `radar` | 1935 Watson-Watt → 1940 Chain Home | OK |
| `television` | BBC public broadcasting 1936 | OK |
| `marketing_research` | 1920s (Nielsen 1923, Gallup 1935) | OK |
| `motorized_artillery` | WWII self-propelled gun proliferation | OK |
| `semiautomatic_rifle` | M1 Garand 1936 | OK |
| `modern_vaccines` | Diphtheria 1923, BCG 1921, tetanus 1924 | OK |
| `mass_media` | Radio mass adoption 1920s | OK |
| `animation` | Steamboat Willie 1928, Snow White 1937 | OK |
| `rural_electrification` | REA 1935 (US); UK widespread 1930s | OK |
| `fluorescent_lamps` | 1938 commercial introduction (GE) | OK |
| `modern_chemical_processes` | Ostwald 1902 + Haber 1909 industrial deployment 1920s | OK (boundary) — naming references pre-era inventions but industrial scale-up is era_6 |
| `aluminum_mass_production` | Hall-Héroult 1886; war-driven scale-up 1940s | OK (boundary) — process is older but mass production is era_6 |
| `stainless_steel_mass_production` | Invented 1913, commercialized 1920s | OK |
| `modern_management_techniques` | Drucker 1940s–50s, Taylorism extension 1920s–40s | OK |
| `naval_convoy_defense` | WWII Atlantic convoys 1939–45 | OK |
| `sonar` | ASDIC 1917–20s, WWII refinement | OK |
| `naval_fire_control_systems` | WWII analog FCS (Mk 37 1939) | OK |
| `cryptography` | Enigma broken 1940–43, SIGABA 1940s | OK |
| `public_works_programs` | New Deal 1933, WPA 1935 | OK |
| `art_deco_architecture` | Paris 1925 exposition, peak 1920s–30s | OK |
| `consumer_credit` | Installment plans 1920s, mass credit 1930s | OK |
| `intergovernmental_organizations` | League of Nations 1920, ILO 1919 | OK |
| `decolonization` | India 1947 — borderline. Pre-WWII self-determination movements + Atlantic Charter 1941 anchor the prerequisite | OK (boundary) — invention/idea predates the post-WWII decolonization wave |

---

## era_7 (1946 – 1967) — 27 techs

| Tech | Canonical year(s) | Verdict |
|---|---|---|
| `transistors` | 1947 Bell Labs | OK |
| `nuclear_energy` | 1954 civilian reactor (Obninsk) | OK |
| `advanced_military_aircraft` | F-86 1947, MiG-15 1948, F-4 1958 | OK |
| `jet_engine_technology` | Mass adoption 1950s | OK |
| `green_revolution` | 1950s–70s (Borlaug Mexico 1944 → Asia 1960s) | OK |
| `civil_rights_movement` | 1954 Brown → 1965 Voting Rights Act | OK |
| `laser_technology` | 1960 Maiman first laser | OK |
| `space_exploration` | Sputnik 1957, Mercury 1961, Apollo started 1961 | OK |
| `pollution_control` | Clean Air Act 1963, NEPA 1969 | OK (boundary) — predominantly 1963–1970 |
| `advanced_submarine_technology` | Nautilus 1954, Polaris 1960 | OK |
| `guided_missiles` | AIM-9 1956, SS-N-3 1958 (early cruise) | OK |
| `plastic_mass_production` | Postwar plastic boom 1950s | OK |
| `mainframe_computers` | UNIVAC 1951, IBM 360 1964 | OK |
| `integrated_circuits` | Kilby/Noyce 1958–61 | OK |
| `prefabricated_construction` | Postwar housing 1946–60s | OK |
| `photocopiers` | Xerox 914 1959, mass adoption 1960s | OK |
| `anti_sub_warfare` | Cold War ASW doctrine 1950s–60s | OK |
| `ICBMs` | R-7 1957, Atlas 1959, Minuteman 1962 | OK |
| `tactical_nuclear_weapons` | Davy Crockett 1961, W54 1961 | OK |
| `recon_satellites` | Corona 1960, KH-7 1963 | OK |
| `inertial_navigation_systems` | Atlas / Polaris 1950s, SR-71 1966 | OK |
| `television_broadcasting` | Mass adoption 1950s | OK |
| `antibiotic_mass_production` | Penicillin postwar scale-up 1945–60 | OK |
| `contraceptive_pill` | Enovid approved 1960 | OK |
| `second_wave_feminism` | Friedan 1963, NOW 1966 | OK |
| `anti_war_movement` | Vietnam protests 1965–75 | OK (boundary) — predominantly late-60s, fine |
| `modern_urban_planning` | Le Corbusier postwar work, Jane Jacobs 1961 | OK |

---

## era_8 (1968 – 1987) — 23 techs

| Tech | Canonical year(s) | Verdict |
|---|---|---|
| `satellite_communications` | Telstar 1962, INTELSAT 1965 (era_7); commercial mature 1970s | **Move to era_7 (suggested)** — first-light era_7; era_8 commercial maturity is the secondary anchor |
| `advanced_materials_armor` | Chobham 1976, Reactive 1980s | OK |
| `predictive_logistics` | MRP 1970s, MRP II 1983 | OK |
| `advanced_assembly_lines` | Toyota Production System 1970s, JIT codified 1978 | OK |
| `modern_pharmaceuticals` | Rational drug design 1970s–80s, cimetidine 1976 | OK |
| `containerization` | Sealand 1956 (era_7) → ISO standard 1968 → global ports 1970s | OK (boundary) — era_8 if "containerization" = ISO/global; era_7 if = invention |
| `fiber_optics` | Corning low-loss 1970, commercial 1977 | OK |
| `computer_networks` | ARPANET 1969, TCP/IP 1983 | OK |
| `personal_computers` | Apple II 1977, IBM PC 1981 | OK |
| `robotics` | Unimate 1961, mass industrial 1970s–80s | OK |
| `supersonic_aircraft` | SR-71 1966 (era_7); Concorde 1976 commercial | OK (boundary) |
| `stealth_technology` | F-117 1981, B-2 1989 | OK |
| `environmental_movement` | Earth Day 1970, EPA 1970 | OK (boundary) |
| `sexual_revolution` | 1960s primary (era_7); extended into 1970s | OK (boundary) — predominantly 1960s but cultural codification 1970s |
| `microprocessor` | Intel 4004 1971 | OK |
| `gene_splicing` | Cohen-Boyer 1973 | OK |
| `computer_aided_design` | Sketchpad 1963 (era_7); practical CAD 1970s–80s (CATIA 1977, AutoCAD 1982) | OK |
| `cellular_networks` | 1G launched Japan 1979, AMPS 1983 | OK |
| `barcodes_and_scanners` | UPC 1973, mass adoption 1980s | OK |
| `precision_guided_munitions` | Paveway 1968, Vietnam 1968–72 | OK |
| `infrared_night_vision` | Starlight scope Vietnam 1960s (era_7); thermal imaging 1980s | OK (boundary) |
| `video_games` | Pong 1972, Atari VCS 1977 | OK |
| `pop_culture` | 1960s phenomenon (era_7) — mass culture concept | **Move to era_7 (suggested)** — anchor decade is 1960s |

---

## era_9 (1988 – 2012) — 28 techs

| Tech | Canonical year(s) | Verdict |
|---|---|---|
| `hydraulic_fracturing` | Mitchell shale 1998–2002, Marcellus boom 2008+ | OK |
| `cloud_computing` | AWS 2006, term popularized 2006 | OK |
| `biotechnology` | CRISPR 2012 (boundary), prior recombinant DNA biotech 1980s+ | OK (boundary) |
| `early_nanotechnology` | STM 1981 (era_8), but term + research program 1990s–2000s | OK |
| `world_wide_web` | Berners-Lee 1989–91, mass 1995–2000 | OK |
| `digital_telecommunications` | ISDN/DSL 1990s, mobile 2G 1991, VoIP 1990s | OK |
| `clean_energy_technologies` | Solar PV cost decline 2000s–2010s; wind boom 2000s | OK |
| `supply_chain_management` | Walmart RFID 2003, SAP R/3 1992, Bullwhip effect 1997 | OK |
| `e-commerce` | Amazon 1994, eBay 1995, mass 2000s | OK |
| `wireless_internet` | Wi-Fi 1997 (802.11), hotspots 2003+ | OK |
| `unmanned_aerial_vehicles` | Predator 1995, mass deployment 2001+ | OK |
| `military_grade_cybersecurity` | Moonlight Maze 1999, Stuxnet 2010 | OK |
| `network_centric_warfare` | Cebrowski 1998 doctrine, Gulf War II 2003 | OK |
| `missile_defense_systems` | Aegis 1983 (era_8), GMD 2004, Iron Dome 2011 | OK (boundary) |
| `automated_surveillance` | Post-9/11 (2001+) | OK |
| `advanced_body_armor` | Interceptor 1998, exoskeleton research 2000s | OK |
| `rapid_deployment_forces` | RDF 1980 (era_8), CENTCOM 1983, modern Special Ops Command 1987–2000s | OK (boundary) |
| `globalization` | WTO 1995, late-20th-century term | OK |
| `social_media` | Friendster 2002, Facebook 2004, Twitter 2006 | OK |
| `virtual_reality` | Lawnmower Man 1992 (cultural), Oculus 2012 | OK (boundary) — modern VR (Oculus → consumer Rift 2016) is era_10; concept is era_8–9 |
| `knowledge_economy` | Drucker 1969, mass term 1990s | OK |
| `digital_entertainment` | DVD 1996, MP3 1995, Netflix streaming 2007 | OK |
| `digital_education` | MOOCs 2012, Khan Academy 2006 | OK |
| `social_justice_movements` | Occupy 2011, BLM 2013 (era_10) | OK (boundary) — 2010s wave straddles era_9/10 boundary |
| `terrorism_and_anti_terrorism` | Post-9/11 (2001) | OK |
| `LGBTQ_rights_movement` | Lawrence v. Texas 2003, marriage rulings 2003–15 | OK |
| `cybersecurity` | General term, 1990s+ usage | OK |
| `advanced_workflow_optimization` | Six Sigma 1986 (era_8), lean six sigma 2000s | OK |

---

## era_10 (~2013 – ~2030, "nowish") — 17 techs

| Tech | Canonical year(s) | Verdict |
|---|---|---|
| `machine_learning` | AlexNet 2012, deep learning boom 2014+ | OK |
| `generative_ai` | GPT-3 2020, DALL-E 2021, ChatGPT 2022 | OK |
| `additive_manufacturing` | Consumer 3D printing 2013+, industrial 2010s | OK |
| `advanced_structural_engineering` | Burj Khalifa 2010 (era_9 boundary), Shanghai Tower 2015, supertall boom 2010s | OK |
| `electric_vehicles` | Tesla Model S 2012, mass adoption 2020s | OK |
| `internet_of_things` | Term 1999, mass adoption 2014+ | OK |
| `mrna_therapeutics` | Pfizer-BioNTech 2020 | OK |
| `reusable_rocketry` | Falcon 9 booster landing 2015 | OK |
| `hypersonic_weapons` | Avangard 2018, US programs 2010s–2020s | OK |
| `directed_energy_defenses` | LaWS 2014, HELIOS 2022 | OK |
| `jadc2` | DoD JADC2 doctrine 2019+ | OK |
| `cyber_warfare` | Stuxnet 2010, NotPetya 2017 | OK |
| `electronic_warfare` | Classical EW (WWII–), modern emphasis 2010s | OK (boundary) — EW has existed forever; era_10 is fine for "modern multi-domain EW" framing |
| `decline_of_organized_religion` | Pew Research religious-nones tracking 2007+, accelerating 2010s | OK |
| `telemedicine` | COVID surge 2020 | OK |
| `universal_basic_income` | Modern debate 2010s (Andrew Yang 2020) | OK |
| `mental_health_awareness` | 2010s–2020s cultural shift, COVID 2020 | OK |

---

## era_11 (~2030 – ~2060, "near future") — 20 techs

Speculative — verdicts assess subject-matter plausibility against era_10 prereqs and era_11 horizon.

| Tech | Plausible era_11? | Notes |
|---|---|---|
| `modern_material_science` | Yes | Graphene/metamaterials maturity is decade-out |
| `abyssal_plain_mining` | Yes | TMC commercial trials 2020s, mass mining 2030s+ |
| `quantum_computing` | Yes | Demonstrations 2019–2024, fault-tolerant 2030s+ |
| `smart_grids` | Borderline (era_10) | Smart-grid deployment is current; could move to era_10 |
| `autonomous_vehicles` | Borderline (era_10) | Waymo level-4 commercial 2024; era_10 is defensible. Era_11 anchors "mass passenger AVs" — fine |
| `genetic_engineering` | Yes | CRISPR therapies clinical 2020s, mass clinical 2030s |
| `synthetic_biology` | Yes | Engineered organisms 2020s, designer organisms 2030s |
| `directed_energy_weapons` | Yes | Operational laser weapons 2020s–30s |
| `space_militarization` | Yes | US Space Force 2019, ramp 2030s |
| `swarm_technology` | Yes | Drone swarms 2020s–30s |
| `quantum_communications` | Yes | QKD demos 2017–2024, network-scale 2030s |
| `bioenhanced_soldiers` | Yes | Speculative; era_11 horizon |
| `augmented_reality_warfare` | Borderline (era_10) | IVAS 2022 deliveries; era_10 defensible |
| `asteroid_mining` | Yes | Speculative; SpaceX/AstroForge propose 2030s |
| `fusion_power` | Yes | NIF ignition 2022, commercial 2035+ (best case) |
| `brain_computer_interfaces` | Yes | Neuralink trials 2024, clinical 2030s |
| `personalized_medicine` | Borderline (era_10) | Genomic medicine current; era_10 anchor possible |
| `lab-grown_food` | Borderline (era_10) | Singapore approval 2020, US 2023; era_10 defensible |
| `universal_digital_identity` | Yes | Aadhaar/eIDAS 2020s, global rollout 2030s |
| `biohacking_and_human_augmentation` | Yes | Speculative |

**Possible era_10 moves (low confidence):** smart_grids, autonomous_vehicles, augmented_reality_warfare, personalized_medicine, lab-grown_food. All are "current generation" tech that could anchor earlier; era_11 anchors their *mass deployment* form. Leaving as-is.

---

## era_12 (2060+, "far future") — 18 techs

All speculative. Verdicts assess that the tech is qualitatively beyond era_11.

| Tech | Plausible era_12? |
|---|---|
| `artificial_intelligence` | Yes (AGI / general intelligence — clearly era_12 vs era_10/11 narrow AI) |
| `advanced_nanofabrication` | Yes |
| `molecular_assemblers` | Yes |
| `quantum_materials` | Yes |
| `orbital_manufacturing` | Yes |
| `programmable_matter` | Yes |
| `compact_fusion_reactors` | Yes |
| `fusion_batteries` | Yes |
| `space_elevator` | Yes |
| `orbital_weapon_platforms` | Yes |
| `space_based_solar_power` | Yes |
| `antimatter_production` | Yes |
| `biological_immortality` | Yes |
| `space_colonization` | Yes |
| `telepathic_communities` | Yes |
| `mind_backups` | Yes |
| `post-scarcity_economy` | Yes |
| `neural_lace` | Yes |

No era_12 entries appear miscategorized.

---

## Summary

- **Total mod techs audited:** 171 (era_6 through era_12).
- **Clear mismatches (move recommended):**
  - `satellite_communications`: era_8 → era_7. Telstar 1962, INTELSAT 1965; era_8 commercial maturity is secondary anchor.
  - `pop_culture`: era_8 → era_7. 1960s phenomenon.
- **Borderline cases noted but not moved** (within 5 years of an era boundary; the assigned era is defensible): `modern_chemical_processes`, `aluminum_mass_production`, `decolonization`, `pollution_control`, `containerization`, `supersonic_aircraft`, `environmental_movement`, `sexual_revolution`, `infrared_night_vision`, `biotechnology`, `missile_defense_systems`, `virtual_reality`, `social_justice_movements`, `rapid_deployment_forces`, `electronic_warfare`, `advanced_structural_engineering`.
- **Speculative eras (11, 12):** thematically plausible. A handful of era_11 techs could justifiably be era_10 (smart_grids, autonomous_vehicles, augmented_reality_warfare, personalized_medicine, lab-grown_food) but mass-deployment framing supports era_11 placement; leaving as-is.
- **Overall verdict:** the mod's era assignments are historically defensible. The only clear misplacements are the two listed; the rest are well-anchored or fall within tolerance.

## Moves applied in this PR

- `satellite_communications` moved era_8 → era_7
- `pop_culture` moved era_8 → era_7

Prerequisite-chain check:
- `satellite_communications` prereqs: `space_exploration` (era_7), `cryptography` (era_6) — both in or before era_7, OK.
- `pop_culture` prereq: `television_broadcasting` (era_7) — OK.
- Downstream of `satellite_communications`: `predictive_logistics` (era_8), `network_centric_warfare` (era_9), `rapid_deployment_forces` (era_9). All later than era_7. OK.
- Downstream of `pop_culture`: `social_media` (era_9), `terrorism_and_anti_terrorism` (era_9), `knowledge_economy` (era_9). All later than era_7. OK.

No prereq cycles or downstream-before-upstream violations introduced.
