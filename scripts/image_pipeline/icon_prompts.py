#!/usr/bin/env python3
"""
icon_prompts.py - FLUX prompt registry for the mod's UI icons.

The icon counterpart of event_image_prompts.py. `CATEGORIES` holds what makes
each category look like its vanilla folder (size, layout, style template);
`ICONS` holds, per category, one subject phrase per entity and its review
state. `generate_icons.py` renders, composes, writes and wires from here.

Each ICONS entry is {"subject": <phrase>, "seed": <state>}:
    seed None     not reviewed yet; renders candidates, writes nothing
    seed <int>    this candidate is the icon: its DDS is written and the
                  entity's icon line points at it
    seed "keep"   the borrowed vanilla icon fits; never rendered or rewired
or {"use": "gfx/interface/icons/.../x.dds"}: a different existing icon fits
better than the borrowed one (vanilla's crossed-out guarantee for withdrawing
one); never rendered, and `wire` points the entity at it.
A "restyle": "gfx/.../x.dds" entry keeps an existing mod icon's picture and
refits it to the category's vanilla look, instead of drawing a new one (the
mod's pre-pipeline building icons, 2024-25, had no gold frame). Its subject
describes that picture. Candidate i is the picture repainted by FLUX
image-to-image at strength i of the category's `restyle_strengths` (or the
entry's own "strengths"); strength 0 is the picture unpainted. The old icon's
outline is shrunk past its own rim and the emptied corners filled from the
picture (icon_render.prepare_restyle); "crop" (default RESTYLE_CROP) then cuts
that share from each side, 0.1 for a circular badge. The source is read from disk,
else from git, so the old file can be deleted once nothing points at it.
An entry may carry its own "style" (a template with {subject}) in place of the
category's: the building style's aerial diorama put orbital stations low over
a map, small (ORBIT).
In a GUI-hosted category (`gui`: icons a .gui file draws, not an entity's),
an entry also names the placeholder it replaces, "now": <vanilla path>, and
may instead be derived: {"from": "<cat>/<key>", "tint": "grey"|"faint",
"layout": "flag", "size": (w, h), "marks": [...], "now": ...}, another
entry's icon reworked with no render of its own. Any entry may carry
"marks": each {"icon": <vanilla .dds>} | {"part": "<cat>/<key>"} |
{"draw": <icon_render.DRAWN name>, ...its settings}, with "at" (centre, as
shares of the side) and "scale", and optionally "under" (drawn beneath the
icon), "rotate" (degrees) and, for a part, "tint". The system panels' states
(#573-#583) added to a derived entry: "tint" "gold"|"silver"|"iron"|"moss",
"damage" "crack"|"split" (FLUX will not break things), "tilt" (a lean about
its foot), "turn" (about its centre), "base" {"scale", "at"} (the emblem
shrunk and placed), and "disc" in place of "from": drawn outright on a disc
of its own colours (the warming tiers). "drawn": True in place of either is
a bare canvas holding only its drawn marks (banking momentum's triple arrows). "solid": True fills back any hole the cut-out left inside the
object (rembg took a crate's front boards for background); only for
objects with no real holes. A `part` category is reviewed like icons but never written; it
supplies derived icons and marks (the UN's emblem and scroll badge).
A subject describes one physical object, with its material and colour. FLUX
fills in whatever a subject leaves open, and review kept catching the same
defaults (September 2026, ~350 icons):
- Unnamed colours drift to real-world defaults: "paper banknotes" drew US
  dollars. No screens with text, no currency, flags or faces.
- Words that imply writing get written: "voting card" drew VOTE, "holy book"
  HOLY, "payment-plan tag" Payment, a share certificate its title, "radio
  jammer" JAMMER. Name the object, not its purpose ("a small green wooden
  block").
- Gold coins come with $ signs ("plain gold coins each stamped with a small
  star"), a camera with a brand name, a customs gate's posts with numbered
  plates. Zoom the raw render of any pick with coins, devices or signage.
- Vehicles and aircraft come with insignia: a red star, a US Army star,
  roundels, red crosses on a bomber. Choose an unmarked candidate; saying "no
  markings" does not stop them.
- Avoid a large white or cream surface: renders are on a white background and
  the cutout cannot tell them apart (a white tray and a cream certificate lost
  patches, which showed as dark holes on the game's UI).
- FLUX will not break, fold or furl on request ("a rifle snapped in two", "a
  furled umbrella"); change the image (a helmet full of poppies).
- Anything hung from a crossbeam reads as a gallows (a pole with a hanging
  bulb, a marionette on its frame).
- In the plinth layout, "on a stand" or "on a base" adds a second pedestal.
- Printed and branded objects bring their print: a circuit board its
  silkscreen, a controller PlayStation symbols, a sci-fi rifle a maker's
  logo, a sun a play-button triangle. Etched lines or plain buttons work.
- A "blank screen" renders pale, and the cutout empties it, leaving the
  device hollow. Give the screen a dark or coloured glow (a heartbeat line).
- Glows and halos around an object turn into grey blobs after the cutout.
- An unqualified object gets its usual context: a helmet comes with a
  soldier wearing it (write "an empty helmet"), and a "globe" is a plain
  green ball (name the Earth's continents and oceans).
- In the framed building layout, a product in front of the plant must have
  no fixed size: heaps of ore, grain or crates work, but a walkie-talkie, a
  jar or bottles come out as big as the building, and photographic. Leave
  those out, and ask for ", loosely hand-painted with visible brush
  strokes" in the subject rather than editing the category style, which
  would change every approved prompt.
- In the embossed layouts (mobilization options, ideologies, trait cards) the
  bevel turns thin parts into dark hairlines: a beam, an antenna, radio
  waves, fronds. Ask for thick shapes. A wide object seen side-on fits the
  icon's width and comes out thin; an angled view fills more of it.
- In the backed layout (Space Race journal entries) the subject still renders
  on white and is cut out, then laid over the shared backdrop. Leave space
  out of the subject ("in orbit", "against stars"): the cut-out would try to
  separate the craft from the stars. Craft the cut-out can keep are gold,
  silver, grey or orange; a white one loses its body.
- Some objects read as something else at icon size: a laser turret as a
  camera (make it fire at a target), a landing craft as a ferry, a flight
  simulator pod as a lunar lander, a parachute as a hot-air balloon, a
  helmet seen from the front as a face.
When both candidates miss, change the subject. When the idea is right and the
renders are weak, `generate_icons.py --seeds 4` adds two more candidates and
keeps the first two.

Design, inventory and decisions: docs/superpowers/specs/2026-09-26-icon-pipeline-design.md.

Usage:
    python3 icon_prompts.py --validate   # registry vs the mod's files; exit 1 on errors
"""

from __future__ import annotations

KEEP = "keep"
RESTYLE_CROP = 0.03

# Style = what makes a category look like its vanilla folder. Subject = the one
# per-entity phrase a human (or an LLM draft from loc) has to write.
# Painterly, not photographic: FLUX.1-schnell drifts to product photography unless
# the prompt names the medium ("hand-painted game icon", brush strokes). Small
# categories (100 px) also need one compact object, or it downsizes to specks.
PAINTED = ("stylized hand-painted video game icon, painterly digital art with visible "
           "brush strokes, soft 3D shading, warm muted palette, blank unmarked surfaces, "
           "three-quarter view from slightly above, centered, isolated on a plain white background")
# For the embossed categories. A plainer "solid black silhouette ... bold clean
# shapes" drew outline-only parts (an envelope, a coiled cord) that emboss to
# hairlines, and let a locomotive run off the canvas, which the emboss then cut
# square.
SILHOUETTE = ("a bold solid black silhouette icon of {subject}, simple flat pictogram stencil, "
              "thick chunky shapes with a few bold white cut-out details, no thin lines, no outlines, "
              "no hatching, the whole object fully visible and centered with a wide white margin on "
              "every side, on a plain white background")
# The UN's GUI icons show at 32-40 px: one bold object in clear colours.
UN_STYLE = ("{subject}, one compact bold object filling the frame, simple chunky silhouette, strong clear "
            "colours, " + PAINTED)

# Orbital buildings, in place of the building style: its "aerial view ...
# miniature diorama ... surrounding landscape" drew a station as a small model
# hovering over a map (2026-10-02). The restyled space elevator shows the
# Earth's curved edge under black space, as this does.
ORBIT = ("{subject}, seen from close by in orbit, filling most of the picture, the curved blue edge of the "
         "Earth below it and black starry space above, detailed painted illustration, warm golden sunlight, "
         "muted palette")

# Company logos (256 px, CompanyType.GetIcon). Vanilla's basic industries and
# historical companies are emblem badges seen straight on: an illustration of
# the trade inside a frame, each frame its own. Vanilla's span 0.91-1.00 of
# the side (median 0.97 for the basic industries, 0.93 for the historical).
EMBLEM = ("a vintage company emblem badge seen straight on: {subject}, painted on a dark slate-blue enamel disc "
          "inside an ornate bronze frame with scrollwork, detailed painterly illustration with visible brush "
          "strokes, muted warm colours, blank unmarked surfaces, centered, isolated on a plain white background")

# The system panels whose GUI icons come from here (the style pass,
# #573-#583): registry prefix -> folder under gfx/interface/icons/, and the
# widget that draws them.
_GUI_SYSTEMS = {
    "banking": "banking_icons",
    "ch": "ch_icons",
    "covert": "covert_icons",
    "gw": "gw_icons",
    "gm": "gm_icons",
    "st_res": "st_res_icons",
    # List 2: provisional until the systems' play-test round 3 ends.
    "nuclear": "nuclear_icons",
    "colonial": "colonial_empire_icons",
    "space": "space_race_icons",
}
_GUI_FILES = {
    "banking": "gui/journal_entry_widgets/banking_dashboard_widget.gui",
    "ch": "gui/journal_entry_widgets/cultural_hegemony_widget.gui",
    "covert": "gui/journal_entry_widgets/covert_operations_widget.gui",
    "gw": "gui/journal_entry_widgets/global_warming_widget.gui",
    "gm": "gui/journal_entry_widgets/grand_monuments_widget.gui",
    "st_res": "gui/journal_entry_widgets/strategic_reserve_widget.gui",
    "nuclear": "gui/journal_entry_widgets/nuclear_overview_widget.gui",
    "colonial": "gui/journal_entry_widgets/colonial_empire_widget.gui",
    "space": "gui/journal_entry_widgets/space_race_widget.gui",
}

# folder/size/mode/fill/style drive rendering and composing. A category that
# `generate_icons.py` produces also names where its entities live
# (`entity_dir`) and the field holding the icon path (`field`); its icons are
# written to gfx/interface/icons/<folder>/<key>.dds.
CATEGORIES = {
    "technology": dict(
        folder="invention_icons", size=256, mode="cutout", fill=0.92,
        entity_dir="common/technology/technologies", field="texture",
        style="{subject}, one chunky readable object, " + PAINTED),
    "treaty_article": dict(
        folder="diplomatic_treaties_articles_icons", size=100, mode="cutout", fill=0.98,
        entity_dir="common/treaty_articles", field="icon",
        style=("{subject}, one compact bold object group filling the frame, simple chunky "
               "silhouette, one strong accent color, " + PAINTED)),
    # The figure stands on the slab lifted from vanilla (icon_render.plinth_template).
    # Asking FLUX for the pedestal drew one detached from its figure.
    # The lens toolbar ignores `texture`: the engine loads
    # lens_toolbar_icons/<key>.dds for every action without show_in_lens = no,
    # and vanilla's is a byte-identical copy of the action icon. `write` keeps
    # that copy (see generate_icons.sync_lens_copies).
    "diplomatic_action": dict(
        folder="diplomatic_action_icons", size=100, mode="plinth", fill=0.8,
        entity_dir="common/diplomatic_actions", field="texture", lens_folder="lens_toolbar_icons",
        style=("{subject}, a compact miniature sculpture, simple chunky silhouette, " + PAINTED)),
    # restyle_strengths: as is, then repaints (applied in eighths, see icon_render.RESTYLE_STEPS).
    # Up to 0.5 the repaint adds texture but keeps a flat picture flat; the brushwork shows from 0.625.
    "building": dict(
        folder="building_icons", size=256, mode="framed", restyle_strengths=(0.0, 0.375, 0.5, 0.625, 0.75),
        entity_dir="common/buildings", field="icon",
        style=("aerial three-quarter view of {subject}, detailed painted illustration "
               "of a miniature diorama, warm golden afternoon light, muted earthy "
               "palette, surrounding landscape, the building fills the center of the image")),
    # Ideology icons are read only from `icon =` (Ideology.GetTexture). IG
    # ideologies are gold on a crimson disc; leader (character) ideologies
    # silver on teal, in ideology_leader/. Vanilla gives an ideology held by
    # both an IG and a leader one symbol in both looks (abolitionist's chains).
    "ideology": dict(
        folder="ideology_icons", size=220, mode="emboss_medallion", fill=0.75,
        entity_dir="common/ideologies", field="icon",
        # fill 0.75: vanilla's symbols span ~156 of 220 px (0.60 gave 123).
        # Colours fitted like mobilization's: symbol top (201,178,140), bottom (174,141,94).
        color=(281, 254, 207), color_bottom=(257, 204, 131), centre_lift=1.25, style=SILHOUETTE),
    "leader_ideology": dict(
        folder="ideology_icons/ideology_leader", size=220, mode="emboss_medallion", fill=0.75,
        entity_dir="common/ideologies", field="icon",
        # Symbol top (179,186,196), bottom (124,132,146): a bluish silver.
        color=(261, 269, 281), color_bottom=(172, 184, 207), centre_lift=1.25, style=SILHOUETTE),
    # Read only from `texture =` (MobilizationOption.GetTexture); no second lookup.
    "mobilization_option": dict(
        folder="mobilization_options", size=208, mode="emboss", fill=0.86,
        entity_dir="common/mobilization_options", field="texture",
        # Fitted so the top and bottom quarters' median colours match
        # vanilla's 19 icons: (181,128,106) pinkish, (148,73,38) orange-brown.
        # Channels above 255 are fine: the emboss multiplies by its lighting
        # (median ~0.6) before clipping.
        color=(283, 212, 185), color_bottom=(249, 115, 55), style=SILHOUETTE),
    # Vanilla's law icons are painted objects in one tan-bronze palette; the
    # `tinted` layout recasts a painted render in it. Read from `icon =`
    # (Law.GetTexture, LawType.GetTexture; amendments show their parent's).
    "law": dict(
        folder="law_icons", size=256, mode="tinted", fill=0.9,
        entity_dir="common/laws", field="icon",
        style="{subject}, one chunky readable object, " + PAINTED),
    # The same metal as laws. The ramp comes from law_icons: institution_icons
    # also holds institution_icon_bg, the dark disc the GUI draws them over.
    # Vanilla's objects span 0.68-0.80 of the side (median 0.775) and the disc
    # 0.80; at 0.9 ours spilled past the disc (#561 in-game review).
    # `background_texture`, the painted strip, is the next category.
    "institution": dict(
        folder="institution_icons", ramp_folder="law_icons", size=256, mode="tinted", fill=0.78,
        entity_dir="common/institutions", field="icon",
        style="{subject}, one chunky readable object, " + PAINTED),
    # Institution strips (3500x220, Institution.GetBackground): the painted
    # scene behind each institution's row. Only about x 1300-2000 shows, at
    # roughly half opacity (icon_render.STRIP_BAND), so a 4:1 render fills the
    # middle and compose_strip mirrors it out to the edges. Block-compressed
    # through texconv like event pictures: vanilla's seven are uncompressed at
    # 4.1 MB each.
    "institution_strip": dict(
        folder="institutions", root="gfx/interface/illustrations", size=(3500, 220),
        gen_size=(1792, 448), mode="strip", dds_format="BC7_UNORM_SRGB",
        entity_dir="common/institutions", field="background_texture",
        style="{subject}, candid close-up, the figures large and cropped at the chest in the middle of "
              "the frame, seen from the side busy at their work, oil painting, historical realism, muted "
              "earthy colours, soft diffuse light, visible brushwork"),
    # IG trait cards (124x162, InterestGroupTrait.GetTexture): a dark embossed
    # pictogram on a card whose colour is the trait's approval slot, gold for
    # loyal, green for happy, rust for unhappy. One category per slot, since
    # the card is per category; card_template() lifts each from vanilla.
    # The pictogram takes a tint from its card, as vanilla's do: colours fitted
    # per slot to the top and bottom quarters of vanilla's pictograms.
    **{f"ig_trait_{slot}": dict(
        folder="ig_trait_icons", size=162, card_size=(124, 162), frame=frame, mode="card",
        fill=(0.82, 0.7), entity_dir="common/interest_group_traits", field="icon",
        color=top, color_bottom=bottom, style=SILHOUETTE)
       for slot, frame, top, bottom in (
           ("loyal", (251, 249, 140), (119, 94, 73), (140, 102, 73)),
           ("happy", (145, 173, 121), (122, 151, 122), (68, 89, 65)),
           ("unhappy", (190, 124, 100), (90, 82, 84), (152, 116, 96)))},
    # Character traits (240x320, CharacterTrait.GetTexture) use the same card
    # layout; the frame colour is the trait's type: condition pink (184,129,128
    # where card_template samples it), skill grey (151,149,139), personality
    # blue (125,147,158). Pictogram colours fitted to vanilla's condition cards.
    # The combined-arms traits then turn card and tint to gold (`recolor`:
    # hue +45 degrees, saturation x1.4): pink marks vanilla's bad traits, and
    # no vanilla type is yellow (#561 in-game review).
    "character_trait": dict(
        folder="character_trait_icons", size=320, card_size=(240, 320), frame=(184, 129, 128),
        recolor=(45, 1.4),
        mode="card", fill=(0.8, 0.72), entity_dir="common/character_traits", field="texture",
        color=(99, 101, 101), color_bottom=(65, 45, 43), style=SILHOUETTE),
    # Harvest conditions (150 px, HarvestConditionType.GetIcon): a painted
    # scene inside a round copper rim, which `framed` lifts from vanilla like
    # the building frame.
    "harvest_condition": dict(
        folder="harvest_condition_icons", size=150, mode="framed",
        entity_dir="common/harvest_condition_types", field="icon",
        style=("{subject}, simple painted illustration of one clear scene, muted colours, soft "
               "painterly brush strokes, the subject fills the center of the image")),
    # Power bloc identities (~200 px, PowerBlocIdentity.GetIcon): one ornate,
    # often gilded object on a transparent background. The background field
    # is shared by every identity, vanilla's too.
    # grade_strength 0.5, not 0.7: the Diplomatic Framework's parchment
    # rendered clipped near white, and the full grade flattened it to one dull
    # beige (#561 in-game review). The two-point grade decrees use turned the
    # clipped parchment blotchy.
    "power_bloc_identity": dict(
        folder="central_identity_pillars_icons", size=200, mode="cutout", fill=0.92, grade_strength=0.5,
        entity_dir="common/power_bloc_identities", field="icon",
        style="{subject}, one ornate readable object, " + PAINTED),
    # Read only from `texture =` (Decree.GetTexture, DecreeType.GetTexture).
    "decree": dict(
        folder="decree", size=158, mode="medallion", fill=0.78,
        # Vanilla's disc, measured on its bare pixels: centre, then edge.
        disc=((28, 42, 42), (25, 44, 50)),
        entity_dir="common/decrees", field="texture",
        # Graded to vanilla decrees' objects at two points (median and 90th
        # percentile): a median grade left ours dull (#561 in-game review).
        grade="spread",
        style="{subject}, one chunky compact object, bright warm lighting, " + PAINTED),
    # Journal entries (150 px, JournalEntry.GetIcon; all three places that draw
    # one read `icon =`). Vanilla's are painted single objects on transparency
    # in event_icons/, shown at 100 px inside the panel's round frame and at 40
    # px in the journal list. Measured on the 17 files: objects span 0.79-0.98
    # of the side (median 0.89), median saturation 0.45 and value 0.57. The
    # Nuclear Weapons entry's mushroom_cloud.dds is a hand-made 1024 px file
    # and is not part of this registry.
    # Prestige goods (256 px, PrestigeGood.GetTexture, read from `texture =`).
    # Vanilla's 74 are its goods icons' painted objects made finer: the same
    # kind of thing (tea for tea, a car for a car), so the two read as a pair
    # in the company panel. Measured: objects span 0.84-0.97 of the side
    # (median 0.92), centred. The folder is vanilla's, so the grade and the
    # sheet's neighbours come from its icons. The mod's 15 used to be their
    # base good's icon under a gold halo (gen_prestige_icons.py).
    # grade_strength 0.4, as for the silver Space Race craft: at 0.7 the
    # silver airliner turned copper and the olive tank a pale lime.
    "prestige_good": dict(
        folder="goods_icons/prestige_goods", size=256, mode="cutout", fill=0.92, grade_strength=0.4,
        entity_dir="common/prestige_goods", field="texture",
        style="{subject}, one chunky readable object, " + PAINTED),
    "journal_entry": dict(
        folder="event_icons", size=150, mode="cutout", fill=0.89, panel_preview=True,
        entity_dir="common/journal_entries", field="icon",
        style="{subject}, one chunky readable object, " + PAINTED),
    # The nine Space Race milestones share one painted disc, so the family
    # reads as one in the journal list. The disc is round, not square: the
    # panel draws the icon inside a round frame and a square's corners would
    # poke out of it. `backdrop` is rendered like an icon (its own prompt, its
    # own candidates, a `seed` picked in review) and lives here, not in ICONS,
    # because it is no journal entry. Subjects render on white as usual; the
    # space comes only from the backdrop at compose time, since a starfield in
    # a subject would go through the cut-out. The objects sit smaller than in
    # the plain category (`fill`) so the disc shows around them. The folder
    # grade is gentler here (0.4, not 0.7): it multiplies a near-grey object's
    # saturation many times over, and turned the orbital satellite's silver
    # sphere copper.
    "journal_entry_space": dict(
        folder="event_icons", size=150, mode="backed", fill=0.66, panel_preview=True, grade_strength=0.4,
        entity_dir="common/journal_entries", field="icon",
        backdrop=dict(
            seed=3, seeds=4,
            prompt=("a painted deep-space scene, a dark navy-blue night sky with soft indigo and teal "
                    "nebula clouds and many fine stars, the curved blue-lit edge of a planet across the "
                    "lower third, no objects, no spacecraft, stylized hand-painted video game background "
                    "art with visible brush strokes")),
        style="{subject}, one chunky readable object, " + PAINTED),
    # Power bloc principles (210 px, PowerBlocPrinciple.GetIcon): painted
    # objects on transparency, one per group, which all its tiers share.
    # Vanilla's span 0.72-0.85 of the side (median 0.79).
    "principle": dict(
        folder="principles_icons", size=210, mode="cutout", fill=0.79,
        entity_dir="common/power_bloc_principles", field="icon",
        style="{subject}, one chunky readable object, " + PAINTED),
    # Basic industries (company_basic_*): written to company_icons/ beside vanilla's basic_*.
    "company": dict(
        folder="company_icons", size=256, mode="cutout", fill=0.96, grade_strength=0.5,
        entity_dir="common/company_types", field="icon", style=EMBLEM),
    # Historical companies that showed gen_placeholder_company_icons.py's
    # PLACEHOLDER card. GUI-hosted in effect: each company and its flagship
    # building already point at historical_company_icons/<key>.dds, so the key
    # is the file name, `now` is the card being replaced, and writing the file
    # is the whole change (gui=(): no .gui file draws them).
    "company_logo": dict(
        folder="company_icons/historical_company_icons", size=256, mode="cutout", fill=0.93, grade_strength=0.5,
        grade_folder="company_icons/historical_company_icons", gui=(), style=EMBLEM),
    # The sidebar's small buttons (main_hud/*_btn.dds, 76 px, drawn at 42x40 by
    # sidepanel_button_small): vanilla's are painted single objects on
    # transparency (a book, a globe, coins), spanning ~0.7 of the side. The
    # Timeline Extended window's launcher is the mod's only one
    # (docs/systems/te_systems_window_gui_icons.md); its brief asked for gold
    # line art, but vanilla's buttons are painted, so it is painted too.
    # main_hud also holds the top bar and speedometer art, so grading follows
    # event_icons' painted objects instead.
    "sidebar_button": dict(
        folder="main_hud", root="gfx/interface", size=76, mode="cutout", fill=0.74, grade_strength=0.5,
        grade_folder="event_icons", neighbours="../main_hud",
        gui=("gui/te_systems_window.gui",),
        style="{subject}, one chunky readable object, " + PAINTED),
    # The UN's journal and Diplomacy-tab GUI (docs/systems/un_gui_icons.md):
    # icons that belong to no game entity, only to a `texture =` line in a .gui
    # file, so the category is GUI-hosted (`gui`): each entry names the
    # placeholder it replaces (`now`), and `wire` is done by hand in the .gui.
    # They show at 32-40 px, so every subject is one bold object. All are
    # written at 150 px (alert_icons' size) to un_icons/, a folder vanilla
    # lacks, so grading and the sheet's neighbours come from alert_icons.
    # Agencies and the topics that are not an agency's share one drawn disc
    # (draw_disc): UN blue enamel under a gold rim, with warm or light
    # symbols on it for contrast.
    "un_disc": dict(
        folder="un_icons", size=150, mode="backed", fill=0.64, grade_strength=0.5,
        grade_folder="alert_icons", neighbours="alert_icons",
        gui=("gui/journal_entry_widgets/un_overview_widget.gui", "gui/journal_entry_widgets/un_layout_widget.gui"),
        backdrop=dict(drawn=dict(centre=(104, 150, 205), edge=(36, 70, 118),
                                 rim_light=(246, 214, 138), rim_dark=(150, 104, 42))),
        style=UN_STYLE),
    # The authority tiers: one colonnade in five stages, as plain cut-outs.
    # grade_strength 0.4: the silver portico would turn copper at 0.7 (see
    # journal_entry_space).
    "un_tier": dict(
        folder="un_icons", size=150, mode="cutout", fill=0.92, grade_strength=0.4,
        grade_folder="alert_icons", neighbours="alert_icons",
        gui=("gui/journal_entry_widgets/un_overview_widget.gui",),
        style=UN_STYLE),
    # Pieces the derived UN icons are built from; reviewed like icons, never
    # written as icons of their own.
    "un_part": dict(
        folder="un_icons", size=150, mode="cutout", fill=0.96, grade_strength=0.5, part=True,
        grade_folder="alert_icons", neighbours="alert_icons", gui=(),
        style=UN_STYLE),
    # Membership, the crisis alert and the vacant seat: the emblem part, greyed
    # or not, under a vanilla mark. Colour means the membership's benefits
    # apply, grey that they do not; the mark says which state.
    "un_member": dict(
        folder="un_icons", size=150, mode="derived", grade_folder="alert_icons", neighbours="alert_icons",
        gui=("gui/journal_entry_widgets/un_overview_widget.gui",)),
    # The system panels' GUI icons (the style pass, #573-#583), made as the
    # UN's were: each system's own list, docs/systems/<system>_gui_icons.md,
    # names the placeholder and the proposed path. Per system, a `_part`
    # category holds the emblems its states share, a derived `_state` category
    # draws each state as its emblem under a mark, tint or break, and a plain
    # cut-out category holds the icons that are one object of their own.
    **{f"{sys_}_part": dict(folder=folder, size=150, mode="cutout", fill=0.96, grade_strength=0.5, part=True,
                            grade_folder="alert_icons", neighbours="alert_icons", gui=(), style=UN_STYLE)
       for sys_, folder in _GUI_SYSTEMS.items()},
    **{f"{sys_}_state": dict(folder=folder, size=150, mode="derived", grade_folder="alert_icons",
                             neighbours="alert_icons", gui=(_GUI_FILES[sys_],))
       for sys_, folder in _GUI_SYSTEMS.items()},
    **{sys_: dict(folder=folder, size=150, mode="cutout", fill=0.92, grade_strength=0.5,
                  grade_folder="alert_icons", neighbours="alert_icons", gui=(_GUI_FILES[sys_],), style=UN_STYLE)
       for sys_, folder in _GUI_SYSTEMS.items()},
}


def prompt_for(cat: str, subject: str, style: str | None = None) -> str:
    return (style or CATEGORIES[cat]["style"]).format(subject=subject) + ", no text, no writing, no letters"


def entry_prompt(cat: str, entry: dict) -> str:
    """An entry's prompt: its subject in its own "style" if it has one, else in the category's."""
    return prompt_for(cat, entry["subject"], entry.get("style"))


def restyle_strengths(cat: str, entry: dict) -> tuple:
    """A restyle entry's candidates: the img2img strength of each, by candidate number."""
    return tuple(entry.get("strengths", CATEGORIES[cat].get("restyle_strengths", ())))


def icon_path(cat: str, key: str) -> str:
    """The mod path an accepted icon is written to and wired as."""
    spec = CATEGORIES[cat]
    return f"{spec.get('root', 'gfx/interface/icons')}/{spec['folder']}/{key}.dds"


_GI = "gfx/interface/icons"
_BI = f"{_GI}/building_icons"

ICONS: dict[str, dict[str, dict]] = {
    "technology": {
        # Mod-added techs that borrowed a vanilla icon (135 of them the
        # mass_communication newspapers), by era then category.
        # era 6
        "bombing_aircraft": {"subject": "a large twin-engine propeller bomber with a glazed glass nose, painted plain olive drab with no markings", "seed": 0},
        "combined_arms": {"subject": "a small olive-green tank, a field gun and a propeller fighter plane grouped together as models on one round base", "seed": 1},
        "cryptography": {"subject": "a wooden-cased rotor cipher machine with a keyboard and three brass rotor wheels", "seed": 1},
        "motorized_artillery": {"subject": "a field howitzer mounted on the back of an olive-green military truck", "seed": 0},
        "naval_convoy_defense": {"subject": "a grey destroyer warship escorting a rust-red cargo freighter, as a tabletop model on a patch of sea", "seed": 1},
        "naval_fire_control_systems": {"subject": "a grey naval rangefinder director with a long horizontal optical arm and brass eyepieces", "seed": 0},
        "nuclear_weapons": {"subject": "a squat dark grey aerial atomic bomb with a boxy tail fin", "seed": 1},
        "radar": {"subject": "a curved steel-mesh radar dish antenna on a lattice tower base", "seed": 1},
        "rocketry": {"subject": "a slender plain grey liquid-fuel rocket with four fins, standing upright on a small launch stand", "seed": 0},
        "semiautomatic_rifle": {"subject": "a semi-automatic infantry rifle with a walnut stock, lying diagonally", "seed": 1},
        "sonar": {"subject": "a grey steel sonar console with a round glowing green scope showing a sweep line and one bright blip, headphones hanging from its side", "seed": 1},
        "aluminum_mass_production": {"subject": "a neat stack of shiny silver aluminium ingots", "seed": 0},
        "bergius_process": {"subject": "a tall riveted steel high-pressure reactor vessel with pipes, beside a heap of black coal", "seed": 1},
        "fluorescent_lamps": {"subject": "a long glowing white fluorescent tube lamp in a metal ceiling fixture", "seed": 0},
        "isoprene": {"subject": "a glass laboratory flask of clear liquid beside a coil of black synthetic rubber hose", "seed": 0},
        "modern_automotive_technology": {"subject": "a rounded 1930s sedan car in dark green with chrome bumpers", "seed": 1},
        "modern_chemical_processes": {"subject": "a compact model of gleaming steel chemical reaction columns connected by pipes", "seed": 1},
        "modern_materials": {"subject": "a spool of shiny white nylon thread beside a translucent green fibreglass panel", "seed": 0},
        "modern_skyscrapers": {"subject": "a model of a slender steel-framed skyscraper with rows of windows and a mast on top", "seed": 1},
        "modern_tools": {"subject": "a small orange forklift truck lifting a wooden pallet", "seed": 1},
        "personal_appliances": {"subject": "a rounded white enamel refrigerator with a chrome handle", "seed": 0},
        "stainless_steel_mass_production": {"subject": "a gleaming stainless steel cooking pot on a stack of polished steel plates", "seed": 1},
        "television": {"subject": "a wooden-cabinet 1940s television set with a small rounded screen showing only a soft grey glow", "seed": 1},
        "advanced_agricultural_statistics": {"subject": "a sheaf of golden wheat standing upright beside a clipboard with a hand-drawn rising bar chart", "seed": 0},
        "animation": {"subject": "a stack of transparent animation cels, each showing a red ball at a different height, with a pencil beside them", "seed": 1},
        "art_deco_architecture": {"subject": "an ornate cream stone Art Deco building facade with gold sunburst motifs and stepped setbacks", "seed": 0},
        "commercial_aviation": {"subject": "a silver twin-engine propeller airliner with a rounded fuselage and a row of windows", "seed": 0},
        "computing_machines": {"subject": "a grey early computer cabinet with rows of glowing vacuum tubes and toggle switches", "seed": 0},
        "consumer_credit": {"subject": "a shiny new wooden radio set with a small blank paper tag tied to its handle with string", "seed": 1},
        "intergovernmental_organizations": {"subject": "a round wooden conference table with empty chairs placed evenly around it", "seed": 1},
        "keynesian_economics": {"subject": "a workman's shovel leaning on a small stack of plain cream-coloured government bonds tied with red ribbon", "seed": 0},
        "marketing_research": {"subject": "a clipboard with a tick-box questionnaire and a pencil, beside a small wicker shopping basket", "seed": 0},
        "mass_media": {"subject": "a large chrome studio microphone on a stand beside a wooden radio set", "seed": 1},
        "modern_management_techniques": {"subject": "a chrome stopwatch lying on a clipboard with a flowchart", "seed": 0},
        "modern_vaccines": {"subject": "a glass syringe beside a small brown glass vaccine vial with a grey rubber stopper", "seed": 1},
        "public_works_programs": {"subject": "a miniature concrete arch dam with water pouring through its spillway", "seed": 1},
        "rural_electrification": {"subject": "a single tall wooden utility pole with glass insulators on its crossarm, its wire running to a small farmhouse with a lit window", "seed": 0},
        # era 7
        "ICBMs": {"subject": "a tall light grey intercontinental ballistic missile with a black nose cone, standing upright in an open concrete silo", "seed": 0},
        "advanced_military_aircraft": {"subject": "a silver swept-wing jet fighter plane", "seed": 1},
        "advanced_submarine_technology": {"subject": "a sleek black nuclear submarine, as a tabletop model", "seed": 1},
        "anti_sub_warfare": {"subject": "a grey naval depth-charge barrel beside a slim homing torpedo", "seed": 0},
        "guided_missiles": {"subject": "a slender light grey guided missile with red-tipped fins on a launch rail", "seed": 0},
        "inertial_navigation_systems": {"subject": "a brass gyroscope: a spinning steel disc inside three nested brass rings set at right angles to each other", "seed": 0},
        "jet_engine_technology": {"subject": "a polished metal jet engine with its fan blades visible in the intake", "seed": 1},
        "nuclear_energy": {"subject": "a bundle of uranium fuel rods in a steel frame, glowing faint blue", "seed": 1},
        "recon_satellites": {"subject": "a boxy gold-foil-wrapped reconnaissance satellite with a large camera lens and solar panel wings", "seed": 1},
        "satellite_communications": {"subject": "a round communications satellite with a large silver dish antenna and blue solar panel wings", "seed": 1},
        "space_exploration": {"subject": "a small silver space capsule with round portholes and a dark heat shield", "seed": 3},
        "tactical_nuclear_weapons": {"subject": "a compact olive-green nuclear artillery shell with a yellow band around it", "seed": 0},
        "green_revolution": {"subject": "a bundle of short-stalked golden wheat heavy with grain, tied with twine", "seed": 0},
        "integrated_circuits": {"subject": "a small black integrated circuit chip with two rows of silver pins", "seed": 1},
        "laser_technology": {"subject": "a metal laser tube emitting a thin bright red beam", "seed": 0},
        "mainframe_computers": {"subject": "a tall grey mainframe computer cabinet with two spinning tape reels", "seed": 1},
        "photocopiers": {"subject": "a boxy beige office photocopier with a blank sheet of paper coming out of its tray", "seed": 1},
        "plastic_mass_production": {"subject": "a bright red plastic bucket full of colourful plastic bottles and containers", "seed": 0},
        "prefabricated_construction": {"subject": "a small yellow crane lowering a grey concrete wall panel with a window opening onto a half-built boxy building", "seed": 2},
        "transistors": {"subject": "a single large vintage transistor with a black casing and three metal legs", "seed": 0},
        "anti_war_movement": {"subject": "a wooden protest placard painted with a white dove", "seed": 1},
        "antibiotic_mass_production": {"subject": "a glass petri dish of blue-green penicillin mould beside a brown medicine bottle", "seed": 0},
        "civil_rights_movement": {"subject": "two hands, one dark brown and one pale, gripping each other in a firm handshake", "seed": 2},
        "contraceptive_pill": {"subject": "a round pastel-blue pill dispenser holding a ring of small white pills", "seed": 1},
        "modern_urban_planning": {"subject": "an architect's scale model of a planned city block with tidy streets, green parks and pale stone buildings", "seed": 1},
        "pollution_control": {"subject": "a squat brick factory chimney capped with a big round green air filter, a sprig of green leaves at its base", "seed": 0},
        "pop_culture": {"subject": "a colourful jukebox with glowing coloured tubes", "seed": 1},
        "second_wave_feminism": {"subject": "a bold purple Venus symbol, a ring with a short cross beneath it, a small raised fist inside the ring", "seed": 3},
        "television_broadcasting": {"subject": "a heavy black studio television camera on a wheeled pedestal", "seed": 0},
        # era 8
        "advanced_materials_armor": {"subject": "a thick slab of layered composite armour plate with blocky reactive armour tiles bolted on", "seed": 1},
        "infrared_night_vision": {"subject": "a pair of olive-green military night-vision goggles with glowing green lenses", "seed": 1},
        "precision_guided_munitions": {"subject": "a dark grey laser-guided bomb with a pointed black seeker head and small steering fins at both ends", "seed": 0},
        "predictive_logistics": {"subject": "a stack of olive-green military supply crates on a pallet with a small glowing blue data tablet on top", "seed": 1},
        "stealth_technology": {"subject": "an angular black stealth aircraft built of flat faceted panels", "seed": 1},
        "supersonic_aircraft": {"subject": "a silver delta-wing supersonic jet with a needle nose", "seed": 1},
        "advanced_assembly_lines": {"subject": "a short conveyor belt carrying identical small metal parts under a hydraulic press", "seed": 1},
        "barcodes_and_scanners": {"subject": "a black handheld barcode scanner casting a red laser line across a cardboard box", "seed": 1},
        "cellular_networks": {"subject": "the top of a grey mobile phone mast, three tall grey rectangular antenna panels clamped around a steel pole with thick black cables", "seed": 1},
        "computer_aided_design": {"subject": "a glowing blue wireframe model of a machine gear floating above a drafting table", "seed": 0},
        "computer_networks": {"subject": "a beige network hub box with many blue cables plugged into it", "seed": 0},
        "fiber_optics": {"subject": "a thick fan of glass fibre-optic strands spraying out of a black cable end like a brush, every tip glowing bright blue", "seed": 0},
        "gene_splicing": {"subject": "a glowing DNA double helix being cut by a small pair of steel scissors", "seed": 0},
        "microprocessor": {"subject": "a square computer processor chip with gold contact pins, seen from above at an angle", "seed": 1},
        "personal_computers": {"subject": "a beige 1980s personal computer with a boxy monitor and keyboard, its screen dark and blank", "seed": 1},
        "robotics": {"subject": "an orange six-axis industrial robot arm on a round grey floor base, a welding torch fixed to the end of the arm", "seed": 0},
        "containerization": {"subject": "a stack of three steel shipping containers in red, blue and rust orange", "seed": 1},
        "environmental_movement": {"subject": "a small blue-and-green Earth globe showing its continents and oceans, with a young green sapling sprouting from its top", "seed": 0},
        "modern_pharmaceuticals": {"subject": "a brown glass pharmacy bottle spilling colourful capsules and tablets", "seed": 1},
        "sexual_revolution": {"subject": "an open round pastel pink contraceptive pill compact holding a ring of small pale yellow tablets", "seed": 0},
        "video_games": {"subject": "a chunky grey game controller with a directional pad and round red buttons", "seed": 1},
        # era 9
        "advanced_body_armor": {"subject": "an olive-green modern ballistic vest with ceramic plate pouches", "seed": 1},
        "automated_surveillance": {"subject": "a grey pan-and-tilt security camera mounted on a metal pole", "seed": 1},
        "military_grade_cybersecurity": {"subject": "a heavy olive-green armoured steel padlock with a glowing green keyhole and thin green circuit lines etched into its body", "seed": 3},
        "missile_defense_systems": {"subject": "a truck-mounted anti-missile launcher with four upright box launch tubes", "seed": 3},
        "network_centric_warfare": {"subject": "a glowing blue holographic map table with small military unit markers linked by lines of light", "seed": 1},
        "rapid_deployment_forces": {"subject": "an open military parachute canopy carrying a small olive-green supply crate", "seed": 1},
        "unmanned_aerial_vehicles": {"subject": "a slender grey military drone with long straight wings and a bulbous camera nose", "seed": 1},
        "biotechnology": {"subject": "a glass test tube holding a glowing green seedling with its roots in liquid", "seed": 1},
        "clean_energy_technologies": {"subject": "a pale grey three-bladed wind turbine standing beside a tilted blue solar panel", "seed": 1},
        "cloud_computing": {"subject": "a soft blue-grey cloud floating above a black rack of server units with blinking lights", "seed": 1},
        "digital_telecommunications": {"subject": "a grey metal telephone switching cabinet with rows of small green indicator lights and thick bundles of blue cables plugged into its front", "seed": 1},
        "e-commerce": {"subject": "a cardboard delivery parcel resting on a closed silver laptop", "seed": 0},
        "early_nanotechnology": {"subject": "a tiny glowing hexagonal carbon nanotube held in steel tweezers", "seed": 0},
        "hydraulic_fracturing": {"subject": "a cutaway block of layered brown and grey rock with a steel well pipe running down its middle, bright blue fluid spreading sideways into cracks in one rock layer", "seed": 0},
        "supply_chain_management": {"subject": "a length of heavy steel chain with small cardboard parcels hanging from its links", "seed": 1},
        "wireless_internet": {"subject": "a black wireless router with two antennas radiating glowing curved signal arcs", "seed": 1},
        "world_wide_web": {"subject": "a spider web of glowing blue light strands with a small globe at its centre", "seed": 1},
        "LGBTQ_rights_movement": {"subject": "a rainbow-striped silk ribbon looped into an awareness ribbon", "seed": 1},
        "advanced_workflow_optimization": {"subject": "interlocking brass gears with a chrome stopwatch set into the largest gear", "seed": 1},
        "cybersecurity": {"subject": "a blue shield emblem with a keyhole, made of glowing circuit-board lines", "seed": 1},
        "digital_education": {"subject": "a black graduation mortarboard cap resting on a dark grey tablet computer with a glowing blue screen", "seed": 1},
        "digital_entertainment": {"subject": "a pair of chunky black over-ear headphones beside a sleek black game controller with plain round red buttons", "seed": 0},
        "globalization": {"subject": "a small globe ringed by a cargo ship and a jet airliner circling it", "seed": 0},
        "knowledge_economy": {"subject": "a stack of books with a glowing light bulb on top", "seed": 1},
        "social_justice_movements": {"subject": "a brass scale of justice with two perfectly level pans", "seed": 0},
        "social_media": {"subject": "a black smartphone with a glowing blue screen, colourful speech bubbles and heart symbols floating up from it", "seed": 0},
        "terrorism_and_anti_terrorism": {"subject": "an empty matte black tactical helmet with night-vision goggles on its front mount, resting on top of a dark grey ballistic shield lying flat", "seed": 1},
        "virtual_reality": {"subject": "a dark grey virtual reality headset with black padding and a strap", "seed": 1},
        # era 10
        "cyber_warfare": {"subject": "a black computer server rack cracked open with red glowing light pouring out", "seed": 1},
        "directed_energy_defenses": {"subject": "a turret-mounted laser cannon on a grey armoured base, firing a thin bright beam upward", "seed": 0},
        "electronic_warfare": {"subject": "an olive-green military jammer box with antennas sending out jagged zigzag waves", "seed": 2},
        "hypersonic_weapons": {"subject": "a sleek black arrowhead-shaped hypersonic glide vehicle trailing a streak of glowing plasma", "seed": 0},
        "jadc2": {"subject": "a glowing holographic globe surrounded by small models of a ship, a jet, a tank and a satellite linked by lines of light", "seed": 1},
        "reusable_rocketry": {"subject": "a tall slim grey cylindrical rocket booster with a flat top, standing upright on four thin splayed landing legs, a small flame and smoke at its base", "seed": 0},
        "additive_manufacturing": {"subject": "a desktop 3D printer printing an orange plastic gear layer by layer", "seed": 1},
        "advanced_structural_engineering": {"subject": "a short thick steel I-beam welded to a black woven carbon-fibre plate, a bright orange glowing weld seam along the joint with a few sparks", "seed": 3},
        "electric_vehicles": {"subject": "a sleek dark blue electric car plugged into a green charging post by a thick cable", "seed": 1},
        "generative_ai": {"subject": "a silver robotic hand holding a paintbrush over a small canvas of colourful strokes", "seed": 3},
        "internet_of_things": {"subject": "a round grey smart home hub surrounded by a thermostat, a light bulb and a small sensor linked by glowing lines", "seed": 0},
        "machine_learning": {"subject": "a small silver robot sitting and reading an open book", "seed": 0},
        "decline_of_organized_religion": {"subject": "an empty dusty wooden pew with a cobweb and a single unlit candle", "seed": 3},
        "mental_health_awareness": {"subject": "a small potted plant sprouting fresh green leaves, with a green awareness ribbon tied around the pot", "seed": 1},
        "mrna_therapeutics": {"subject": "a small glass vaccine vial with a glowing pink ribbon of RNA curling around it", "seed": 1},
        "telemedicine": {"subject": "a stethoscope draped over a dark grey tablet computer whose dark screen shows one glowing blue heartbeat line", "seed": 1},
        "universal_basic_income": {"subject": "an open hand holding a small brown paper pay envelope with a few plain gold coins spilling out of it", "seed": 0},
        # era 11
        "asteroid_mining": {"subject": "a grey asteroid chunk with a small drilling rig on top and glinting veins of metal ore", "seed": 1},
        "augmented_reality_warfare": {"subject": "a military helmet with a glowing transparent visor display", "seed": 0},
        "bioenhanced_soldiers": {"subject": "a glowing green serum injector beside an olive-green military helmet", "seed": 1},
        "directed_energy_weapons": {"subject": "a futuristic rifle-shaped energy weapon with glowing blue coils", "seed": 2},
        "fusion_power": {"subject": "a doughnut-shaped tokamak fusion reactor with a glowing pink plasma ring inside", "seed": 0},
        "quantum_communications": {"subject": "two glowing deep violet crystal orbs linked by a bright twisting beam of cyan light", "seed": 1},
        "space_militarization": {"subject": "a dark grey armed military satellite with folded solar wings and a small missile rack", "seed": 1},
        "swarm_technology": {"subject": "a tight cluster of small black quadcopter drones flying in formation", "seed": 0},
        "abyssal_plain_mining": {"subject": "a yellow deep-sea mining crawler with a vacuum nozzle, on dark seabed strewn with black nodules", "seed": 1},
        "autonomous_vehicles": {"subject": "a small silver self-driving car with a black sensor dome on its roof", "seed": 1},
        "genetic_engineering": {"subject": "a glowing DNA double helix inside a laboratory glass vial", "seed": 1},
        "modern_material_science": {"subject": "a sheet of shimmering iridescent hexagonal graphene draped over a steel block", "seed": 1},
        "quantum_computing": {"subject": "a golden chandelier-like quantum computer with tiers of copper tubes and cables", "seed": 1},
        "smart_grids": {"subject": "an electricity pylon with glowing blue data pulses running along its cables", "seed": 1},
        "synthetic_biology": {"subject": "a glowing green engineered cell in a petri dish with a pipette above it", "seed": 0},
        "biohacking_and_human_augmentation": {"subject": "a sleek chrome prosthetic arm with glowing blue joints", "seed": 1},
        "brain_computer_interfaces": {"subject": "a model of a human brain with a small circuit chip and fine wires attached", "seed": 1},
        "lab-grown_food": {"subject": "a round petri dish holding a pink cultured meat steak", "seed": 0},
        "personalized_medicine": {"subject": "a single capsule pill with a DNA helix pattern on its shell", "seed": 1},
        "universal_digital_identity": {"subject": "a plain pale blue identity card with a glowing blue fingerprint and a gold chip", "seed": 1},
        # era 12
        "antimatter_production": {"subject": "a glowing magnetic containment bottle with a bright violet sphere suspended inside", "seed": 1},
        "compact_fusion_reactors": {"subject": "a compact barrel-sized cylindrical fusion reactor core glowing blue-white at its centre", "seed": 1},
        "fusion_batteries": {"subject": "a chunky cylindrical battery cell with a glowing sun-like core behind a glass window", "seed": 3},
        "orbital_weapon_platforms": {"subject": "a large armed space station with a long cannon barrel and solar panel wings", "seed": 1},
        "space_based_solar_power": {"subject": "a vast orbiting solar panel array sending a thin red energy beam downward", "seed": 0},
        "space_elevator": {"subject": "a small blue-and-green Earth globe with a thin glowing cable rising from its equator up to a small grey space station above it, a cylindrical climber pod partway along the cable", "seed": 0},
        "advanced_nanofabrication": {"subject": "a tiny precise crystal lattice being built by a glowing needle-tipped robotic arm", "seed": 0},
        "artificial_intelligence": {"subject": "a silver humanoid robot head with a glowing blue brain visible under a glass dome", "seed": 1},
        "molecular_assemblers": {"subject": "a cluster of coloured atom spheres being snapped together by tiny robotic arms", "seed": 0},
        "orbital_manufacturing": {"subject": "a space station module with a robotic arm assembling a glowing crystal", "seed": 1},
        "programmable_matter": {"subject": "a shimmering silver liquid-metal blob reshaping itself into a cube and a sphere", "seed": 1},
        "quantum_materials": {"subject": "a glowing iridescent crystal block levitating above a superconducting disc", "seed": 1},
        "biological_immortality": {"subject": "a glass hourglass with a green sprouting sprig growing inside it", "seed": 1},
        "mind_backups": {"subject": "a glowing crystal data cube with the faint shape of a brain inside", "seed": 1},
        "neural_lace": {"subject": "a delicate glowing silver mesh net shaped like a human brain", "seed": 1},
        "post-scarcity_economy": {"subject": "an overflowing cornucopia horn spilling fruit, bread and gleaming gadgets", "seed": 1},
        "space_colonization": {"subject": "a domed habitat colony on a red rocky planet surface", "seed": 0},
        "telepathic_communities": {"subject": "two glowing translucent human heads facing each other, linked by a ribbon of light", "seed": 1},
    },
    "treaty_article": {
        # Mod-added treaty articles on a borrowed icon (18 on offer_embassy).
        "nuclear_security_assistance": {"subject": "a nuclear warhead locked inside a steel cage with a big padlock", "seed": 1},
        "nuclear_arms_limitation": {"subject": "a brass balance scale with one short grey missile standing on each pan", "seed": 1},
        "request_influence": {"subject": "a small figure bowing and offering up a silver key with both hands", "seed": 0},
        "crisis_resolution": {"subject": "a cracked stone pillar bound with a bandage and propped up by a wooden brace", "seed": 0},
        "extend_influence": {"subject": "a bronze hand pushing a black chess pawn forward on a small chessboard", "seed": 3},
        "education_aid": {"subject": "a stack of schoolbooks with a red apple on top", "seed": 1},
        "healthcare_aid": {"subject": "a black leather doctor's bag with a stethoscope draped over it", "seed": 1},
        "security_aid": {"subject": "a steel riot shield and a black police baton crossed together", "seed": 1},
        "development_assistance": {"subject": "a small brick schoolhouse under construction with wooden scaffolding", "seed": 0},
        "science_aid": {"subject": "a brass microscope standing on a wooden crate", "seed": 0},
        "science_aid_2": {"subject": "a brass microscope, a glass flask and a steel gear packed together in an open wooden crate", "seed": 1},
        "suppress_subject_liberty": {"subject": "a chess pawn bound with a heavy iron chain and padlock", "seed": 0},
        "nuclear_disarmament": {"subject": "a nuclear missile warhead cracked open, with a large steel wrench resting across it", "seed": 1},
        "nuclear_program_aid": {"subject": "a lead-lined steel case of glowing green uranium pellets", "seed": 1},
        "intelligence_sharing_pact": {"subject": "a manila dossier folder sealed with red wax, a brass magnifying glass lying on top", "seed": 1},
        "joint_military_exercises": {"subject": "two crossed rifles with two different-coloured steel helmets hung on them", "seed": 0},
        "join_united_nations": {"subject": "a small pale blue globe on a brass stand, wreathed in two olive branches", "seed": 1},
        "nuclear_program_pause": {"subject": "a nuclear warhead frozen inside a block of blue ice", "seed": 1},
        "disband_company": {"subject": "a small brick factory model cracked cleanly into two halves", "seed": 0},
        "seize_company": {"subject": "a hand grabbing a small brick factory model by its chimney", "seed": 1},
        "minority_protection": {"subject": "three small figures huddled together beneath a large raised steel shield", "seed": 1},
        "free_port_concession": {"subject": "an open brass padlock hanging from a ship's anchor", "seed": 1},
        "corporate_concessions": {"subject": "a brown leather briefcase with a gold key resting on top", "seed": 0},
        "enforce_privatization": {"subject": "a small brick factory model with a blank price tag tied to its chimney", "seed": 1},
        "religious_mission_rights": {"subject": "a closed brown leather book with a brass clasp and a plain unmarked cover, a wooden walking staff leaning against it", "seed": 0},
        "demilitarized_zone": {"subject": "an upturned steel army helmet with red poppies growing out of it", "seed": 1},
        "forced_disarmament": {"subject": "a heap of rifles and steel helmets bound together by a padlocked chain", "seed": 0},
        "cultural_exchange_program": {"subject": "two hands passing a small painted vase between them", "seed": 1},
        "enforce_emissions_reduction": {"subject": "a factory chimney with a big green cork stopper in its top", "seed": 0},
        "nuclear_guarantee": {"subject": "a large open steel umbrella with a yellow-and-black radiation trefoil painted on its canopy", "seed": 0},
        "population_transfer": {"subject": "a heap of worn suitcases and cloth bundles tied with rope", "seed": 1},
        # The monetary articles, on law icons until now.
        "currency_peg": {"subject": "a big gold coin and a smaller silver coin joined by a short heavy brass chain, both stamped with a small star", "seed": 2},
        # Round 1 (no marks named) stamped $ on a coin in all three candidates.
        "imposed_currency_peg": {"subject": "a small plain copper coin stamped with a small star, chained to a big plain gold coin stamped with a small star by a heavy iron chain with a closed iron padlock on it", "seed": None},
        "swap_line": {"subject": "two short stacks of plain coins side by side, one gold and one silver, with one gold coin and one silver coin swapped on top of the other stack", "seed": 1},
        "lender_of_last_resort": {"subject": "a red and orange striped life ring buoy around a short stack of plain gold coins stamped with a small star", "seed": 0},
        "debt_receivership": {"subject": "a thick brown leather ledger book bound shut with a heavy iron chain and a closed iron padlock", "seed": 1},
    },
    "diplomatic_action": {
        # Mod-added diplomatic actions on a borrowed icon. Three have a better
        # vanilla match than the one they borrowed.
        "voluntary_union": {"subject": "two bronze hands clasped in a handshake above a small white classical government building", "seed": 1},
        "voluntary_union_decentralized": {"subject": "an open bronze palm holding three small thatched village huts", "seed": 1},
        "irr_seek_war_blessing": {"subject": "a kneeling bronze figure presenting a sword across both open palms", "seed": 1},
        # The Nuclear Guarantee article's umbrella, furled.
        "nd_withdraw_umbrella_action": {"subject": "a closed, tightly furled steel umbrella with a yellow-and-black radiation trefoil on its fabric, lying on its side", "seed": 0},
        # The covert operations (pacts) had no icon at all; a black glove or mask marks the series.
        "covert_election_interference_action": {"subject": "a black-gloved hand slipping a folded paper ballot into a wooden ballot box", "seed": 0},
        "covert_financial_subversion_action": {"subject": "a black-gloved hand pulling a coin from the bottom of a teetering stack of gold coins", "seed": 1},
        "covert_infrastructure_sabotage_action": {"subject": "a bundle of dynamite sticks with a lit fuse strapped to a small steel bridge", "seed": 1},
        "covert_comms_disruption_action": {"subject": "an old black telephone with its cord snipped by a pair of red-handled pliers", "seed": 1},
        "covert_industrial_espionage_action": {"subject": "a black-gloved hand pulling a rolled blue blueprint out of a small brick factory's window", "seed": 2},
        "covert_military_espionage_action": {"subject": "a small brass spy camera photographing a folded military map with pins in it", "seed": 1},
        "covert_influence_campaign_action": {"subject": "a brass microphone draped with a black domino mask", "seed": 0},
        "covert_ideological_subversion_action": {"subject": "a stone pillar cracked through by a creeping black vine", "seed": 0},
        "covert_destabilization_action": {"subject": "a tower of wooden blocks toppling over, nudged by a black-gloved finger", "seed": 1},
        "covert_regime_change_action": {"subject": "a black-gloved hand lifting a small golden crown off a red cushion", "seed": 1},
        "covert_nuclear_sabotage_action": {"subject": "a pair of wire cutters snipping a red wire on a grey nuclear warhead marked with a yellow-and-black radiation trefoil", "seed": 1},
        "covert_space_espionage_action": {"subject": "a grey rocket standing on its launch pad with a small brass spy camera on a tripod aimed at it", "seed": 1},
        "covert_cultivate_assets_action": {"subject": "two hands in shadow exchanging a sealed brown envelope", "seed": 3},
        "covert_secure_material_action": {"subject": "a black-gloved hand gripping the handle of a lead-lined steel case marked with a radiation trefoil", "seed": 2},
        # Other actions that had no icon.
        "decolonize_diplo_action": {"subject": "an open brass birdcage with a small bird flying out of its door", "seed": 1},
        "annex_subject_peaceful": {"subject": "two small stone houses joined under a single shared roof", "seed": 1},
        "diplomatic_alignment": {"subject": "two bronze arrows side by side pointing upward, bound together with a red ribbon", "seed": 1},
        "humanitarian_aid": {"subject": "a wooden supply crate with a loaf of bread and a rolled brown blanket on top", "seed": 0},
        "nd_nuclear_warning_action": {"subject": "a brown envelope closed with a black wax seal stamped with a radiation trefoil", "seed": 0},
        "nd_nuclear_ultimatum_action": {"subject": "a bronze megaphone with a yellow-and-black radiation trefoil on its bell", "seed": 0},
        "nd_repudiate_pledge_action": {"subject": "a brown parchment scroll with a radiation trefoil, torn in two", "seed": 0},
        "nuke_diplo_action": {"subject": "a small bronze mushroom cloud rising over a cluster of factory chimneys", "seed": 1},
        "tactical_nuke_diplo_action": {"subject": "a small bronze mushroom cloud rising over a battlefield trench with a field gun", "seed": 1},
        "un_secure_commitment_action": {"subject": "two hands shaking above a small green wooden block", "seed": 1},
        "un_secure_commitment_against_action": {"subject": "two hands shaking above a small plain red square tile", "seed": 0},
        "un_lobby_for_action": {"subject": "a hand dropping a green voting card into a pale blue ballot box", "seed": 0},
        "un_lobby_against_action": {"subject": "a hand dropping a red voting card into a pale blue ballot box", "seed": 0},
        "colonial_culture_change": {"use": "gfx/interface/icons/diplomatic_action_icons/change_culture.dds"},  # culture change; the borrowed crest was religion's
        "force_cultural_acceptance": {"use": "gfx/interface/icons/diplomatic_action_icons/force_culture.dds"},  # the culture crest; the borrowed one was religion's
        "force_cultural_adoption": {"use": "gfx/interface/icons/diplomatic_action_icons/force_culture.dds"},  # the culture crest; the borrowed one was religion's
    },
    "building": {
        # Mod-added buildings on another building's (or a good's) icon. Company
        # buildings are left out: flagships carry their company's own logo by
        # design (docs/vanilla/vanilla_company_buildings_reference.md).
        # Except the generic flagships of the basic company types, which all
        # sat on vanilla's skyscraper.dds: their companies' logos are the basic
        # industry icons, shared by several companies, so each gets a painting
        # of what it does. Not the eleven retired ones the monthly cleanup removes.
        # Skipped for lettering or watermarks: rd_complex s0, granary s0, vintner s1, lumber s1.
        "building_generic_rd_complex": {"subject": "a modern research campus of glass-walled laboratory buildings around a green courtyard, a small satellite dish on one roof", "seed": 1},
        "building_generic_logistics_hub": {"subject": "a large logistics warehouse complex with rows of loading docks, parked lorries and stacked shipping containers", "seed": 1},
        "building_generic_industrial_zone": {"subject": "a cluster of factory halls with sawtooth roofs, pipe racks and small chimneys, linked by roads and a rail spur", "seed": 0},
        "building_generic_materials_lab": {"subject": "a materials research laboratory with a domed furnace building and racks of shiny metal sheets and carbon-fibre rolls outside", "seed": 0},
        "building_generic_robotics_institute": {"subject": "a modern institute building with tall windows showing orange industrial robot arms at work inside, a test yard beside it", "seed": 0},
        "building_generic_data_fortress": {"subject": "a low fortified concrete data centre bunker with rows of cooling fans on its roof inside a high security fence", "seed": 1},
        "building_generic_media_hq": {"subject": "a modern media headquarters tower with large satellite dishes and broadcast antennas on its roof", "seed": 0},
        "building_generic_power_hub": {"subject": "a compact modern power station with a substation yard of transformers and high-voltage pylons leading away", "seed": 0},
        "building_generic_proving_grounds": {"subject": "a military proving ground in open scrubland, a concrete observation bunker beside a dirt test track with a tank on it", "seed": 1},
        "building_generic_resource_depository": {"subject": "a fortified depository of low concrete vaults with heavy steel doors, beside heaps of ore and stacks of metal ingots", "seed": 1},
        "building_generic_granary_complex": {"subject": "a grain storage complex of tall round concrete silos beside a rail siding, golden wheat fields around it", "seed": 1},
        # Round 1 showed no cloth.
        "building_generic_textile_depot": {"subject": "a brick textile warehouse whose yard is crossed by long lines hung with bolts of bright red, blue and yellow cloth drying in the sun, round dyeing vats beside them", "seed": None},
        "building_generic_cold_storage": {"subject": "a large windowless refrigerated warehouse with insulated walls, lorries backed up to its loading bays", "seed": 1},
        "building_generic_paper_mill_complex": {"subject": "a pulp and paper mill beside a river, with log piles, a tall chimney and big rolls of paper stacked in the yard", "seed": 1},
        "building_generic_foundry_complex": {"subject": "a sprawling steel foundry with blast furnaces, molten metal glowing orange and tall smoking chimneys", "seed": 0},
        "building_generic_machine_shop": {"subject": "a large brick machine shop with big windows, lathes visible inside and heaps of gears and machine parts in the yard", "seed": 0},
        "building_generic_chem_works": {"subject": "a chemical works with tall distillation columns, spherical storage tanks and tangled pipework", "seed": 0},
        "building_generic_tank_farm": {"subject": "an oil tank farm with rows of large round storage tanks joined by pipelines, a small refinery tower beside them", "seed": 0},
        "building_generic_ordnance_depot": {"subject": "a military ordnance depot of earth-covered concrete bunkers behind barbed wire, crates of shells stacked outside", "seed": 0},
        "building_generic_motor_works": {"subject": "a motor vehicle factory with a long assembly hall and rows of new cars parked in its yard", "seed": 0},
        "building_generic_dry_dock": {"subject": "a large dry dock with a steel ship hull inside it, tall cranes standing over it at the waterside", "seed": 1},
        "building_generic_arsenal": {"subject": "a fortified brick arsenal with crenellated walls, cannons and stacked weapon crates in its courtyard", "seed": 0},
        "building_generic_fish_market": {"subject": "a harbourside fish market hall with fishing boats moored at its quay and crates of fish on the stones", "seed": 1},
        "building_generic_colonial_depot": {"subject": "a colonial trading depot of whitewashed warehouses with a veranda, tea chests and bales stacked on a wharf", "seed": 0},
        "building_generic_export_warehouse": {"subject": "a bonded export warehouse on a riverside quay, sacks of coffee and bales of cotton being loaded onto a cargo ship", "seed": 1},
        "building_generic_electronics_lab": {"subject": "a modern electronics laboratory building with a radio mast on its roof and rows of lit windows", "seed": 0},
        # Round 1: ASSAY OFFICE on the facade (s0), a watermark (s1).
        "building_generic_assay_office": {"subject": "a squat solid stone strongroom building with barred windows and a heavy iron door, a small wooden cart loaded with gold bullion bars at its door, blank unmarked walls", "seed": None},
        "building_generic_ore_processing": {"subject": "an ore processing plant with crushers, conveyor belts and heaps of crushed ore beside a smelter chimney", "seed": 0},
        "building_generic_mineral_refinery": {"subject": "a mineral refinery with tall leaching tanks, conveyor belts and heaps of white and yellow mineral powder", "seed": 0},
        "building_generic_silk_exchange": {"subject": "an East Asian trading house with curved tiled roofs, bales of raw silk and dyed silk cloth stacked outside", "seed": 0},
        "building_generic_vintner_hall": {"subject": "a stone winery hall among vineyards, rows of oak barrels outside and grape vines on the hillside", "seed": 0},
        # Round 1: EMPORIUM (s0) and a lettered plaque (s1).
        "building_generic_furniture_showroom": {"subject": "a two-storey brick furniture workshop with tall plain glass windows showing chairs and tables inside, stacked timber planks in the yard behind it, blank unmarked walls", "seed": None},
        "building_generic_lumber_yard": {"subject": "an industrial sawmill and timber yard with stacks of sawn planks and piles of logs beside a river", "seed": 0},
        "building_generic_dye_fiber_park": {"subject": "a campus of small laboratories and pilot plants with pipes and tanks, spools of brightly dyed fibre in the yard", "seed": 1},
        # Wonders: the landmark alone, as vanilla draws its monuments.
        "building_wonder_golden_gate_bridge": {"subject": "the Golden Gate Bridge, its red-orange suspension towers and cables spanning a blue strait between green headlands, a little fog rolling in", "seed": 0},
        "building_wonder_empire_state_building": {"subject": "the Empire State Building, a limestone Art Deco skyscraper with stepped setbacks and a slender mast, towering over Manhattan's city blocks", "seed": 0},
        "building_wonder_sydney_opera_house": {"subject": "the Sydney Opera House, its white shell-shaped roof sails on a harbour point surrounded by blue water", "seed": 0},
        "building_wonder_cn_tower": {"subject": "the CN Tower of Toronto, a very tall slender concrete tower with a round observation pod near its top, on a lakeshore beside city blocks", "seed": 0},
        "building_wonder_hoover_dam": {"subject": "the Hoover Dam, a massive curved concrete arch dam wedged in a narrow desert canyon, a blue reservoir behind it and four intake towers", "seed": 1},
        # s4 is not a plain render: FLUX draws the Pentagon with eight sides, so s2 was warped
        # to five and repainted at img2img strength 0.56 (the spec's building review).
        "building_wonder_pentagon": {"subject": "the Pentagon seen from high above: a five-sided pentagon-shaped grey building with five straight outer walls and five corners, five nested pentagonal rings around a small green pentagonal courtyard, surrounded by lawns, parking lots and highways", "seed": 4},
        "building_wonder_aswan_high_dam": {"subject": "the Aswan High Dam seen from above: a very long straight embankment dam of piled grey rock with a road along its crest, across the wide Nile, a vast blue reservoir lake on one side and a hydroelectric power station at its foot, yellow desert all around", "seed": 1},
        "building_wonder_tokyo_tower": {"subject": "Tokyo Tower, an orange-and-white painted steel lattice tower rising above dense city blocks", "seed": 0},
        "building_wonder_moscow_state_university": {"subject": "the main building of Moscow State University, a tall Stalinist wedding-cake skyscraper with a gilded spire and symmetrical stepped wings, above formal gardens", "seed": 0},
        "building_wonder_berlin_tv_tower": {"subject": "the Berlin TV Tower, a tall concrete needle with a silver sphere near its top and a red-and-white antenna, above a wide city square", "seed": 0},
        "building_wonder_azadi_tower": {"subject": "the Azadi Tower of Tehran, a white marble monument shaped like an inverted Y with a tall arched gateway, in a large oval plaza with fountains", "seed": 1},
        "building_wonder_kenyatta_icc": {"subject": "the Kenyatta International Convention Centre in Nairobi, a round terracotta-red tower topped by a flat helipad disc, beside a cone-roofed amphitheatre hall", "seed": 2},
        "building_wonder_burj_khalifa": {"subject": "the Burj Khalifa, an extremely tall silver-glass needle skyscraper with stepped setbacks, towering over a desert city", "seed": 0},
        "building_wonder_world_trade_center": {"subject": "the twin towers of the World Trade Center, two identical tall square silver skyscrapers side by side at the tip of Manhattan, by the harbour", "seed": 0},
        "building_wonder_lotus_temple": {"subject": "the Lotus Temple in Delhi, a white marble building shaped like a half-open lotus flower of pointed petals, surrounded by nine blue pools and green gardens", "seed": 0},
        "building_wonder_itaipu_dam": {"subject": "the Itaipu Dam, a very long concrete buttress dam with a huge spillway of white rushing water, a wide river and green rainforest", "seed": 0},
        "building_wonder_petronas_towers": {"subject": "the Petronas Twin Towers skyscrapers of Kuala Lumpur joined by their skybridge", "seed": 1},
        "building_wonder_basilica_of_our_lady_of_peace": {"subject": "the Basilica of Our Lady of Peace in Yamoussoukro, a huge church with a great grey-blue dome and curved colonnades embracing a plaza, among palm trees", "seed": 1},
        "building_wonder_three_gorges_dam": {"subject": "the Three Gorges Dam, an enormous straight concrete dam across the Yangtze river between steep green mountain gorges, with a staircase of ship locks beside it", "seed": 0},
        "building_wonder_channel_tunnel": {"subject": "a sleek white high-speed train entering the round concrete portal of the Channel Tunnel at the foot of green hills, the grey sea and white cliffs nearby", "seed": 0},
        "building_wonder_taipei_101": {"subject": "Taipei 101, a blue-green glass skyscraper built of stacked flared segments like a bamboo stalk, above the city with green mountains behind", "seed": 0},
        "building_wonder_lotte_world_tower": {"subject": "the Lotte World Tower in Seoul, a very tall pale tapering glass skyscraper with a slit crown, by a lake in the city", "seed": 1},
        "building_wonder_gardens_by_the_bay": {"subject": "Gardens by the Bay in Singapore, tall tree-shaped steel towers covered in green plants and linked by a skywalk, beside two curved glass conservatory domes on the waterfront", "seed": 1},
        "building_wonder_abraj_al_bait": {"subject": "the Abraj Al-Bait clock tower, a massive pale skyscraper with a huge plain white clock face on each side and a golden crescent spire, rising above a cluster of high-rise hotel towers", "seed": 1},
        "building_wonder_shanghai_tower": {"subject": "the Shanghai Tower, a twisting spiralling glass supertall skyscraper above the Pudong skyline beside a river", "seed": 0},
        "building_wonder_fast_telescope": {"subject": "the FAST radio telescope, a gigantic round dish of silver panels filling a bowl-shaped karst valley among green conical hills, six tall cable towers around its rim", "seed": 0},
        "building_wonder_statue_of_unity": {"subject": "the Statue of Unity, a colossal bronze statue of a standing man in a long shawl on a tall plinth on a river island, a dam and green hills behind", "seed": 1},
        "building_wonder_golden_bridge": {"subject": "the Golden Bridge of Vietnam, a gold-coloured curving footbridge held up by two giant moss-covered stone hands rising out of a green forested mountainside", "seed": 1},
        "building_wonder_large_hadron_collider": {"subject": "the Large Hadron Collider's giant particle detector: a huge round machine of red, blue and silver steel sectors radiating like wheel spokes from a central beam pipe, in a vast underground cavern with scaffolding and tiny workers", "seed": 3},
        "building_wonder_svalbard_seed_vault": {"subject": "the Svalbard Global Seed Vault, a narrow concrete entrance wedge jutting out of a snowy arctic mountainside above a fjord, its front glittering with turquoise light", "seed": 1},
        # s4 is not a plain render: FLUX drew one arm, parallel arms or a fan, never a wide V.
        # A one-arm render was rotated on its ground plane into a 90-degree V and repainted at
        # img2img strength 0.5 (the spec's building review).
        "building_wonder_ligo": {"subject": "the LIGO observatory seen from very high altitude behind its corner station: two extremely long thin straight pale concrete tubes forming a giant V, diverging from a small white building in the foreground, one running away to the upper left and one to the upper right, each several kilometres long across a vast patchwork of flat farm fields and forest until they vanish at the horizon, tiny roads and farmhouses", "seed": 4},
        "building_wonder_peace_palace": {"subject": "the Peace Palace in The Hague, a neo-Renaissance palace of red brick and pale stone with a tall clock tower and grey slate roofs, in formal gardens", "seed": 0},
        "building_wonder_palais_des_nations": {"subject": "the Palais des Nations in Geneva, a long pale-stone neoclassical palace with colonnaded wings in a green park, Lake Geneva and snowy mountains beyond", "seed": 0},
        # Fictional: a continent-wide union's seat, cross-shaped like the Berlaymont.
        "building_wonder_continental_union_hq": {"subject": "a modern headquarters of four curved glass wings in a cross shape around a central atrium, beside a round assembly hall with a copper dome, in a landscaped plaza with a long reflecting pool", "seed": 0},
        # System buildings, all on government administration, barracks, urban
        # center or power plant art. The UN is described, not named: its name
        # brings the flag row and the emblem.
        "building_un_headquarters": {"subject": "a tall slim skyscraper slab of green glass beside a low white assembly hall with a shallow dome, on a riverbank with city towers behind", "seed": 0},
        "building_power_bloc_hq": {"subject": "a huge ring-shaped modern headquarters of white concrete and dark glass around a circular garden courtyard, a tall communications mast beside it and a wide plaza in front", "seed": 0},
        "building_grand_monument": {"subject": "a colossal triumphal stone column topped by a gilded winged figure, rising from a paved ceremonial plaza with steps, flowerbeds and a colonnade", "seed": 1},
        "building_resettlement_colony": {"subject": "a small frontier land office with a porch, surrounded by rows of new timber houses and freshly fenced plots going up, piles of lumber and covered wagons, open grassland and forest beyond", "seed": 1},
        "building_strategic_reserve_hub": {"subject": "a large fenced national stockpile depot: rows of long concrete warehouses, a tall grain elevator, round white fuel storage tanks and stacked crates, with a railway siding", "seed": 0},
        "building_strategic_reserve_silo": {"subject": "a remote storage depot of three tall round concrete silos and a grass-covered earth bunker with a steel door, behind a wire fence in open countryside", "seed": 0},
        "building_military_base": {"subject": "a modern military base: rows of low barracks around a parade ground, vehicle sheds, a concrete bunker and a watchtower inside a walled perimeter, green grass and trees around it, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_state_youth_centers": {"subject": "a modern community youth centre, a low building of red brick and glass with a gymnasium roof, beside a running track and a football pitch with small figures playing", "seed": 0},
        "building_solar_receiver": {"subject": "a vast circular field of dark mesh antenna panels in rows on a desert plain around a central control building, a pale beam of light descending from the sky onto its centre", "seed": 0},
        "building_antimatter_facility": {"subject": "a futuristic research complex around a huge ring-shaped particle accelerator, with a round steel and glass containment dome at its centre holding a small glowing violet sphere", "seed": 0},
        "building_antimatter_engine": {"subject": "a colossal futuristic rocket engine on a concrete test stand, its polished steel nozzle glowing violet, with fuel tanks, pipes and a gantry beside it", "seed": 0},
        "te_construction_market_site": {"subject": "a construction site with cranes, scaffolding and stacked building materials", "seed": KEEP},  # a construction camp fits
        # Industry variants: vanilla's industrial layout, the plant behind and
        # its product large in the foreground. They were on goods icons.
        "building_synthetics_plant_silk": {"subject": "a chemical plant with a large bolt of shiny synthetic fabric in the foreground", "seed": KEEP},  # vanilla's synthetics plant fits
        "building_synthetics_plant_coal": {"subject": "a direct air capture facility: a long low flat-roofed steel building whose whole front is a wall of big round black fans, beside rows of squat white storage tanks, all low to the ground in green forest, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_synthetics_plant_wood": {"subject": "a modern resin panel factory: long halls with big resin vats and pipes, a yard of stacked honey-brown panels being loaded onto trucks, green trees around it, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_synthetics_plant_sugar": {"subject": "a clean white chemical plant with round steel reactor tanks and pipework, beside green sugar cane fields, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_synthetics_plant_meat": {"subject": "a clean white laboratory factory with rows of round steel bioreactor tanks linked by pipes and glass-roofed lab halls, green lawns around it, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_synthetics_plant_fruit": {"subject": "a glass vertical farm building with stacked shelves of green plants under pink grow lights, with a wooden crate of red apples and oranges in the foreground", "seed": 0},
        "building_synthetics_plant_drinks": {"subject": "a beverage plant with tall steel mixing tanks, pipes and a loading dock with delivery trucks, beside green orchards, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_synthetics_plant_biomass": {"subject": "a biorefinery with tall steel fermentation towers and tanks beside green fields, with a heap of golden grain in the foreground", "seed": 1},
        "building_electrics_industry_radio": {"subject": "an electronics factory with a tall lattice radio mast and satellite dishes on its roof, a row of tall transmitter towers beside it, green hills around it, loosely hand-painted with visible brush strokes", "seed": 1},
        # Mines, on the five vanilla mine icons: the ore's colour and form tell
        # them apart, in the same layout.
        "building_manganese_mine": {"subject": "a mine with a timber headframe and ore sheds on dark rocky ground, with a heap of lumpy black-brown manganese ore nodules in the foreground", "seed": 0},
        "building_chromium_mine": {"subject": "a terraced open-pit mine in dark grey rock, a processing plant and a long ore conveyor at its rim, loosely hand-painted with visible brush strokes", "seed": 2},
        "building_specialty_alloy_metal_mine": {"subject": "a mountainside mine with a steel headframe and ore bins, with a bundle of dull grey tungsten rods and dark metallic ore crystals in the foreground", "seed": 1},
        "building_copper_mine": {"subject": "a huge stepped open-pit copper mine with terraced orange-brown walls and a turquoise pool at the bottom, with a stack of shiny reddish copper ingots in the foreground", "seed": 0},
        "building_bauxite_mine": {"subject": "an open-pit mine cut into deep red earth with trucks on its terraces, with a heap of red-brown bauxite ore pebbles in the foreground", "seed": 1},
        "building_precious_minor_base_metal_mine": {"subject": "a hillside mine entrance with a timber headframe and ore carts, with a stack of silver bars and dull grey tin ingots in the foreground", "seed": 0},
        "building_nickel_cobalt_mine": {"subject": "an open-pit mine with rust-orange earthen walls, with a heap of silvery nickel pellets and deep blue cobalt ore crystals in the foreground", "seed": 0},
        "building_lithium_mine": {"subject": "lithium brine evaporation ponds, rectangles of bright turquoise, green and white on a high desert salt flat with mountains behind, with a heap of fine white lithium powder in the foreground", "seed": 0},
        "building_rare_earth_metals_mine": {"subject": "a large open-pit mine with pale grey terraces and tailings ponds, with a small pile of shiny silvery rare earth metal chunks and glittering purple crystals in the foreground", "seed": 1},
        "building_platinum_group_metals_mine": {"subject": "a deep mine on a rocky hillside: a tall steel headframe, shaft buildings and a refinery with pale grey ore heaps, loosely hand-painted with visible brush strokes", "seed": 2},
        "building_graphite_mine": {"subject": "an open-pit mine with black glittering walls, with a heap of shiny black graphite flakes in the foreground", "seed": 1},
        "building_phosphate_mine": {"subject": "a wide open-cast mine with pale tan terraces and a long conveyor belt, with a heap of pale grey-tan phosphate rock pellets in the foreground", "seed": 0},
        "building_potash_mine": {"subject": "a mine with a tall headframe beside huge pink salt heaps, with a pile of pink and red potash salt crystals in the foreground", "seed": 0},
        "building_industrial_mineral_salt_mine": {"subject": "shallow salt evaporation pans and white salt heaps with conveyor belts, with a pile of large white salt crystals and grey gypsum chunks in the foreground", "seed": 1},
        # Mod buildings that shared another mod building's icon (the 2026-10-02 audit).
        # Each megaproject construction site gets its own: the building's subject,
        # half-built. The orbital ones are in ORBIT: in the building style both
        # solar collector renders were small arrays over a map.
        "building_consciousness_network": {"subject": "a futuristic government data centre: a low dark glass building with a glowing blue dome of light on its roof, linked by glowing blue fibre-optic lines to small relay nodes across green countryside, loosely hand-painted with visible brush strokes", "seed": 0},
        "building_consciousness_network_construction_site": {"subject": "the construction site of a futuristic data centre: a half-built low glass building in scaffolding with tower cranes, the steel ribs of a dome going up on its roof, cable trenches dug across green countryside, loosely hand-painted with visible brush strokes", "seed": 0},
        "building_mind_upload_nexus": {"subject": "a sleek futuristic white tower clad in glass, rings of glowing teal server racks visible through its walls, a beam of pale light rising from its crown, in a landscaped plaza, loosely hand-painted with visible brush strokes", "seed": 0},
        "building_mind_upload_nexus_construction_site": {"subject": "a half-built sleek white glass tower wrapped in scaffolding with tower cranes, its lower floors already glowing teal, stacks of building materials in a landscaped plaza, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_orbital_battlestation": {"subject": "a large armoured military space station: a dark grey ring-shaped hull bristling with long gun turrets and missile pods, small craft docking at it, plain unmarked hull", "style": ORBIT, "seed": 3},
        "building_orbital_battlestation_construction_site": {"subject": "a half-assembled ring-shaped military space station: an open lattice skeleton with only part of its dark grey armour plating fitted, small construction craft and floating girders around it", "style": ORBIT, "seed": 3},
        "building_antimatter_warhead_plant": {"subject": "a high-security weapons plant in a desert: low windowless concrete bunkers behind double fences and watchtowers, a round armoured reactor dome glowing violet at its centre, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_nanofabrication_center": {"subject": "a modern fabrication campus of white cleanroom halls with sawtooth roofs and rooftop air vents around a glass dome glowing pale blue, green parkland around it, with a heap of shimmering silver-grey metallic powder in the foreground, loosely hand-painted with visible brush strokes", "seed": 0},
        "building_nanofabrication_center_construction_site": {"subject": "the construction site of a modern fabrication campus: half-built white cleanroom halls on bare steel frames, scaffolding and tower cranes, the ribs of a glass dome going up in the middle, loosely hand-painted with visible brush strokes", "seed": 1},
        "building_solar_collector": {"subject": "a huge orbital solar power station: a vast square array of dark blue solar panels on a golden lattice frame, a round collector dish at its centre glowing with gathered sunlight and sending a pale beam down toward the Earth", "style": ORBIT, "seed": 1},
        "building_solar_collector_construction_site": {"subject": "a half-built orbital solar power station: a vast square golden lattice frame with only its first rows of dark blue solar panels fitted and the rest still bare girders, small construction craft carrying more panels to it", "style": ORBIT, "seed": 1},
        "building_antimatter_facility_construction_site": {"subject": "the construction site of a futuristic research complex on orange desert sand: a wide round ring-shaped building of pale concrete half-built, part of its curved roof still bare steel girders, the steel frame of a round glass dome going up at its centre, tower cranes and scaffolding, stacks of materials, loosely hand-painted with visible brush strokes", "seed": 0},
        "building_space_program": {"subject": "a national space agency headquarters: a modern glass mission control building with a big white satellite dish on its roof and a tall white rocket standing upright on display in the plaza in front, landscaped grounds, loosely hand-painted with visible brush strokes", "seed": 0},
        # Wonders: the landmark alone.
        # A plain render of ITER is a grey hall that reads as a warehouse; the cutaway shows the reactor.
        # The ISS in the building style was a flat orange cross over a map.
        "building_wonder_iter": {"subject": "a cutaway of the ITER fusion reactor building among the green hills of southern France, its roof open to show a giant doughnut-shaped tokamak reactor ring of steel magnet coils glowing with pink-violet plasma inside the concrete hall, cranes and tiny workers around it", "seed": 1},
        "building_wonder_international_space_station": {"subject": "the International Space Station: a long grey central truss carrying four pairs of huge dark golden solar panel wings, white cylindrical modules clustered at its middle", "style": ORBIT, "seed": 3},
        "building_wonder_kennedy_space_center": {"subject": "the Kennedy Space Center: a huge plain grey-white boxy rocket assembly building beside a launch pad where a white rocket stands in its steel gantry tower, flat green Florida marshland, lagoons and the sea", "seed": 1},
        # The mod's own icons from before the pipeline (2024-25): kept, refitted to
        # the gold frame (`restyle`). Each subject describes the picture as it is.
        # The owner of each formerly shared picture keeps it.
        # s0's QUALITY TESTED sign was painted out of the raw (retouched lettering, 2026-10-02).
        "building_electrics_industry_appliances": {"restyle": f"{_BI}/appliance.dds", "subject": "a bright factory floor where workers in green overalls assemble cream-coloured refrigerators and toasters", "seed": 0},
        "building_ocean_mine": {"restyle": f"{_BI}/deep_sea_mine.dds", "crop": 0.1, "subject": "a deep-sea mining machine with glowing lamps crawling over the dark ocean floor, cables rising toward the surface", "seed": 2},
        "building_fusion_plant": {"restyle": f"{_BI}/fusion_plant.dds", "crop": 0.1, "subject": "a futuristic fusion power plant: a tall silver cylindrical reactor with a glowing blue ring at its base, surrounded by white technical buildings and pipes", "seed": 2},
        "building_highway": {"restyle": f"{_BI}/highway.dds", "subject": "a wide multi-lane highway full of cars and trucks running toward the horizon under an overpass, green trees on both sides", "seed": 0},
        "building_renewable_energy_plant": {"restyle": f"{_BI}/renewable_plant.dds", "crop": 0.1, "subject": "a renewable energy plant: white wind turbines and fields of solar panels around a white power building, green fields", "seed": 0},
        "building_software_industry": {"restyle": f"{_BI}/software.dds", "crop": 0.06, "subject": "a modern dark glass office building at night with rows of lit windows and a glowing blue sign on its facade", "seed": 0},
        "building_synthetics_plant_oil": {"restyle": f"{_BI}/synth_oil.dds", "subject": "an old smoky synthetic fuel refinery with tall towers and pipes, workers and a tank train in the foreground, sepia haze", "seed": 0},
        "building_synthetics_plant_rubber": {"restyle": f"{_BI}/synth_rubber.dds", "subject": "a synthetic rubber works: workers by a conveyor of rubber sheets in front of a chemical plant with domed tanks and chimneys, olive-green haze", "seed": 3},
        "building_space_mine": {"restyle": f"{_BI}/space_base.dds", "crop": 0.1, "subject": "an extraplanetary base: white domed habitats, solar panels and a small rover on a red rocky planet at dusk, a moon in the sky", "seed": 2},
        "building_aerospace_industry": {"restyle": f"{_BI}/space.dds", "crop": 0.06, "subject": "a rocket lifting off from its launch tower at night in a burst of orange flame and smoke, a radar dish nearby", "seed": 2},
        "building_space_elevator": {"restyle": f"{_BI}/space_elevator.dds", "subject": "a space elevator: a single thin tether rising from the Earth's curved horizon up into black starry space, a climber pod on it", "seed": 0},
        "building_space_elevator_construction_site": {"restyle": f"{_BI}/space_elevator_construction_site.dds", "crop": 0.15, "subject": "the construction site of a space elevator's base tower: a tall steel lattice tower in scaffolding with cranes, workers and stacked materials", "seed": 2},
        "building_nuclear_plant": {"restyle": f"{_BI}/nuclear_plant.dds", "crop": 0.1, "subject": "a nuclear power plant with two large concrete cooling towers releasing white steam, reactor buildings and power lines, green fields and a river", "seed": 0},
        # Redrawn in the building style (owner, 2026-10-02: "make new ones for hydro, and any
        # other existing ones you don't think are great"): the flat vectors, the interiors
        # and the still lifes; the comment names the restyle each replaced. The old picture
        # won for appliances (every redraw was a warehouse of crates), the deep-sea mine
        # (the owner likes the ocean floor) and the highway (the interchanges made no sense).
        "building_airport": {"subject": "a modern airport: a long curved glass terminal with a tall control tower, plain white jet airliners parked at its gates and one taking off from a long runway, green fields around", "seed": 3},  # fallback: restyle airport.dds
        "building_synthetics_plant_opium": {"subject": "a clean modern pharmaceutical plant: white factory buildings with gleaming steel tanks and pipes and a glass-walled laboratory wing, green lawns and trees around, loosely hand-painted with visible brush strokes", "seed": 0},  # fallback: restyle drugs.dds
        "building_hydro_plant": {"subject": "a hydroelectric power plant: a tall curved concrete arch dam across a river gorge between wooded green hills, white water rushing from its spillways, a power station at its foot and power lines on steel pylons climbing the hillside, a blue reservoir lake behind", "seed": 0},  # fallback: restyle hydro_plant.dds, crop 0.18
        "building_national_park": {"subject": "a national park: a log-cabin ranger station with a wooden lookout tower beside a calm blue lake, a winding trail through pine forests, snowy mountains behind", "seed": 0},  # fallback: restyle national_park.dds
        "building_robotics_industry": {"subject": "a modern robotics factory: long white halls with sawtooth roofs, through the open end of one hall a line of big yellow robotic arms welding car bodies in showers of sparks, loosely hand-painted with visible brush strokes", "seed": 1},  # fallback: restyle robot.dds, crop 0.08
        "building_electronic_components_and_semiconductor_industry": {"subject": "a semiconductor plant: a big boxy windowless white cleanroom building with rows of rooftop air handlers and silver exhaust stacks, a glass entrance hall glowing golden, car parks and green lawns around, loosely hand-painted with visible brush strokes", "seed": 1},  # fallback: restyle semiconductor.dds
        "building_tourism_industry": {"subject": "a seaside resort: a tall white hotel with balconies above a sandy beach lined with rows of colourful parasols, palm trees and a promenade with cafes, a turquoise sea with small sailing boats", "seed": 2},  # fallback: restyle tourism.dds
        "building_network_infrastructure": {"subject": "a telecommunications hub: a tall red-and-white steel radio mast and several big white satellite dishes beside a low grey exchange building, telephone poles and cable trenches running away across green countryside toward a distant city", "seed": 0},  # fallback: restyle network.dds
        "building_advanced_material_fabricator": {"subject": "a high-tech materials plant: a sleek dark grey factory hall with a glowing orange furnace seen through its open doors, stacks of black carbon-fibre sheets and dark composite panels in its yard, loosely hand-painted with visible brush strokes", "seed": 0},  # fallback: restyle advanced_materials.dds
    },
    "mobilization_option": {
        # Mod-added options on a vanilla icon (14 on machinegunners), by group.
        # The emboss bevels every edge, so a thin part (a beam, an antenna,
        # radio waves) comes out as a dark hairline: ask for thick shapes.
        # supplies: the four logistics tiers share the crate stack, as vanilla's
        # supply tiers share their tins.
        "mobilization_option_home_communications": {"subject": "a chunky old telephone handset with a thick coiled cord beside a sealed envelope", "seed": 1},
        "mobilization_option_robotic_assistance": {"subject": "a chunky industrial robot arm with thick jointed segments and a two-fingered gripper claw", "seed": 1},
        "mobilization_option_logistical_support": {"subject": "a stack of three wooden supply crates on a short railway flatcar, side view", "seed": 1},
        "mobilization_option_extensive_logistical_support": {"subject": "a stack of three wooden supply crates in front of a canvas-covered military cargo truck, side view", "seed": 3},
        "mobilization_option_modern_logistical_support": {"subject": "a big round parachute canopy with thick cords lowering a stack of three wooden supply crates", "seed": 0},
        "mobilization_option_advanced_logistical_support": {"subject": "a stack of three wooden supply crates beside a cone-shaped space capsule with a round hatch", "seed": 1},
        # supplements
        "mobilization_option_coffee": {"subject": "a coffee cup on a saucer with thick wavy steam rising from it and three coffee beans beside it", "seed": 1},
        "mobilization_option_appliances": {"subject": "an electric kettle and a pop-up toaster side by side", "seed": 0},
        # transport
        "mobilization_option_air_transport": {"subject": "a big four-engine propeller cargo plane with a high wing, side view", "seed": 2},
        "mobilization_option_space_transport": {"subject": "a tall multi-stage rocket lifting off on a thick billowing exhaust plume", "seed": 1},
        "mobilization_option_entrenchment": {"subject": "a spade stuck upright in a wall of stacked sandbags", "seed": 1},
        # reconnaissance
        "mobilization_option_space_recon": {"subject": "a reconnaissance satellite: a boxy body with a big round camera lens and two wide rectangular solar panel wings", "seed": 1},
        "mobilization_option_molecular_scanners": {"subject": "a big magnifying glass held over a molecule model of five linked balls", "seed": 0},
        # special weapons
        "mobilization_option_radar": {"subject": "a big dish-shaped radar antenna tilted upward on a thick pedestal mount", "seed": 1},
        "mobilization_option_night_vision_gear": {"subject": "an empty combat helmet with night vision goggles of two thick tube lenses mounted on its front", "seed": 1},
        "mobilization_option_missile_defense_system": {"subject": "a truck-mounted launcher with four thick box-shaped missile canisters raised at a steep angle, one missile leaving on a short thick flame", "seed": 1},
        "mobilization_option_directed_energy_defenses": {"subject": "a squat turret on a thick pedestal firing one long thick straight beam diagonally up to the top right corner, where a small missile bursts into a star-shaped flash", "seed": 1},
        "mobilization_option_cyberwarfare_team": {"subject": "an open laptop computer with a big skull and crossbones on its screen", "seed": 1},
        "mobilization_option_electronic_warfare": {"subject": "a military backpack radio set with a thick antenna, a big bold lightning bolt striking diagonally across its front", "seed": 0},
        "mobilization_option_exoskeleton_suits": {"subject": "a soldier striding in a bulky powered exoskeleton suit with thick mechanical leg and arm braces, side view", "seed": 1},
        # medic support
        "mobilization_option_medevac_helicopters": {"subject": "a medical helicopter with a big cross on its side and thick rotor blades, side view", "seed": 1},
        # training. The two enhancement options run on the augmentation laws and
        # consume robotics and electronics: cybernetic, not chemical.
        "mobilization_option_voluntary_enhancement": {"subject": "a big open robotic hand with thick jointed metal fingers, palm facing forward", "seed": 1},
        "mobilization_option_mandatory_enhancement": {"subject": "a jointed robotic forearm and mechanical hand with a heavy iron shackle and chain locked around its wrist", "seed": 0},
        "mobilization_option_jungle_combat_training": {"subject": "a machete crossed over one big broad banana leaf", "seed": 1},
        "mobilization_option_mountain_combat_training": {"subject": "an ice axe crossed over a jagged snow-capped mountain peak", "seed": 1},
        "mobilization_option_flight_simulators": {"subject": "an aircraft control joystick with a trigger and thumb buttons, a small jet fighter plane flying above it", "seed": 1},
        "mobilization_option_amphibious_warfare": {"subject": "a flat-bottomed military landing craft with its front ramp lowered onto a sandy beach, side view", "seed": 1},
    },
    # Mod-added ideologies on another ideology's (or an IG's) icon. The 24
    # ideology_custom_religion_* variants keep their base ideology's icon, as
    # vanilla's variants do (papal_paternalistic on paternalistic).
    # An ideology an IG and a leader both hold shares its subject, as vanilla's
    # do; the same subject and seed render the same symbol in both looks.
    "ideology": {
        "ideology_multicultural_ig": {"subject": "three hands clasping each other's wrists to form a triangle", "seed": 0},
        "ideology_anti_colonialist": {"subject": "a raised clenched fist in front of a globe with its continents, a thick white outline all around the fist separating it from the globe", "seed": 1},
        "ideology_islamic_inheritance": {"subject": "an open book resting on an X-shaped folding wooden book stand, a small crescent moon above it", "seed": 1},
    },
    # Mod-added decrees: 13 on road_maintenance, greenest grass on vanilla's
    # greener grass wagon, the resettlement drive on social mobility's ladder.
    # Vanilla's encourage_* decrees share a mint-green arrow; the migration
    # ones here borrow it.
    "decree": {
        "decree_war_propaganda": {"subject": "a large brass megaphone with a red cloth streamer tied to its handle", "seed": 1},
        "decree_political_patronage": {"subject": "a gilded key on a red ribbon passed from one hand to another", "seed": 0},
        "decree_bureaucracy_reform": {"subject": "a tall stack of manila folders tied with red tape, a pair of steel scissors beside it", "seed": 0},
        "decree_cultural_emigration_initiative": {"subject": "a battered brown leather suitcase with a big mint-green arrow pointing away to the right", "seed": 1},
        "decree_pollution_control": {"subject": "a squat brick factory chimney capped with a big mint-green air filter, a green leaf beside it", "seed": 0},
        "decree_cultural_integration": {"subject": "two hands clasped in a firm handshake, one in a brown wool sleeve and one in a blue linen sleeve", "seed": 1},
        "decree_natalism_initiative": {"subject": "a wooden baby cradle with a soft blue blanket", "seed": 0},
        # "a stack of gold coins" drew $ signs on every coin.
        "decree_tax_breaks": {"subject": "a stack of plain gold coins each stamped with a small star, beside a big mint-green arrow pointing down", "seed": 0},
        # A customs gate came with numbered plates on its posts.
        "decree_trade_reform": {"subject": "a red and white striped boom barrier arm raised up on a squat post, a wooden cargo crate on the ground beside it", "seed": 0},
        "decree_antiterrorism_campaign": {"subject": "a black riot shield and a police baton crossed", "seed": 1},
        # s1 is retouched: FLUX drew a second lens ring over the first.
        "decree_promote_tourism": {"subject": "a straw sun hat and a vintage brown leather camera", "seed": 1},
        "decree_encourage_emigration": {"subject": "a small ocean liner with a big mint-green arrow pointing away to the right", "seed": 0},
        "decree_subsidize_immigration": {"subject": "a battered brown leather suitcase standing on a stack of gold coins", "seed": 0},
        "decree_greenest_grass_campaign": {"subject": "a covered wagon drawn by two horses on a patch of vivid green grass, a big mint-green arrow pointing up behind it", "seed": 1},
        "decree_resettlement_recruitment_drive": {"subject": "a small new timber house with a big mint-green arrow pointing into its open door", "seed": 0},
    },
    # The four mod-added laws still on another law's icon.
    "law": {
        "law_penal_labor_camps": {"subject": "a heavy iron ball and chain lying beside a pickaxe", "seed": 0},
        "law_private_military_contractors": {"subject": "an empty modern combat helmet sitting on a tall stack of gold coins", "seed": 0},
        "law_littoral_defense": {"subject": "a squat round stone coastal gun tower on a rocky shore, a small fast patrol boat beside it", "seed": 1},
        # s1 is retouched: hull number, bow emblems and truck lettering painted out.
        "law_auxiliary_fleet": {"subject": "a big sealift cargo ship with army trucks and crates lashed on its deck", "seed": 1},
        # Resource Transition (#660): subjects from the spec's placeholders audit.
        "law_unrestricted_extraction": {"subject": "a tall steel coal mine headframe with its big winding wheel, an oil pumpjack beside it, on a heap of black coal", "seed": 3},
        "law_fossil_expansion_moratorium": {"subject": "a half-built brick power station with bare steel girders on top and a red-and-white striped barrier pole across its gate", "seed": 1},
        "law_managed_fossil_phaseout": {"subject": "a tall brick smokestack with its top sections taken down and stacked in a neat pile beside it, a white wind turbine standing behind it", "seed": 3},
        # The ministries all shared national_bank.dds's picture (spec, mod placeholders audit).
        "law_ministry_of_foreign_affairs": {"subject": "a rolled parchment treaty scroll tied with a ribbon and a wax seal, a feather quill lying across it", "seed": 1},
        "law_ministry_of_war": {"subject": "two crossed cavalry sabres behind an empty steel army helmet", "seed": 1},
        "law_ministry_of_commerce": {"subject": "a merchant's balance scale beside a small wooden crate and a short stack of coins", "seed": 0},
        # Round 1's round doors read as portholes: show the gold behind.
        "law_national_bank": {"subject": "a heavy round steel bank vault door swung half open, stacks of gold bars inside the vault behind it", "seed": None},
        # Culture s0 has a signature and s1 lettering; commerce s1 a signature; secrecy s1 a W seal.
        "law_ministry_of_culture": {"subject": "a lyre leaning against a classical marble bust of a man", "seed": 2},
        "law_ministry_of_the_environment": {"subject": "a young leafy tree sapling growing from a mound of soil, a small watering can beside it", "seed": 1},
        "law_ministry_of_intelligence_and_security": {"subject": "a brass spyglass lying across a locked steel strongbox", "seed": 2},
        "law_ministry_of_refugee_affairs": {"subject": "a worn leather suitcase with a rolled blanket and a round loaf of bread on top of it", "seed": 2},
        "law_ministry_of_propaganda": {"subject": "a big flared loudspeaker horn mounted on a short pole", "seed": 1},
        "law_ministry_of_science": {"subject": "a brass telescope on a tripod beside a round glass laboratory flask", "seed": 1},
        "law_ministry_of_thought_control": {"subject": "a metal headband fitted with wires that run to a small box covered in dials", "seed": 0},
        # Round 1's round shield read as a plate or a mirror.
        "law_ministry_of_consumer_protection": {"subject": "a pointed knight's heater shield standing in front of a wicker shopping basket full of bread and fruit", "seed": None},
        "law_ministry_of_urban_planning": {"subject": "a drafting compass standing over a small model of city blocks on a square board", "seed": 1},
        "law_ministry_of_religion": {"subject": "two lit candles in tall candlesticks beside a closed book with a clasp", "seed": 1},
        "law_ministry_of_international_aid": {"subject": "a stack of burlap grain sacks and wooden crates on a wooden pallet", "seed": 2},
        # The "no ministry" laws all shared one picture too. Vanilla draws a "no X"
        # law as X inside its prohibition ring (no police, no schools): each is
        # its ministry's icon, shrunk, under the ring lifted from no_police.dds.
        # Not No Ministry of Labor: its ministry keeps an older picture of its own.
        **{f"law_no_{m}": {"from": f"law/law_{m}", "base": {"scale": 0.78},
                           "marks": [{"draw": "prohibition", "at": (0.5, 0.5), "scale": 1.0}]}
           for m in ("ministry_of_foreign_affairs", "ministry_of_war", "ministry_of_commerce", "national_bank",
                     "ministry_of_culture", "ministry_of_the_environment", "ministry_of_intelligence_and_security",
                     "ministry_of_refugee_affairs", "ministry_of_propaganda", "ministry_of_science",
                     "ministry_of_thought_control", "ministry_of_consumer_protection", "ministry_of_urban_planning",
                     "ministry_of_religion", "ministry_of_international_aid")},
        # Six pairs of unrelated laws had byte-identical files (spec, mod placeholders
        # audit): the law whose old picture fits worse gets its own.
        "law_neocolonialism": {"subject": "an empty pith helmet resting on top of a closed leather briefcase", "seed": 2},
        # Round 1 stamped a B on every coin (one with a lettered tag): a block chain, no coins.
        "law_decentralized_cryptocurrency": {"subject": "a short chain of four thick metal cubes linked together, each cube etched with simple circuit lines", "seed": None},
        "law_unregulated_donations": {"subject": "a bulging cloth money sack tied with cord, coins spilling from it onto the steps of a small columned government building", "seed": 1},
        "law_informal_government_secrecy": {"subject": "a thick closed folder tied shut with ribbon and sealed with a wax seal, a large old iron key lying on top", "seed": 0},
        "law_minority_rights_violent_hostility": {"subject": "a burning wooden torch crossed with a heavy wooden club", "seed": 2},
        "law_protected_class": {"subject": "a level balance scale with a man's top hat in one pan and a woman's bonnet in the other", "seed": 1},
    },
    # Mod-added institutions, all on one of vanilla's seven icons.
    "institution": {
        "institution_ministry_of_war": {"subject": "two crossed cavalry sabres behind a round iron army helmet", "seed": 1},
        "institution_ministry_of_commerce": {"subject": "a bulging leather money pouch beside a stack of coins", "seed": 1},
        "institution_ministry_of_foreign_affairs": {"subject": "a rolled treaty scroll tied with a ribbon and a wax seal, a quill pen beside it", "seed": 0},
        # "a classical bank building" wrote BANK on its pediment.
        "institution_national_bank": {"subject": "a stack of gold bars on the steps of a classical building front with tall columns and a plain blank triangular pediment", "seed": 0},
        "institution_ministry_of_culture": {"subject": "a laurel-crowned marble bust beside a painter's palette with brushes", "seed": 1},
        "institution_ministry_of_labor": {"subject": "a worker's flat cap resting on an anvil with a hammer", "seed": 1},
        "institution_ministry_of_the_environment": {"subject": "a young oak sapling growing from a mound of earth, a watering can beside it", "seed": 0},
        "institution_ministry_of_intelligence_and_security": {"subject": "a large magnifying glass lying across a sealed dossier folder", "seed": 1},
        "institution_ministry_of_refugee_affairs": {"subject": "a canvas relief tent with a bundle and a suitcase in front of it", "seed": 0},
        "institution_ministry_of_propaganda": {"subject": "a big vintage broadcast microphone on a stand", "seed": 0},
        "institution_ministry_of_science": {"subject": "a brass microscope beside a round-bottomed glass flask", "seed": 0},
        "institution_ministry_of_thought_control": {"subject": "a large padlock locking a closed book shut", "seed": 1},
        "institution_ministry_of_consumer_protection": {"subject": "a wicker shopping basket of groceries in front of a round shield", "seed": 1},
        "institution_ministry_of_urban_planning": {"subject": "a small architectural model of a city block with a drafting compass leaning on it", "seed": 0},
        "institution_ministry_of_religion": {"subject": "a large brass bell standing on the ground beside a lit candle", "seed": 1},
        "institution_ministry_of_international_aid": {"subject": "a wooden supply crate with a cross on its side, a sack of grain beside it", "seed": 0},
        "institution_migration_controls": {"subject": "a wooden rubber stamp standing on an ink pad beside a small booklet", "seed": 0},
    },
    # The same institutions' background strips, each scene set in its
    # institution's era and echoing its icon. All were on vanilla's seven.
    "institution_strip": {
        "institution_ministry_of_war": {"subject": "army officers in dark 1900s uniforms leaning over a map spread on a table, one pointing at it, in a wood-panelled war room lit by a hanging lamp", "seed": 1},
        "institution_ministry_of_commerce": {"subject": "merchants in frock coats inspecting bolts of cloth, sacks of coffee and wooden crates in a busy 19th-century harbour warehouse, tall sailing ships beyond the open doors", "seed": 0},
        "institution_ministry_of_foreign_affairs": {"subject": "diplomats in 19th-century frock coats seated along a long polished table signing a treaty, under a crystal chandelier in a gilded palace hall", "seed": 0},
        "institution_national_bank": {"subject": "clerks in waistcoats counting stacks of banknotes and weighing gold bars at long wooden counters in a marble-columned 19th-century bank hall", "seed": 1},
        "institution_ministry_of_culture": {"subject": "visitors in 19th-century dress admiring large framed landscape paintings and marble statues in a grand skylit museum gallery", "seed": 0},
        "institution_ministry_of_labor": {"subject": "a government mediator in a grey suit seated at a table between factory workers in flat caps and a mill owner in a waistcoat, on an early 1900s factory floor with machinery behind them", "seed": 1},
        # Rerolled at 4 seeds (owner): "taking water samples" drew two men standing
        # idle in the reeds, and one seed a giant cropped torso. Of the reroll, s1
        # cut the scientists off at the neck.
        "institution_ministry_of_the_environment": {"subject": "two scientists in 1970s field jackets crouching at the edge of a murky river, filling glass sample jars, a smoking factory chimney in the hazy distance behind them", "seed": 0},
        "institution_ministry_of_intelligence_and_security": {"subject": "intelligence officers in 1950s suits examining photographs and files under a desk lamp in a dim office, a reel-to-reel tape recorder on a shelf", "seed": 1},
        "institution_ministry_of_refugee_affairs": {"subject": "families with bundles and suitcases standing in line at a relief table outside rows of white canvas tents, aid workers handing out blankets", "seed": 1},
        # s0 has a framed certificate at its left edge, under the panel's fade.
        "institution_ministry_of_propaganda": {"subject": "a 1930s radio broadcasting studio, a man in a suit speaking into a large chrome microphone while technicians watch through a glass window beside dials and switches", "seed": 0},
        "institution_ministry_of_science": {"subject": "scientists in white coats working at laboratory benches with glass flasks, brass microscopes and a large electrical apparatus in an early 20th-century laboratory", "seed": 0},
        "institution_ministry_of_thought_control": {"subject": "rows of clerks wearing headphones seated at desks with reel-to-reel tape recorders in a grim grey concrete hall under harsh hanging lamps", "seed": 0},
        "institution_ministry_of_consumer_protection": {"subject": "food inspectors in white coats examining tin cans and loaves of bread on a long steel table in a 1950s testing laboratory", "seed": 0},
        "institution_ministry_of_urban_planning": {"subject": "architects in 1950s shirtsleeves gathered around a large white scale model of a city with tower blocks and parks, drafting tables behind them", "seed": 1},
        "institution_ministry_of_religion": {"subject": "robed clerics conferring around a long wooden table in a candlelit stone hall with tall stained glass windows", "seed": 0},
        # FLUX lettered the grain sacks: large on s1, small on s0 under the panel's fade.
        "institution_ministry_of_international_aid": {"subject": "1960s aid workers unloading sacks of grain from a dusty truck for waiting villagers in a sunlit rural village", "seed": 0},
        "institution_migration_controls": {"subject": "immigration officers at wooden desks checking the papers of arriving families with trunks, in a large early 1900s inspection hall with tall arched windows", "seed": 1},
    },
    # The custom-religion IG traits on another trait's card (all but the
    # traditionalist trio, which is the Devout IG's own set). Slot = category.
    "ig_trait_loyal": {
        "ig_trait_custom_religion_market_liberal_loyal": {"subject": "a stack of coins with a small seedling sprouting from the top", "seed": 0},
        "ig_trait_custom_religion_social_democrat_loyal": {"subject": "three simple human figures standing arm in arm", "seed": 0},
        "ig_trait_custom_religion_totalitarian_loyal": {"subject": "an armoured gauntlet gripping a shepherd's crook", "seed": 0},
        "ig_trait_custom_religion_imperial_cult_loyal": {"subject": "a crown above a raised open hand taking an oath", "seed": 1},
        "ig_trait_custom_religion_theocratic_loyal": {"subject": "a judge's gavel resting on an open book", "seed": 1},
    },
    "ig_trait_happy": {
        "ig_trait_custom_religion_market_liberal_happy": {"subject": "two praying hands pressed together around a single plain coin stamped with a star", "seed": 0},
        "ig_trait_custom_religion_social_democrat_happy": {"subject": "a ladle over a steaming soup pot", "seed": 1},
        "ig_trait_custom_religion_totalitarian_happy": {"subject": "a grid of identical small human figures in neat rows", "seed": 0},
        "ig_trait_custom_religion_imperial_cult_happy": {"subject": "a radiant crown with bold rays behind it", "seed": 0},
        "ig_trait_custom_religion_theocratic_happy": {"subject": "two hands clasped in a handshake over an open book", "seed": 0},
    },
    "ig_trait_unhappy": {
        "ig_trait_custom_religion_market_liberal_unhappy": {"subject": "a fat bulging money sack spilling coins", "seed": 1},
        "ig_trait_custom_religion_social_democrat_unhappy": {"subject": "a lopsided balance scale, its left pan sunk low and heaped with coins, its right pan raised high and empty", "seed": 0},
        "ig_trait_custom_religion_totalitarian_unhappy": {"subject": "a heavy military boot stamping down on a quill pen", "seed": 1},
        "ig_trait_custom_religion_imperial_cult_unhappy": {"subject": "a sword crossed over a sceptre behind a round shield", "seed": 1},
        "ig_trait_custom_religion_theocratic_unhappy": {"subject": "a flaming torch crossed with a pitchfork", "seed": 1},
    },
    # The combined-arms general traits (type = condition, so the condition
    # card) on vanilla skill and personality icons.
    "character_trait": {
        "trait_combined_arms_infantry_screen": {"subject": "a line of three infantry soldiers kneeling with rifles raised, side view", "seed": 1},
        "trait_combined_arms_fire_support": {"subject": "a field artillery howitzer firing, a bold burst of flame at its muzzle", "seed": 1},
        "trait_combined_arms_recon": {"subject": "a mounted scout on horseback raising binoculars to his eyes", "seed": 0},
        "trait_combined_arms_armor": {"subject": "a battle tank charging forward, side view", "seed": 1},
        "trait_combined_arms_air_superiority": {"subject": "a fighter plane diving steeply", "seed": 0},
        # s2 is retouched: the tank's front plate filled (FLUX drew it hollow) and a hull star removed.
        "trait_combined_arms_full_spectrum": {"subject": "a fighter plane flying low over a tank, an infantry soldier standing beside the tank, all overlapping as one compact group", "seed": 2},
    },
    # The mod's financial "harvest conditions", on law icons.
    "harvest_condition": {
        # market_downturn and bull_market s0 are retouched: painters' signatures along the bottom.
        "financial_panic": {"subject": "a crowd of small figures rushing at the shut doors of a columned bank under a dark stormy sky", "seed": 0},
        "market_downturn": {"subject": "a row of shuttered shop fronts on an empty grey street at dusk, dry leaves blowing past", "seed": 0},
        "bull_market": {"subject": "a charging bull in front of a bright golden sunrise", "seed": 0},
    },
    # Diplomatic Framework, on the Ideological Union's lectern.
    "power_bloc_identity": {
        "identity_diplomatic": {"subject": "a rolled treaty parchment with a red wax seal, a gilded olive branch laid across it", "seed": 0},
    },
    "leader_ideology": {
        "ideology_multicultural": {"subject": "three hands clasping each other's wrists to form a triangle", "seed": 0},
        "ideology_anti_colonialist_leader": {"subject": "a raised clenched fist in front of a globe with its continents, a thick white outline all around the fist separating it from the globe", "seed": 1},
        "ideology_multicultural_inclusive": {"subject": "three hands clasping each other's wrists to form a triangle around a heart", "seed": 0},
        "ideology_environmentalists": {"subject": "a broad oak tree with a round leafy crown and spreading roots", "seed": 0},
        "ideology_optimist_transhumanist": {"subject": "a DNA double helix rising in front of a half sun with bold rays", "seed": 1},
        "ideology_corporate": {"subject": "a leather briefcase in front of a tall skyscraper", "seed": 1},
    },
    # The mod's prestige goods, each its base good's object made finer, as
    # vanilla's are (see the category). Base good in brackets.
    "prestige_good": {
        # [fine_art, Art and Entertainment] Masterpieces: Disney, Sony, Netflix, Nintendo.
        # Not s1, whose two reels sit in perpendicular planes (owner).
        "prestige_good_entertainment": {"subject": "a gleaming gold 1930s movie camera with two large film reels on top, on a short wooden tripod", "seed": 0},
        # [consumer_appliances] Premium Appliances: Apple, Samsung, Sony, HP.
        "prestige_good_generic_consumer_appliances": {"subject": "a sleek brushed-aluminium laptop computer, half open, its screen glowing a deep blue gradient", "seed": 2},
        # [electronic_components] High-Precision Components: TSMC, Intel, ASML, NVIDIA.
        "prestige_good_generic_electronic_components": {"subject": "a polished silicon wafer disc covered in a shimmering rainbow grid of tiny square chips, with one black microchip with rows of gold pins lying in front of it", "seed": 0},
        # [digital_assets, Software] Enterprise Solutions: Microsoft, Oracle, SAP, Google.
        # s1 is retouched: lettering on the cabinet's foot.
        "prestige_good_generic_software": {"subject": "a tall black server cabinet with a glass door, rows of thin servers inside lit by small blue and green status lights", "seed": 1},
        # [advanced_materials, a buckyball] High-Performance Materials.
        "prestige_good_generic_advanced_materials": {"subject": "a ball-shaped molecular lattice of polished gold rods joined by small glossy deep-blue spheres", "seed": 0},
        # [automobiles] Luxury Automobiles: Rolls-Royce, Ferrari, Toyota.
        "prestige_good_luxury_automobiles": {"subject": "a long sleek glossy deep-red 1930s grand touring car with flowing curved fenders, chrome trim and chrome wire wheels", "seed": 1},
        # [aeroplanes] Superior Airframes: Airbus, Boeing, Dassault, Lockheed Martin.
        "prestige_good_advanced_aircraft": {"subject": "a gleaming polished-silver supersonic airliner with a long pointed needle nose and slim delta wings, in flight", "seed": 3},
        # [tanks] Cutting-Edge Armaments: FCM (the Char 2C), Hyundai (Hyundai Rotem's K2).
        # s0 is retouched: a white number plate on the hull.
        "prestige_good_advanced_weaponry": {"subject": "a modern angular main battle tank in dark olive green with a long smooth gun barrel and wide tracks", "seed": 0},
        # [robotics, Industrial Robotics] Advanced Automation: Boston Dynamics, Fanuc, Toyota.
        # "A sleek polished-silver humanoid robot" drew cute white toy robots.
        "prestige_good_precision_robotics": {"subject": "a sleek precision robotic arm of polished chrome steel with black joints and a slim three-fingered gripper, mounted on a round black base", "seed": 0},
        # [launch_capacity] Heavy-Lift Launch Systems: SpaceX, Roscosmos, Lockheed Martin.
        # "A tall gleaming stainless-steel super-heavy rocket with small black fins" drew retro toy rockets;
        # "... with a plain dark grey body and four strap-on boosters, lifting off" a dark upright
        # sliver, lost on the dark UI at 32 px. Light, and at a slant to fill the square.
        "prestige_good_heavy_lift_launch": {"subject": "a huge realistic multi-stage heavy-lift rocket with a light silver-grey body, thin black bands and four strap-on boosters, climbing at a steep diagonal slant on a long plume of bright orange flame", "seed": 2},
        # [oil] Refined Petrochemicals: Aramco, Shell, BP, Petrobras.
        "prestige_good_refined_petrochemicals": {"subject": "a glossy dark-blue steel oil drum with polished brass bands, beside a tall glass laboratory flask of clear amber liquid", "seed": 2},
        # [merchant_marine, Bulk Transportation] Integrated Logistics Solutions: Amazon, SAP, Shopify.
        "prestige_good_integrated_logistics": {"subject": "a large modern container ship with a dark-blue hull, its deck stacked high with plain ribbed red, orange, green and blue shipping containers", "seed": 2},
        # [telephones, Wired Telecommunication Gear] Advanced Telecommunications: Huawei, Verizon, BlackBerry (Apple and Samsung moved to Precision Wireless Gear).
        "prestige_good_advanced_telecom": {"subject": "a slim black glass smartphone standing upright, its screen glowing a deep teal gradient", "seed": 3},
        # [tourism] Resort Travel: Disney, Axiom Space.
        "prestige_good_resort_travel": {"subject": "two stacked tan leather suitcases with brass corners and buckled straps, beside an open red-and-yellow striped beach umbrella", "seed": 1},
        # [lead, Conductive and Base Metals] Pure Heavy Metals: BHP.
        "prestige_good_generic_lead": {"subject": "a neat stack of polished copper ingots and blue-grey metal ingots, topped by a rainbow-iridescent bismuth crystal with stepped square terraces", "seed": 2},
        # [rubber] Performance Tires: Michelin, Pirelli, JSR, IG Farben.
        "prestige_good_generic_rubber": {"subject": "a single glossy black racing car tire standing upright at a slight angle, with a deep sharp tread and a thin red stripe around its plain smooth sidewall, on a polished silver five-spoke wheel", "seed": 3},
        # [ammunition] Match-Grade Ammunition: Rheinmetall, Armstrong Whitworth, generic Munitions.
        "prestige_good_generic_ammunition": {"subject": "a neat upright row of five long gleaming polished brass rifle cartridges with sharp pointed copper bullets, held together at their bases by a dark steel clip", "seed": 2},
        # [tech_metals, Tech-Critical Metals] Refined Critical Metals: BHP, Vale, generic Metal and Mineral Mining.
        # "A polished cylindrical ingot of bright silver-white metal standing on its end, with thin
        # bands of purple-blue heat tint" drew pale lumps that read as soap or stone.
        "prestige_good_generic_tech_metals": {"subject": "a neat stack of three mirror-polished chrome-bright metal bars with crisp sharp edges and strong reflections, one with a faint blue and violet sheen, beside a small heap of glittering dark-violet metal crystals", "seed": 1},
    },
    # Journal entries on vanilla's event icons (the nine Space Race milestones
    # shared its gears; the rest a newspaper, portrait, flag or building icon).
    # Not the Nuclear Weapons entry, which has its own mushroom cloud, nor
    # je_unite_the_nations, a vanilla entry the mod replaces.
    "journal_entry": {
        "je_banking_cycle": {"subject": "a bronze bull statuette and a bronze bear statuette facing each other, side by side", "seed": 1},
        "je_civil_rights": {"subject": "a level brass balance scale with two identical pans, one holding a dark brown wooden block and the other a pale tan wooden block of the same size", "seed": 0},
        "je_colonial_empire": {"subject": "an empty tan pith helmet resting on a rolled sepia-brown map tied with red cord", "seed": 0},
        "je_covert_warfare": {"subject": "a black-handled dagger lying across a folded dark grey fedora hat", "seed": 0},
        "je_cultural_hegemony": {"subject": "a pair of gold and deep-blue theatre masks, one smiling and one sad, side by side", "seed": 1},
        "je_digital_rights": {"subject": "a grey box security camera on a metal wall bracket, beside a closed brass padlock", "seed": 1},
        "je_global_warming": {"subject": "a tall glass thermometer with a bright red liquid column rising to its top and plain unlabelled tick marks, beside a small melting block of pale blue ice", "seed": 0},
        "je_grand_monuments": {"subject": "a tall grey stone obelisk with a golden pyramid tip on a stepped stone base", "seed": 0},
        "je_heir_education": {"subject": "a small gold crown resting on a stack of three closed leather-bound books with blank covers", "seed": 1},
        "je_human_augmentation": {"subject": "a polished steel prosthetic hand with an open palm, brass pistons and gears showing at the wrist", "seed": 3},
        "je_mental_health_crisis": {"subject": "a featureless grey plaster mannequin head in profile with a tangled knot of black wire rising from the top of it", "seed": 0},
        "je_post_scarcity": {"subject": "a golden cornucopia horn spilling ripe fruit, golden wheat and small brass gears", "seed": 1},
        "je_strategic_reserve": {"subject": "a neat stack of olive-green wooden ammunition crates and rust-red steel oil barrels with a brown burlap grain sack on top", "seed": 1},
        "je_united_nations": {"subject": "a round globe of the Earth with green continents and blue oceans, held in a curved golden olive-branch wreath", "seed": 1},
        "je_state_collapse": {"subject": "a single weathered stone column with its top half fallen and lying broken in rubble at its base", "seed": 0},
        "je_create_new_religion": {"subject": "a plain grey stone altar block with a lit red candle on top and a brass bowl beside it", "seed": 0},
        "je_world_war": {"subject": "a dark thundercloud with yellow lightning bolts above a small black iron field cannon", "seed": 0},
        # Legislated tax code: s1 stamped a coin with $ and s3 with a rouble sign.
        "je_tax_code": {"subject": "a thick open ledger book with a red wax seal on its page and a short stack of gold coins beside it", "seed": 2},
    },
    # The Space Race milestones, in order, over the shared backdrop. Silhouettes
    # have to differ at 40 px, and none may redraw a space tech's icon
    # (rocketry, space_exploration, recon_satellites, satellite_communications).
    # Craft are gold, silver, grey or orange, never white: the cut-out loses a
    # large white surface. No flags on the Moon or Mars.
    # mars_landing s2 is retouched: FLUX's painted cast shadow (a grey wedge left of
    # the rock, opaque after the cut-out) whitened out in the raw.
    "journal_entry_space": {
        "je_space_race_suborbital": {"subject": "a stubby glossy orange sounding rocket with a black nose cone and three fins, launching upward at a slant on a short jet of orange flame", "seed": 1},
        "je_space_race_orbital": {"subject": "a polished silver sphere with four long swept-back whip antennas", "seed": 3},
        "je_space_race_moon_landing": {"subject": "a spindly gold-foil-wrapped lunar lander with four thin legs, standing on a small mound of grey moon dust", "seed": 0},
        "je_space_race_probe": {"subject": "a deep-space probe with a large gold parabolic dish, a long boom carrying a small instrument box, and a grey cylindrical power unit", "seed": 1},
        "je_space_race_moon_base": {"subject": "a low moon habitat of two silver-grey rounded domes joined by a short tube, small square lit windows along its side, on a mound of grey moon dust", "seed": 2},
        "je_space_race_mars_landing": {"subject": "a dark grey cone-shaped crew capsule standing on three legs, its hatch open with a small ladder, on a mound of rust-red rocky ground", "seed": 2},
        "je_space_race_interstellar_probe": {"subject": "a long slim silver needle-shaped spacecraft with a wide round gold shield disc at its rear and a bright blue engine flame", "seed": 1},
        "je_space_race_interstellar_results": {"subject": "three large grey radio-telescope dishes in a row, tilted up toward the sky on steel frames", "seed": 1},
        "je_space_race_solar_colonization": {"subject": "a large banded tan-and-brown ringed gas giant planet beside a small rust-red planet and a small blue-and-green planet", "seed": 1},
    },
    # Mod principle groups on one of four vanilla icons (spec, mod placeholders
    # audit). One picture per group, as vanilla gives; tiers 2-5 use tier 1's.
    "principle": {
        "principle_artistic_expression_1": {"subject": "a wooden painter's easel holding a small colourful landscape canvas, a palette and brushes at its foot", "seed": 1},
        "principle_artistic_expression_2": {"use": f"{_GI}/principles_icons/principle_artistic_expression_1.dds"},
        "principle_artistic_expression_3": {"use": f"{_GI}/principles_icons/principle_artistic_expression_1.dds"},
        "principle_artistic_expression_4": {"use": f"{_GI}/principles_icons/principle_artistic_expression_1.dds"},
        "principle_artistic_expression_5": {"use": f"{_GI}/principles_icons/principle_artistic_expression_1.dds"},
        "principle_cultural_plurality_1": {"subject": "a folded patchwork quilt of many differently coloured and patterned squares", "seed": 1},
        "principle_cultural_plurality_2": {"use": f"{_GI}/principles_icons/principle_cultural_plurality_1.dds"},
        "principle_cultural_plurality_3": {"use": f"{_GI}/principles_icons/principle_cultural_plurality_1.dds"},
        "principle_cultural_plurality_4": {"use": f"{_GI}/principles_icons/principle_cultural_plurality_1.dds"},
        "principle_cultural_plurality_5": {"use": f"{_GI}/principles_icons/principle_cultural_plurality_1.dds"},
        "principle_cultural_unity_1": {"subject": "many differently coloured threads braided together into one thick rope, coiled", "seed": 1},
        "principle_cultural_unity_2": {"use": f"{_GI}/principles_icons/principle_cultural_unity_1.dds"},
        "principle_cultural_unity_3": {"use": f"{_GI}/principles_icons/principle_cultural_unity_1.dds"},
        "principle_cultural_unity_4": {"use": f"{_GI}/principles_icons/principle_cultural_unity_1.dds"},
        "principle_cultural_unity_5": {"use": f"{_GI}/principles_icons/principle_cultural_unity_1.dds"},
        "principle_diplomacy_1": {"subject": "a rolled parchment treaty scroll with two red wax seals, a feather quill and an inkwell beside it", "seed": 0},
        "principle_diplomacy_2": {"use": f"{_GI}/principles_icons/principle_diplomacy_1.dds"},
        "principle_diplomacy_3": {"use": f"{_GI}/principles_icons/principle_diplomacy_1.dds"},
        "principle_diplomacy_4": {"use": f"{_GI}/principles_icons/principle_diplomacy_1.dds"},
        "principle_diplomacy_5": {"use": f"{_GI}/principles_icons/principle_diplomacy_1.dds"},
        "principle_education_1": {"subject": "a small brass desk globe standing on a stack of three leather-bound school books, a wooden ruler leaning on them", "seed": 0},
        "principle_education_2": {"use": f"{_GI}/principles_icons/principle_education_1.dds"},
        "principle_education_3": {"use": f"{_GI}/principles_icons/principle_education_1.dds"},
        "principle_education_4": {"use": f"{_GI}/principles_icons/principle_education_1.dds"},
        "principle_education_5": {"use": f"{_GI}/principles_icons/principle_education_1.dds"},
        "principle_engineering_and_logistics_1": {"subject": "a big steel gear wheel and a heavy wrench leaning against a stack of wooden shipping crates", "seed": 1},
        "principle_engineering_and_logistics_2": {"use": f"{_GI}/principles_icons/principle_engineering_and_logistics_1.dds"},
        "principle_engineering_and_logistics_3": {"use": f"{_GI}/principles_icons/principle_engineering_and_logistics_1.dds"},
        "principle_engineering_and_logistics_4": {"use": f"{_GI}/principles_icons/principle_engineering_and_logistics_1.dds"},
        "principle_engineering_and_logistics_5": {"use": f"{_GI}/principles_icons/principle_engineering_and_logistics_1.dds"},
        "principle_environmental_sustainability_1": {"subject": "a small white wind turbine beside a young green tree on a grassy mound", "seed": 1},
        "principle_environmental_sustainability_2": {"use": f"{_GI}/principles_icons/principle_environmental_sustainability_1.dds"},
        "principle_environmental_sustainability_3": {"use": f"{_GI}/principles_icons/principle_environmental_sustainability_1.dds"},
        "principle_environmental_sustainability_4": {"use": f"{_GI}/principles_icons/principle_environmental_sustainability_1.dds"},
        "principle_environmental_sustainability_5": {"use": f"{_GI}/principles_icons/principle_environmental_sustainability_1.dds"},
        # Round 1's round shield drew a porthole: a helmet on a globe instead.
        "principle_global_security_1": {"subject": "an empty light-blue steel army helmet resting on top of a small globe of the Earth with green continents and blue oceans", "seed": None},
        "principle_global_security_2": {"use": f"{_GI}/principles_icons/principle_global_security_1.dds"},
        "principle_global_security_3": {"use": f"{_GI}/principles_icons/principle_global_security_1.dds"},
        "principle_global_security_4": {"use": f"{_GI}/principles_icons/principle_global_security_1.dds"},
        "principle_global_security_5": {"use": f"{_GI}/principles_icons/principle_global_security_1.dds"},
        "principle_healthcare_1": {"subject": "a brass mortar and pestle with green herbs, beside a roll of bandage and a small glass vial", "seed": 1},
        "principle_healthcare_2": {"use": f"{_GI}/principles_icons/principle_healthcare_1.dds"},
        "principle_healthcare_3": {"use": f"{_GI}/principles_icons/principle_healthcare_1.dds"},
        "principle_healthcare_4": {"use": f"{_GI}/principles_icons/principle_healthcare_1.dds"},
        "principle_healthcare_5": {"use": f"{_GI}/principles_icons/principle_healthcare_1.dds"},
        "principle_military_training_1": {"subject": "a pair of worn brown army boots beside an empty steel helmet and a coiled climbing rope", "seed": 1},
        "principle_military_training_2": {"use": f"{_GI}/principles_icons/principle_military_training_1.dds"},
        "principle_military_training_3": {"use": f"{_GI}/principles_icons/principle_military_training_1.dds"},
        "principle_military_training_4": {"use": f"{_GI}/principles_icons/principle_military_training_1.dds"},
        "principle_military_training_5": {"use": f"{_GI}/principles_icons/principle_military_training_1.dds"},
        "principle_monetary_union_1": {"subject": "an open wooden strongbox full of identical gold coins each stamped with a small star", "seed": 1},
        "principle_monetary_union_2": {"use": f"{_GI}/principles_icons/principle_monetary_union_1.dds"},
        "principle_monetary_union_3": {"use": f"{_GI}/principles_icons/principle_monetary_union_1.dds"},
        "principle_monetary_union_4": {"use": f"{_GI}/principles_icons/principle_monetary_union_1.dds"},
        "principle_monetary_union_5": {"use": f"{_GI}/principles_icons/principle_monetary_union_1.dds"},
        "principle_multilateral_institutions_1": {"subject": "a round marble rotunda building with a dome and a ring of columns", "seed": 1},
        "principle_multilateral_institutions_2": {"use": f"{_GI}/principles_icons/principle_multilateral_institutions_1.dds"},
        "principle_multilateral_institutions_3": {"use": f"{_GI}/principles_icons/principle_multilateral_institutions_1.dds"},
        "principle_multilateral_institutions_4": {"use": f"{_GI}/principles_icons/principle_multilateral_institutions_1.dds"},
        "principle_multilateral_institutions_5": {"use": f"{_GI}/principles_icons/principle_multilateral_institutions_1.dds"},
        "principle_rural_1": {"subject": "a wooden farm cart loaded with hay bales, a pitchfork leaning against its wheel", "seed": 1},
        "principle_rural_2": {"use": f"{_GI}/principles_icons/principle_rural_1.dds"},
        "principle_rural_3": {"use": f"{_GI}/principles_icons/principle_rural_1.dds"},
        "principle_rural_4": {"use": f"{_GI}/principles_icons/principle_rural_1.dds"},
        "principle_rural_5": {"use": f"{_GI}/principles_icons/principle_rural_1.dds"},
        # Round 1's cut-out lost the townhouses behind the tram: the tram alone.
        "principle_urban_planning_1": {"subject": "a chunky red and cream city tram car on a short stretch of rails", "seed": None},
        "principle_urban_planning_2": {"use": f"{_GI}/principles_icons/principle_urban_planning_1.dds"},
        "principle_urban_planning_3": {"use": f"{_GI}/principles_icons/principle_urban_planning_1.dds"},
        "principle_urban_planning_4": {"use": f"{_GI}/principles_icons/principle_urban_planning_1.dds"},
        "principle_urban_planning_5": {"use": f"{_GI}/principles_icons/principle_urban_planning_1.dds"},
        "principle_welfare_1": {"subject": "a wicker basket holding a loaf of bread, apples and a jug of milk", "seed": 0},
        "principle_welfare_2": {"use": f"{_GI}/principles_icons/principle_welfare_1.dds"},
        "principle_welfare_3": {"use": f"{_GI}/principles_icons/principle_welfare_1.dds"},
        "principle_welfare_4": {"use": f"{_GI}/principles_icons/principle_welfare_1.dds"},
        "principle_welfare_5": {"use": f"{_GI}/principles_icons/principle_welfare_1.dds"},
    },
    # The nine new basic industries, on vanilla basic_* icons until now (spec, mod placeholders audit).
    "company": {
        "company_basic_entertainment": {"subject": "a vintage movie camera on a short tripod with two round film reels on top", "seed": 1},
        "company_basic_power": {"subject": "a tall steel electricity pylon carrying power lines, a bright yellow lightning bolt above it", "seed": 1},
        "company_basic_electronics": {"subject": "a vintage wooden valve radio set with a glowing amber dial", "seed": 1},
        "company_basic_aerospace": {"subject": "a silver jet airliner climbing beside a slender rocket on its launch tower", "seed": 1},
        "company_basic_software": {"subject": "a beige desktop computer with a dark screen glowing green and a keyboard in front of it", "seed": 1},
        "company_basic_advanced_materials": {"subject": "a gleaming hexagonal honeycomb lattice of grey carbon atoms over a roll of black carbon-fibre cloth", "seed": 1},
        "company_basic_autarky": {"subject": "a black rubber tyre leaning against an oil barrel in front of a tall distillation tower", "seed": 1},
        "company_basic_synthetics": {"subject": "spools of brightly dyed red, blue and yellow thread beside a glass flask of purple dye", "seed": 1},
        "company_basic_biotechnology": {"subject": "a glass laboratory flask with a green leafy sprout growing out of its neck, a red apple beside it", "seed": 1},
    },
    # The PLACEHOLDER cards of gen_placeholder_company_icons.py: the company's trade, no logo or lettering.
    "company_logo": {
        "british_rolls_royce": {"subject": "a gleaming silver aircraft jet engine seen from the front, its fan blades spread", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/british_rolls_royce.dds"},
        "british_bp": {"subject": "an offshore oil platform standing in a green sea under a round yellow sun", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/british_bp.dds"},
        "german_bayer": {"subject": "a glass laboratory flask of bright green liquid beside a scatter of round pills", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/german_bayer.dds"},
        "german_thyssen": {"subject": "a steel mill ladle pouring a stream of glowing orange molten steel", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/german_thyssen.dds"},
        "american_boeing": {"subject": "a silver jet airliner climbing into a blue sky", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/american_boeing.dds"},
        "french_renault": {"subject": "a dark blue vintage motor car with large spoked wheels, seen from the side", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/french_renault.dds"},
        "french_michelin": {"subject": "a neat stack of three black rubber tyres", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/french_michelin.dds"},
        "italian_pirelli": {"subject": "a coil of thick black rubber electrical cable beside a single black car tyre", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/italian_pirelli.dds"},
        "british_jardine_matheson": {"subject": "a tall clipper sailing ship with full sails on a green sea, tea chests stacked on its deck", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/british_jardine_matheson.dds"},
        "japanese_sumitomo_besshi": {"subject": "a copper mine entrance in a forested mountainside, a mine cart of reddish copper ore on rails in front", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/japanese_sumitomo_besshi.dds"},
        "american_genentech": {"subject": "a twisting DNA double helix model in blue and gold", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/american_genentech.dds"},
        "american_monsanto": {"subject": "a cob of golden maize with green husks beside a glass chemical flask", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/american_monsanto.dds"},
        "danish_novo_nordisk": {"subject": "a small glass medicine vial with a blue cap beside a slim syringe", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/danish_novo_nordisk.dds"},
        "japanese_ajinomoto": {"subject": "a red lacquered bowl of steaming soup broth with a pair of chopsticks resting across it", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/japanese_ajinomoto.dds"},
        "indian_biocon": {"subject": "a glass laboratory fermenter tank of green liquid full of bubbles", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/indian_biocon.dds"},
        "chinese_bgi": {"subject": "a metal rack of glass sample tubes filled with colourful liquids", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/chinese_bgi.dds"},
        "german_biontech": {"subject": "a spiky round red and grey virus particle model beside a glass vaccine vial with an orange cap", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/german_biontech.dds"},
        "scifi_rosen_association": {"subject": "a lifelike artificial owl made of brass and glass, its eyes glowing amber", "seed": None,
                 "now": f"{_GI}/company_icons/historical_company_icons/scifi_rosen_association.dds"},
    },
    # The Timeline Extended window's launcher, on vanilla's Journal button until now.
    "sidebar_button": {
        "te_systems_window_btn": {"subject": "a small brass hourglass, its upper glass bulb holding a blue globe of the Earth with green continents, its lower bulb a small silver rocket pointing up", "seed": 1,
                                  "now": "gfx/interface/main_hud/journal_btn.dds"},
    },
    # The UN's GUI icons (docs/systems/un_gui_icons.md). Keys are the file
    # names. `now` is the vanilla placeholder the .gui drew before them. Symbols on the blue disc are warm or light, for contrast.
    "un_disc": {
        # Agencies (36 px in the overview): one symbol each.
        "agency_who": {"subject": "a thick gold staff with one green serpent coiled around it", "seed": 0,
                       "now": f"{_GI}/institution_icons/health_service.dds"},
        "agency_unesco": {"subject": "an ancient Greek amphora vase in terracotta orange with black bands", "seed": 0,
                          "now": f"{_GI}/goods_icons/fine_art.dds"},
        "agency_icj": {"subject": "a pair of polished brass balance scales, the two pans level", "seed": 0,
                       "now": f"{_GI}/institution_icons/home_affairs.dds"},
        "agency_unhrc": {"subject": "a golden dove with its wings spread wide", "seed": 0,
                         "now": f"{_GI}/institution_icons/social_security.dds"},
        "agency_iaea": {"subject": "a gold atom model, three thick elliptical orbit rings around a red ball nucleus", "seed": 0,
                        "now": f"{_GI}/goods_icons/electricity.dds"},
        "agency_unep": {"subject": "a single broad bright green leaf with pale veins", "seed": 1,
                        "now": f"{_GI}/goods_icons/wood.dds"},
        "agency_unhcr": {"subject": "a small tan canvas ridge tent with its flap open", "seed": 0,
                         "now": f"{_GI}/institution_icons/colonization.dds"},
        # A satellite is wide and thin side-on: a speck at 36 px (two seeds).
        "agency_unoosa": {"subject": "a tan and cream banded ringed planet like Saturn, its wide ring tilted", "seed": 1,
                          "now": f"{_GI}/goods_icons/aeroplanes.dds"},
        "agency_itlos": {"subject": "a heavy brass ship's anchor", "seed": 1,
                         "now": f"{_GI}/goods_icons/merchant_marine.dds"},
        "agency_icc": {"subject": "a dark polished wooden judge's gavel lying on its round wooden block", "seed": 0,
                       "now": f"{_GI}/institution_icons/police.dds"},
        "agency_cppnm": {"subject": "a heavy closed brass padlock with a black-and-yellow radiation trefoil on its body", "seed": 0,
                         "now": f"{_GI}/goods_icons/explosives.dds"},
        # Phase 7 agencies, until now byte copies (CCD of UNESCO, TPNW of IAEA, INCB of WHO).
        "agency_ccd": {"subject": "a wooden artist's palette with thick blobs of red, yellow, blue and green paint", "seed": 1,
                       "now": f"{_GI}/goods_icons/fine_art.dds"},
        "agency_tpnw": {"subject": "a fat dark grey aerial bomb with stubby tail fins lying on its side, wrapped in a heavy iron chain", "seed": 0,
                        "now": f"{_GI}/goods_icons/electricity.dds"},
        "agency_incb": {"subject": "a bright red poppy flower with a green poppy seed pod on a stem beside it", "seed": 1,
                        "now": f"{_GI}/institution_icons/health_service.dds"},
        # Resolution topics that are no agency's (40 px in the session strip).
        # War, condemned: the mandate's crossed swords under vanilla's red cross.
        # A lone sword was too thin at 40 px, and a gauntlet read as a mug.
        "topic_condemn": {"from": "un_disc/topic_mandate", "marks": [{"icon": f"{_GI}/generic_icons/red_cross.dds"}],
                          "now": f"{_GI}/alert_icons/land_invasion.dds"},
        # rembg cut the crate's front boards out as background: `solid` fills them back.
        "topic_sanctions": {"subject": "a wooden crate bound shut with a heavy iron chain", "seed": 1, "solid": True,
                            "now": f"{_GI}/alert_icons/blockaded.dds"},
        # The permanent member's gold star (as on its membership icon), falling.
        # s1 drew six points; s2 of four is a clean five.
        "topic_expulsion": {"subject": "a polished gold five-pointed star", "seed": 2,
                            "marks": [{"draw": "arrow_down", "scale": 0.5}],
                            "now": f"{_GI}/alert_icons/is_losing_rank.dds"},
        # Vanilla's war symbol; a sword in a wreath read as a ring with a line at 40 px.
        "topic_mandate": {"subject": "two crossed broad steel swords with gold hilts", "seed": 0,
                          "now": f"{_GI}/goods_icons/artillery.dds"},
        "topic_peacekeepers": {"subject": "an empty light-blue steel army helmet seen from the side", "seed": 1,
                               "now": f"{_GI}/goods_icons/small_arms.dds"},
        "topic_aid": {"subject": "two plump burlap grain sacks tied at the top", "seed": 1,
                      "now": f"{_GI}/goods_icons/groceries.dds"},
        # A glass inkwell cut out as a hollow grey ring and the white quill faded (two seeds).
        "topic_reform": {"subject": "a brown feather quill pen standing in a squat dark blue ceramic inkwell", "seed": 1,
                         "now": f"{_GI}/alert_icons/reform_government.dds"},
        # FLUX will not break a chain on request, and open shackles read as a
        # horseshoe (two seeds): a new nation's flag instead.
        "topic_decolonization": {"subject": "a plain bright green cloth flag on a short wooden pole planted in a small mound of brown earth", "seed": 1,
                                 "now": f"{_GI}/alert_icons/secession.dds"},
        # A convention topic founds or runs an agency: that agency's icon under
        # the scroll badge.
        **{f"topic_{topic}": {"from": f"un_disc/agency_{agency}",
                              "marks": [{"part": "un_part/scroll_badge", "at": (0.75, 0.77), "scale": 0.48}],
                              "now": now}
           for topic, agency, now in (
               ("human_rights", "unhrc", f"{_GI}/institution_icons/social_security.dds"),
               ("icc", "icc", f"{_GI}/institution_icons/police.dds"),
               ("npt", "iaea", f"{_GI}/goods_icons/electricity.dds"),
               ("climate", "unep", f"{_GI}/goods_icons/wood.dds"),
               ("pandemic", "who", f"{_GI}/institution_icons/health_service.dds"),
               ("refugee", "unhcr", f"{_GI}/institution_icons/colonization.dds"),
               ("heritage", "unesco", f"{_GI}/goods_icons/fine_art.dds"),
               ("space", "unoosa", f"{_GI}/goods_icons/aeroplanes.dds"),
               ("law_of_sea", "itlos", f"{_GI}/goods_icons/merchant_marine.dds"),
               ("physical_protection", "cppnm", f"{_GI}/goods_icons/explosives.dds"),
               ("cultural_diversity", "ccd", f"{_GI}/goods_icons/fine_art.dds"),
               ("nuclear_ban", "tpnw", f"{_GI}/goods_icons/electricity.dds"),
               ("narcotics", "incb", f"{_GI}/institution_icons/health_service.dds"))},
        # Phase 7 topics that are no agency's, until now byte copies of older topics.
        # Round 1 drew a clock and a box under the map, no scales: name the two pans.
        "topic_court_referral": {"subject": "a pair of polished brass balance scales with two hanging pans, a small rolled tan map tied with red cord lying in the left pan", "seed": None,
                                 "now": f"{_GI}/institution_icons/police.dds"},
        # Round 1's olive shells read as barrels and drums: a pointed brass shell.
        "topic_arms_embargo": {"subject": "a tall pointed brass artillery shell with a copper band, standing upright, a heavy iron chain wrapped around it with a closed padlock hanging from the chain", "seed": None,
                               "now": f"{_GI}/alert_icons/blockaded.dds"},
        # Suspended credentials: the folder under vanilla's red cross, as Condemn is the mandate under it.
        "topic_credentials": {"subject": "a closed brown leather diplomatic folder with a round gold seal on its cover and a red ribbon", "seed": 0,
                              "marks": [{"icon": f"{_GI}/generic_icons/red_cross.dds"}],
                              "now": f"{_GI}/alert_icons/is_losing_rank.dds"},
        "topic_standing_force": {"subject": "three empty light-blue steel army helmets in a row, seen from the side", "seed": 1,
                                 "now": f"{_GI}/goods_icons/small_arms.dds"},
        "topic_observer_request": {"subject": "a pair of black binoculars resting on top of a small dark wooden box with a slot in its lid", "seed": 1,
                                   "now": f"{_GI}/institution_icons/social_security.dds"},
        "topic_food_reserve": {"subject": "a tall round grey steel grain silo with a domed roof, a heap of golden wheat grain at its foot", "seed": 1,
                               "now": f"{_GI}/goods_icons/groceries.dds"},
        "topic_ceasefire": {"subject": "a small black iron field cannon with a leafy green olive branch sticking out of its muzzle", "seed": 1,
                            "now": f"{_GI}/alert_icons/land_invasion.dds"},
        "topic_development_fund": {"subject": "a short stack of plain gold coins with a green seedling sprouting from the top coin", "seed": 2,
                                   "now": f"{_GI}/goods_icons/groceries.dds"},
        # Round 1 drew open chests: a closed box with a lock and a slot.
        "topic_referendum": {"subject": "a closed square wooden ballot box with a brass lock on its front and a narrow slot in its flat lid, a folded tan paper ballot standing half out of the slot", "seed": None,
                             "now": f"{_GI}/alert_icons/secession.dds"},
    },
    # Authority tiers (32 px): the colonnade gains columns and finer metal.
    "un_tier": {
        # "Stone blocks at its base" drew an orange ground patch, or a block (two seeds).
        "tier_moribund": {"subject": "a broken grey marble column snapped off at half height with a jagged top, two fallen column drums lying beside it", "seed": 1,
                          "now": f"{_GI}/alert_icons/revolution.dds"},
        "tier_contested": {"subject": "two thick weathered bronze columns of unequal height", "seed": 0,
                           "now": f"{_GI}/alert_icons/low_legitimacy.dds"},
        "tier_established": {"subject": "three thick bronze columns under a plain flat stone lintel", "seed": 0,
                             "now": f"{_GI}/generic_icons/checkmark.dds"},
        "tier_strong": {"subject": "a silver classical portico of four thick columns under a triangular pediment", "seed": 0,
                        "now": f"{_GI}/generic_icons/green_checkmark.dds"},
        "tier_supranational": {"subject": "a gleaming gold classical temple front of six thick columns under a triangular pediment", "seed": 0,
                               "now": f"{_GI}/alert_icons/formable_possible.dds"},
    },
    "un_part": {
        # A globe needs its continents named, or it renders as a plain ball.
        "emblem": {"subject": "a round emblem: a blue globe with green continents and blue oceans, encircled by a thick gold laurel wreath", "seed": 2},
        # Tan, not cream: a pale surface is lost in the cut-out.
        "scroll_badge": {"subject": "a small rolled tan parchment scroll tied with a red ribbon", "seed": 3},
    },
    "un_member": {
        "member_no_un": {"from": "un_part/emblem", "tint": "faint",
                         "now": f"{_GI}/generic_icons/map_list_cross.dds"},
        "member_cannot_join": {"from": "un_part/emblem", "tint": "grey",
                               "marks": [{"icon": f"{_GI}/generic_icons/red_cross.dds", "scale": 0.62}],
                               "now": f"{_GI}/generic_icons/red_cross.dds"},
        "member_can_join": {"from": "un_part/emblem", "tint": "grey",
                            "marks": [{"icon": f"{_GI}/generic_icons/map_list_plus.dds", "scale": 0.62}],
                            "now": f"{_GI}/generic_icons/checkbox_simple.dds"},
        "member": {"from": "un_part/emblem",
                   "marks": [{"icon": f"{_GI}/generic_icons/green_checkmark.dds", "scale": 0.62}],
                   "now": f"{_GI}/generic_icons/green_checkmark.dds"},
        "member_permanent": {"from": "un_part/emblem",
                             "marks": [{"icon": f"{_GI}/generic_icons/green_checkmark.dds", "scale": 0.62},
                                       {"draw": "star", "at": (0.24, 0.24), "scale": 0.44}],
                             "now": f"{_GI}/generic_icons/checkbox_greencheck.dds"},
        # Suspended: the overlord carries the seat, so the benefits apply (colour) ...
        "member_suspended_carried": {"from": "un_part/emblem",
                                     "marks": [{"draw": "pause", "scale": 0.56}],
                                     "now": f"{_GI}/generic_icons/checkmark.dds"},
        # ... or nobody does, and they do not (grey).
        "member_suspended": {"from": "un_part/emblem", "tint": "grey",
                             "marks": [{"draw": "pause", "scale": 0.56}],
                             "now": f"{_GI}/generic_icons/warning.dds"},
        "crisis": {"from": "un_part/emblem",
                   "marks": [{"icon": f"{_GI}/generic_icons/warning.dds", "scale": 0.62}],
                   "now": f"{_GI}/alert_icons/critical_supply_network.dds"},
        # A permanent seat with nobody in it, in place of a flag: bare UN-blue
        # cloth with the emblem as a faint watermark. 3:2 like a flag.
        "seat_vacant": {"from": "un_part/emblem", "layout": "flag", "size": (132, 88),
                        "now": "gfx/interface/progressbar/progressbar_empty.dds"},
    },
    # ── The system panels (docs/systems/<system>_gui_icons.md) ────────────
    # Banking (banking_gui_icons.md): 32 px, the budget emblem also at 18 px.
    "banking_part": {
        "bank": {"subject": "a squat tan sandstone bank building front: four thick columns under a triangular pediment, "
                            "a heavy dark wooden door, three broad steps", "seed": 1},
        "coins": {"subject": "a short neat stack of five thick plain gold coins, each stamped with a small star", "seed": 3},
        "coin": {"subject": "a single thick plain gold coin stamped with a small star, tilted toward the viewer",
                 "seed": 0},
        "valve": {"subject": "a dry polished brass pipe tap with a large round red handwheel on top and a short thick "
                             "spout pointing straight down", "seed": 3},
        "padlock": {"subject": "a heavy closed dark steel padlock with a thick shackle", "seed": 2},
        # Kraft brown, not white: a pale tag is lost in the cut-out.
        "tag": {"subject": "a blank brown kraft-paper price tag with a punched round hole and a loop of red string",
                "seed": 3},
        "flame": {"subject": "a single bold bright orange and red flame with a yellow core, flat stylized shape",
                  "seed": 2},
        "foreign_coin": {"subject": "a large plain silver coin with a square hole in its centre", "seed": 3},
        "seal": {"subject": "a round red wax seal stamped with a small star", "seed": 0},
    },
    "banking": {
        "price_hyper": {"subject": "a wooden wheelbarrow heaped high with bundles of plain green paper banknotes "
                                   "tied with string", "seed": 0,
                        "now": f"{_GI}/generic_icons/red_cross.dds"},
        # Also drawn at 18 px beside each tool's point cost: few, thick counters.
        "budget": {"subject": "a short stack of three thick plain gold tokens stamped with a small star, "
                              "a fourth token lying flat beside it", "seed": 0,
                   "now": f"{_GI}/diplomatic_treaties_articles_icons/bankroll_treaties.dds"},
    },
    # Cultural Hegemony (cultural_hegemony_gui_icons.md): 36 px. The tiers are
    # one emblem growing, as the UN's tiers are one colonnade: separate renders.
    # FLUX drew the negligible sprig green whatever the subject said: it is
    # greyed as a derived icon.
    "ch_part": {
        "sprig": {"subject": "a short grey stone laurel twig with two broad thick leaves", "seed": 3},
        # FLUX drew no rays in four seeds: they are drawn under the wreath.
        "wreath_gold": {"subject": "a gleaming gold lyre inside a full round wreath of thick gold laurel leaves, "
                                   "short thick pointed gold rays fanning out behind the wreath", "seed": 0},
    },
    "ch": {
        "tier_minor": {"subject": "a small plain wooden lyre with a short bronze laurel twig lying across its base",
                       "seed": 3, "now": f"{_GI}/event_icons/je_cultural_hegemony.dds"},
        "tier_moderate": {"subject": "a bronze lyre with one thick curved bronze laurel branch rising along its left "
                                     "side only", "seed": 1,
                          "now": f"{_GI}/event_icons/je_cultural_hegemony.dds"},
        "tier_significant": {"subject": "a bronze lyre inside a full round wreath of thick bronze laurel leaves",
                             "seed": 1, "now": f"{_GI}/event_icons/je_cultural_hegemony.dds"},
        "tier_major": {"subject": "a polished silver lyre inside a full round wreath of thick silver laurel leaves",
                       "seed": 1, "now": f"{_GI}/event_icons/je_cultural_hegemony.dds"},
        "benchmark": {"subject": "a small plain grey iron sceptre standing in front of a large gold laurel wreath",
                      "seed": 0, "now": f"{_GI}/generic_icons/warning.dds",
                      "marks": [{"draw": "arrow", "dir": "down", "colour": "red", "at": (0.78, 0.7), "scale": 0.44}]},
    },
    # Covert Warfare (covert_gui_icons.md): 36 px, the slot 26 px and faded while free.
    "covert_part": {
        "shield": {"subject": "a round polished steel shield with a thick gold rim and a large closed eye embossed "
                              "in its centre", "seed": 1},
        # A word on the band would be written out ("classified"): name the band only.
        "envelope": {"subject": "a sealed tan manila envelope with a red paper band around it, a thick stack of plain "
                                "green banknotes showing at its open edge", "seed": 2},
        "envelope_empty": {"subject": "an open empty tan manila envelope, its flap up, a torn red paper band hanging "
                                      "from it", "seed": 1},
        "fedora": {"subject": "a black fedora hat resting on a closed brown leather dossier folder", "seed": 1},
    },
    "covert": {
        # A searchlight's beam would cut out as a grey blob: the caught spy's raised hands say it.
        # The first subject (s1 kept in ~/flux_runs/originals/gui_spy_caught) looked too
        # photorealistic (owner): stylized, the face in shadow, brush strokes.
        "spy_caught": {"subject": "a stylized cartoon spy in a tan trench coat and black fedora with both hands raised "
                                  "high, his face hidden in shadow under the hat brim, simple bold shapes, loosely "
                                  "hand-painted with visible brush strokes", "seed": 0,
                       "now": f"{_GI}/military_icons/navy_icons/detection_navy.dds"},
        "operation_slot": {"subject": "a closed tan manila case file folder with a small black-and-white photograph "
                                      "held on its cover by a steel paper clip", "seed": 2,
                           "now": f"{_GI}/event_icons/je_covert_warfare.dds"},
    },
    # Global Warming (global_warming_gui_icons.md): tiers 36 px (drawn), policies
    # 26 px and at 25% opacity while not in force.
    "gw_part": {
        "crate": {"subject": "a small closed wooden crate of goods with rope handles", "seed": 1},
        "crown": {"subject": "a small gold crown with red jewels", "seed": 0},
    },
    "gw": {
        "penalty": {"subject": "a square tile of cracked dry parched brown earth", "seed": 3,
                    "now": f"{_GI}/generic_icons/warning.dds",
                    "marks": [{"draw": "arrow", "dir": "down", "colour": "red", "at": (0.5, 0.3), "scale": 0.5}]},
        "policy_carbon_tax": {"subject": "a red brick factory smokestack with a large plain gold coin stamped with a "
                                         "small star leaning against its base", "seed": 2,
                              "now": f"{_GI}/trade_icons/consumption_tax.dds"},
        # White turbines are lost in the cut-out: grey.
        "policy_renewable_investment": {"subject": "a tilted blue solar panel with a light grey three-bladed wind "
                                                   "turbine with thick blades behind it", "seed": 1,
                                        "now": f"{_GI}/building_icons/renewable_plant.dds"},
        "policy_emission_standards": {"subject": "a red brick factory smokestack with a large round gauge on its side, "
                                                 "a dark gauge face with a green zone and the needle in the green",
                                      "seed": 3, "now": f"{_GI}/decree/decree_pollution_control.dds"},
        "policy_climate_adaptation": {"subject": "a thick grey stone sea wall with a big curling deep blue wave "
                                                 "breaking against it", "seed": 3,
                                      "now": f"{_GI}/state_status_icons/state_infrastructure.dds"},
        "policy_reforestation": {"subject": "a young green sapling tree planted in a mound of brown earth",
                                 "seed": 0, "now": f"{_GI}/decree/decree_greenest_grass_campaign.dds"},
        "policy_public_transit": {"subject": "a green electric tram seen from the front, its pantograph on top",
                                  "seed": 1, "now": f"{_GI}/goods_icons/transportation.dds"},
        "policy_fossil_fuel_divestment": {"subject": "a black oil barrel with a plain gold coin stamped with a small "
                                                     "star flying up and away from it", "seed": 3,
                                          "now": f"{_GI}/generic_icons/money.dds"},
        "policy_green_building_codes": {"subject": "a small red brick building front with a large bright green leaf "
                                                   "emblem on its wall", "seed": 3,
                                        "now": f"{_GI}/production_method_icons/cat_building_green_p1.dds"},
    },
    # Grand Monuments (grand_monuments_gui_icons.md): 36 px, faded while a count is zero.
    "gm_part": {
        "monument": {"subject": "a small grey stone obelisk on a square stone plinth, a blank flat panel on its face",
                     "seed": 2},
        "wreath": {"subject": "a small round gold laurel wreath of thick leaves", "seed": 2},
        "railing": {"subject": "a short low bronze railing of thick round posts joined by a thick rail", "seed": 0},
        # The stele (monument s2) reads as a gravestone at 36 px: an obelisk as the alternative.
        "obelisk": {"subject": "a tall slender grey stone obelisk with a pointed top on a stepped square stone "
                               "plinth, a blank smooth panel on the plinth's face", "seed": None},
    },
    "gm": {
        # The first subject drew a mortar and pestle or a cleaver (its s2, bowl and tools
        # spread apart, is kept in ~/flux_runs/originals/gui_hard_times).
        "hard_times": {"subject": "a stonemason's steel chisel and wooden mallet lying crossed in front of an empty "
                                  "upturned wooden bowl", "seed": 3,
                       "now": f"{_GI}/generic_icons/warning.dds"},
    },
    # Strategic Reserve (strategic_reserve_gui_icons.md): 24 px.
    "st_res_part": {
        "crate": {"subject": "an empty open-topped wooden supply crate with thick planks", "seed": 3},
    },
    "st_res": {
        # Drawn at 25% opacity on Manual: the silhouette carries it.
        "policy_automated": {"subject": "a brass centrifugal governor: two heavy brass balls on thick angled arms "
                                        "around a central brass spindle", "seed": 0,
                             "now": "gfx/interface/production_methods/auto_expand.dds"},
    },
    # ── List 2 (provisional): Nuclear, Colonial Empire, Space Race ────────
    # Nuclear Weapons (nuclear_gui_icons.md): 36 px. The programme and the
    # doctrines share the warhead; readiness the missile on its launcher; launch
    # authority the brass key.
    "nuclear_part": {
        "warhead": {"subject": "a stubby polished steel-grey nuclear warhead casing with a rounded nose cone and four "
                               "small fins, standing nose up, a small yellow-and-black radiation trefoil on its side",
                    "seed": 0},
        "wrench": {"subject": "a heavy brass adjustable wrench", "seed": 3},
        "treaty_seal": {"subject": "a round red wax seal on a short wide blue silk ribbon", "seed": 1},
        # A dove seen from the front read as a heraldic eagle (UN); white is lost in the cut-out.
        "dove": {"subject": "a pale grey dove flying in side view, an olive branch in its beak", "seed": 2},
        "wall": {"subject": "a low thick wall of rough grey stone blocks", "seed": 3},
        "sword": {"subject": "a broad steel sword with a gold hilt", "seed": 2},
        "crate": {"subject": "a closed heavy dark green steel military crate with steel corners", "seed": 1},
        "missile": {"subject": "a long slender olive-green ballistic missile with a dark grey nose cone and small "
                               "fins, lying horizontal", "seed": 1},
        "key": {"subject": "a large ornate brass key", "seed": 3},
        "gov_seal": {"subject": "a round bronze seal medallion with a raised laurel border and a star in its centre",
                     "seed": 0},
        "cap": {"subject": "an olive-green military officer's peaked cap with a gold badge and gold braid",
                "seed": 1},
        "radar": {"subject": "a grey radar dish on a sturdy mount, tilted up", "seed": 2},
        "cabinet": {"subject": "a grey steel mainframe computer cabinet with rows of dials and a big red lamp on top",
                    "seed": 2},
    },
    # Colonial Empire (colonial_empire_gui_icons.md): 36 px; the programmes faded while idle.
    "colonial_part": {
        # A globe needs its continents named, or it renders as a plain ball (UN).
        "globe": {"subject": "a small globe of the Earth with green continents and blue oceans, no stand",
                  "seed": 1},
        # A ring of turned-away figures, or a round table of flags (tried: a brown disc with
        # specks at 36 px), would not read: a lone flag on a bare rock, for both alerts.
        "lone_flag": {"subject": "a small plain orange cloth flag on a thin pole planted on a tiny bare grey rock "
                                 "island", "seed": 1},
    },
    "colonial": {
        # The eligible-territories row (22 px), lit while the territory counts as a colony and
        # dimmed to 25% while not: one file, the widget dims it. Added in the updated list (2026-09-30).
        "territory_colony": {"subject": "a small plain orange cloth flag on a pole planted on a small green tropical "
                                        "island coast with one palm tree and a strip of sandy beach", "seed": 0,
                             "now": f"{_GI}/state_status_icons/colony.dds"},
        "programme_invest": {"subject": "a short steel railway bridge span under construction over a river, a small "
                                        "yellow crane on it", "seed": 1,
                             "now": f"{_GI}/building_icons/building_browser_filter_icons/filter_icons_development.dds"},
        "programme_garrison": {"subject": "a squat sandstone fort gatehouse with crenellations and a plain red pennant "
                                          "on a short pole", "seed": 1,
                               "now": f"{_GI}/generic_icons/battalions.dds"},
        "programme_assimilation": {"subject": "a small red wooden schoolhouse with a bell tower, an open book lying on "
                                              "its front steps", "seed": 2,
                                   "now": "gfx/interface/population/pop_culture.dds"},
    },
    # Space Race (space_race_gui_icons.md): 36 px; the interstellar states 44 px,
    # the first-to-finish mark 18 px. A white craft loses its body in the cut-out.
    "space_part": {
        "rocket": {"subject": "a squat silver rocket with red fins and a pointed nose cone, standing upright",
                   "seed": 1},
    },
    "space": {
        "first": {"subject": "a gold pennant flag on a staff planted on the rim of a grey moon crater", "seed": 3,
                  "now": f"{_GI}/event_icons/waving_flag.dds"},
        "first_mark": {"subject": "a small bold gold pennant flag on a thick short staff", "seed": 0,
                       "now": f"{_GI}/event_icons/waving_flag.dds"},
        "stage": {"subject": "a small rust-red ringed planet with a small silver domed settlement on its upper edge",
                  "seed": 3, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        # Our Colonies rows (#598): one icon per kind of world, shown at 24 px
        # left of the specialization's name. The rows had no icon, so `now` is
        # the stage icon, only as the sheet's "current" tile. A world that is
        # mostly white or pale loses its body in the cut-out: keep them coloured.
        "colony_mars": {"subject": "a round rust-red planet with dark canyon scars and a small pale polar cap at the top",
                        "seed": 1, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_asteroid": {"subject": "a lumpy potato-shaped grey-brown asteroid with deep round craters",
                            "seed": 2, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_jovian": {"subject": "a small round cratered grey-and-ochre moon in front of the curved edge of a "
                                     "large banded orange-and-tan gas giant planet",
                          "seed": 1, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_venus": {"subject": "a smooth glossy round yellow-ochre planet with soft swirled cloud bands across it",
                         "seed": 3, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_mercury": {"subject": "a small round grey-brown cratered planet, bright on one side and dark on the other",
                           "seed": 1, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_saturnian": {"subject": "a round hazy orange planet with one wide flat tan ring tilted at a steep "
                                        "angle around its middle, the ring passing in front of the planet",
                             "seed": 3, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        # The pick (s1) drew no ring: its icy blue-grey colour carries the kind. Saturnian and Venus
        # were rerolled with rewritten subjects (a face-on ring read as a plate, "wrapped in clouds"
        # gave a crumpled rim), so their subjects describe what the picks drew.
        "colony_uranian": {"subject": "a small round icy grey-blue moon with a thin cyan ring tilted steeply behind it",
                           "seed": 1, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_neptunian": {"subject": "a small round pink-and-blue moon with a dark streak of geyser plumes across it",
                             "seed": 2, "now": f"{_GI}/state_status_icons/colonizable.dds"},
        "colony_dwarf": {"subject": "a small round tan-and-rust-brown dwarf planet with a pale heart-shaped patch and "
                                    "one tiny grey moon beside it",
                         "seed": 1, "now": f"{_GI}/state_status_icons/colonizable.dds"},
    },
}


# ── The system panels' derived states ────────────────────────────────────
# Each family is one emblem (a `_part`) drawn in each state: a tint for the
# metal, a drawn mark for the direction, a drawn break for damage. Marks sit
# at the lower right, as the UN's do, unless the idea needs them elsewhere.
_TM = f"{_GI}/timed_modifier_icons"


# The covert shield's eyelid, over the eye of shield s1 (drawn: FLUX kept it open).
_LID = {"draw": "eyelid", "pre": True, "at": (0.485, 0.505), "scale": 0.43}


def _bank(now, tint=None, marks=()):
    """A banking phase: the bank front, nudged left, with its mark beside it."""
    e = {"from": "banking_part/bank", "base": {"scale": 0.88, "at": (0.44, 0.5)}, "now": now,
         "marks": [dict(m, at=m.get("at", (0.76, 0.66)), scale=m.get("scale", 0.5)) for m in marks]}
    if tint:
        e["tint"] = tint
    return e


def _bubble(now, scale, colour, cracked=False):
    """Bubble pressure: the same coin stack inside a bubble that grows each band.

    A bubble resting on top of the stack read as a light bulb at 32 px.
    """
    mark = {"draw": "bubble", "colour": colour, "scale": scale, "at": (0.5, 0.97 - scale / 2)}
    if cracked:
        mark["cracked"] = True
    return {"from": "banking_part/coins", "base": {"scale": 0.34, "at": (0.5, 0.78)}, "marks": [mark], "now": now}


# The coins tumbling from the tap's spout (at x 0.4 of the icon), nearest
# first: one coin is a drop, four a gush. Spaced and turned, so they read as
# falling rather than as a pile.
_FLOW = [(0.41, 0.68, 0.2, 20), (0.34, 0.8, 0.21, -25), (0.53, 0.84, 0.2, 40), (0.2, 0.88, 0.19, -10)]


def _stance(now, coins, lock=False):
    marks = [{"part": "banking_part/coin", "at": (x, y), "scale": k, "rotate": r} for x, y, k, r in _FLOW[:coins]]
    if lock:
        marks.append({"part": "banking_part/padlock", "at": (0.66, 0.3), "scale": 0.42})
    return {"from": "banking_part/valve", "base": {"scale": 0.66, "at": (0.52, 0.34)}, "marks": marks, "now": now}


def _tag(now, mark):
    return {"from": "banking_part/tag", "base": {"scale": 0.9, "at": (0.44, 0.48)},
            "marks": [dict(mark, at=mark.get("at", (0.74, 0.68)), scale=mark.get("scale", 0.5))], "now": now}


def _gw_tier(level, centre, edge, burst=False):
    mark = {"draw": "thermometer", "level": level, "at": (0.5, 0.5), "scale": 0.78}
    if burst:
        mark["burst"] = True
    return {"disc": {"centre": centre, "edge": edge, "rim_light": (240, 225, 190), "rim_dark": (120, 95, 60)},
            "marks": [mark], "now": f"{_GI}/event_icons/je_global_warming.dds"}


_DT = f"{_GI}/diplomatic_treaties_articles_icons"


def _row_of_warheads(now, marks=(), top=0.22):
    """Three identical warheads racked one above another (series production), with any marks over them.

    FLUX lays a warhead on its side whatever the subject says (four seeds), so
    the row the list asked for is a rack."""
    step = (0.8 - top) / 2
    return {"from": "nuclear_part/warhead", "base": {"scale": 0.66, "at": (0.5, 0.8)}, "now": now,
            "marks": [{"part": "nuclear_part/warhead", "under": True, "at": (0.5, y), "scale": 0.66,
                       "outline": False} for y in (top, top + step)] + list(marks)}


def _readiness(angle, lamp, now):
    """The missile on its pad at `angle` (0 lying, 90 upright), and the lamp.

    Every launcher FLUX drew was a long flat truck, most already carrying a
    missile, and a sliver at 36 px: the missile stands on a drawn pad instead.
    Missile s1 lies nose down-left at about 30 degrees, hence the offset."""
    return {"from": "nuclear_part/missile", "turn": -(30 + angle), "now": now,
            "base": {"scale": 0.84 if angle else 0.9, "at": (0.5, 0.46 if angle else 0.62)},
            "marks": [{"draw": "bar", "colour": "steel", "at": (0.5, 0.92), "scale": 0.7},
                      {"draw": "disc", "colour": lamp, "at": (0.84, 0.16), "scale": 0.26}]}


def _key(holder, now):
    """Launch authority: the brass key with whoever holds it."""
    return {"from": f"nuclear_part/{holder}", "base": {"scale": 0.86, "at": (0.44, 0.46)}, "now": now,
            "marks": [{"part": "nuclear_part/key", "at": (0.72, 0.72), "scale": 0.54}]}


def _band(link, now):
    return {"from": "colonial_part/globe", "base": {"scale": 0.86, "at": (0.5, 0.5)}, "now": now,
            "marks": [dict({"draw": "link", "at": (0.5, 0.5), "scale": 0.96}, **link)]}


def _rocket(now, flame, marks=(), tilt=0):
    """The rocket; under it Banking's flame turned to point down, `flame` long (0: on its pad).

    Every render asked for an exhaust flame alone drew a rocket with it."""
    e = {"from": "space_part/rocket", "base": {"scale": 0.72, "at": (0.5, 0.4 if flame else 0.5)}, "now": now,
         "marks": ([{"part": "banking_part/flame", "rotate": 180 + tilt, "under": True,
                     "at": (0.5 + tilt / 300, 0.78 + flame / 5), "scale": flame}] if flame else []) + list(marks)}
    if tilt:
        e["tilt"] = tilt
    return e


def _st_res(now, mark):
    return {"from": "st_res_part/crate", "base": {"scale": 0.78, "at": (0.5, 0.62)}, "marks": [mark], "now": now}


ICONS.update({
    "banking_state": {
        # The cycle's mirror pairs: Panic and Frenzy, Downturn and Boom, Stagnation and Expansion.
        "phase_panic": _bank(f"{_TM}/modifier_fire_negative.dds",
                             marks=[{"draw": "arrow", "dir": "down", "colour": "red", "double": True, "scale": 0.58}]),
        "phase_downturn": _bank(f"{_TM}/modifier_coins_negative.dds",
                                marks=[{"draw": "arrow", "dir": "down", "colour": "red"}]),
        "phase_stagnation": _bank(f"{_TM}/modifier_flag_negative.dds", tint="grey",
                                  marks=[{"draw": "bar", "colour": "amber", "scale": 0.44}]),
        "phase_stable": _bank(f"{_GI}/event_icons/je_banking_cycle.dds",
                              marks=[{"draw": "bar", "colour": "white", "scale": 0.44}]),
        "phase_expansion": _bank(f"{_TM}/modifier_flag_positive.dds",
                                 marks=[{"draw": "arrow", "dir": "up", "colour": "green"}]),
        "phase_boom": _bank(f"{_TM}/modifier_coins_positive.dds", tint="gold",
                            marks=[{"draw": "arrow", "dir": "up", "colour": "blue"}]),
        "phase_frenzy": _bank(f"{_TM}/modifier_fire_positive.dds", tint="gold",
                              marks=[{"draw": "arrow", "dir": "up", "colour": "red", "double": True, "scale": 0.58},
                                     {"part": "banking_part/coin", "at": (0.2, 0.86), "scale": 0.22},
                                     {"part": "banking_part/coin", "at": (0.36, 0.9), "scale": 0.2}]),
        # Momentum's outer bands (#812): vanilla's arrows stop at the double, so
        # Freefall and Overheating get a third head, drawn in vanilla's faceted
        # style and red, the overview's colour for the extremes.
        "momentum_freefall": {"drawn": True, "now": f"{_GI}/generic_icons/down_down.dds",
                              "marks": [{"draw": "trend", "dir": "down", "colour": "red", "count": 3,
                                         "at": (0.5, 0.5), "scale": 1.0}]},
        "momentum_overheating": {"drawn": True, "now": f"{_GI}/generic_icons/trend_upup.dds",
                                 "marks": [{"draw": "trend", "dir": "up", "colour": "red", "count": 3,
                                            "at": (0.5, 0.5), "scale": 1.0}]},
        "bubble_low": _bubble(f"{_GI}/generic_icons/green_checkmark.dds", 0.5, "green"),
        "bubble_building": _bubble(f"{_GI}/generic_icons/maybe_icon.dds", 0.6, "white"),
        "bubble_elevated": _bubble(f"{_TM}/modifier_coins_negative.dds", 0.72, "yellow"),
        "bubble_high": _bubble(f"{_TM}/modifier_fire_negative.dds", 0.84, "gold"),
        "bubble_severe": _bubble(f"{_GI}/generic_icons/red_cross.dds", 0.94, "red", cracked=True),
        "stance_very_loose": _stance(f"{_TM}/modifier_fire_positive.dds", 4),
        "stance_loose": _stance(f"{_TM}/modifier_coins_positive.dds", 3),
        "stance_neutral": _stance(f"{_GI}/generic_icons/money.dds", 2),
        "stance_tight": _stance(f"{_TM}/modifier_coins_negative.dds", 1),
        "stance_very_tight": _stance(f"{_TM}/modifier_documents_negative.dds", 0, lock=True),
        "price_deflation": _tag(f"{_TM}/modifier_coins_negative.dds", {"draw": "arrow", "dir": "down", "colour": "blue"}),
        "price_stable": _tag(f"{_TM}/modifier_coins_positive.dds", {"draw": "bar", "colour": "green", "scale": 0.44}),
        "price_elevated": _tag(f"{_GI}/generic_icons/warning.dds", {"draw": "arrow", "dir": "up", "colour": "yellow"}),
        "price_high": _tag(f"{_TM}/modifier_fire_negative.dds",
                           {"draw": "arrow", "dir": "up", "colour": "orange", "double": True, "scale": 0.56}),
        "price_very_high": _tag(f"{_TM}/modifier_fire_negative.dds", {"part": "banking_part/flame", "scale": 0.56}),
        "price_dollarised": _tag(f"{_GI}/generic_icons/world_market.dds", {"part": "banking_part/foreign_coin"}),
        "price_planned": _tag(f"{_GI}/generic_icons/government_building_icon.dds", {"part": "banking_part/seal"}),
    },
    "ch_state": {
        "tier_negligible": {"from": "ch_part/sprig", "tint": "grey",
                            "now": f"{_GI}/event_icons/je_cultural_hegemony.dds"},
        "tier_hegemon": {"from": "ch_part/wreath_gold", "base": {"scale": 0.8, "at": (0.5, 0.5)},
                         "marks": [{"draw": "rays", "under": True, "at": (0.5, 0.5), "scale": 1.0}],
                         "now": f"{_GI}/event_icons/je_cultural_hegemony.dds"},
    },
    "covert_state": {
        # One shield, its metal and damage the standing: gold rim, silver, dull
        # iron, iron cracked, iron split. FLUX will not crack or split a shield,
        # so the breaks are drawn; nor shut an eye, so the lid is drawn too:
        # shut while defended, half open when exposed, wide open when vulnerable.
        "standing_fortress": {"from": "covert_part/shield", "marks": [_LID],
                              "now": f"{_GI}/generic_icons/green_checkmark.dds"},
        "standing_hardened": {"from": "covert_part/shield", "marks": [_LID], "tint": "silver",
                              "now": f"{_GI}/generic_icons/approval_icon.dds"},
        "standing_defended": {"from": "covert_part/shield", "marks": [_LID], "tint": "iron",
                              "now": f"{_GI}/generic_icons/undecided_icon.dds"},
        "standing_exposed": {"from": "covert_part/shield", "marks": [dict(_LID, opening=0.5)], "tint": "iron",
                             "damage": "crack", "now": f"{_GI}/generic_icons/disapproval_icon.dds"},
        "standing_vulnerable": {"from": "covert_part/shield", "tint": "iron", "damage": "split",
                                "now": f"{_GI}/generic_icons/red_cross.dds"},
        "funding": {"from": "covert_part/envelope", "now": f"{_GI}/generic_icons/gdp.dds"},
        "funding_dormant": {"from": "covert_part/envelope_empty", "tint": "grey",
                            "now": f"{_GI}/generic_icons/warning.dds"},
        # The agent's rise: the fedora on its dossier, one gold chevron per tier.
        **{f"tradecraft_{n}": {"from": "covert_part/fedora", "base": {"scale": 0.84, "at": (0.42, 0.5)},
                               "marks": ([{"draw": "chevrons", "count": n, "patch": True, "at": (0.8, 0.66),
                                           "scale": 0.5}]
                                         if n else []),
                               "now": now}
           for n, now in ((0, f"{_GI}/generic_icons/maybe_icon.dds"), (1, f"{_GI}/generic_icons/population.dds"),
                          (2, "gfx/interface/politics_view/institution_level_icon.dds"),
                          (3, f"{_GI}/formation_order_icons/upgrade.dds"),
                          (4, f"{_GI}/generic_icons/most_senior_front_commander.dds"))},
    },
    "gw_state": {
        # The warming tiers: one drawn thermometer, its column climbing, on a
        # disc warming from blue-green to dark red. Drawn, so only the column
        # and the colour change.
        "tier_negligible": _gw_tier(0.0, (150, 205, 195), (60, 120, 115)),
        "tier_slight": _gw_tier(0.2, (190, 210, 120), (95, 125, 45)),
        "tier_moderate": _gw_tier(0.4, (235, 210, 90), (150, 120, 30)),
        "tier_significant": _gw_tier(0.6, (240, 160, 70), (160, 80, 25)),
        "tier_severe": _gw_tier(0.8, (230, 105, 60), (150, 45, 25)),
        "tier_catastrophic": _gw_tier(1.0, (200, 50, 40), (110, 20, 15)),
        "tier_apocalyptic": _gw_tier(1.0, (130, 25, 25), (55, 8, 10), burst=True),
        # Vanilla's market-capital mark may stay for the leader (the sheet shows it as "current").
        "role_leader": {"from": "gw_part/crate", "base": {"scale": 0.8, "at": (0.5, 0.6)},
                        "marks": [{"part": "gw_part/crown", "at": (0.5, 0.22), "scale": 0.52}],
                        "now": f"{_GI}/state_status_icons/state_market_capital_icon.dds"},
        "role_member": {"from": "gw_part/crate", "tint": "grey", "base": {"scale": 0.8, "at": (0.5, 0.6)},
                        "now": f"{_GI}/generic_icons/world_market.dds"},
    },
    "gm_state": {
        # One monument, its state: bare, wreathed, mossy behind a railing, cracked and leaning.
        "status_undedicated": {"from": "gm_part/monument", "now": f"{_GI}/generic_icons/undecided_icon.dds"},
        "status_upheld": {"from": "gm_part/monument", "marks": [{"part": "gm_part/wreath", "at": (0.5, 0.52),
                                                                  "scale": 0.4}],
                          "now": f"{_GI}/generic_icons/green_checkmark.dds"},
        "status_heritage": {"from": "gm_part/monument", "tint": "moss",
                            "marks": [{"part": "gm_part/railing", "at": (0.5, 0.86), "scale": 0.86}],
                            "now": f"{_GI}/generic_icons/maybe_icon.dds"},
        "status_contested": {"from": "gm_part/monument", "damage": "crack", "tilt": 9,
                             "now": f"{_GI}/generic_icons/disapproval_icon.dds"},
    },
    "nuclear_state": {
        # The programme: one warhead in each state.
        "programme_unfunded": {"from": "nuclear_part/warhead", "tint": "grey", "marks": [{"draw": "pause", "scale": 0.5}],
                               "now": f"{_GI}/generic_icons/paused.dds"},
        "programme_developing": {"from": "nuclear_part/warhead",
                                 "marks": [{"part": "nuclear_part/wrench", "at": (0.72, 0.7), "scale": 0.56}],
                                 "now": f"{_GI}/invention_icons/nuclear_weapons.dds"},
        "programme_producing": _row_of_warheads(f"{_GI}/event_icons/mushroom_cloud.dds"),
        "programme_frozen": {"from": "nuclear_part/warhead",
                             "marks": [{"part": "nuclear_part/treaty_seal", "at": (0.7, 0.7), "scale": 0.52}],
                             "now": f"{_DT}/nuclear_program_pause.dds"},
        "programme_at_ceiling": _row_of_warheads(f"{_DT}/nuclear_arms_limitation.dds",
                                                 [{"draw": "bar", "colour": "gold", "at": (0.5, 0.1), "scale": 0.96}],
                                                 top=0.34),
        "programme_dismantling": {"from": "nuclear_part/warhead", "damage": "split",
                                  "marks": [{"part": "nuclear_part/wrench", "at": (0.5, 0.78), "scale": 0.46}],
                                  "now": f"{_DT}/nuclear_disarmament.dds"},
        "programme_none": {"from": "nuclear_part/warhead", "tint": "faint",
                           "now": f"{_GI}/invention_icons/nuclear_weapons.dds"},
        "programme_renounced": {"from": "nuclear_part/warhead", "damage": "split",
                                "marks": [{"part": "nuclear_part/dove", "at": (0.5, 0.3), "scale": 0.62}],
                                "now": f"{_DT}/nuclear_disarmament.dds"},
        "programme_disarmed": {"from": "nuclear_part/warhead", "tint": "grey",
                               "marks": [{"icon": f"{_GI}/generic_icons/red_cross.dds", "scale": 0.6}],
                               "now": f"{_DT}/nuclear_disarmament.dds"},
        "warheads": {"from": "nuclear_part/warhead", "now": f"{_GI}/invention_icons/guided_missiles.dds"},
        "crisis": {"from": "nuclear_part/warhead", "base": {"scale": 0.78, "at": (0.5, 0.5)},
                   "marks": [{"draw": "disc", "colour": "red", "under": True, "at": (0.5, 0.5), "scale": 1.0},
                             {"icon": f"{_GI}/generic_icons/warning.dds", "at": (0.74, 0.74), "scale": 0.5}],
                   "now": f"{_GI}/diplomatic_action_icons/nd_nuclear_ultimatum_action.dds"},
        # Doctrine: the warhead with what it answers to.
        "doctrine_nfu": {"from": "nuclear_part/warhead", "base": {"scale": 0.62, "at": (0.5, 0.48)},
                         "marks": [{"draw": "shield", "colour": "gold", "filled": True, "under": True,
                                    "at": (0.5, 0.5), "scale": 0.98}],
                         "now": f"{_DT}/crisis_resolution.dds"},
        "doctrine_existential": {"from": "nuclear_part/warhead", "base": {"scale": 0.82, "at": (0.5, 0.42)},
                                 "marks": [{"part": "nuclear_part/wall", "at": (0.5, 0.8), "scale": 0.96}],
                                 "now": f"{_DT}/nuclear_guarantee.dds"},
        "doctrine_flexible": {"from": "nuclear_part/warhead", "tilt": 18, "base": {"scale": 0.8, "at": (0.44, 0.5)},
                              "marks": [{"draw": "shield", "colour": "gold", "filled": True, "under": True,
                                         "at": (0.66, 0.5), "scale": 0.74}],
                              "now": f"{_GI}/diplomatic_action_icons/nd_nuclear_warning_action.dds"},
        "doctrine_compellence": {"from": "nuclear_part/warhead", "flip": True, "base": {"scale": 0.8, "at": (0.42, 0.5)},
                                 "marks": [{"draw": "arrow", "dir": "right", "colour": "red", "at": (0.86, 0.5),
                                            "scale": 0.34}],
                                 "now": f"{_GI}/diplomatic_action_icons/nd_nuclear_ultimatum_action.dds"},
        # The sword lies lower left to upper right; the warhead turned to cross it.
        "doctrine_warfighting": {"from": "nuclear_part/warhead", "turn": -40, "base": {"scale": 0.86, "at": (0.5, 0.5)},
                                 "marks": [{"part": "nuclear_part/sword", "under": True, "at": (0.5, 0.5),
                                            "scale": 0.96}],
                                 "now": f"{_GI}/invention_icons/tactical_nuclear_weapons.dds"},
        # Readiness: the missile lying, raised, upright on its launcher; the lamp green, amber, red.
        "readiness_recessed": {"from": "nuclear_part/crate",
                               "marks": [{"part": "banking_part/padlock", "at": (0.72, 0.7), "scale": 0.46}],
                               "now": "gfx/interface/buttons/button_icons/lock.dds"},
        "readiness_routine": _readiness(0, "green", f"{_GI}/commander_order_icons/standby.dds"),
        "readiness_heightened": _readiness(40, "amber", f"{_GI}/generic_icons/warning.dds"),
        "readiness_high_alert": _readiness(90, "red", f"{_GI}/generic_icons/mobilize_icon_single.dds"),
        # Launch authority: the brass key, and whose it is.
        "authority_central": _key("gov_seal", f"{_GI}/generic_icons/government_building_icon.dds"),
        "authority_delegation": _key("cap", f"{_GI}/generic_icons/most_senior_front_commander.dds"),
        "authority_on_warning": _key("radar", f"{_GI}/lens_toolbar_icons/nd_nuclear_warning_action.dds"),
        "authority_automatic": _key("cabinet", f"{_GI}/generic_icons/observer_mode_icon.dds"),
    },
    "colonial_state": {
        # One globe; the tie between home and overseas coasts is the band.
        "band_solidified": _band({"colour": "gold", "width": 0.13}, f"{_GI}/state_status_icons/state_homelands.dds"),
        "band_stable": _band({"colour": "gold", "width": 0.06}, f"{_GI}/state_status_icons/incorporated_state.dds"),
        "band_strained": _band({"colour": "amber", "width": 0.06, "state": "taut"},
                               f"{_GI}/generic_icons/warning.dds"),
        "band_crumbling": _band({"colour": "red", "width": 0.08, "state": "cracked"},
                                f"{_GI}/state_status_icons/has_turmoil.dds"),
        "band_collapsing": _band({"colour": "red", "width": 0.08, "state": "broken"},
                                 f"{_GI}/war_goals/independence.dds"),
        # Great-power pressure: the lone flag on amber (isolated), on red with
        # arrows closing in (a consensus against it).
        "alert_isolation": {"from": "colonial_part/lone_flag", "base": {"scale": 0.8, "at": (0.5, 0.52)},
                            "marks": [{"draw": "disc", "colour": "amber", "under": True, "at": (0.5, 0.5),
                                       "scale": 1.0}],
                            "now": f"{_GI}/generic_icons/disapproval_icon.dds"},
        "alert_consensus": {"from": "colonial_part/lone_flag", "base": {"scale": 0.6, "at": (0.5, 0.53)},
                            "marks": [{"draw": "disc", "colour": "red", "under": True, "at": (0.5, 0.5), "scale": 1.0},
                                      {"draw": "arrows_in", "at": (0.5, 0.5), "scale": 0.98}],
                            "now": f"{_GI}/generic_icons/red_cross.dds"},
    },
    "space_state": {
        # One rocket; its state is what surrounds it.
        # An empty gantry (the list's idea) was a thin lattice at 36 px: the rocket, greyed.
        "state_idle": {"from": "space_part/rocket", "tint": "grey", "base": {"scale": 0.78, "at": (0.5, 0.5)},
                       "now": f"{_GI}/generic_icons/inactive_building.dds"},
        "state_standard": _rocket(f"{_GI}/commander_order_icons/move.dds", 0.3),
        "state_safe": _rocket(f"{_GI}/commander_order_icons/defend.dds", 0,
                              [{"draw": "shield", "colour": "blue", "under": True, "at": (0.5, 0.52), "scale": 0.98}]),
        "state_ambitious": _rocket(f"{_GI}/military_icons/navy_icons/speed_navy.dds", 0.48, tilt=-20),
        "state_shielded": _rocket(f"{_GI}/generic_icons/clock.dds", 0,
                                  [{"draw": "dome", "at": (0.5, 0.5), "scale": 0.98},
                                   {"icon": f"{_GI}/generic_icons/clock.dds", "at": (0.78, 0.76), "scale": 0.36}]),
        "risk": {"from": "space_part/rocket", "damage": "crack",
                 "marks": [{"icon": f"{_GI}/generic_icons/warning.dds", "at": (0.74, 0.72), "scale": 0.5}],
                 "now": f"{_GI}/generic_icons/warning.dds"},
        # The interstellar programme's four states, on its journal icons (#571),
        # so the row keeps the Space Race's painted disc.
        "interstellar_not_begun": {"from": "journal_entry_space/je_space_race_interstellar_probe", "tint": "grey",
                                   "now": f"{_GI}/event_icons/je_space_race_interstellar_probe.dds"},
        "interstellar_under_way": {"from": "journal_entry_space/je_space_race_interstellar_probe",
                                   "marks": [{"part": "nuclear_part/wrench", "at": (0.74, 0.74), "scale": 0.46}],
                                   "now": f"{_GI}/event_icons/je_space_race_interstellar_probe.dds"},
        "interstellar_awaiting_data": {"from": "journal_entry_space/je_space_race_interstellar_results",
                                       "marks": [{"icon": f"{_GI}/generic_icons/clock.dds", "at": (0.74, 0.74),
                                                  "scale": 0.42}],
                                       "now": f"{_GI}/event_icons/je_space_race_interstellar_results.dds"},
        "interstellar_data_received": {"from": "journal_entry_space/je_space_race_interstellar_results",
                                       "marks": [{"icon": f"{_GI}/generic_icons/green_checkmark.dds",
                                                  "at": (0.74, 0.74), "scale": 0.46}],
                                       "now": f"{_GI}/event_icons/je_space_race_interstellar_results.dds"},
    },
    "st_res_state": {
        # One crate; the lane's state is the mark in its word's colour.
        "status_idle": _st_res(f"{_GI}/generic_icons/trend_nochange.dds",
                               {"draw": "bar", "colour": "yellow", "at": (0.5, 0.64), "scale": 0.66}),
        "status_storing": _st_res(f"{_GI}/generic_icons/trend_up.dds",
                                  {"draw": "arrow", "dir": "down", "colour": "green", "at": (0.5, 0.26),
                                   "scale": 0.5}),
        "status_withdrawing": _st_res(f"{_GI}/generic_icons/trend_down.dds",
                                      {"draw": "arrow", "dir": "up", "colour": "orange", "at": (0.5, 0.26),
                                       "scale": 0.5}),
        "status_blocked": _st_res(f"{_GI}/generic_icons/warning.dds",
                                  {"draw": "barrier", "at": (0.5, 0.62), "scale": 0.86}),
    },
})


def check(mod_root: str | None = None, on_disk: set[str] | None = None) -> dict:
    """Compare ICONS with the mod's entity files.

    Errors:
      unknown     a key with no plain or REPLACE_OR_CREATE: top-level definition
                  in its entity_dir
      bad_entry   an empty subject, a seed that is not None, an int or "keep",
                  or a "use" that is not a gfx/ .dds path; a "restyle" that is
                  not one, or with a crop outside 0-0.3, no strengths, or a seed
                  past its last strength; a "style" with no {subject}, or with
                  other braces; for a GUI-hosted
                  category, a missing `now` placeholder; a malformed mark, or a
                  derived entry whose source is not a rendered entry
      missing_dds an accepted seed whose DDS is not committed (or on disk)
      bad_backdrop a category's shared `backdrop` with no prompt, a seed that is
                  not None or an int, or no seed while an icon over it is
                  accepted (its DDS could not be written); a drawn one missing
                  a colour
    Information:
      states      how many entries are unreviewed / accepted / kept / reused /
                  derived
    A GUI-hosted category (`gui`) has no entity files, so its keys are never
    `unknown`. An accepted `part` needs no DDS; a derived entry needs one as
    soon as its source and parts are accepted.
    `on_disk` defaults to the icon paths git tracks, so it works in a sparse
    worktree.
    """
    import os
    import re
    import subprocess

    mod_root = mod_root or os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    if on_disk is None:
        out = subprocess.run(["git", "-C", mod_root, "ls-files", "--", "gfx/interface"],
                             capture_output=True, text=True, check=True).stdout
        on_disk = set(out.splitlines())
    report: dict = {"unknown": [], "bad_entry": [], "missing_dds": [], "bad_backdrop": [], "states": {}}
    for cat, entries in ICONS.items():
        spec = CATEGORIES[cat]
        defined: set[str] = set()
        # A GUI-hosted category has no entity files: its keys are file names.
        for dirpath, _dirs, files in os.walk(os.path.join(mod_root, spec["entity_dir"])) if "gui" not in spec else ():
            for fname in files:
                if fname.endswith(".txt"):
                    with open(os.path.join(dirpath, fname), encoding="utf-8-sig", errors="replace") as fh:
                        defined |= set(re.findall(r"^(?:REPLACE_OR_CREATE:)?([A-Za-z0-9_\-]+)\s*=\s*\{",
                                                   fh.read(), re.M))
        states = {"unreviewed": 0, "accepted": 0, "kept": 0, "reused": 0, "derived": 0}
        for key, entry in entries.items():
            if "gui" not in spec and key not in defined:
                report["unknown"].append((cat, key))
            if "gui" in spec and not spec.get("part") and not _is_gfx_path(entry.get("now"), (".dds",)):
                report["bad_entry"].append((cat, key))
                continue
            if not _marks_ok(entry.get("marks", [])):
                report["bad_entry"].append((cat, key))
                continue
            if "use" in entry:
                use = entry["use"]
                if isinstance(use, str) and use.startswith("gfx/") and use.endswith(".dds"):
                    states["reused"] += 1
                else:
                    report["bad_entry"].append((cat, key))
                continue
            if _is_derived(entry):
                if not _derived_ok(spec, entry):
                    report["bad_entry"].append((cat, key))
                    continue
                states["derived"] += 1
                if all(_accepted(c, k) for c, k in _depends_on(entry)) and icon_path(cat, key) not in on_disk:
                    report["missing_dds"].append((cat, key))
                continue
            seed = entry.get("seed")
            if not entry.get("subject") or not (seed is None or seed == KEEP
                                                or (isinstance(seed, int) and seed >= 0)):
                report["bad_entry"].append((cat, key))
                continue
            if "restyle" in entry and not _restyle_ok(cat, entry):
                report["bad_entry"].append((cat, key))
                continue
            if "style" in entry and not _style_ok(entry["style"]):
                report["bad_entry"].append((cat, key))
                continue
            if seed is None:
                states["unreviewed"] += 1
            elif seed == KEEP:
                states["kept"] += 1
            else:
                states["accepted"] += 1
                if not spec.get("part") and icon_path(cat, key) not in on_disk:
                    report["missing_dds"].append((cat, key))
        report["states"][cat] = states
        bd = spec.get("backdrop")
        if bd and "drawn" in bd:
            drawn = bd["drawn"]
            if not all(isinstance(drawn.get(k), tuple) and len(drawn[k]) == 3
                       for k in ("centre", "edge", "rim_light", "rim_dark")):
                report["bad_backdrop"].append((cat, "_backdrop"))
        elif bd:
            seed = bd.get("seed")
            picked = isinstance(seed, int) and not isinstance(seed, bool) and seed >= 0
            if not bd.get("prompt") or not (seed is None or picked) or (seed is None and states["accepted"]):
                report["bad_backdrop"].append((cat, "_backdrop"))
    return report


TINTS = ("grey", "faint", "moss", "gold", "silver", "iron")
LAYOUTS = ("flag",)
DAMAGE = ("crack", "split")
DRAWN_MARKS = ("star", "pause", "arrow_down", "arrow", "bar", "chevrons", "barrier", "bubble", "thermometer",
               "disc", "shield", "dome", "link", "rays", "eyelid",
               "arrows_in", "trend", "prohibition")
MARK_COLOURS = ("red", "green", "blue", "yellow", "amber", "orange", "white", "gold", "steel")


def _is_gfx_path(path, suffixes) -> bool:
    return isinstance(path, str) and path.startswith("gfx/") and path.endswith(suffixes)


def _ref(path) -> tuple[str, str] | None:
    """"<category>/<key>" naming an ICONS entry, as (category, key); None otherwise."""
    if not isinstance(path, str) or "/" not in path:
        return None
    cat, key = path.split("/", 1)
    return (cat, key) if key in ICONS.get(cat, {}) else None


def _restyle_ok(cat: str, entry: dict) -> bool:
    """A gfx .dds source, a crop that leaves most of it, strengths in [0, 1), and a seed among them."""
    strengths = restyle_strengths(cat, entry)
    crop = entry.get("crop", RESTYLE_CROP)
    seed = entry.get("seed")
    return (_is_gfx_path(entry["restyle"], (".dds",))
            and isinstance(crop, (int, float)) and 0 <= crop < 0.3
            and bool(strengths) and all(isinstance(x, (int, float)) and 0 <= x < 1 for x in strengths)
            and (not isinstance(seed, int) or seed < len(strengths)))


def _style_ok(style) -> bool:
    """A template that places the subject and has no other fields."""
    if not isinstance(style, str) or "{subject}" not in style:
        return False
    try:
        style.format(subject="")
    except (KeyError, IndexError, ValueError):
        return False
    return True


def _is_derived(entry: dict) -> bool:
    """Built on another entry's icon ("from"), drawn on a disc ("disc") or drawn outright ("drawn"):
    no render of its own."""
    return "from" in entry or "disc" in entry or bool(entry.get("drawn"))


def _depends_on(entry: dict) -> list[tuple[str, str]]:
    return (([_ref(entry["from"])] if "from" in entry else [])
            + [_ref(m["part"]) for m in entry.get("marks", []) if "part" in m])


def _accepted(cat: str, key: str) -> bool:
    seed = ICONS[cat][key].get("seed")
    return not _is_derived(ICONS[cat][key]) and isinstance(seed, int) and not isinstance(seed, bool)


def _marks_ok(marks) -> bool:
    """Each mark is one vanilla .dds, one registry part or one drawn shape, placed on the icon."""
    if not isinstance(marks, list):
        return False
    for m in marks:
        kinds = [k for k in ("icon", "part", "draw") if k in m]
        if len(kinds) != 1:
            return False
        if "icon" in m and not _is_gfx_path(m["icon"], (".dds",)):
            return False
        if "part" in m and not (_ref(m["part"]) and CATEGORIES[_ref(m["part"])[0]].get("part")):
            return False
        if "draw" in m and (m["draw"] not in DRAWN_MARKS or m.get("colour", "red") not in MARK_COLOURS
                            or m.get("dir", "down") not in ("up", "down", "left", "right")
                            or m.get("state", "whole") not in ("whole", "taut", "cracked", "broken")):
            return False
        if m.get("tint") not in (None,) + TINTS or not isinstance(m.get("rotate", 0), (int, float)):
            return False
        at, scale = m.get("at", (0.5, 0.5)), m.get("scale", 0.5)
        if not (len(at) == 2 and all(0 <= v <= 1 for v in at) and 0 < scale <= 1):
            return False
    return True


def _derived_ok(spec: dict, entry: dict) -> bool:
    """A derived entry: built on a rendered entry or a drawn disc, with a known tint, damage and layout.

    GUI-hosted categories have them for states of one emblem; an entity
    category for an entity drawn as another's icon reworked (vanilla's "no X"
    laws, X under a prohibition ring).
    """
    if "disc" in entry:
        disc = entry["disc"]
        if "from" in entry or not all(isinstance(disc.get(k), tuple) and len(disc[k]) == 3
                                      for k in ("centre", "edge", "rim_light", "rim_dark")):
            return False
    elif entry.get("drawn"):
        # Marks on a bare canvas: nothing to draw them on but the marks themselves.
        if "from" in entry or entry["drawn"] is not True or not entry.get("marks") \
                or any("draw" not in m for m in entry["marks"]):
            return False
    else:
        src = _ref(entry["from"])
        if not src or _is_derived(ICONS[src[0]][src[1]]) or "subject" not in ICONS[src[0]][src[1]]:
            return False
    if entry.get("tint") not in (None,) + TINTS or entry.get("layout") not in (None,) + LAYOUTS:
        return False
    if entry.get("damage") not in (None,) + DAMAGE or not all(isinstance(entry.get(k, 0), (int, float))
                                                              for k in ("tilt", "turn")) \
            or not isinstance(entry.get("flip", False), bool):
        return False
    base = entry.get("base", {})
    if not (isinstance(base, dict) and 0 < base.get("scale", 1) <= 1
            and all(0 <= v <= 1 for v in base.get("at", (0.5, 0.5)))):
        return False
    return entry.get("layout") != "flag" or (isinstance(entry.get("size"), tuple) and len(entry["size"]) == 2)


def validate() -> bool:
    r = check()
    for title in ("unknown", "bad_entry", "missing_dds", "bad_backdrop"):
        if r[title]:
            print(f"{title.upper()} ({len(r[title])}):")
            for cat, key in r[title]:
                print(f"  {cat}/{key}")
    for cat, states in r["states"].items():
        print(f"{cat}: " + ", ".join(f"{n} {s}" for s, n in states.items()))
    errors = sum(len(r[t]) for t in ("unknown", "bad_entry", "missing_dds", "bad_backdrop"))
    print(f"Errors: {errors}")
    return errors == 0


if __name__ == "__main__":
    import sys

    if "--validate" in sys.argv:
        sys.exit(0 if validate() else 1)
    for cat, entries in ICONS.items():
        print(f"{cat}: {len(entries)} icons")
