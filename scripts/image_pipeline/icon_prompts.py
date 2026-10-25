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
objects with no real holes. "see_through": (x0, y0, x1, y1), shares of the side, does the
reverse inside that box: the light backdrop the cut-out kept there (the white between a
gate's bars) goes transparent. A `part` category is reviewed like icons but never written; it
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
  helmet seen from the front as a face, a blue spark over a brass pipe
  fitting as a gas flame (draw a zigzag lightning bolt), a knobbly green
  germ as a cabbage (give a virus spaced stalks with red tips).
- A lattice pylon or tower is all thin lines and vanishes at a goods text
  icon's 25 px: give it thick girders and something solid in front.
When both candidates miss, change the subject. When the idea is right and the
renders are weak, `generate_icons.py --seeds 4` adds two more candidates and
keeps the first two.

Design, inventory and decisions: docs/superpowers/archive/specs/2026-09-26-icon-pipeline-design.md.

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
    # The Demographics tab and state subtab (docs/systems/demographics_gui_icons.md).
    "demog": "demographics_icons",
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
    "demog": "gui/te_demographics_widgets.gui",
}

# folder/size/mode/fill/style drive rendering and composing. A category that
# `generate_icons.py` produces also names where its entities live
# (`entity_dir`) and the field holding the icon path (`field`); its icons are
# written to gfx/interface/icons/<folder>/<key>.dds.
# The framed diorama of vanilla's building icons, also the Grand Monument pictures'.
BUILDING_STYLE = ("aerial three-quarter view of {subject}, detailed painted illustration "
                  "of a miniature diorama, warm golden afternoon light, muted earthy "
                  "palette, surrounding landscape, the building fills the center of the image")
# A trophy's own picture (gm_picture keys trophy_<landmark>, 2026-10-16): what was carried off, close,
# on display in a museum room. The monuments' aerial view in a long gallery shrank the exhibit to a
# sliver at 96 px.
TROPHY_STYLE = ("close three-quarter view from above of {subject}, detailed painted illustration of a miniature "
                "diorama, warm golden light from skylights, muted earthy palette, the exhibit large in the "
                "foreground and filling the center of the image")
# The Venus de Milo's own picture (2026-10-16): close and from the front. Under BUILDING_STYLE's
# aerial view, four rounds drew her from behind, looking out over the bay, and every round gave her arms.
STATUE_STYLE = ("close three-quarter view from above of {subject}, detailed painted illustration of a miniature "
                "diorama, warm golden afternoon light, muted earthy palette, the statue large in the foreground "
                "facing the viewer and filling the center of the image")

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
        entity_dir="common/buildings", field="icon", style=BUILDING_STYLE),
    # Grand Monument pictures (spec 2026-10-11): one per style and form, shown in
    # the journal entry's monument rows and on the state card through the
    # gm_picture type, so GUI-hosted (keys are file names, written to
    # gm_pictures/<key>.dds). Framed like the building icons, whose frame and
    # neighbours they borrow: there is no vanilla gm_pictures folder.
    "gm_picture": dict(
        folder="gm_pictures", size=256, mode="framed", template_folder="building_icons",
        neighbours="building_icons",
        gui=("gui/journal_entry_widgets/grand_monuments_widget.gui", "gui/te_state_panel_widgets.gui"),
        style=BUILDING_STYLE),
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
    # Vanilla's own prestige goods the mod renamed (localization/english/replace/),
    # whose picture no longer fits the name. The mod defines no entity to wire,
    # so the key is vanilla's file name and writing it over vanilla's path is
    # the whole change, as for the goods.
    "prestige_good_vanilla": dict(
        folder="goods_icons/prestige_goods", size=256, mode="cutout", fill=0.92, grade_strength=0.4,
        gui=(), style="{subject}, one chunky readable object, " + PAINTED),
    # War goals and diplomatic plays (160 px, `texture =` in common/diplomatic_plays).
    # Vanilla's 33 are painted objects on transparency in muted slate blue with
    # dark red accents: chess pieces, flags on map tiles, documents. Measured:
    # objects span 0.78-0.99 of the side (median 0.86), median saturation 0.33
    # and value 0.43.
    "war_goal": dict(
        folder="war_goals", size=160, mode="cutout", fill=0.86, grade_strength=0.5,
        entity_dir="common/diplomatic_plays", field="texture",
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
    # Mod goods drawn by older generators (flat vector art, badges) instead of
    # vanilla's painted objects. GUI-hosted in effect, like company_logo:
    # common/goods and the goods' text icons (gui/zzz_extra_goods_texticons.gui)
    # already point at goods_icons/<key>.dds, so the key is the file name and
    # writing it is the whole change. Vanilla's span 0.86-0.95 of the side (median 0.90).
    "good": dict(
        folder="goods_icons", size=256, mode="cutout", fill=0.90, grade_strength=0.4,
        gui=(), style="{subject}, one chunky readable object, " + PAINTED),
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
    # The Demographics History charts' pips (9-10 px, in a lane above a census
    # year's bars): at that size only a flat one-colour shape reads, so a
    # silhouette is embossed in one colour, as the mobilization options are,
    # with a dark rim (`outline`, 8 px here, under 1 px in game) that `fill`
    # leaves room for. Written at 120 px, the size of the generic_icons they
    # replace. Amber by default; an entry sets its own colours. The emboss's
    # lighting has a median of about 0.6, so colours are set above the target.
    "demog_pip": dict(
        folder="demographics_icons", size=120, mode="emboss", fill=0.84, outline=8,
        color=(372, 268, 74), color_bottom=(338, 206, 50),
        neighbours="generic_icons", gui=("gui/te_demographics_widgets.gui",), style=SILHOUETTE),
    # Production methods (PM.GetTexture, `texture =`): vanilla's are embossed
    # tan-bronze silhouettes, 205 at 104 px and 86 at 208. Measured on all of
    # them: the shape spans 0.865 of the side (median), its top quarter
    # (173,159,134) and its bottom quarter (116,87,63), which `color` and
    # `color_bottom` are fitted to. Vanilla shares PM art widely, so only a
    # method whose borrowed icon says something wrong gets one here; the older
    # mod PM icons are gen_pm_icons.py's drawn glyphs.
    "production_method": dict(
        folder="production_method_icons", size=208, mode="emboss", fill=0.865,
        entity_dir="common/production_methods", field="texture",
        color=(259, 238, 201), color_bottom=(211, 158, 115), style=SILHOUETTE),
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
        # Shared clean_energy_technologies.dds until 2026-10-08. s1 cut the rock off at the frame.
        "carbon_capture_and_storage": {"subject": "a row of boxy grey steel air-capture machines with big fan grilles, a thick green pipe bending down into dark rock below", "seed": 2},
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
        # Owner picks (2026-10-07): the $ on a coin is unreadable at icon size.
        "currency_peg": {"subject": "a big gold coin and a smaller silver coin joined by a short heavy brass chain, both stamped with a small star", "seed": 0},
        "imposed_currency_peg": {"subject": "a small copper coin chained to a big gold coin by a heavy iron chain with a closed iron padlock on it", "seed": 2},
        "swap_line": {"subject": "two short stacks of plain coins side by side, one gold and one silver, with one gold coin and one silver coin swapped on top of the other stack", "seed": 1},
        "lender_of_last_resort": {"subject": "a red and orange striped life ring buoy around a short stack of plain gold coins stamped with a small star", "seed": 2},
        "debt_receivership": {"subject": "a thick brown leather ledger book bound shut with a heavy iron chain and a closed iron padlock", "seed": 1},
        # The Grand Monuments' articles (2026-10-16), on borrowed icons until now.
        "surrender_monument": {"subject": "a large hand lifting a small bronze statue of a robed figure off its square white stone pedestal", "seed": 0},
        "return_cultural_property": {"subject": "a small white marble bust packed in an open wooden crate full of straw, a green ribbon tied in a bow around the crate", "seed": 3},
        "archaeological_concession": {"subject": "an iron spade stuck upright in a small mound of brown earth beside a terracotta amphora split cleanly into two halves", "seed": 3},
        "excavation_permit": {"subject": "a rolled parchment scroll sealed with a big red wax seal, a small iron trowel and a soft brush lying across it", "seed": 0},
        # Power grids (#1109), on Transit Rights' crates until now.
        # Not household plugs (round 1), nor a spark over a brass fitting, which read as a gas flame (round 2).
        "grid_interconnection_agreement": {"subject": "two thick armoured high-voltage cables, one with a red sheath and one with a blue sheath, joined end to end by a big bolted steel coupling, a jagged bright blue zigzag lightning bolt above the join", "seed": 2},
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
        "building_generic_textile_depot": {"subject": "a brick textile warehouse whose yard is crossed by long lines hung with bolts of bright red, blue and yellow cloth drying in the sun, round dyeing vats beside them", "seed": 0},
        "building_generic_cold_storage": {"subject": "a large windowless refrigerated warehouse with insulated walls, lorries backed up to its loading bays", "seed": 1},
        "building_generic_paper_mill_complex": {"subject": "a pulp and paper mill beside a river, with log piles, a tall chimney and big rolls of paper stacked in the yard", "seed": 1},
        "building_generic_foundry_complex": {"subject": "a sprawling steel foundry with blast furnaces, molten metal glowing orange and tall smoking chimneys", "seed": 0},
        "building_generic_machine_shop": {"subject": "a large brick machine shop with big windows, lathes visible inside and heaps of gears and machine parts in the yard", "seed": 0},
        "building_generic_chem_works": {"subject": "a chemical works with tall distillation columns, spherical storage tanks and tangled pipework", "seed": 0},
        "building_generic_tank_farm": {"subject": "an oil tank farm with rows of large round storage tanks joined by pipelines, a small refinery tower beside them", "seed": 0},
        "building_generic_ordnance_depot": {"subject": "a military ordnance depot of earth-covered concrete bunkers behind barbed wire, crates of shells stacked outside", "seed": 0},
        "building_generic_motor_works": {"subject": "a motor vehicle factory with a long assembly hall and rows of new cars parked in its yard", "seed": 0},
        "building_generic_dry_dock": {"subject": "a large dry dock with a steel ship hull inside it, tall cranes standing over it at the waterside", "seed": 0},
        "building_generic_arsenal": {"subject": "a fortified brick arsenal with crenellated walls, cannons and stacked weapon crates in its courtyard", "seed": 0},
        "building_generic_fish_market": {"subject": "a harbourside fish market hall with fishing boats moored at its quay and crates of fish on the stones", "seed": 1},
        "building_generic_colonial_depot": {"subject": "a colonial trading depot of whitewashed warehouses with a veranda, tea chests and bales stacked on a wharf", "seed": 0},
        "building_generic_export_warehouse": {"subject": "a bonded export warehouse on a riverside quay, sacks of coffee and bales of cotton being loaded onto a cargo ship", "seed": 1},
        "building_generic_electronics_lab": {"subject": "a modern electronics laboratory building with a radio mast on its roof and rows of lit windows", "seed": 0},
        # Round 1: ASSAY OFFICE on the facade (s0), a watermark (s1).
        "building_generic_assay_office": {"subject": "a squat solid stone strongroom building with barred windows and a heavy iron door, a small wooden cart loaded with gold bullion bars at its door, blank unmarked walls", "seed": 0},
        "building_generic_ore_processing": {"subject": "an ore processing plant with crushers, conveyor belts and heaps of crushed ore beside a smelter chimney", "seed": 0},
        "building_generic_mineral_refinery": {"subject": "a mineral refinery with tall leaching tanks, conveyor belts and heaps of white and yellow mineral powder", "seed": 0},
        "building_generic_silk_exchange": {"subject": "an East Asian trading house with curved tiled roofs, bales of raw silk and dyed silk cloth stacked outside", "seed": 0},
        "building_generic_vintner_hall": {"subject": "a stone winery hall among vineyards, rows of oak barrels outside and grape vines on the hillside", "seed": 0},
        # Round 1: EMPORIUM (s0) and a lettered plaque (s1).
        "building_generic_furniture_showroom": {"subject": "a two-storey brick furniture workshop with tall plain glass windows showing chairs and tables inside, stacked timber planks in the yard behind it, blank unmarked walls", "seed": 0},
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
        # Power grids (#1107), on the power plant's icon until now. A substation, not a plant:
        # FLUX puts chimneys on anything called a plant.
        "building_grid_transfer_station": {"subject": "an electrical substation yard: rows of big grey transformers and steel lattice gantries strung with high-voltage lines behind a wire fence, the lines leaving on tall steel pylons across green fields, loosely hand-painted with visible brush strokes", "seed": 0},
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
        # Judiciary (docs/superpowers/archive/specs/2026-10-17-judiciary-design.md)
        "law_executive_tribunals": {"subject": "a royal crown resting on top of a closed leather-bound law book", "seed": None},
        "law_religious_courts": {"subject": "a thick holy book lying open on a carved wooden lectern, a string of prayer beads draped across its pages", "seed": None},
        "law_statutory_courts": {"subject": "a stack of three thick bound law codes with a judge's curled white wig resting on top", "seed": None},
        "law_constitutional_review": {"subject": "a long parchment charter unrolled and pinned flat by two brass weights, a large red wax seal at its foot", "seed": None},
        "law_judicial_supremacy": {"subject": "a pair of large brass balance scales on a marble pedestal, one pan holding a small rolled scroll and sitting lower than the other", "seed": None},
        "law_algorithmic_jurisprudence": {"subject": "a pair of brass balance scales whose central pillar is a computer chip with glowing circuit traces running out along the beam", "seed": None},
        # The ministries all shared national_bank.dds's picture (spec, mod placeholders audit).
        "law_ministry_of_foreign_affairs": {"subject": "a rolled parchment treaty scroll tied with a ribbon and a wax seal, a feather quill lying across it", "seed": 1},
        "law_ministry_of_war": {"subject": "two crossed cavalry sabres behind an empty steel army helmet", "seed": 1},
        "law_ministry_of_commerce": {"subject": "a merchant's balance scale beside a small wooden crate and a short stack of coins", "seed": 0},
        # A round vault door read as a porthole twice (rounds 1 and 2): no door.
        # s0 is retouched: numbers painted off the bars' faces.
        "law_national_bank": {"subject": "a neat pyramid of stacked gold bars with a heavy brass bank key lying in front of it", "seed": 0},
        # Culture s0 has a signature and s1 lettering; commerce s1 a signature; secrecy s1 a W seal.
        "law_ministry_of_culture": {"subject": "a lyre leaning against a classical marble bust of a man", "seed": 2},
        "law_ministry_of_the_environment": {"subject": "a young leafy tree sapling growing from a mound of soil, a small watering can beside it", "seed": 1},
        "law_ministry_of_intelligence_and_security": {"subject": "a brass spyglass lying across a locked steel strongbox", "seed": 2},
        "law_ministry_of_refugee_affairs": {"subject": "a worn leather suitcase with a rolled blanket and a round loaf of bread on top of it", "seed": 2},
        "law_ministry_of_propaganda": {"subject": "a big flared loudspeaker horn mounted on a short pole", "seed": 1},
        "law_ministry_of_science": {"subject": "a brass telescope on a tripod beside a round glass laboratory flask", "seed": 1},
        # The wired headband read as headphones: a bust in a wired cap (owner, 2026-10-08).
        "law_ministry_of_thought_control": {"subject": "a plaster bust of a head in profile wearing a metal cap bristling with wires that run to a small box covered in dials", "seed": 0},
        # Round 1's round shield read as a plate or a mirror.
        "law_ministry_of_consumer_protection": {"subject": "a pointed knight's heater shield standing in front of a wicker shopping basket full of bread and fruit", "seed": 1},
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
        "law_decentralized_cryptocurrency": {"subject": "a short chain of four thick metal cubes linked together, each cube etched with simple circuit lines", "seed": 2},
        "law_unregulated_donations": {"subject": "a bulging cloth money sack tied with cord, coins spilling from it onto the steps of a small columned government building", "seed": 1},
        "law_informal_government_secrecy": {"subject": "a thick closed folder tied shut with ribbon and sealed with a wax seal, a large old iron key lying on top", "seed": 0},
        "law_minority_rights_violent_hostility": {"subject": "a burning wooden torch crossed with a heavy wooden club", "seed": 2},
        "law_protected_class": {"subject": "a level balance scale with a man's top hat in one pan and a woman's bonnet in the other", "seed": 1},
        # The Legislated Tax Code's carrier law, visible under its game rule, on
        # vanilla's proportional_taxation.dds until 2026-10-08. Round 1 lettered
        # the "statute book" STATUTE and drew the rubber stamp as a chess piece.
        "law_te_tax_code": {"subject": "a thick closed leather-bound ledger with plain brass corners, sealed shut with a red wax seal", "seed": 0},
        # Four later laws gen_law_icons.py drew in the same glyph style (2026-09-28 to 10-04).
        # Vanilla draws each bureaucracy law as an object beside a quill in an inkwell.
        "law_automated_bureaucracy": {"subject": "a small brass robot arm holding a feather quill over a square glass inkwell", "seed": 1},
        "law_contracted_administration": {"subject": "a closed leather briefcase beside a feather quill standing in a square glass inkwell", "seed": 0},
        "law_communal_administration": {"subject": "three raised open hands side by side beside a feather quill in a square glass inkwell", "seed": 0},
        "law_private_policing": {"subject": "a security guard's peaked cap lying beside a big ring of keys and a flashlight", "seed": 0},
        # gen_law_icons.py's flat bronze glyphs (2026-04-12), many near-identical
        # (spec, "Batch 4"). One object per law in the law style; siblings differ in
        # silhouette, since the tint drops colour. A "no X" law whose sibling's object
        # crossed out reads right is that object under the prohibition ring.
        # LGBTQ+ Rights
        "law_active_persecution": {"subject": "a heavy wooden judge's gavel lying across a pair of thick iron shackles joined by a chain", "seed": 2},
        "law_basic_protections": {"subject": "a small plain wooden kite shield with an iron rim, propped upright on a short wooden stake", "seed": 2},
        "law_comprehensive_rights": {"subject": "a large sturdy umbrella opened wide, its curved wooden handle resting on the ground", "seed": 0},
        "law_full_equality_and_protection": {"subject": "two identical thick gold wedding rings interlocked, standing upright on a small square wooden base", "seed": 1},
        "law_legal_limbo": {"subject": "a short sagging rope bridge segment with several of its wooden planks missing", "seed": 1},
        # Antitrust & Market Structure
        "law_command_cooperative_economy": {"subject": "a large wooden abacus with rows of heavy beads, a small cog wheel leaning against it", "seed": 2},
        "law_dirigisme": {"subject": "a large wooden ship's steering wheel standing on its tall carved wooden helm post", "seed": 2},
        "law_freedom_of_contract": {"subject": "two hands clasped in a firm handshake, white shirt cuffs and dark jacket sleeves showing", "seed": 1},
        "law_guilds_chartered_monopolies": {"subject": "a blacksmith's iron anvil with a hammer resting on it, a heavy padlock hanging from its side", "seed": 2},
        "law_regulated_utilities": {"subject": "a big brass water tap and a chunky electric wall socket mounted side by side on a wooden board", "seed": 2},
        # Owner rerolls: bolt cutters read as shears over an uncut chain, a chisel as a cleaver.
        "law_trust_busting": {"subject": "a short length of thick iron chain with its middle link snapped open, the two ends pulled apart", "seed": 3},
        # Criminal Justice
        "law_punishment_focused_criminal_justice": {"subject": "a heavy barred steel prison cell door slammed shut and bolted with a thick iron bar", "seed": 0},
        "law_rehabilitation_focused_criminal_justice": {"subject": "a small carpenter's workbench with a hand saw, a wood plane and a closed book on top", "seed": 1},
        # Round 1's gold-mended vase lost its gold to the tint: a broken pot.
        "law_restorative_justice": {"subject": "a cracked clay pot held together by thick metal staples across its cracks and a tight band of twine", "seed": 0},
        # Distribution of Power (a vanilla group)
        "law_algorithmic_governance": {"subject": "a large square computer microchip with gold pins resting on a tasselled royal velvet cushion", "seed": 2},
        # Electoral Finance
        "law_donation_limits": {"subject": "a fat leather money bag cinched tight around its middle by a thick buckled leather belt", "seed": 0},
        "law_no_campaign_finance_laws": {"from": "law/law_publicly_funded_elections", "base": {"scale": 0.78},
            "marks": [{"draw": "prohibition", "at": (0.5, 0.5), "scale": 1.0}]},
        "law_publicly_funded_elections": {"subject": "two identical plain wooden speaker's lecterns standing side by side at exactly equal height", "seed": 1},
        # Family & Reproductive Policy
        "law_communal_child_rearing": {"subject": "a tall three-tier iron dormitory bunk bed made up with identical small pillows and blankets", "seed": 2},
        "law_population_control_measures": {"subject": "a white stork standing locked inside a tall iron birdcage with a padlocked door", "seed": 2},
        "law_pro_natalist_subsidies": {"subject": "a large old-fashioned baby pram with a fat drawstring money pouch tied to its handle", "seed": 1},
        "law_state_sponsored_family_planning": {"subject": "a doctor's leather medical bag standing open beside a small plain glass pill bottle", "seed": 2},
        "law_traditional_family_structure": {"subject": "a small cosy cottage with a pitched roof, a front porch and a smoking brick chimney", "seed": 1},
        # Financial Regulation
        # Round 1's lever in a glass case, round 2's governor (it drew scales) and round 3's
        # gyroscope (ship's wheels) missed. Alternative: an owl on gold bars (sheet 11).
        "law_central_bank_independence": {"subject": "a bronze hawk and a white dove perched side by side on one stone pedestal", "seed": 3},
        # Round 1's funnel read as a loudspeaker horn, Ministry of Propaganda's object.
        "law_directed_credit_development_banks": {"subject": "a big tin watering can pouring water onto a small brick factory with a tall smokestack", "seed": 0},
        "law_free_mutual_banking": {"subject": "a traditional domed straw beehive skep on a wooden stand, a few bees around it", "seed": 0},
        "law_prudential_narrow_banking": {"subject": "a ceramic piggy bank sitting safely behind a low, thick, solid brick wall", "seed": 2},
        "law_state_owned_banking": {"subject": "a classical stone bank building with four columns and an empty flagpole on its roof", "seed": 0},
        "law_universal_banking_light_prudence": {"subject": "a big multi-tool pocket knife with all of its blades and tools folded out", "seed": 0},
        "law_unregulated_banking": {"subject": "a tall precarious tower of stacked wooden building blocks leaning dangerously, about to topple", "seed": 0},
        # Genetic Rights
        "law_ban_on_genetic_modification": {"from": "law/law_open_source_genetics", "base": {"scale": 0.78},
            "marks": [{"draw": "prohibition", "at": (0.5, 0.5), "scale": 1.0}]},
        "law_corporate_genetic_licensing": {"subject": "a sealed glass vial holding a tiny DNA helix, displayed in an open velvet-lined jewellery case", "seed": 1},
        "law_open_source_genetics": {"subject": "a chunky twisted DNA double helix sculpture standing upright, cradled at its base by two open hands", "seed": 2},
        "law_state_eugenics_program": {"subject": "a brass laboratory microscope standing beside a wooden rack of glass test tubes and a syringe", "seed": 2},
        "law_traditional_heredity": {"subject": "a gnarled old oak tree with a thick trunk, a full leafy canopy and deep spreading roots", "seed": 1},
        # Distribution of Power (a vanilla group)
        "law_direct_democracy": {"subject": "a long rectangular wooden table with a row of identical high-backed chairs down both long sides", "seed": 0},
        "law_neocameralism": {"subject": "a sleek modern glass-and-steel corporate skyscraper model with a small helipad on its roof", "seed": 1},
        # Human Augmentation
        "law_human_purity": {"subject": "a classical white marble statue of a standing athlete, unaltered, on a square stone plinth", "seed": 1},
        "law_mandatory_augmentation": {"subject": "a reclined steel surgical chair with wrist restraints, a robotic surgical arm poised above it", "seed": 0},
        # Round 1's X of crutch and prosthetic read as two crossed crutches.
        "law_medical_augmentation_only": {"subject": "a steel prosthetic leg with a hinged knee joint standing upright beside a plain wooden crutch", "seed": 0},
        "law_no_augmentation": {"from": "law/law_regulated_augmentation_market", "base": {"scale": 0.78},
            "marks": [{"draw": "prohibition", "at": (0.5, 0.5), "scale": 1.0}]},
        "law_regulated_augmentation_market": {"subject": "a sleek robotic cybernetic hand standing upright on a small velvet-topped display pedestal", "seed": 0},
        "law_unrestricted_augmentation": {"subject": "a bulky cybernetic arm bristling with drills, blades and dangling wires, crudely bolted together", "seed": 2},
        # Inheritance Laws
        "law_equal_inheritance": {"subject": "a long crusty loaf of bread cut into identical even slices on a wooden board", "seed": 2},
        # 2026-10-08 redesign (#822). Testation: a pen lying across the scroll
        # sheared the roll. State heir: an open iron strongbox drew
        # Primogeniture's chest again and lettered STATE on it; a rubber stamp
        # on a house was the first pick, and the tint turns gold coins pale.
        "law_free_testation": {"subject": "a single tightly rolled parchment scroll lying on its side, tied around its middle with a black ribbon and a big red wax seal, a feather quill pen and a small inkwell standing beside it", "seed": 3},
        "law_state_universal_heir": {"subject": "a small neoclassical government building with columns and a triangular pediment, a little model house and a sack of coins set on its front steps", "seed": 5},
        "law_non_inheritable_usage_rights": {"subject": "a round stone village well with a small wooden roof and a bucket on a rope", "seed": 2},
        "law_partible": {"subject": "a small square diorama of farmland split by wooden fences into three unequal fields", "seed": 1},
        "law_primogeniture": {"subject": "one large ornate iron-bound treasure chest with a single big iron key in its lock", "seed": 1},
        # Intellectual Property
        "law_creative_commons": {"subject": "a painter's wooden easel with a blank canvas, a jar of brushes standing beside it", "seed": 1},
        "law_no_ip_protection": {"from": "law/law_traditional_ip_protection", "base": {"scale": 0.78},
            "marks": [{"draw": "prohibition", "at": (0.5, 0.5), "scale": 1.0}]},
        "law_open_source_innovation": {"subject": "three large interlocking jigsaw puzzle pieces fitted together, a fourth piece sliding into place", "seed": 2},
        "law_state_intellectual_property": {"subject": "a tall steel filing cabinet with its top drawer pulled open, rolled blueprints sticking out", "seed": 1},
        "law_strict_ip_protection": {"subject": "a glass light bulb wrapped tightly in heavy iron chains locked with a big padlock", "seed": 0},
        "law_traditional_ip_protection": {"subject": "a whole rolled parchment scroll tied with a red ribbon and a wax seal, a glass light bulb standing beside it", "seed": 3},
        # Internet Governance
        "law_net_neutrality": {"subject": "a sleek network router with antennas, a carpenter's spirit level lying flat across its top", "seed": 1},
        "law_no_internet_policy": {"subject": "an empty modern swivel office chair with a network cable coiled loosely on its seat", "seed": 0},
        "law_state_controlled_internet": {"subject": "a tall computer server cabinet wrapped in heavy iron chains and locked with a big padlock", "seed": 0},
        "law_unregulated_internet": {"subject": "a covered pioneer wagon loaded high with computer servers and coiled network cables", "seed": 1},
        # Language Policy
        "law_civic_monolingualism": {"subject": "a large ornate iron key lying across one thick closed book with brass corners", "seed": 2},
        # Round 1's cage muzzle came out as a birdcage, Population Control's object.
        "law_linguistic_purity": {"subject": "a pair of iron pruning shears beside a small neatly clipped topiary bush in a clay pot", "seed": 1},
        "law_local_vernacular": {"subject": "a folded patchwork quilt of mismatched squares draped over a rustic wooden stool", "seed": 0},
        "law_multilingual_federalism": {"subject": "three brass bells of different sizes and shapes hanging together from one sturdy wooden beam", "seed": 1},
        "law_state_led_language_reform": {"subject": "a feather quill in a heavy brass inkwell, a wooden set square leaning against it", "seed": 0},
        "law_ubiquitous_translation": {"subject": "a sleek mechanical robot parrot with metal feathers perched on a small brass stand", "seed": 0},
        # Ministry of Labor
        "law_no_ministry_of_labor": {"from": "law/law_pro_labor_ministry_of_labor", "base": {"scale": 0.78},
            "marks": [{"draw": "prohibition", "at": (0.5, 0.5), "scale": 1.0}]},
        "law_pro_capital_ministry_of_labor": {"subject": "a worker's riveted steel hard hat with a gentleman's tall silk top hat standing beside it", "seed": 0},
        "law_pro_labor_ministry_of_labor": {"subject": "a worker's riveted steel hard hat sitting on top of a dented tin lunch pail", "seed": 1},
        # Minority Rights
        "law_minority_rights_affirmative_action": {"subject": "a sturdy wooden ladder leaning against a tall stone pedestal, offering a way up", "seed": 2},
        "law_minority_rights_cultural_assimilation": {"subject": "a large black iron melting pot over a fire, assorted small trinkets melting together inside", "seed": 1},
        "law_minority_rights_discrimination": {"subject": "a thick velvet rope barrier hanging between two polished brass stanchion posts, blocking the way", "seed": 2},
        # The white seen between the gate's bars stayed in the cut-out: `see_through` clears it.
        "law_minority_rights_ghettoization": {"subject": "a section of high brick wall topped with barbed wire, a narrow iron-barred gate in it", "seed": 1, "see_through": (0.42, 0.40, 0.63, 0.86)},
        # Every round-1 seed opened the "closed" shutters: the guard looks away instead.
        "law_minority_rights_indifference": {"subject": "a big guard dog curled up fast asleep in front of its wooden kennel on a straw mat", "seed": 1},
        "law_minority_rights_protection": {"subject": "a polished steel armour cuirass mounted upright on a simple wooden armour stand", "seed": 1},
        # Monetary Policy
        "law_commodity_money": {"subject": "a heap of rough raw gold nuggets beside a small chunky hand-forged silver ingot", "seed": 0},
        "law_digital_currency": {"subject": "an open slim leather wallet with a large gold microchip filling its inner pocket", "seed": 1},
        "law_fiat_currency": {"subject": "a heavy cast-iron printing press with a fresh stack of blank paper sheets beside it", "seed": 1},
        # s2 is retouched: GOLD and a mint mark painted off the bar.
        "law_gold_standard": {"subject": "brass balance scales, a gold bar in one pan and a tied bundle of plain paper in the other", "seed": 2},
        # Privacy Rights
        "law_intrusive_surveillance": {"subject": "a cluster of several security cameras mounted on one steel pole, pointing in all directions", "seed": 1},
        "law_minimal_privacy_protection": {"subject": "a short section of white wooden picket fence with a small latched garden gate", "seed": 2},
        "law_moderate_data_privacy": {"subject": "a closed laptop computer with a sturdy brass padlock looped through a hasp on its lid", "seed": 0},
        "law_strong_privacy_rights": {"subject": "a small stone castle keep with its wooden drawbridge raised and its gate shut", "seed": 1},
        # Right to Information
        "law_freedom_of_information": {"subject": "a long wooden archive drawer pulled fully open, plain folders fanned upward inside it", "seed": 2},
        "law_open_government": {"subject": "a bright brass oil lantern with clear glass panes, its open door letting light shine out", "seed": 0},
        "law_state_secrets": {"subject": "a tall upright steel safe with thick riveted walls and a heavy lever handle on its door", "seed": 1},
        # Rules of War
        "law_humanitarian_regulations": {"subject": "a canvas army field stretcher with wooden poles and a folded wool blanket on it", "seed": 2},
        # Owner rerolls (2026-10-08): a sword tied or locked to its scabbard came out
        # unsheathed, a hood over a cannon's muzzle not at all; s0 lettered a tag.
        "law_limited_war": {"subject": "an old field cannon wrapped in a heavy iron chain padlocked around its barrel and wheel", "seed": 1},
        "law_total_war": {"subject": "a big artillery shell standing upright, a crowded cluster of smaller shells piled around it", "seed": 0},
        "law_traditional_rules_of_war": {"subject": "a large carved wooden chess knight piece standing alone on a small stone pedestal", "seed": 1},
        "law_war_crimes_forbidden": {"subject": "a bolt-action rifle lying on its side with a pair of steel handcuffs locked around it", "seed": 2},
        # State Power
        "law_devolution": {"subject": "a heavy bunch of different iron keys, several of them taken off and lying beside it", "seed": 1},
        "law_federal_system": {"subject": "a sturdy wooden barrel built of separate staves bound together by iron hoops", "seed": 1},
        "law_feudal_contracts": {"subject": "a medieval longsword lying diagonally across a thick sheaf of wheat tied with twine", "seed": 0},
        "law_unitary_state": {"subject": "a classical stone arch with a large prominent central keystone holding it together", "seed": 0},
        # Distribution of Power (a vanilla group)
        "law_post-scarcity": {"subject": "a large overflowing cornucopia horn spilling out fruit, bread and small machine gears", "seed": 1},
        "law_universal_basic_income": {"subject": "a sturdy knotted rope safety net slung taut between two thick wooden posts", "seed": 1},
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
        # [merchant_marine] Integrated Logistics Solutions: Amazon (SAP and Shopify until #1050).
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
        "principle_cultural_unity_1": {"subject": "many differently coloured threads braided together into one thick rope, coiled", "seed": 0},
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
        "principle_global_security_1": {"subject": "an empty light-blue steel army helmet resting on top of a small globe of the Earth with green continents and blue oceans", "seed": 0},
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
        "principle_urban_planning_1": {"subject": "a chunky red and cream city tram car on a short stretch of rails", "seed": 2},
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
        # On vanilla's basic_construction until 2026-10-08, which vanilla's power bloc construction company keeps.
        "company_infrastructure": {"subject": "a steel truss railway bridge with a train crossing it, a concrete highway running underneath", "seed": 1},
        "company_basic_biotechnology": {"subject": "a glass laboratory flask with a green leafy sprout growing out of its neck, a red apple beside it", "seed": 1},
        # Batch 5. Megastructure was left on basic_construction in batch 4: a space elevator, a lattice
        # tower and an orbital ring drew a radio mast, an oil derrick and a station on a pale disc that
        # broke the badge style. Batch 5: the tower above clouds mostly lost its disc (the sky was matted
        # out with the ground); the owner took s3, whose disc partly survives (2026-10-11).
        "company_megastructure_consortium": {"subject": "a colossal stepped skyscraper tower rising high above a layer of white clouds, two tiny construction cranes on its unfinished top", "seed": 3},
        # "Unnamed Monument", the Grand Monuments name carrier: shown in the rename popup while a monument is named.
        "company_gm_name_carrier": {"subject": "a blank smooth grey granite dedication plaque standing upright, a stonemason's wooden mallet and steel chisel resting against its foot", "seed": 2},
    },
    # The PLACEHOLDER cards of gen_placeholder_company_icons.py: the company's trade, no logo or lettering.
    # Interim for the seventeen real companies: the owner may draw their real logos (2026-10-07); drop an
    # entry when its company's logo replaces the file. The Rosen Association's (fictional) is final.
    "company_logo": {
        "british_rolls_royce": {"subject": "a gleaming silver aircraft jet engine seen from the front, its fan blades spread", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/british_rolls_royce.dds"},
        "british_bp": {"subject": "an offshore oil platform standing in a green sea under a round yellow sun", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/british_bp.dds"},
        "german_bayer": {"subject": "a glass laboratory flask of bright green liquid beside a scatter of round pills", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/german_bayer.dds"},
        "german_thyssen": {"subject": "a steel mill ladle pouring a stream of glowing orange molten steel", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/german_thyssen.dds"},
        "american_boeing": {"subject": "a silver jet airliner climbing into a blue sky", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/american_boeing.dds"},
        "french_renault": {"subject": "a dark blue vintage motor car with large spoked wheels, seen from the side", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/french_renault.dds"},
        "french_michelin": {"subject": "a neat stack of three black rubber tyres", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/french_michelin.dds"},
        "italian_pirelli": {"subject": "a coil of thick black rubber electrical cable beside a single black car tyre", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/italian_pirelli.dds"},
        "british_jardine_matheson": {"subject": "a tall clipper sailing ship with full sails on a green sea, tea chests stacked on its deck", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/british_jardine_matheson.dds"},
        "japanese_sumitomo_besshi": {"subject": "a copper mine entrance in a forested mountainside, a mine cart of reddish copper ore on rails in front", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/japanese_sumitomo_besshi.dds"},
        "american_genentech": {"subject": "a twisting DNA double helix model in blue and gold", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/american_genentech.dds"},
        "american_monsanto": {"subject": "a cob of golden maize with green husks beside a glass chemical flask", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/american_monsanto.dds"},
        "danish_novo_nordisk": {"subject": "a small glass medicine vial with a blue cap beside a slim syringe", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/danish_novo_nordisk.dds"},
        "japanese_ajinomoto": {"subject": "a red lacquered bowl of steaming soup broth with a pair of chopsticks resting across it", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/japanese_ajinomoto.dds"},
        "indian_biocon": {"subject": "a glass laboratory fermenter tank of green liquid full of bubbles", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/indian_biocon.dds"},
        "chinese_bgi": {"subject": "a metal rack of glass sample tubes filled with colourful liquids", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/chinese_bgi.dds"},
        "german_biontech": {"subject": "a spiky round red and grey virus particle model beside a glass vaccine vial with an orange cap", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/german_biontech.dds"},
        "scifi_rosen_association": {"subject": "a lifelike artificial owl made of brass and glass, its eyes glowing amber", "seed": 1,
                 "now": f"{_GI}/company_icons/historical_company_icons/scifi_rosen_association.dds"},
    },
    # Mod goods drawn by older generators: flat vector art and badges, not
    # vanilla's painted objects. Keys are the file names (written in place).
    "good": {
        "rocket": {"subject": "a tall white multi-stage rocket standing upright on a small steel launch pad", "seed": 1,
                   "now": f"{_GI}/goods_icons/rocket.dds"},
        "robot": {"subject": "a yellow industrial robot arm with a steel two-fingered gripper on a heavy base", "seed": 0,
                  "now": f"{_GI}/goods_icons/robot.dds"},
        "software": {"subject": "a short stack of colourful floppy disks with blank unmarked labels, a silver compact disc leaning on them", "seed": 0,
                     "now": f"{_GI}/goods_icons/software.dds"},
        # s0 is retouched: a brand name painted off the router's front.
        "digital_access": {"subject": "a white wireless router with two antennas beside a black smartphone with a dark blank screen", "seed": 0,
                           "now": f"{_GI}/goods_icons/digital_access.dds"},
        "consumer_appliances": {"subject": "a cream-coloured retro refrigerator beside a small chrome toaster and a kitchen blender", "seed": 0,
                                "now": f"{_GI}/goods_icons/consumer_appliances.dds"},
        # s0 lettered its circuit board.
        "electronic_components": {"subject": "a green circuit board holding a black microchip, round capacitors and striped resistors", "seed": 1,
                                  "now": f"{_GI}/goods_icons/electronic_components.dds"},
        "tech_metals": {"subject": "a pile of shiny silvery metal ingots with a few dark glittering mineral crystals", "seed": 1,
                        "now": f"{_GI}/goods_icons/tech_metals.dds"},
        "tourism": {"subject": "a brown leather suitcase with a camera on a strap and a straw sun hat resting on top", "seed": 2,
                    "now": f"{_GI}/goods_icons/tourism.dds"},
        # Batch 5: vanilla goods the mod renamed, written over vanilla's file so the
        # text icon (@fertilizer!, @opium!) follows. Chemicals showed the basic
        # chemicals company badge (REPLACE:fertilizer's texture, pointed back at
        # goods_icons/fertilizer.dds) and its text icon vanilla's potted plant.
        # Not bottles, which Dye is. Next subject if it misses: a dented blue steel
        # drum beside a round-bottomed glass flask of green liquid.
        "fertilizer": {"subject": "a large round green glass carboy of clear liquid with a cork stopper, held in a wooden crate packed with straw", "seed": 1,
                       "now": f"{_GI}/company_icons/basic_chemicals.dds"},
        # Drugs, which includes medicines, on vanilla's opium pipe and poppy pods.
        # Reroll: "a dried poppy seed pod" drew a brown burr.
        "opium": {"subject": "a white porcelain apothecary mortar and pestle with a few round white pills and a smooth green poppy seed head beside it", "seed": 3,
                  "now": f"{_GI}/goods_icons/opium.dds"},
        # Grid Power (#1107), on Electricity's icon until now; common/goods, its text icon and the
        # station's method group point here by hand. A pylon, not Electricity's coil. Rounds before:
        # a lattice pylon (too thin at 25 px, twice), an insulator stack (a copper spool), a
        # transformer (a box). s3 is the lattice-pylon version of this one.
        "grid_power": {"subject": "a chunky grey steel transmission pylon with thick legs and fat blue glass insulators on its arms, a big bright blue zigzag lightning bolt in front of it", "seed": 1,
                       "now": f"{_GI}/goods_icons/electricity.dds"},
    },
    # Batch 5: the two renamed prestige goods of the goods above, each a finer
    # version of its good's idea (bulk carboy -> small reagent vials).
    "prestige_good_vanilla": {
        # Specialty Reagents (vanilla's Enriched Fertilizer, a fertilizer sack).
        "generic_fertilizer_prestige": {"subject": "a polished wooden laboratory rack holding a row of slender stoppered glass vials of bright red, blue, green and amber liquids", "seed": 1,
                                        "now": f"{_GI}/goods_icons/prestige_goods/generic_fertilizer_prestige.dds"},
        # Potent Formulations (vanilla's Pure Opium, an opium box and pipe).
        "generic_opium_prestige": {"subject": "a small open silver pillbox lined with blue velvet, full of glossy red-and-white capsules", "seed": 1,
                                   "now": f"{_GI}/goods_icons/prestige_goods/generic_opium_prestige.dds"},
    },
    # Batch 5: the mod's diplomatic plays on a vanilla war goal's picture.
    "war_goal": {
        # War After a Nuclear Exchange, on Humiliation's boots on a flag. s3, the owner's pick (2026-10-11).
        "dp_nuclear_exchange": {"subject": "a cracked and scorched slate-blue map tile of land with a small grey mushroom cloud rising from its centre, muted slate-blue and grey colours", "seed": 3},
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
        # The dark grey bomb was dark on the blue disc: brass (owner, 2026-10-08).
        "agency_tpnw": {"subject": "a fat polished brass aerial bomb with stubby tail fins lying on its side, wrapped in a heavy iron chain", "seed": 2,
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
        "topic_court_referral": {"subject": "a pair of polished brass balance scales with two hanging pans, a small rolled tan map tied with red cord lying in the left pan", "seed": 1,
                                 "now": f"{_GI}/institution_icons/police.dds"},
        # Round 1's olive shells read as barrels and drums: a pointed brass shell.
        "topic_arms_embargo": {"subject": "a tall pointed brass artillery shell with a copper band, standing upright, a heavy iron chain wrapped around it with a closed padlock hanging from the chain", "seed": 2,
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
        # The black iron cannon was dark on the blue disc: bronze on red wheels (owner, 2026-10-08).
        "topic_ceasefire": {"subject": "a small bronze field cannon on red wooden wheels with a leafy green olive branch sticking out of its muzzle", "seed": 1,
                            "now": f"{_GI}/alert_icons/land_invasion.dds"},
        "topic_development_fund": {"subject": "a short stack of plain gold coins with a green seedling sprouting from the top coin", "seed": 2,
                                   "now": f"{_GI}/goods_icons/groceries.dds"},
        # Round 1 drew open chests: a closed box with a lock and a slot.
        "topic_referendum": {"subject": "a closed square wooden ballot box with a brass lock on its front and a narrow slot in its flat lid, a folded tan paper ballot standing half out of the slot", "seed": 0,
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
    # Power grids (#1109): the station's HVDC Undersea Interconnector, on vanilla's electric engines until now.
    # A cable bent under the waves with a bolt over it read as a life ring or a hook.
    "production_method": {
        "pm_grid_hvdc_interconnector": {"subject": "the cut end of a fat round undersea power cable showing three round cores inside it, lying above three thick wavy lines of sea water", "seed": 1},
    },
    # Demographics (demographics_gui_icons.md): the Leading Cause of Death cell, 44 px, shows
    # the leading cause's own icon (te_dg_dc_lead), the headstone until the first count.
    # The keys follow the pie's textures (pie_<cause>.dds).
    "demog": {
        # s0 lost its pale face in the cut-out.
        "ov_leading_cause": {"subject": "a rounded grey granite headstone with a perfectly plain smooth face, a small bunch of red flowers at its foot on a patch of green grass", "seed": 2,
                             "now": f"{_GI}/generic_icons/red_cross.dds"},
        # A fat green germ covered in knobs read as a cabbage or a ball of beads.
        "cause_infection": {"subject": "a round dark green virus: a smooth ball with short thick stalks ending in round red knobs sticking out evenly all over it", "seed": 1,
                            "now": f"{_GI}/generic_icons/red_cross.dds"},
        # A brown medicine bottle with pills read as medicine in general.
        "cause_chronic": {"subject": "a plump dark red anatomical human heart with thick stubby red and blue vessels on top", "seed": 2,
                          "now": f"{_GI}/generic_icons/red_cross.dds"},
        # s0 and s3 lettered a corner of the sign. A crutch crossed with a bandage read as a gallows.
        "cause_external": {"subject": "a yellow triangular warning sign with a red border and a thick black exclamation mark in its middle", "seed": 2,
                           "now": f"{_GI}/generic_icons/red_cross.dds"},
        "cause_work": {"subject": "an empty battered yellow miner's hard hat with a small brass lamp on its front", "seed": 2,
                       "now": f"{_GI}/generic_icons/red_cross.dds"},
        # Not the Fertility cell's cradle. A stork carrying a bundle (s0) was thin at 44 px.
        "cause_maternal": {"subject": "a pair of small pink knitted baby booties tied with ribbon", "seed": 0,
                           "now": f"{_GI}/generic_icons/red_cross.dds"},
        # Nuclear strikes and crushed uprisings. s3 signed its base.
        "cause_killed": {"subject": "a small grey and orange mushroom cloud rising from a burst of flame", "seed": 1,
                         "now": f"{_GI}/generic_icons/red_cross.dds"},
        # The war dead, not war: two crossed sabres were thin at 44 px.
        "cause_war": {"subject": "an empty dented steel army helmet resting on the butt of a rifle stuck upright in a mound of earth", "seed": 1,
                      "now": f"{_GI}/generic_icons/red_cross.dds"},
    },
    "demog_pip": {
        # s0 came out broken.
        "pip_war": {"subject": "two crossed swords with broad straight blades and thick crossguards", "seed": 3,
                    "color": (342, 108, 92), "color_bottom": (300, 70, 58),
                    "now": f"{_GI}/generic_icons/battalions.dds"},
        # The doc's blue disc with a white dot, drawn outright: nothing for FLUX to add.
        "pip_event": {"drawn": True, "marks": [{"draw": "disc", "colour": "blue", "scale": 0.9, "at": (0.5, 0.5)},
                                               {"draw": "disc", "colour": "white", "scale": 0.34, "at": (0.5, 0.5)}],
                      "now": f"{_GI}/generic_icons/information.dds"},
        "pip_famine": {"subject": "an empty round bowl seen from the side with a spoon resting across its rim", "seed": 2,
                       "now": f"{_GI}/generic_icons/goods_shortage.dds"},
    },
    # Grand Monument pictures (spec 2026-10-11 §3.1): one per style and form; keys are
    # test_grand_monument_registry.py's picture_key(code). Archetypes, never a real holy site.
    "gm_picture": {
        "undedicated": {"subject": "a tall monument entirely hidden under a huge pale canvas drape tied with ropes, scaffolding poles beside it, a small crowd waiting in the plaza, loosely hand-painted with visible brush strokes", "seed": 1,
                       "now": f"{_BI}/building_grand_monument.dds"},
        "generic__column": {"subject": "a tall fluted marble column topped by a bronze statue of a figure, on a stepped pedestal in a city square", "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        # s1 is retouched: lettering on its attic panel (owner's pick, 2026-10-11).
        "generic__arch": {"subject": "a massive neoclassical triumphal arch of pale stone with carved reliefs, a wide avenue running through it", "seed": 1,
                         "now": f"{_BI}/building_grand_monument.dds"},
        "generic__obelisk": {"subject": "a tall plain white stone obelisk with a pointed pyramid tip, standing centred on a wide stepped stone plaza in a park", "seed": 1,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "generic__statue": {"subject": "a colossal bronze equestrian statue of a rider on a rearing horse, on a tall granite pedestal in a city square", "seed": 0,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "generic__gate": {"subject": "a monumental neoclassical city gate of twelve Doric columns forming five passages under a plain flat entablature, nothing on its roof, at the end of a wide boulevard", "seed": 1,
                         "now": f"{_BI}/building_grand_monument.dds"},
        "generic__hall": {"subject": "a grand neoclassical hall with a long colonnade and wide steps, on a hill above a river", "seed": 1,
                         "now": f"{_BI}/building_grand_monument.dds"},
        "generic__mausoleum": {"subject": "a domed neoclassical marble mausoleum with a columned portico, among dark cypress trees", "seed": 0,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_latin__column": {"subject": "a Roman triumphal column wrapped in a spiralling carved frieze, a bronze statue on top, in a paved forum", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_latin__arch": {"subject": "a Roman triumphal arch with three passages, carved reliefs and a bronze four-horse chariot on top", "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_latin__forum": {"subject": "a Roman forum, a paved open square ringed by temples with Corinthian columns and a long basilica", "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_hebrew__gate": {"subject": "a massive city gate of golden limestone with a pointed arch between two crenellated towers", "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_hebrew__court": {"subject": "a great colonnaded courtyard of golden limestone around a fountain, a grand domed hall at its far end", "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_hebrew__pillar": {"subject": "a single tall golden limestone memorial pillar on a stepped base, carved with grapevines and pomegranates", "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_hebrew__menorah": {"subject": "a giant bronze candelabrum sculpture with exactly seven smooth plain branches, three curving up on each side of a central stem, on a stepped stone plinth in a plaza", "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_sanskrit__pillar": {"subject": "a tall polished sandstone pillar crowned by four stone lions back to back, on a stone platform", "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_sanskrit__gate": {"subject": "a sandstone gateway of two square pillars carrying three curved stone crossbeams one above another, carved elephants on the beams, at the edge of a grassy terrace", "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_geez__stele": {"subject": "a towering carved granite stele with false windows and doors carved up its face, among smaller stelae", "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_geez__rock_hewn_church": {"subject": "a rectangular church carved down out of a single block of red rock, its flat roof level with the ground, carved windows on its sides, standing in a deep trench cut around it", "seed": 2,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_slavonic__memorial_church": {"subject": "a white stone memorial church with gilded onion domes", "seed": 0,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_slavonic__column": {"subject": "a tall red granite column topped by a bronze angel, in a vast palace square", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_slavonic__bell_tower": {"subject": "a tall white tiered bell tower with a golden dome and open arched bell chambers", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_avestan__gate": {"subject": "a monumental Persian palace gate guarded by huge stone winged bulls, tall columns rising behind it", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_avestan__hall": {"subject": "a vast Persian columned audience hall on a raised stone terrace, with carved processional stairways", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_arabic__hall": {"subject": "a great palace hall with rows of red and white striped horseshoe arches under a carved dome", "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_arabic__gate": {"subject": "a monumental gate with a tall pointed arch covered in blue and turquoise tilework, between two slender towers", "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_chinese__hall": {"subject": "a grand Chinese palace hall with a double-eaved golden-yellow tiled roof on a three-tiered white marble terrace", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_chinese__gate": {"subject": "a tall Chinese ceremonial archway of red lacquered pillars and green-and-gold tiled roofs", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_chinese__pagoda": {"subject": "a tall nine-storey Chinese pagoda with upturned eaves at every level, beside a lake", "seed": 0,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_greek__pantheon": {"subject": "a Greek Doric temple of white marble with a sculpted pediment, on a rocky hilltop", "seed": 0,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_greek__column": {"subject": "a single tall Ionic marble column bearing a winged victory statue, in a Greek plaza", "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_greek__stoa": {"subject": "a long two-storey Greek stoa colonnade of white marble lining a market square", "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_irish__round_tower": {"subject": "a tall slender Irish stone round tower with a conical stone cap, beside a ruined chapel in green hills", "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_irish__high_cross": {"subject": "a tall carved Celtic stone high cross with a ring around its head, in a green churchyard", "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_nahuatl__pyramid": {"subject": "a stepped Aztec pyramid with twin temples on top and a steep double staircase, in a plaza", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_nahuatl__sun_stone": {"subject": "a giant round carved stone sun calendar disc standing upright on a plinth in a plaza", "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_norse__rune_stone": {"subject": "a tall rune stone carved with a looping serpent band, on a grassy burial mound by a fjord", "seed": 0,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_norse__hall": {"subject": "a long Viking mead hall with a curved turf roof and carved dragon heads on its gables", "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_gothic__hall_of_fame": {"subject": "a white marble Greek-temple hall of fame on a high terraced hill above a wide river", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_gothic__tower": {"subject": "a massive square memorial tower of dark granite on a hilltop, ringed near its top by huge stone warrior figures, its plain walls and base uncarved", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_mayan__pyramid": {"subject": "a steep Maya temple-pyramid with a roof-comb temple on top, rising from the jungle", "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_mayan__stela": {"subject": "a tall Maya stone stela carved with a richly dressed ruler, beside a round altar stone in a jungle plaza", "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_prussian__hill_shrine": {"subject": "a grassy terraced hill fort with a wooden palisade and a small wooden shrine on its summit", "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_prussian__sacred_oak": {"subject": "an enormous ancient oak tree in a clearing, ringed by carved wooden posts around a stone altar", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_aramaic__rock_cut": {"subject": "a tall classical temple facade carved straight into a rose-red sandstone cliff", "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_aramaic__colonnade": {"subject": "a long desert colonnade of weathered sandstone columns with a monumental arch, palm trees around it", "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "faith_catholic__faith": {"subject": "a great domed basilica with twin bell towers and a colonnaded forecourt", "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "faith_protestant__faith": {"subject": "a tall Gothic cathedral of grey stone with a single soaring spire", "seed": 0,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "faith_orthodox__faith": {"subject": "a large Orthodox cathedral with five gilded onion domes and white walls", "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "faith_oriental_orthodox__faith": {"subject": "an ancient stone church with a tall conical dome on a high plateau", "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "faith_sunni__faith": {"subject": "a great mosque with a broad central dome, cascading half-domes and four slender minarets", "seed": 0,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "faith_shiite__faith": {"subject": "a Persian shrine mosque with a golden onion dome on a tall tiled drum, two slender golden minarets and a tall tiled entrance arch facing a courtyard", "seed": 2,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "faith_ibadi__faith": {"subject": "a plain whitewashed mosque with a square minaret and a small low dome, beside date palms", "seed": 0,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "faith_jewish__faith": {"subject": "a grand domed synagogue in Moorish revival style with two towers and horseshoe arches", "seed": 0,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "faith_mahayana__faith": {"subject": "a tall multi-storey wooden Buddhist pagoda with red pillars and upturned eaves among pine trees", "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "faith_gelugpa__faith": {"subject": "a vast white and red Tibetan monastery climbing a mountainside, with golden roofs", "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "faith_theravada__faith": {"subject": "a huge golden bell-shaped stupa with a tall pointed spire, ringed by smaller shrines", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "faith_confucian__faith": {"subject": "a Confucian temple of red walls and yellow-tiled halls around a courtyard of old cypress trees", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "faith_hindu__faith": {"subject": "a Hindu temple complex with tall carved stone gateway towers and a stepped water tank", "seed": 1,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "faith_shinto__faith": {"subject": "a Shinto grand shrine of unpainted cypress wood with a thatched roof, approached through a large torii gate in a cedar forest", "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "faith_sikh__faith": {"subject": "a white marble gurdwara with a ribbed central dome and small domed kiosks, beside a large pool", "seed": 0,
                             "now": f"{_BI}/building_grand_monument.dds"},
        "faith_animist__faith": {"subject": "a sacred grove of giant trees hung with ribbons, carved wooden totems around a stone circle in a clearing", "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "generic__opera_house": {"subject": "a grand Beaux-Arts opera house with a green copper dome and gilded statues on its facade", "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_chinese__opera_house": {"subject": "a Chinese opera stage pavilion with sweeping red and gold roofs, facing a courtyard of seats", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_greek__opera_house": {"subject": "a great semicircular open-air Greek stone theatre cut into a hillside, a stage building at its foot", "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "generic__gardens": {"subject": "botanical gardens with a great Victorian glass and iron palm house among formal flower beds", "seed": 0,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_avestan__gardens": {"subject": "a Persian garden divided into four by long water channels, a pavilion at its centre and rows of cypresses", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_arabic__gardens": {"subject": "an Andalusian courtyard garden with a long reflecting pool, orange trees and arcades of slender columns", "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_chinese__gardens": {"subject": "a Chinese scholar's garden with a zigzag bridge, rockeries, a pond and a pavilion", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "generic__observatory": {"subject": "a grand domed astronomical observatory on a hilltop, its dome slit open to the sky", "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_sanskrit__observatory": {"subject": "a courtyard of huge pink stone astronomical instruments: a giant triangular sundial wall with a staircase up its sloping edge and curved quadrant scales on both sides", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_avestan__observatory": {"subject": "a great curved stone meridian arc descending into a round blue-tiled building", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_chinese__observatory": {"subject": "an ancient Chinese observatory on a city wall tower, with large bronze armillary spheres", "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_mayan__observatory": {"subject": "a Maya round observatory tower on a stepped stone platform in the jungle", "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "generic__exhibition_hall": {"subject": "a vast glass and iron exhibition palace with a barrel-vaulted transept, flags flying", "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "generic__stadium": {"subject": "a large modern oval sports stadium with floodlights and a green pitch inside", "seed": 1,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_latin__stadium": {"subject": "a great oval Roman amphitheatre arena of tiered stone arches", "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_greek__stadium": {"subject": "a long horseshoe-shaped white marble stadium with tiered stone seats", "seed": 0,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_nahuatl__stadium": {"subject": "an Aztec ball court shaped like a capital I with stone rings set in its walls, in a plaza", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "heritage_mayan__stadium": {"subject": "a Maya ball court between two long sloping stone walls with stone rings set high on them", "seed": 0,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        # The landmarks standing in 1836 (phase 4 spec 2026-10-12 §5.1): the real monument, as it stood then.
        "landmark_arc_de_triomphe__arch": {"subject": "the Arc de Triomphe in Paris: a colossal single-bay neoclassical triumphal arch of pale limestone with great sculpted relief groups on its four piers and a plain flat attic, alone at the centre of a vast round plaza with broad avenues radiating from it", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_alexander_column__column": {"subject": "the Alexander Column in Saint Petersburg: a single tall polished red granite column topped by a bronze angel holding a cross, on a square bronze-trimmed pedestal, centred in a vast cobbled square in front of a long green and white Baroque palace", "seed": 1,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_brandenburg_gate__gate": {"subject": "the Brandenburg Gate in Berlin: a sandstone neoclassical gateway of twelve Doric columns forming five passages, topped by a bronze chariot drawn by four horses, flanked by two small temple-like side wings, at the head of a long tree-lined avenue", "seed": 2,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_washington_monument_baltimore__column": {"subject": "a monument in Baltimore: one tall round white marble Doric column of even width with a plain shaft and a square capital, a small statue of a standing man in a toga on its top, on a broad square stone base, in a cross-shaped park of lawns and trees among red brick townhouses", "seed": 0,
                                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_la_scala__opera_house": {"subject": "La Scala opera house in Milan: a restrained neoclassical facade of pale stone with a projecting portico of arched carriage entrances carrying a columned loggia and a low triangular pediment, on a narrow city square", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        # s0 is retouched: lettering on its pediment (raw in ~/flux_runs/originals/gm_pictures/).
        "landmark_teatro_di_san_carlo__opera_house": {"subject": "a neoclassical opera house in Naples: a projecting porch of five rusticated round arches on the ground floor and a row of Ionic columns on the floor above, built onto the side of a long red royal palace on a city square, the Bay of Naples and a volcano beyond", "seed": 0,
                                                     "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_jantar_mantar__observatory": {"subject": "the Jantar Mantar in Jaipur: a walled courtyard of huge ochre-yellow stone astronomical instruments, a giant triangular sundial wall with a staircase up its sloping edge, round sunken bowls and curved quadrant scales, a pink sandstone palace behind", "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_shalimar_gardens__gardens": {"subject": "the Shalimar Gardens in Lahore: a walled Mughal garden on three descending terraces, long water channels lined with rows of fountains, a great marble pool with a central platform, red sandstone pavilions with small domed kiosks, cypress and fruit trees", "seed": 1,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_jardim_botanico__gardens": {"subject": "the botanical garden of Rio de Janeiro: a long straight avenue of towering royal palm trees leading to a small stone fountain, tropical flower beds and a lily pond, steep forested granite peaks behind", "seed": 1,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_stelae_of_aksum__stele": {"subject": "the great stele of Aksum in Ethiopia: one tall slender monolith of smooth dressed grey granite with a rounded top, carved to look like a many-storeyed tower, each storey a band of small false windows above a row of round beam ends, a false door at its foot, standing on a stone base plate among smaller plain stelae in a dry highland park, a town of round thatched houses and green hills beyond", "seed": 2,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_liberty_column__obelisk": {"subject": "a tall slender pointed obelisk of pale red sandstone with nothing on its tip, on a square pedestal with four small white marble statues standing at its corners, in the middle of a wide Copenhagen street lined with tall townhouses", "seed": 2,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_lion_monument__statue": {"subject": "the Lion Monument in Lucerne: a dying lion carved in relief into a vertical sandstone cliff face, lying in a shallow niche cut into the rock with a broken spear in its side and a paw over a shield, a still dark pond at the foot of the cliff, trees on the clifftop", "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        # Added 2026-10-11 (owner): monuments a revolution contests.
        "landmark_temple_of_heaven__hall": {"subject": "the Temple of Heaven in Beijing: a round three-tiered hall with deep blue glazed tile roofs and a gilded top, on a three-level round white marble terrace, at the end of a long raised walkway through a park of old cypress trees", "seed": 1,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_topkapi_palace__gate": {"subject": "Topkapı Palace in Istanbul: a walled Ottoman palace of courtyards shaded by plane trees, low domed kiosks with wide eaves, rows of conical lead chimneys and a tall stone tower with a pointed lead spire, entered through a massive white marble gate with a tall pointed arch, on a green point above the Bosphorus", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_golestan_palace__hall": {"subject": "the Golestan Palace in Tehran: a Persian royal hall open at the front on twisted marble columns, its back wall glittering with mirror mosaic, a carved marble throne on its terrace above a long pool in a garden courtyard of tiled walls", "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_basilica_of_superga__mausoleum": {"subject": "the Basilica of Superga: a Baroque church with a tall dome between two bell towers and a columned portico, alone on a wooded hilltop high above the city of Turin and the Po valley, the snowy Alps beyond", "seed": 2,
                                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tomb_of_william_the_silent__mausoleum": {"subject": "the New Church of Delft: a tall Gothic brick church with a soaring many-tiered spire on the market square of a Dutch canal town, stepped-gabled houses around the square", "seed": 2,
                                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_cenotaph_of_maximilian__mausoleum": {"subject": "the Court Church of Innsbruck: a white Gothic church with a tall onion-domed bell tower beside a long Habsburg palace in an old Alpine town, snowy mountain peaks behind", "seed": 0,
                                                      "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_arco_de_santa_maria__gate": {"subject": "the Arco de Santa María in Burgos: a tall pale stone gate tower in the old city wall, its face a triumphal facade of niches holding statues of kings and an emperor, round turrets at its corners, a river bridge in front and the spires of a Gothic cathedral behind", "seed": 0,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_statue_of_louis_xiv__statue": {"subject": "the equestrian statue of Louis XIV in Lyon: a bronze king on horseback on a tall stone pedestal, alone in the middle of a vast open square of red-ochre gravel framed by tall pale buildings, a hill above the city", "seed": 1,
                                                "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_lion_of_saint_mark__column": {"subject": "a tall granite column topped by a bronze winged lion on the waterfront square of Venice, before the pink and white Gothic palace of the Doges, gondolas on the lagoon", "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_sans_souci_palace__hall": {"subject": "the Sans-Souci Palace in Haiti: a grand ochre and white royal palace with wide double staircases and terraced gardens on green tropical hillsides, a great stone fortress on a mountain peak beyond", "seed": 0,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_nikko_toshogu__gate": {"subject": "Nikkō Tōshō-gū: an ornate Japanese shrine gate painted white and gold, crowded with carved figures under curved black roofs, on a stone terrace in a forest of tall cedar trees, lacquered shrine halls behind", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        # Added 2026-10-12 (the loot spec, 2026-10-12-grand-monument-loot-and-1836-trophies-design.md):
        # the landmarks to loot, as they stood in 1836.
        "landmark_parthenon__pantheon": {"subject": "the ruined Parthenon on the Acropolis of Athens: a roofless Doric temple of weathered honey-coloured marble, a wide gap blown out of the middle of both long colonnades, fallen column drums and blocks heaped in the gap, a small domed mosque standing inside the ruin, on the high flat walled rock above the little town of Athens, a tall square medieval tower by the citadel's gateway", "seed": 2,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_obelisks_of_karnak__obelisk": {"subject": "the temple of Amun at Karnak: two tall slender pink granite obelisks rising among massive ruined sandstone gateways and a forest of huge carved columns, the ruins half buried in drifted sand, mud-brick village houses and palm trees around them, the Nile beyond", "seed": 1,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_royal_palace_of_benin__hall": {"subject": "the royal palace of Benin in West Africa: long low walls of red earth moulded in horizontal ridges around courtyards, under steep roofs of grey palm thatch, tall pyramid-shaped turrets each crowned by a large cast-brass bird with spread wings, a huge brass snake winding down a turret's face, an open gallery on wooden pillars faced with square brass plaques, a city of red earth houses among palm trees", "seed": 0,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_royal_palace_of_kumasi__hall": {"subject": "the Asante king's palace in Kumasi: courtyard houses with walls of red earth carved in bold swirling relief patterns, polished red below and whitewashed above, under steep thatched roofs, beside them a square two-storey stone treasure house with a flat roof and small arched windows, a great shade tree and large royal umbrellas on the open square", "seed": 2,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_bukgwan_victory_stele__stele": {"subject": "a tall slender grey stone stele with a carved roof-shaped capstone, set on a low stone base, its face weathered smooth and blank, standing alone on a stone terrace on a pine-covered hillside above a walled Korean town of curved grey-tiled roofs, rugged mountains beyond", "seed": 1,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_imperial_city_of_hue__gate": {"subject": "the Meridian Gate of the citadel of Huế: a massive U-shaped stone platform pierced by arched passages, crowned by a long two-storey wooden pavilion with tiers of yellow glazed tile roofs on red lacquered pillars, a moat of lotus flowers and a stone bridge in front", "seed": 2,
                                                "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_persepolis__hall": {"subject": "the ruins of Persepolis: a vast stone terrace at the foot of a bare mountain, a few very tall slender fluted stone columns still standing alone, a ruined gateway guarded by colossal stone winged bulls with bearded human heads, a broad double staircase carved with rows of relief figures, a dry plain", "seed": 0,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_red_fort__gate": {"subject": "the Red Fort of Delhi: massive crenellated walls of red sandstone above a moat, a great gatehouse with a tall pointed arch between two octagonal towers topped with open domed pavilions, a row of small white marble domed kiosks along its top, a crowded bazaar street before it", "seed": 2,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_great_zimbabwe__round_tower": {"subject": "the Great Enclosure of Great Zimbabwe: a huge curving wall of neatly fitted grey granite blocks laid without mortar, a chevron pattern along its top, inside it a tall solid conical stone tower, a rocky hill with ruined walls among boulders behind, savanna trees and long grass growing over the ruins", "seed": 1,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_royal_palaces_of_abomey__hall": {"subject": "the royal palace of the kings of Dahomey at Abomey: long low buildings with red clay walls under huge shaggy golden straw-thatch roofs that come down almost to the ground, small square painted clay relief panels of lions, sharks and warriors set in rows along the walls, a high red earth wall around a wide dusty courtyard, baobab trees", "seed": 1,
                                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_klungkung_palace__gate": {"subject": "the palace of Klungkung in Bali: a tall roofed gateway of red brick covered in carved grey stone ornament with a narrow door at the top of steep steps, beside it an open hall of justice on a high stone platform under a steep roof, its ceiling painted with crowded figures, a pond with a floating pavilion, frangipani trees", "seed": 2,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_uffizi_gallery__hall": {"subject": "the Uffizi in Florence: two long uniform wings of a Renaissance building of grey stone and pale plaster facing each other across a narrow courtyard, an arcaded loggia along the ground floor, joined at the far end by an arched block over the river Arno, the tall stone tower of the Palazzo Vecchio beyond", "seed": 2,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        # s0 is retouched: a lettered plaque at the ramp's foot (raw in ~/flux_runs/originals/gm_loot/).
        "landmark_capitoline_museums__forum": {"subject": "Michelangelo's square on the Capitoline Hill in Rome: a bronze equestrian statue of a Roman emperor at the centre of a paved piazza, twin palaces with giant pilasters and ground-floor porticoes facing each other on either side, a palace with a double outdoor staircase and a bell tower at the far end, a broad stepped ramp rising to the square between colossal statues of youths with horses", "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_bodrum_castle__tower": {"subject": "Bodrum Castle: a crusader castle of honey-coloured stone on a rocky peninsula between two turquoise bays, tall square towers with battlements over curtain walls and a sea gate, carved marble frieze slabs and coats of arms set into its walls, a small whitewashed town and old windmills on the hills", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_temples_of_baalbek__colonnade": {"subject": "the ruins of Baalbek: six colossal Roman columns standing alone in a row under a fragment of richly carved entablature, on a platform of enormous stone blocks, beside a well-preserved Roman temple ringed with columns, inside ruined medieval citadel walls, the snowy mountains of Lebanon beyond", "seed": 2,
                                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_palmyra__colonnade": {"subject": "the ruins of Palmyra in the Syrian desert: a long colonnaded street of honey-coloured columns, a monumental arch, the great walled temple of Bel with mud-brick village houses crowded inside its walls, square tower tombs on the bare hills, the palm groves of an oasis", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_xanthos__rock_cut": {"subject": "the ruins of Xanthos in Lycia: two tall square stone pillars, each topped by a small carved stone burial chamber with a heavy lid, beside a ruined Roman theatre, a heap of tumbled carved blocks and broken columns where a temple-tomb has fallen, tomb fronts carved into a cliff face, on a wooded hill above a river valley", "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mesha_stele__stele": {"subject": "a black basalt stele with a rounded top, its face finely incised with rows of small carved signs, standing upright in the foreground on the ruined stone mound of an ancient town on a dry upland plateau, low stone walls, black Bedouin tents, a deep gorge beyond", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_arch_of_ctesiphon__arch": {"subject": "Taq Kasra at Ctesiphon: a gigantic open-fronted brick vault, a tall parabolic arched opening like the mouth of a huge tunnel rising from the ground, set in the middle of a high flat brick wall covered in rows of small blind arches and stretching out on both sides, alone on the flat dusty plain by the Tigris, a few palm trees", "seed": 0,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        # The never-placed origins of the 1836 trophies (placed=False), as each would stand once its
        # trophy goes home.
        "landmark_rosetta_stone__stele": {"subject": "a dark grey granite slab with a jagged broken top edge and a polished face finely incised with rows of tiny carved signs, set upright on a low stone plinth in the courtyard of a sand-coloured Ottoman fort on the Nile delta, date palms beyond", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_temple_of_dendera__colonnade": {"subject": "the temple of Hathor at Dendera in Egypt: a massive flat-roofed sandstone temple, its front a row of six thick columns topped by huge square capitals carved with a woman's face, a deep curved Egyptian cornice above, its courts half buried in drifted sand with mud-brick huts on the roof, inside a high mud-brick enclosure wall, desert and palms beyond", "seed": 1,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        # s0 is retouched: lettering on its lintel and a sign (raw in ~/flux_runs/originals/gm_loot/).
        "landmark_luxor_obelisk__obelisk": {"subject": "the temple of Luxor on the bank of the Nile: a tall pink granite obelisk standing before a huge sloping stone temple gateway, two colossal seated pharaoh statues half buried in sand by its door, mud-brick village houses and a small mosque among the ruins, palm trees", "seed": 0,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_venus_de_milo__statue": {"subject": "an armless white marble statue of a goddess, her arms ending in rough broken stumps just below the shoulders, bare to the hips with heavy drapery round her legs, standing outdoors on a stone pedestal among ruined ancient stone terraces on a Greek island hillside, olive trees, the blue sea far below", "seed": 11, "style": STATUE_STYLE,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_piraeus_lion__statue": {"subject": "a colossal white marble lion seated upright on its haunches on a tall stone plinth at the mouth of a small ancient harbour, a rocky Greek shore, fishing boats, bare hills", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_horses_of_saint_mark__statue": {"subject": "four gilded bronze horses striding side by side on a tall stone pedestal on the long open square of the old Hippodrome of Constantinople, an ancient Egyptian obelisk nearby, the domes and slender minarets of a great mosque beyond", "seed": 0,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tipus_tiger__statue": {"subject": "a life-size painted wooden tiger mauling a man in a red coat, on a low dais under the painted arcades of an Indian teak summer palace, its walls covered in bright murals, a formal garden and cypress trees beyond", "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_baba_merzoug__column": {"subject": "a very long bronze cannon on a heavy wooden carriage on a stone harbour battery, pointing out to sea, the white houses of Algiers climbing a steep hill behind, an old lighthouse tower on the harbour mole", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_royal_palace_of_kandy__hall": {"subject": "the royal palace of Kandy in Ceylon: an open audience hall of carved wooden pillars under a steep red-tiled roof, beside an octagonal white pavilion with a tiered tiled roof, long low white palace buildings on the shore of a lake, wooded green hills", "seed": 0,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        # The buried sites (issue #939), as each stands once dug: the excavated site, never a museum
        # room. A portable find (a statue-form site) is drawn where it was found.
        "landmark_nineveh_library__hall": {"subject": "the excavated Assyrian palace at Nineveh: deep trenches cut into a great grassy mound beside the Tigris, long walls of grey stone relief panels carved with lion hunts and chariots exposed along the trench sides, a palace doorway guarded by two colossal stone winged bulls with bearded human heads, spoil heaps and wooden ladders, the domes and minarets of a city across the river", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_winged_victory_of_samothrace__statue": {"subject": "the headless Winged Victory: a white marble statue of a winged goddess with no head and no arms, broken off at the neck and shoulders, great outspread wings behind her and wind-blown robes, standing on a grey stone ship's prow that juts out over a pool, high on a terrace of a ruined Greek sanctuary on a steep green island above the sea", "seed": 0,
                                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_vindolanda_tablets__hall": {"subject": "the excavated Roman fort of Vindolanda: the low grey stone foundations of barracks, granaries, a bathhouse and a commander's courtyard house laid out in neat rectangles on green northern moorland, a rebuilt stretch of stone wall with a square turret and a wooden gate tower, open excavation trenches of dark wet earth, bleak rolling hills and a long stone wall running along a ridge", "seed": 1,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_troy_hisarlik__gate": {"subject": "the excavated citadel mound of Hisarlik: a great sloping wall of fitted limestone blocks with a wide gateway and a stone-paved ramp leading up into it, layer upon layer of ruined walls of different ages exposed in a huge deep trench cut through the mound, dry grass and oak scrub, a flat plain running to the sea at the mouth of a strait", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mycenae_grave_circle__mausoleum": {"subject": "a Bronze Age Greek citadel: massive walls of huge rough-cut grey stone blocks around a rocky hilltop, a gateway with a great stone lintel under a triangular stone slab carved with two lions standing face to face, just inside the gate a ring of upright stone slabs enclosing deep rectangular shaft graves, ruined palace walls climbing to the summit, bare mountains and a green plain", "seed": 1,
                                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_pergamon_altar__pantheon": {"subject": "the excavated great altar of Pergamon: a broad nearly square marble platform on a terrace high on a steep acropolis hill, its base lined with a carved frieze of gods fighting giants, a wide flight of marble steps cut into one side leading up to an Ionic colonnade, fallen columns and carved blocks lying around it, ruined temples and a steep theatre on the slope, a town and a green plain far below", "seed": 0,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_deir_el_bahari_cache__rock_cut": {"subject": "the terraced temple of Hatshepsut at Deir el-Bahari: three broad colonnaded terraces of pale limestone joined by long central ramps, built against a towering sheer cliff of golden rock, a narrow dark shaft cut into the cliff face above, a line of workers carrying painted wooden coffins down the slope, the green Nile valley in the distance", "seed": 0,
                                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_ishtar_gate_babylon__gate": {"subject": "the Ishtar Gate of Babylon: a towering arched gateway between crenellated towers faced in deep blue glazed brick decorated with rows of yellow bulls and white dragons in relief, a processional way between high walls of blue glazed brick with striding lions leading to it, excavated out of brown earthen mounds on a flat plain, date palms and a river", "seed": 1,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_palace_of_knossos__hall": {"subject": "the excavated Minoan palace of Knossos on Crete: a sprawling maze of stone rooms, light wells, courtyards and grand staircases on a low hillside, a restored portico of red columns that taper towards their base with black cushion capitals, a wall painted with a fresco of a charging bull, a pair of huge carved stone bull's horns on a wall top, olive groves and mountains", "seed": 2,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_antikythera_mechanism__statue": {"subject": "a rocky bay on a small barren Greek island, clear turquoise water showing the seabed where an ancient shipwreck lies strewn with clay amphorae and fallen bronze statues, a wooden sponge divers' boat at anchor above it with a diver in a heavy copper helmet on its ladder, on the stone quay a large weathered green bronze sculpture of interlocking gear wheels on a plinth, a small white chapel and a few houses on the shore", "seed": 0,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_oseberg_ship__statue": {"subject": "a Viking ship burial being uncovered: a long slender dark oak longship with a tall spiralling carved prow and stern, lying in a deep trench cut into a great grassy earthen burial mound, its hull packed in blue clay, timber shoring and wooden walkways around it, a Norwegian farm of red wooden barns, birch trees and a fjord beyond", "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_machu_picchu__gate": {"subject": "Machu Picchu: the grey granite ruins of an Inca city of roofless stone houses, temples and long green terraces on a narrow saddle between two steep jungle-covered mountains, a sharp pointed peak towering behind, a trapezoid stone gateway, clouds in the deep valleys below", "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_bust_of_nefertiti__statue": {"subject": "the excavated ruins of Amarna on a wide desert plain beside the Nile: the low mud-brick walls of a city of houses laid bare in a grid, in the middle the open courtyard of a sculptor's workshop where a painted limestone bust of an Egyptian queen with a tall flat-topped blue crown sits on a low plinth beside shelves of plaster heads, a curve of pale cliffs and a strip of green palms beyond", "seed": 1,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mohenjo_daro__forum": {"subject": "the excavated ruins of an ancient Indus city: a grid of straight streets and roofless walls of baked red brick with covered drains, in front a great rectangular sunken bathing tank of fired brick with steps down at each end, behind it a low eroded brick mound with a crumbling round brick stump on top, the flat dusty plain", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tomb_of_tutankhamun__mausoleum": {"subject": "the Valley of the Kings: a dry rocky desert valley between steep pale limestone cliffs under a tall natural rocky peak, the dark doorways of rock-cut tombs in the cliff sides, a steep flight of stone steps cut down into the valley floor to a newly opened tomb doorway, gilded wooden shrines and chests being carried out, the excavators' white tents", "seed": 1,
                                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_royal_cemetery_at_ur__mausoleum": {"subject": "the excavated city of Ur in the Mesopotamian desert: a great stepped temple tower of mud brick with three long stairways meeting at its front, beside it a deep stepped excavation pit opening the royal tombs, chambers of mud brick at its bottom, lines of basket carriers on ramps of spoil, a flat dusty plain", "seed": 1,
                                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_sanxingdui_pits__hall": {"subject": "the excavated sacrificial pits of Sanxingdui in Sichuan: neat rectangular pits cut in red earth under a long timber-roofed shelter, filled with green bronze masks with huge protruding eyes and great flared ears and heaps of ivory elephant tusks, a tall green bronze tree with birds perched on its branches standing beside the pits, rice paddies, bamboo and misty green hills", "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_sutton_hoo__mausoleum": {"subject": "an Anglo-Saxon ship burial being uncovered: a deep trench cut into a large round grassy burial mound on a sandy heath, at its bottom the ghostly imprint of a long ship traced in rows of rusted iron rivets in the sand, other low burial mounds around it, pine trees and a river estuary beyond", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_lascaux_caves__rock_cut": {"subject": "the cave of Lascaux shown as a cut-away of a wooded limestone hillside above a river valley: a narrow cave entrance among oak trees, and inside the hill a vaulted cave hall whose pale walls are painted in red, black and ochre with great bulls, horses and stags, lit by a lantern", "seed": 1,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_nag_hammadi_library__stele": {"subject": "the foot of steep honey-coloured cliffs above the Nile valley, honeycombed with the dark doorways of ancient rock tombs, scree slopes, at their foot a tall red clay storage jar broken open beside a boulder, a farmer with a donkey, green sugar cane fields and the river beyond", "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_dead_sea_scrolls__stele": {"subject": "the caves of Qumran: dark cave mouths in steep crumbling tan cliffs above the ruins of a stone settlement with cisterns on a dry terrace, tall cylindrical clay jars with lids in the mouth of a cave, the flat pale blue Dead Sea and purple mountains beyond", "seed": 2,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tomb_of_pakal__pyramid": {"subject": "a Maya temple-pyramid at Palenque: a steep stepped limestone pyramid with a broad central stairway, topped by a temple with five doorways and a sloping roof, beside a palace with a square stone tower, cleared from dense green rainforest, mist on the hills", "seed": 2,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mawangdui_tombs__mausoleum": {"subject": "an opened Han dynasty tomb: a deep stepped pit cut into a hill of yellow earth, at its bottom a huge rectangular box tomb of dark wooden planks with its lid planks lifted off, showing nested coffins lacquered glossy black and red and painted with swirling clouds, workers on the terraced sides of the pit, rice fields and green hills", "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_terracotta_army__mausoleum": {"subject": "the Terracotta Army: long parallel earthen trenches open to the sky, filled with rows upon rows of life-size grey clay soldiers and horses facing forward, the great forested burial mound of the First Emperor rising from the plain beyond, distant mountains", "seed": 2,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tomb_of_philip_ii__mausoleum": {"subject": "the royal tombs of Vergina: the painted marble facade of a Macedonian royal tomb with four Doric half-columns, a painted frieze of a hunting scene and great marble doors, uncovered at the bottom of a deep cut into a huge round grassy burial mound, a Greek village of red-tiled roofs and mountains", "seed": 1,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tomb_of_marquis_yi__hall": {"subject": "an opened ancient Chinese tomb: a vast burial chamber of dark wooden timbers divided into rooms at the bottom of a deep pit in a red earth hill, in one room a long two-tier lacquered wooden frame hung with rows of bronze bells of graded size, black and red lacquered coffins in another, green hills", "seed": 1,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_royal_tombs_of_sipan__pyramid": {"subject": "the royal tombs of Sipan in northern Peru: two huge ancient mounds of mud brick, so worn by rain that they look like shapeless rounded brown hills cut by deep gullies, beside them a low flat-topped mud-brick platform excavated in square pits, one open burial chamber laid with gold and copper ornaments, green sugar-cane fields and dry desert hills", "seed": 1,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_otzi_the_iceman__statue": {"subject": "a high rocky mountain pass on a glacier ridge in the Alps: a shallow rock gully where melting ice has left a hollow, a small stone pyramid marker standing on the rocks beside it, patches of old snow, a wooden mountain hut, jagged snowy peaks all around under a clear sky", "seed": 1,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_caral_supe__pyramid": {"subject": "the sacred city of Caral in Peru: several great flat-topped platform mounds built of grey stone terraces, each a broad truncated mound with one wide central staircase and a flat empty top, a round sunken plaza ringed by stone steps in front of the largest, on a dry desert terrace above a green river valley of fields, bare brown mountains", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_gobekli_tepe__colonnade": {"subject": "Gobekli Tepe: the rounded summit of a hill of pale limestone and dry grass, dug out into several round sunken enclosures, each walled with rough stone and ringed by a dozen huge T-shaped limestone pillars set into its wall and carved in relief with foxes, boars and vultures, two taller T-shaped pillars standing in the middle of each, rolling brown steppe hills and a lone tree", "seed": 1,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_olympia__pantheon": {"subject": "the sanctuary of Olympia: the great ruined Doric temple of Zeus, its huge column drums lying fallen in rows where an earthquake toppled them, a few columns of a smaller temple standing, a long stadium entered through a vaulted stone tunnel, ruined colonnades and treasuries among pine trees on a green wooded hill, a river valley", "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_delphi__stoa": {"subject": "the sanctuary of Delphi on the slopes of Mount Parnassus: a ruined Doric temple with six columns standing on a high terrace, a small marble treasury temple on a winding sacred way, a stone theatre above the temple, a long colonnade along a terrace wall below, towering grey cliffs above and a deep valley of olive trees running to the sea", "seed": 2,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_sidon_necropolis__mausoleum": {"subject": "a royal necropolis on a hillside of orange groves above an old Mediterranean port: a deep square shaft opened in the rock with burial chambers cut around its foot, white marble sarcophagi carved with battle and hunting scenes and lids shaped like temple roofs being hauled up on ropes, the port town and a small sea castle beyond", "seed": 1,
                                                "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_villa_of_the_papyri__hall": {"subject": "the excavated Villa of the Papyri at Herculaneum: a grand Roman seaside villa with a long colonnaded garden and a narrow ornamental pool lined with bronze statues, partly dug out of a deep cliff of grey hardened volcanic rock, a town on top of the cliff, the volcano Vesuvius beyond, the Bay of Naples", "seed": 1,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tomb_of_alexander__mausoleum": {"subject": "a cut-away of the city of Alexandria: beneath its streets, a domed mosque and palm trees, a sealed underground royal tomb of white alabaster opened by excavators, its burial chamber holding a golden sarcophagus, the harbour and a lighthouse tower beyond", "seed": 1,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_pompeii__forum": {"subject": "the excavated ruins of a Roman town dug out of grey volcanic ash: a long open forum paved with pale stone slabs, lined on both sides by rows of broken columns, a ruined temple on a high red brick podium at its far end, roofless houses with red and ochre plastered walls along straight stone-paved streets all around, a steep bank of grey ash at the edge of the dig, the broad cone of the volcano Vesuvius beyond with a thin plume of smoke, vineyards and umbrella pines", "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        # The historical opportunities' landmarks (signatures spec §6.4), as completed.
        "landmark_walhalla__hall_of_fame": {"subject": "the Walhalla near Regensburg: a white marble Doric temple like the Parthenon, its pediments filled with sculpture, standing high on a wooded hillside above the river Danube on a vast stepped terrace of grey stone with broad flights of stairs climbing to it, a green plain below", "seed": 0,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_bunker_hill_monument__obelisk": {"subject": "a tall plain grey granite obelisk with a small pyramid tip, alone on a grassy hilltop square ringed by an iron fence, the red brick and white clapboard houses of a New England town around it, a harbour with sailing ships beyond", "seed": 2,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_obelisk_of_the_second_of_may__obelisk": {"subject": "a slender grey granite obelisk on a tall square stone pedestal carved with a sarcophagus, four allegorical stone statues seated around its base, inside a small round garden ringed by iron railings on a wide tree-lined boulevard of Madrid, a long neoclassical museum building beyond", "seed": 3,
                                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_muhammad_ali_mosque__faith": {"subject": "the Mosque of Muhammad Ali in Cairo: a great Ottoman mosque with a large central dome surrounded by cascading half domes and smaller domes, exactly two very tall slender pencil-shaped minarets standing side by side at its front corners, its walls faced in pale alabaster, crowning the walled stone citadel on a hill above the domes and minarets of the city, dusty lanes with camels and donkeys, desert hills beyond", "seed": 2,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_nelsons_column__column": {"subject": "Nelson's Column in London: a very tall grey granite Corinthian column topped by a small statue of an admiral, four great bronze lions lying around its square base, in the middle of a wide paved square with two fountains, a long columned gallery building with a small dome along one side", "seed": 1,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_washington_monument__obelisk": {"subject": "the Washington Monument: a colossal plain white marble obelisk with a pointed pyramid tip, alone on a grassy rise in the middle of a long open lawn, a white domed capitol building at the far end", "seed": 2,
                                                 "now": f"{_BI}/building_grand_monument.dds"},
        # To History, standing in 1836 (tourism heritage spec 2026-10-23, PR #1139): as they stood then.
        "landmark_pyramids_of_giza__pyramid": {"subject": "the Pyramids of Giza: three great pyramids of weathered tan limestone blocks on a desert plateau, the largest stripped of its casing to rough stepped courses, the second still capped with smooth white casing near its peak, the head and shoulders of the Great Sphinx rising from drifted sand in front, the green Nile valley with palm groves and mud-brick villages below", "seed": 2,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_petra__rock_cut": {"subject": "the Treasury at Petra: a tall two-storey temple facade of columns, a broken pediment and a round central pavilion carved straight into a sheer rose-red sandstone cliff, at the end of a narrow winding gorge, rock-cut tomb fronts in the cliffs around, a few Bedouin with camels", "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_moscow_kremlin__tower": {"subject": "the Moscow Kremlin: long red brick walls with swallowtail battlements and tall pointed red brick towers with green tent roofs and small golden eagles on their spires, above a river embankment, inside the walls white cathedrals with clusters of gilded onion domes and a tall white bell tower with a golden dome", "seed": 2,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_fasil_ghebbi__hall": {"subject": "the royal castle of Gondar in Ethiopia: a massive castle of rough brown stone with round corner towers capped by domes, battlemented walls and a tall square keep, inside a walled enclosure of other ruined stone palaces among tall trees, green highland hills", "seed": 2,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_valley_of_the_temples__pantheon": {"subject": "the Temple of Concordia at Agrigento: a well-preserved Doric temple of golden-brown limestone with its full ring of columns and both pediments, on a long ridge among almond and olive trees, other ruined temples with a few columns standing along the ridge, the sea beyond", "seed": 2,
                                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_borobudur__gate": {"subject": "Borobudur in Java: a huge stepped stone monument of square terraces lined with carved relief galleries and small niches holding seated Buddhas, topped by three round terraces ringed with many small bell-shaped latticed stone stupas around one great central stupa, jungle cleared from its slopes, green volcanoes beyond", "seed": 5,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_old_city_of_sanaa__hall": {"subject": "the old city of Sana'a in Yemen: a dense cluster of tall many-storeyed tower houses of brown stone and mud brick, their facades decorated with white gypsum friezes around arched windows, a slender minaret among them, inside a city wall, bare mountains behind", "seed": 0,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_shibam__tower": {"subject": "Shibam in Yemen, the mud-brick city of tower houses: hundreds of very tall, very narrow tower houses of brown sun-dried mud brick, each eight storeys high and much taller than it is wide, packed shoulder to shoulder into one tall block with straight sheer sides, their top storeys whitewashed, small windows in rows up every face, a low mud wall at their foot, alone on a wide flat valley floor of fields and date palms between steep barren cliffs", "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_amphitheatre_of_el_djem__forum": {"subject": "the Roman amphitheatre of El Djem in Tunisia: a huge oval amphitheatre of honey-coloured stone with three tiers of arches, a wide gap broken through one side, standing among the small flat-roofed white houses of a village, olive groves on a flat plain", "seed": 2,
                                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_abu_simbel__rock_cut": {"subject": "the great temple of Abu Simbel: four colossal seated pharaoh statues carved out of a sandstone cliff face beside a doorway, sand drifted high against the cliff and up over their legs and laps, on the bank of the Nile in Nubia, desert hills", "seed": 3,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_temple_of_seti_abydos__colonnade": {"subject": "the temple of Seti I at Abydos: a long low limestone temple, its front a portico of thick square pillars carved with reliefs, behind it a roofed hall of massive papyrus columns, half buried in drifted sand, mud-brick village houses around it, palm trees at the desert edge", "seed": 0,
                                                     "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_pyramids_of_meroe__pyramid": {"subject": "the pyramids of Meroe in Sudan: dozens of small narrow pyramids of dark sandstone blocks with very steep sides, each with a small temple gateway at its foot, crowded in rows along low ridges of red sand, several with their tops broken off, a dry savanna with acacia trees", "seed": 1,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_windsor_castle__tower": {"subject": "Windsor Castle: a great grey stone royal castle with battlemented walls and towers, a tall round keep on a high grassy mound at its centre, a long Gothic chapel, on a hill above the river Thames and a small town, green parkland", "seed": 2,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_pont_du_gard__arch": {"subject": "the Pont du Gard: a Roman aqueduct bridge of three tiers of golden stone arches, large arches below and a long row of small arches on top, spanning a green river gorge between wooded hills", "seed": 2,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_palais_des_papes__hall": {"subject": "the Palace of the Popes in Avignon: a massive Gothic fortress palace of pale stone with tall square towers, high walls with deep pointed arches and battlements, on a rock above the river Rhone beside a cathedral, a broken medieval bridge reaching halfway into the river", "seed": 2,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mont_saint_michel__tower": {"subject": "Mont-Saint-Michel: a small rocky tidal island rising from wide wet sands at low tide, a Gothic abbey church with a short square tower on its summit above the tall walls of a monastery, a little walled village of grey stone houses climbing its slopes", "seed": 1,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_chateau_de_chambord__hall": {"subject": "the Chateau de Chambord: a huge French Renaissance chateau of white stone with four great round corner towers, its roof a forest of turrets, ornate chimneys, lanterns and small domes, a moat in front, in a vast forest park", "seed": 2,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_jeronimos_monastery__hall": {"subject": "the Jeronimos Monastery in Lisbon: an ornate white limestone Manueline monastery church with a richly carved portal and a short bell tower, a two-storey cloister of carved arches beside it, on the riverside plain of the Tagus, a small fortified tower standing in the river nearby", "seed": 0,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_alhambra__hall": {"subject": "the Alhambra in Granada: a red-walled Moorish palace fortress with square towers of red earth on a wooded hill, inside a long courtyard with a narrow rectangular pool lined with myrtle hedges reflecting a slender arched portico of delicate carved plasterwork, the snowy Sierra Nevada beyond", "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mezquita_of_cordoba__hall": {"subject": "the inside of the Great Mosque of Cordoba seen from above with its roof taken away: a vast hall filled with a forest of slender columns in long straight rows, every column carrying two tiers of horseshoe arches striped in red brick and white stone, the striped arches repeating into the distance, a richly gilded prayer niche in the far wall", "seed": 1,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_shore_temple__pillar": {"subject": "the Shore Temple at Mahabalipuram: two pyramid-shaped granite temple towers of tiered carved storeys, worn smooth by salt wind, standing on the beach at the edge of the sea with waves breaking near them, small carved stone bulls along the enclosure wall, great carved boulders on the land behind", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_charminar__gate": {"subject": "the Charminar in Hyderabad: a square monument of pale stone with four identical tall slender minarets, one rising from each of its four corners, each minaret ringed by balconies and topped by a small dome, each of its four faces pierced by one great pointed arch, a small mosque with arched windows on its upper floor between the minarets, at the crossing of four bazaar streets crowded with stalls, people and bullock carts", "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_gwalior_fort__gate": {"subject": "Gwalior Fort: a long hilltop fortress on steep sandstone cliffs above a town, massive walls, and a palace with round towers topped by small domed kiosks, its walls decorated with bands of blue, green and yellow glazed tiles, ancient temples on the plateau behind", "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_meteora__memorial_church": {"subject": "the monasteries of Meteora in Greece: small stone monasteries with red-tiled roofs perched on the flat tops of giant sheer grey rock pillars rising from a green plain, a rope net hoist hanging down one cliff", "seed": 1,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_citadel_of_aleppo__gate": {"subject": "the Citadel of Aleppo: a massive medieval fortress on a huge oval mound with a steep stone-faced slope, ringed by a dry moat, entered by a tall fortified gate tower reached over a long arched stone bridge, the domes and minarets of an old stone city around it", "seed": 2,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_naqsh_e_jahan_square__hall": {"subject": "Naqsh-e Jahan Square in Isfahan: a vast rectangular square lined with two-storey arcades, at one end the great blue-tiled dome and tall turquoise entrance arch of a mosque with minarets, on one side a flat-roofed palace with a wooden columned terrace, a smaller cream and blue tiled dome of a second mosque opposite", "seed": 1,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_buddhas_of_bamiyan__statue": {"subject": "the colossal Buddha of Bamiyan: a giant standing Buddha statue in folded robes carved in a tall arched niche in a sheer tan sandstone cliff, its face worn away, a second smaller standing Buddha in another niche along the cliff, many small cave openings in the cliff, a green valley of poplar trees and fields below, snowy mountains", "seed": 2, "style": STATUE_STYLE,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_musalla_of_herat__tower": {"subject": "the Musalla of Herat: a great complex of tiled madrasas and a mosque with a tall entrance arch, many tall slender minarets covered in blue and turquoise glazed tilework, the ribbed blue dome of a mausoleum, on a dusty plain outside a walled city, mountains beyond", "seed": 1,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_grand_palace_bangkok__hall": {"subject": "the Grand Palace in Bangkok: a walled compound of Thai royal halls and temples with steep layered roofs of orange and green glazed tiles, gilded pointed spires and ornate gables, white crenellated walls, beside a broad river with boats", "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_changdeokgung__hall": {"subject": "Changdeokgung Palace in Seoul: a Korean palace of wooden halls with curved grey tiled roofs, red pillars and colourful painted eaves on stone terraces, a two-storey throne hall facing a stone-paved courtyard, a lotus pond with a pavilion in a wooded garden at the foot of a mountain", "seed": 2,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_bulguksa__pagoda": {"subject": "Bulguksa temple in Korea: a few weathered wooden temple halls with curved tiled roofs on a high stone terrace reached by double stone stairways, two stone pagodas in the courtyard, one plain three-storeyed, one ornate, on a forested mountainside", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_kinkaku_ji__pagoda": {"subject": "Kinkaku-ji in Kyoto: a three-storey pavilion with its upper two storeys covered in weathered gold leaf, under a curved shingled roof topped by a bronze phoenix, at the edge of a still pond with small pine-covered islands and rocks, a garden of maples and pines", "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_todai_ji__hall": {"subject": "Todai-ji in Nara: a colossal wooden temple hall with a huge two-tiered hipped roof of grey tiles with golden horn ornaments on its ridge, in a wide gravel courtyard behind a massive wooden gate, deer grazing in a park of trees", "seed": 0,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_itsukushima_shrine__gate": {"subject": "the great gate of Itsukushima: a giant vermilion wooden shrine gate standing in the sea, its two curved crossbeams topped in black, before a vermilion shrine of long open corridors and halls on piers over the water, a green forested mountain on the island behind", "seed": 0,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_potala_palace__hall": {"subject": "the Potala Palace in Lhasa: a huge fortress palace climbing a rocky hill, tiers of white walls with a dark red central palace block on top, rows of trapezoid windows, gilded roofs on the summit, long zigzag stairways up its face, a valley and bare mountains", "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_swayambhunath__pagoda": {"subject": "Swayambhunath above Kathmandu: a large white dome stupa topped by a gilded square tower painted on each side with a pair of watchful eyes and a gilded tiered spire, small shrines and pagoda-roofed temples around it, strings of prayer flags, on a forested hilltop above the valley", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_leshan_giant_buddha__statue": {"subject": "the Leshan Giant Buddha: a colossal seated Buddha carved into a red sandstone cliff face where three rivers meet, its hands on its knees, ferns and shrubs growing on its shoulders and its head of curls, tiny figures on a stairway cut down the cliff beside it, a temple with curved roofs on the clifftop", "seed": 1, "style": STATUE_STYLE,
                                                "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_temple_of_confucius__hall": {"subject": "the Temple of Confucius at Qufu: a great hall with a double-eaved roof of yellow glazed tiles on carved stone pillars wound with dragons, on a white marble terrace, in a vast walled courtyard of ancient cypress trees, a series of gates and pavilions along a straight axis", "seed": 1,
                                              "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_yungang_grottoes__rock_cut": {"subject": "the Yungang Grottoes: a long sandstone cliff face carved with many cave temples, in the largest an open niche holding a colossal seated Buddha carved from the rock, wooden temple fronts with tiled roofs built against the cliff over some caves, a dry valley of yellow earth", "seed": 1,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_humble_administrators_garden__pagoda": {"subject": "the Humble Administrator's Garden in Suzhou: a classical Chinese garden of winding lotus ponds, zigzag stone bridges, pavilions with upturned tiled roof corners, white walls with round moon gates, rockeries of twisted limestone and willows, a tall pagoda beyond the garden walls", "seed": 1,
                                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_longmen_grottoes__rock_cut": {"subject": "the Longmen Grottoes: limestone cliffs along a river honeycombed with thousands of small caves and niches of carved Buddhas, a great open terrace niche high on the cliff holding a colossal seated Buddha with standing attendant statues on each side, stairways up the cliff", "seed": 1,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_registan__gate": {"subject": "the Registan in Samarkand: a great square framed on three sides by three madrasas, each with a huge arched portal covered in faded blue and turquoise tiles, tall minarets, some of them leaning, and ribbed blue domes, market stalls on the sandy square", "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_itchan_kala__gate": {"subject": "the old walled town of Khiva in Central Asia: tall slender minarets banded with blue and turquoise tiles rising above flat-roofed mud-brick houses, madrasas with tiled arched portals and small turquoise domes, inside thick brown mud-brick walls with rounded bastions and a great gate, green irrigated fields and poplar trees outside the walls", "seed": 0,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mausoleum_of_sultan_sanjar__mausoleum": {"subject": "the Mausoleum of Sultan Sanjar at Merv: a massive cube of brown baked brick topped by a high dome with most of its blue tiles gone, an arcaded gallery round its upper drum, standing alone among the eroded mud-brick walls and mounds of a ruined city on a flat plain", "seed": 2,
                                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_kazan_kremlin__tower": {"subject": "the Kazan Kremlin: white stone fortress walls with round towers on a hill above a river, inside a white cathedral with onion domes and a tall leaning red brick tower of seven tiers with a green spire", "seed": 0,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_saint_sophia_kiev__memorial_church": {"subject": "Saint Sophia's Cathedral in Kiev: a large white Baroque cathedral with many green and gilded pear-shaped domes, the largest gilded in the centre, beside a tall white and blue tiered Baroque bell tower with a gilded dome, inside a monastery wall in a city of trees", "seed": 0,
                                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_diocletians_palace__colonnade": {"subject": "Diocletian's Palace in Split: the massive walls of a Roman palace on the Adriatic waterfront, crowded inside and around with the stone houses and red roofs of an old town, a colonnaded Roman courtyard of granite columns and arches, a tall Romanesque bell tower rising beside an octagonal domed mausoleum", "seed": 2,
                                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_marksburg__tower": {"subject": "the Marksburg: a medieval castle of whitewashed walls and grey slate roofs with a tall square keep, perched on a steep wooded hilltop above the river Rhine, vineyards on the slopes, a small village and boats on the river below", "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_aachen_cathedral__hall": {"subject": "Aachen Cathedral: an octagonal Carolingian chapel with a tall domed roof, joined to a soaring Gothic choir of tall stained glass windows, small chapels around it and a short tower, among the tiled roofs of an old German town", "seed": 0,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_basilica_of_saint_francis__hall": {"subject": "the Basilica of Saint Francis in Assisi: a pale pink and white stone church with a rose window and a square Romanesque bell tower, built on massive arched buttresses over a long arcaded friary, on the slope of a hill town above the green Umbrian plain", "seed": 1,
                                                    "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_walls_of_tallinn__gate": {"subject": "the old town walls of Tallinn: tall round medieval stone towers with steep red conical roofs strung along a long grey limestone town wall, a narrow gate between two towers, red-roofed merchant houses and the tall Gothic spires of churches inside, the Baltic Sea beyond", "seed": 0,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        # To History sites, buried until the game (tourism heritage phase 3): as they stand once dug.
        "landmark_ephesus__colonnade": {"subject": "the excavated Roman city of Ephesus: the two-storey marble facade of a great library with paired columns and statues in niches, at the foot of a marble-paved street lined with broken columns, a huge theatre cut into the hillside, low green hills", "seed": 2,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_tikal__pyramid": {"subject": "Tikal in the Guatemalan jungle: a steep narrow Maya temple pyramid of grey limestone with nine stepped terraces and a steep central stairway, topped by a small temple with a tall carved roof comb, rising above the dense green jungle canopy, a second temple pyramid facing it across a grassy plaza", "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_chichen_itza__pyramid": {"subject": "the great pyramid of Chichen Itza: a square Maya stepped pyramid of nine terraces with a broad stairway up the middle of each of its four sides, carved serpent heads at the foot of the stairs, a square temple on top, on a wide flat grassy plaza, a colonnade of square pillars and a ball court nearby, low scrub forest", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_teotihuacan__pyramid": {"subject": "Teotihuacan: the Pyramid of the Sun, a broad squat pyramid much wider than it is tall, five sloping stepped tiers of rough grey stone rising to a wide flat empty summit, a single broad stairway up its front, beside a long straight avenue lined with low stone platforms leading to a smaller pyramid in the distance, on a dry high plain of grass and cactus ringed by mountains", "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_monte_alban__pyramid": {"subject": "the ruins of Monte Alban: a great long plaza on a levelled mountaintop, lined with stepped stone platforms and terraced temple bases with wide stairways and a ball court, the broad green valley of Oaxaca far below on every side", "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_leptis_magna__forum": {"subject": "the excavated Roman city of Leptis Magna on the Libyan coast: a four-way triumphal arch with carved reliefs, colonnaded streets, a large forum and basilica of grey and pink granite columns, a theatre facing the Mediterranean, sand dunes half covering the outer ruins", "seed": 2,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_cyrene__pantheon": {"subject": "the ruins of Cyrene in Libya: a Doric Greek temple with a few re-erected columns on a terrace beside a sacred spring, a theatre and ruined stone buildings on a green hillside above a plateau, tombs carved into the cliffs, the coastal plain and the sea far below", "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_merida_theatre__forum": {"subject": "the excavated Roman theatre of Merida: a semicircle of stone seating tiers facing a stage with a tall two-storey backdrop of marble columns with statues between them, an oval amphitheatre beside it, olive trees and a Spanish town", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_chogha_zanbil__pyramid": {"subject": "the ziggurat of Chogha Zanbil: a massive square stepped temple tower of brown baked mud brick, its lower stages still standing and its top worn away, inside a square enclosure wall, on a flat plain of tawny dry grass by a river", "seed": 1,
                                           "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_hattusa__gate": {"subject": "the Lion Gate of Hattusa: a gateway in a massive Hittite city wall of huge rough-cut stone blocks, its arched doorway flanked by two large lions carved out of the gateposts, the wall running over the rocky hills of a bare Anatolian plateau, the excavated foundations of temples below", "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mount_nemrut__statue": {"subject": "the summit of Mount Nemrut: a huge cone-shaped mound of loose stone chips on a mountaintop, before it on a stone terrace a row of colossal seated stone figures without heads, and in front of them a row of giant carved stone heads in tall conical caps standing on the ground, bare mountain ranges beyond", "seed": 0, "style": STATUE_STYLE,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_mogao_caves__rock_cut": {"subject": "the Mogao Caves near Dunhuang: a long cliff face of crumbling sandstone honeycombed with hundreds of cave doorways on several levels, linked by wooden walkways and stairs, a tall nine-storey wooden temple facade with red pillars and tiered roofs built against the cliff, poplar trees along a stream, sand dunes beyond", "seed": 0,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_khajuraho__pillar": {"subject": "the temples of Khajuraho: tall sandstone Hindu temples on high platforms, each a cluster of rising curved spires like a mountain range, their walls covered in bands of carved figures, on a green lawn among trees by a lake", "seed": 2,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "landmark_hampi__pillar": {"subject": "the ruins of Hampi: a stone chariot carved as a small shrine with stone wheels in a courtyard before a temple hall of carved granite pillars, a tall tiered temple gateway tower beyond, among a landscape of giant round granite boulders, banana groves and a river", "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        # The trophies' own pictures (2026-10-16): what was carried off, close, in a museum room
        # (TROPHY_STYLE); keys trophy_<landmark>, codes TROPHY_PICTURES in the registry test.
        "trophy_arc_de_triomphe": {"subject": "great sculpted stone relief groups of soldiers rallied by a winged figure with outspread wings, cut from a triumphal arch and set up along the walls of a museum room with a skylight", "style": TROPHY_STYLE, "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_alexander_column": {"subject": "a tall polished red granite column topped by a bronze angel holding a cross, re-erected in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_brandenburg_gate": {"subject": "a bronze chariot drawn by four horses abreast, driven by a winged goddess holding a staff topped with a wreath, on a stone plinth in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_washington_monument_baltimore": {"subject": "a tall white marble column with a small statue of a man in a toga on its top, re-erected in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_la_scala": {"subject": "opera costumes on mannequins, a model of a stage set, bound music scores and a conductor's podium, in glass cases in a museum room with red velvet walls and a gilded theatre box", "style": TROPHY_STYLE, "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_teatro_di_san_carlo": {"subject": "painted stage scenery flats, opera costumes on mannequins, a harpsichord and bound music scores in glass cases, in a museum room with red and gold walls", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_jantar_mantar": {"subject": "large Indian astronomical instruments: a great brass astrolabe on a stand, an armillary sphere and a marble sundial, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_shalimar_gardens": {"subject": "a great glass and iron greenhouse filled with rare plants and fruit trees from a Mughal garden, a marble fountain basin and a carved red sandstone pavilion inside it", "style": TROPHY_STYLE, "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_jardim_botanico": {"subject": "a great glass and iron palm house filled with tall tropical palms, giant water lilies in a pool and tropical flowers", "style": TROPHY_STYLE, "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_stelae_of_aksum": {"subject": "a tall slender grey granite obelisk carved to look like a many-storeyed tower with rows of false windows and a false door at its foot, re-erected in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_liberty_column": {"subject": "a tall slender pink sandstone obelisk with four small white marble statues at its corners, re-erected in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_lion_monument": {"subject": "a dying lion carved in relief with a broken spear in its side and a paw over a shield, on a huge block of sandstone displayed in a museum hall with a skylight", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_temple_of_heaven": {"subject": "Chinese imperial ritual treasures: bronze ritual vessels, jade discs, blue and gold altar furnishings and embroidered yellow silk robes on stands, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_topkapi_palace": {"subject": "the carved white marble crowning of an Ottoman palace gate with gilded arabesque panels and a gilded crest, set up on a plinth on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_golestan_palace": {"subject": "Persian royal treasures: a jewelled throne shaped like a platform, panels of mirror mosaic, jewelled crowns and enamelled gold vessels, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_basilica_of_superga": {"subject": "the marble tombs of kings: carved marble sarcophagi with reclining figures, and crowns and swords on velvet cushions, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        # s0 is retouched: a lettered wall panel (raw in ~/flux_runs/originals/gm_trophy/).
        "trophy_tomb_of_william_the_silent": {"subject": "a marble and black stone tomb canopy over the reclining white effigy of a prince, with bronze statues of virtues at its corners, reassembled in a museum hall with a skylight", "style": TROPHY_STYLE, "seed": 0,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_cenotaph_of_maximilian": {"subject": "a kneeling bronze statue of an emperor on top of a black marble tomb, surrounded by rows of larger-than-life bronze statues of armoured knights and ladies, in a museum hall with a skylight", "style": TROPHY_STYLE, "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_arco_de_santa_maria": {"subject": "a carved stone group of statues of kings, an emperor and a guardian angel taken from a city gate, set up on a plinth on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_statue_of_louis_xiv": {"subject": "a bronze statue of a king on horseback on a tall stone pedestal, re-erected in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_lion_of_saint_mark": {"subject": "a bronze winged lion standing on a fountain pedestal in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_sans_souci_palace": {"subject": "the treasures of a Caribbean king: a gilded throne under a red canopy, a crown and swords on cushions and fine porcelain, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_nikko_toshogu": {"subject": "ornately carved and painted wooden panels from a Japanese shrine gate, white and gold with dragons, peonies and figures, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        # s1 is retouched: a painted signature in a corner (raw in ~/flux_runs/originals/gm_trophy/).
        "trophy_parthenon": {"subject": "long marble frieze slabs carved with a procession of horsemen, and the broken reclining marble statues of a temple pediment on a low plinth, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_obelisks_of_karnak": {"subject": "two tall slender pink granite obelisks side by side, re-erected in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 2,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_royal_palace_of_benin": {"subject": "cast brass plaques of warriors in relief hung on a wall, brass heads of kings and carved ivory tusks on plinths in front of them, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_royal_palace_of_kumasi": {"subject": "Asante gold regalia: gold-hilted state swords, cast gold masks and badges, gold weights and gold-leafed staffs, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                         "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_bukgwan_victory_stele": {"subject": "a tall slender grey stone stele with a carved roof-shaped capstone on a stone base, its face weathered smooth and blank, standing in a quiet walled museum garden", "style": TROPHY_STYLE, "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_imperial_city_of_hue": {"subject": "the treasures of Vietnamese emperors: a gold and red lacquer throne, gold and silver seals, enamelled bronze vessels, jade objects and embroidered yellow silk dragon robes on stands, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_persepolis": {"subject": "carved grey limestone relief slabs of rows of Persian guards and tribute bearers in profile carrying gifts up a stair, and a carved stone column capital of two bull heads back to back, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_red_fort": {"subject": "Mughal regalia: a jewelled gold throne under a canopy, white jade wine cups, jewelled daggers and swords and a jewelled turban ornament, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_rosetta_stone": {"subject": "a dark grey granite slab with a jagged broken top edge, its polished face covered in rows of tiny carved signs, standing on a plinth on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_temple_of_dendera": {"subject": "a round carved stone ceiling relief of an ancient Egyptian zodiac, a disc of stars, animals and figures held up by kneeling goddesses, mounted on a low dais on display in a dim museum room with pale walls", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_luxor_obelisk": {"subject": "a tall pink granite obelisk standing on a granite plinth in the glass-roofed courtyard of a museum, galleries with columns around it", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_venus_de_milo": {"subject": "an armless white marble statue of a goddess, bare to the hips with drapery round her legs, on a pedestal on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_piraeus_lion": {"subject": "a colossal white marble lion seated upright on its haunches on a plinth in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 0,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_horses_of_saint_mark": {"subject": "four gilded bronze horses striding side by side on a long plinth on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tipus_tiger": {"subject": "a life-size painted wooden tiger mauling a man in a red coat lying on his back, in a glass case on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_baba_merzoug": {"subject": "a very long bronze cannon on a stone pedestal in the glass-roofed courtyard of a museum", "style": TROPHY_STYLE, "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_great_zimbabwe": {"subject": "tall carved green soapstone birds perched on top of carved soapstone columns, a row of them on plinths on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_royal_palaces_of_abomey": {"subject": "three tall carved wooden royal statues, half man and half beast, a lion-man, a shark-man and a bird-man, beside carved wooden thrones, on plinths on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_klungkung_palace": {"subject": "Balinese royal regalia: a kris dagger with a jewelled gold hilt, gold betel boxes, gold ornaments and a gilded carved wooden throne, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_royal_palace_of_kandy": {"subject": "a throne of gilded wood covered in gold sheet and set with rock crystals and gems, its tall back carved with a sun and lions, a matching footstool, on a dais on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_uffizi_gallery": {"subject": "a white marble statue of a nude goddess shyly covering herself with her hands, on a round pedestal, on display in a museum room with pale walls and a skylight, paintings in gold frames on the walls", "style": TROPHY_STYLE, "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_capitoline_museums": {"subject": "a marble statue of a dying warrior slumped on his shield with his head bowed and a torc around his neck, on a pedestal, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_bodrum_castle": {"subject": "long carved marble frieze slabs of Greeks fighting Amazons and colossal broken marble statues of a man, a woman and a horse from an ancient tomb, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_temples_of_baalbek": {"subject": "richly carved stone blocks from a Roman temple, a huge cornice with lion heads, a ceiling slab carved with gods in hexagonal frames and a fluted column capital, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_palmyra": {"subject": "rows of carved limestone funerary busts of men and women in rich jewellery and headdresses, set in niches along the walls on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_xanthos": {"subject": "the facade of a small Ionic temple-tomb rebuilt inside a museum hall with a skylight, marble statues of women in wind-blown robes standing between its columns on a high base carved with a battle frieze", "style": TROPHY_STYLE, "seed": 0,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mesha_stele": {"subject": "a black basalt stele with a rounded top, pieced back together from broken fragments, its face finely incised with rows of small carved signs, in a glass case on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_arch_of_ctesiphon": {"subject": "Persian royal treasures: silver-gilt plates showing kings hunting on horseback, a cup of rock crystal and gold, gold coins and a jewelled crown, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_nineveh_library": {"subject": "huge grey stone relief panels carved with a royal lion hunt lining the walls of a museum room with a skylight, a pair of colossal stone winged bulls with bearded human heads guarding its doorway, glass cases of clay tablets", "style": TROPHY_STYLE, "seed": 0,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_winged_victory_of_samothrace": {"subject": "a white marble winged goddess with no head and great outspread wings, her wind-blown robes clinging to her body, on a grey stone base carved as the prow of a warship, at the top of a museum staircase under a skylight", "style": TROPHY_STYLE, "seed": 1,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_vindolanda_tablets": {"subject": "thin wooden leaf tablets covered in faded ink handwriting, laid out in flat glass cases with Roman leather shoes and tools, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_troy_hisarlik": {"subject": "an ancient gold treasure: a golden diadem of hanging chains of tiny gold leaves, gold cups, bracelets and earrings and silver vessels, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mycenae_grave_circle": {"subject": "a flat hammered sheet-gold funeral mask of a bearded man's face with closed eyes and a curled moustache, no headdress, on a dark stand in a glass case, with gold cups and bronze daggers inlaid with gold, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_pergamon_altar": {"subject": "the west front of a great marble altar rebuilt inside a museum hall with a skylight: a broad flight of marble steps rising between two wings to an Ionic colonnade, its base wrapped in a carved frieze of gods fighting giants", "style": TROPHY_STYLE, "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_deir_el_bahari_cache": {"subject": "painted wooden coffins of Egyptian pharaohs shaped like the dead and wrapped mummies, laid in a row of glass cases on display in a dim museum room with pale walls", "style": TROPHY_STYLE, "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_ishtar_gate_babylon": {"subject": "a towering flat-topped gateway of deep blue glazed brick between two square crenellated towers, decorated with rows of yellow bulls and white dragons in relief, an arched passage through it, rebuilt inside a museum hall with a skylight, a processional way of blue walls with striding lions leading to it", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_palace_of_knossos": {"subject": "fragments of colourful wall frescoes of a charging bull with acrobats leaping over it, of dolphins and of blue birds, mounted on the walls of a museum room with a skylight, tall Minoan clay jars in front", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_antikythera_mechanism": {"subject": "corroded green bronze fragments of an ancient geared mechanism in a glass case, beside it a gleaming bronze reconstruction of the complete box of interlocking gear wheels, bronze statues from a shipwreck around them on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_oseberg_ship": {"subject": "a long slender dark oak Viking ship with a tall spiralling carved prow, displayed in a white vaulted museum hall, carved wooden sledges and a cart beside it", "style": TROPHY_STYLE, "seed": 2,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_machu_picchu": {"subject": "Inca finds: bronze tools and knives, painted clay jars with pointed bases and small silver figurines, in rows of glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_bust_of_nefertiti": {"subject": "a painted limestone bust of an Egyptian queen with a tall flat-topped blue crown, alone in a glass case in a dim domed museum room", "style": TROPHY_STYLE, "seed": 2,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mohenjo_daro": {"subject": "a small stone bust of a bearded man in a robe patterned with trefoils, a bronze figurine of a dancing girl and rows of small square stone seals carved with bulls, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tomb_of_tutankhamun": {"subject": "a gold funeral mask of a pharaoh with a blue-striped headdress inlaid with lapis lazuli, in a glass case on display in a dim museum room, gilded wooden shrines and a golden coffin behind it", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_royal_cemetery_at_ur": {"subject": "a wooden box panel inlaid with shell and blue lapis lazuli mosaic of rows of soldiers, chariots and a banquet, beside a golden goat rearing up against a flowering tree, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_sanxingdui_pits": {"subject": "huge green bronze masks with protruding cylindrical eyes and great flared ears, a tall bronze standing figure and a bronze tree with birds on its branches, displayed on display in a dim museum room", "style": TROPHY_STYLE, "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_sutton_hoo": {"subject": "an Anglo-Saxon iron and bronze helmet with a face mask, a gold belt buckle, gold and garnet shoulder clasps and a great silver dish, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_lascaux_caves": {"subject": "slabs of cave wall cut out of a painted cave, their pale rock painted in red and black with bulls, horses and stags, displayed on display in a dim museum room", "style": TROPHY_STYLE, "seed": 2,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_nag_hammadi_library": {"subject": "leather-bound papyrus books with worn covers and fragile brown pages, laid open in flat glass cases beside a tall red clay jar, on display in a dim museum room", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_dead_sea_scrolls": {"subject": "rolled and unrolled parchment scrolls and tall cylindrical clay jars with lids, in glass cases in a dim round museum room under a white dome", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tomb_of_pakal": {"subject": "a burial mask of green jade mosaic with eyes of white shell and black obsidian, jade bead necklaces and ear spools, in a glass case on display in a dim museum room", "style": TROPHY_STYLE, "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mawangdui_tombs": {"subject": "a long T-shaped painted silk banner of heaven, earth and the underworld hanging in a glass case, beside lacquered red and black dishes and a nested lacquered coffin, on display in a dim museum room", "style": TROPHY_STYLE, "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_terracotta_army": {"subject": "three life-size grey clay warriors of the Chinese emperor's army with topknots and armour of small plates, a kneeling archer, a standing general with a long robe and a clay horse, on low plinths on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tomb_of_philip_ii": {"subject": "a small gold casket with a sixteen-rayed star on its lid and a golden wreath of oak leaves, in a glass case on display in a dim museum room, bronze armour beside it", "style": TROPHY_STYLE, "seed": 0,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tomb_of_marquis_yi": {"subject": "a long two-tier lacquered wooden frame hung with rows of bronze bells of graded size, held up by bronze figures of swordsmen, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_royal_tombs_of_sipan": {"subject": "the gold regalia of a Moche lord of ancient Peru laid out flat in a long glass case: a great crescent-shaped gold headdress ornament, a gold nose ornament, large round gold and turquoise ear discs, necklaces of big gold and silver peanut-shaped beads and a gold sceptre, on display in a dim museum room", "style": TROPHY_STYLE, "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_otzi_the_iceman": {"subject": "a museum room with a small refrigerated glass chamber holding a mummified prehistoric man, beside it in glass cases his copper axe, a longbow, a quiver of arrows, a grass cape and a fur cap", "style": TROPHY_STYLE, "seed": 1,
                                  "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_caral_supe": {"subject": "ancient Peruvian finds: unbaked clay figurines, knotted cord records, bone flutes and woven baskets, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_gobekli_tepe": {"subject": "two huge T-shaped limestone pillars carved in relief with foxes, boars and vultures, standing in a museum hall with a skylight", "style": TROPHY_STYLE, "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_olympia": {"subject": "a white marble statue of a young god holding a baby on his arm, leaning on a tree trunk draped with a cloak, on a pedestal on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_delphi": {"subject": "a life-size bronze statue of a charioteer standing upright in a long pleated robe, holding the reins, on a pedestal on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                         "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_sidon_necropolis": {"subject": "white marble sarcophagi carved with battle and hunting scenes and with lids shaped like temple roofs, a row of them on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_villa_of_the_papyri": {"subject": "bronze statues of runners, deer and philosophers from a Roman villa, and blackened rolled papyrus scrolls in glass cases, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tomb_of_alexander": {"subject": "a golden sarcophagus, a golden wreath of oak leaves and an alabaster funeral bier from the tomb of a Macedonian king, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_pompeii": {"subject": "a huge ancient Roman floor mosaic of a battle made of tiny stone tiles in ochre, brown, black and white, horsemen with long spears charging a king who turns back in his chariot among rearing horses, the mosaic set upright in a heavy frame against the wall, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_walhalla": {"subject": "rows of white marble portrait busts of famous men and women on tall pedestals, and a carved marble pediment group of standing figures, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_bunker_hill_monument": {"subject": "a white marble statue of a general in a long coat on a pedestal, beside glass cases of old flintlock muskets, powder horns, a tricorne hat and a small model of a tall granite obelisk, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_obelisk_of_the_second_of_may": {"subject": "a carved stone funeral urn on a tall pedestal, flanked by four allegorical stone statues of seated women, and laurel wreaths of gilded bronze, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_muhammad_ali_mosque": {"subject": "an ornate gilded wooden pulpit with a tall pointed canopy at the top of its staircase, rings of hanging glass mosque lamps and carved pale alabaster wall panels, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_nelsons_column": {"subject": "a stone statue of an admiral with one empty sleeve pinned across his coat, standing beside a coiled rope, and a large bronze relief panel of a dying admiral on a ship's deck among sailors, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_washington_monument": {"subject": "the small polished aluminium pyramid that capped a great obelisk, on a velvet plinth, beside carved marble and granite memorial blocks with relief carvings of eagles and shields, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_pyramids_of_giza": {"subject": "a dark basalt stone sarcophagus carved like a palace facade with panelled niches, smooth white limestone casing blocks, and grey stone statues of a pharaoh standing between two goddesses, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_petra": {"subject": "a carved rose-red sandstone column capital and frieze blocks from a temple facade cut in a cliff, a carved stone eagle, and thin painted Nabataean bowls patterned with leaves, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_moscow_kremlin": {"subject": "the treasures of the tsars: a gold filigree crown trimmed with dark sable fur and topped with a cross, an ivory throne, jewelled gold icons and gilded silver plate, and a great gilded cross taken from a bell tower, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_fasil_ghebbi": {"subject": "Ethiopian royal treasures: a gold filigree crown with hanging pendants, parchment books painted with bright saints, silver and brass processional crosses and painted wooden church panels, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_valley_of_the_temples": {"subject": "a colossal carved stone giant, a bearded male figure standing with his arms bent up behind his head as if holding up a roof, rebuilt from blocks, beside black and red painted Greek vases, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_borobudur": {"subject": "rows of carved grey stone Buddha heads with tightly curled hair, seated stone Buddha statues and carved relief panels of court scenes and ships, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_old_city_of_sanaa": {"subject": "half-moon windows of carved white gypsum tracery set with coloured glass, curved silver daggers in ornate sheaths, and small ancient alabaster heads with inlaid eyes, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_shibam": {"subject": "tall carved wooden house doors with heavy wooden locks, carved wooden window shutters, silver jewellery and painted clay water jars, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                         "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_amphitheatre_of_el_djem": {"subject": "ancient Roman floor mosaics of lions and leopards hunting antelope and of men fighting wild beasts in an arena, set upright in frames against the walls, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_abu_simbel": {"subject": "a colossal carved sandstone head of a pharaoh in a striped headdress and tall crown, broken from a seated statue, and painted carved statues of a queen and gods, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_temple_of_seti_abydos": {"subject": "finely carved painted limestone relief slabs from a temple wall, a pharaoh in a tall crown offering incense to a seated falcon-headed god, the figures in bright red, blue and yellow, and a carved stone statue of a kneeling king holding an altar, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_pyramids_of_meroe": {"subject": "the gold treasure of a Nubian queen: gold armlets with coloured enamel inlays, gold shield-shaped rings, signet rings and necklaces of gold and glass beads, in glass cases on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_windsor_castle": {"subject": "suits of engraved plate armour on stands, a great silver-gilt banqueting service on a long table, gilt-framed royal portraits and carved oak panelling, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_pont_du_gard": {"subject": "a whole arch of golden limestone blocks taken from a Roman aqueduct bridge and re-erected in a museum hall with a skylight, with Roman lead water pipes and bronze taps in glass cases", "style": TROPHY_STYLE, "seed": 2,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_palais_des_papes": {"subject": "fragments of medieval frescoes cut from palace walls, painted with prophets on a deep blue ground and with hunting and fishing scenes in green forests, framed on the walls, beside a carved papal throne and gold chalices, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mont_saint_michel": {"subject": "a gilded statue of the archangel Michael slaying a dragon, gold and enamel reliquaries, and medieval books open on stands with brightly painted pages, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_chateau_de_chambord": {"subject": "Renaissance tapestries of royal stag hunts, a gilded royal bed under a canopy, carved oak chests and suits of armour, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_jeronimos_monastery": {"subject": "a gold monstrance of delicate Gothic tracery with tiny enamelled kneeling figures, and white marble royal tombs resting on the backs of carved stone elephants, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_alhambra": {"subject": "a tall golden lustre-glazed Moorish vase with winged handles, panels of delicately carved white plasterwork arches, and panels of coloured geometric tiles, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mezquita_of_cordoba": {"subject": "carved ivory caskets with domed lids covered in vines and figures, carved marble column capitals, and a red and white striped horseshoe arch re-erected on two columns, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_shore_temple": {"subject": "South Indian bronze statues of a four-armed god dancing in a ring of fire and of seated goddesses, and a carved granite reclining bull, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_charminar": {"subject": "Deccan royal treasures: black metal vessels inlaid with silver flowers, jewelled daggers, a large faceted diamond on a velvet cushion and painted miniatures of sultans, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_gwalior_fort": {"subject": "panels of glazed tiles in blue, green and yellow with ducks, elephants and banana trees, and carved sandstone temple sculptures of gods and dancers, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_meteora": {"subject": "painted Byzantine icons of saints on gold grounds, a carved gilded wooden altar screen, hanging silver lamps and silver censers, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_citadel_of_aleppo": {"subject": "iron-studded carved wooden gate doors, brass basins inlaid with silver, enamelled glass mosque lamps and a carved stone lintel with two lions, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_naqsh_e_jahan_square": {"subject": "panels of blue and turquoise Persian tilework with flowers and arabesques, great silk carpets of medallions and flowers hung on the walls, and enamelled vessels, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_buddhas_of_bamiyan": {"subject": "fragments of wall paintings of seated Buddhas in blue and ochre halos cut from cave walls, and grey stone and stucco Buddha heads with wavy hair, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_musalla_of_herat": {"subject": "a tall broken drum of a minaret standing upright, covered in tile mosaic of deep blue, turquoise and white stars and flowers, beside large framed panels of the same tile mosaic and a marble tomb chest carved with leaves and flowers, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_grand_palace_bangkok": {"subject": "a small green jade Buddha seated high on a tall tiered gilded altar, with gilded umbrellas, mother-of-pearl inlaid doors and gilded lacquer cabinets, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                       "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_changdeokgung": {"subject": "a royal folding screen painted with a red sun, a white moon and five blue mountain peaks above waves and pine trees, set behind a red lacquered throne, with pale green celadon vases, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_bulguksa": {"subject": "weathered stone lion statues taken from the corners of a pagoda's stairs, and seated gilt-bronze Buddha statues, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_kinkaku_ji": {"subject": "a gilded bronze phoenix taken from a temple roof, on a stand, a gilded wooden seated Buddha statue, black and gold lacquer boxes and tea bowls, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_todai_ji": {"subject": "the treasures of an imperial temple storehouse: a five-stringed lute inlaid with mother-of-pearl, lacquered boxes, pale blue glass bowls and painted folding screens of ladies under trees, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_itsukushima_shrine": {"subject": "suits of ancient Japanese armour of laced red and gold plates on stands, carved painted wooden dance masks, a vermilion lacquered lantern and gilded lacquer boxes, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_potala_palace": {"subject": "gilded bronze statues of Buddhas and many-armed deities, bright painted silk scroll paintings hung on the walls and a gold reliquary stupa set with turquoise, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_swayambhunath": {"subject": "a huge gilded copper thunderbolt sceptre on a drum-shaped base, gilded copper statues of Buddhas and goddesses set with stones, and prayer wheels, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_leshan_giant_buddha": {"subject": "red sandstone Buddha statues and heads cut from cliff niches, gilded bronze temple bells and bronze incense burners, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_temple_of_confucius": {"subject": "a wooden frame of hanging bronze bells and a frame of L-shaped stone chimes for ritual music, bronze ritual vessels and embroidered silk robes on stands, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                      "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_yungang_grottoes": {"subject": "carved sandstone Buddha heads with calm smiling faces, and relief panels of musicians and flying figures cut from cave walls, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_humble_administrators_garden": {"subject": "a tall twisted grey limestone garden rock on a carved stand, dark rosewood scholar's furniture, a painted silk scroll of a garden, porcelain vases and potted dwarf trees, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_longmen_grottoes": {"subject": "large carved limestone relief panels of an emperor and an empress in procession with their courtiers, cut from a cave wall, and carved stone Buddha heads, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_registan": {"subject": "glazed tile panels from a madrasa portal showing a striped tiger chasing a deer under a rising sun with a human face, and panels of blue and turquoise tile mosaic, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                           "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_itchan_kala": {"subject": "the silver-covered throne of a Central Asian khan, tall slender carved wooden columns on bulb-shaped bases, and carved wooden doors, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mausoleum_of_sultan_sanjar": {"subject": "glazed tile fragments, carved stucco panels, bronze ewers and incense burners shaped like lions and birds, and a carved marble cenotaph, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                                             "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_kazan_kremlin": {"subject": "the gold crown of a Tatar khan, a domed cap of gold filigree set with turquoises and rubies, with curved Tatar swords and silver-mounted saddles, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_saint_sophia_kiev": {"subject": "Byzantine gold mosaics of a standing Virgin with raised arms on a glittering gold ground, fresco fragments of saints, and a carved stone sarcophagus of a prince, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                    "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_diocletians_palace": {"subject": "a black granite Egyptian sphinx, carved Roman column capitals and relief friezes, and a carved stone sarcophagus, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                     "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_marksburg": {"subject": "suits of medieval armour, crossbows, swords and halberds on racks, and a carved oak chest, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_aachen_cathedral": {"subject": "a gold reliquary bust of a crowned bearded emperor, a jewelled gold processional cross, and a plain white marble throne on steps, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_basilica_of_saint_francis": {"subject": "fresco fragments of a saint in a brown robe preaching to birds, gilded panel paintings and gold reliquaries, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                            "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_walls_of_tallinn": {"subject": "a long medieval painted panel of skeletons dancing with a pope, an emperor and a king, and carved gilded altarpieces, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 2,
                                   "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_ephesus": {"subject": "a carved marble column drum with life-size figures from a great temple, a bronze statue of an athlete, and long marble relief friezes of battles, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_tikal": {"subject": "carved dark wooden lintel beams covered in reliefs of a Maya lord on a throne beneath a great serpent, jade masks and painted Maya vases, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                        "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_chichen_itza": {"subject": "a reclining stone figure holding a dish on its belly, gold discs embossed with warriors, and jade beads and ornaments dredged from a sacred well, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_teotihuacan": {"subject": "greenstone masks with inlaid shell eyes, a carved stone feathered serpent head, and painted wall fragments of red and green figures, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_monte_alban": {"subject": "the treasure of a Mixtec tomb: gold pendants and necklaces of tiny gold bells, carved jaguar bones, rock crystal goblets and turquoise mosaic, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_leptis_magna": {"subject": "tall granite and marble columns, carved capitals and pieces of entablature from a Roman city, re-erected as a ruined colonnade inside a museum hall with a skylight, with marble statues of emperors", "style": TROPHY_STYLE, "seed": 0,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_cyrene": {"subject": "a white marble statue of the god Apollo with a lyre and a python coiled round a tree stump, and marble heads and statues of goddesses, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                         "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_merida_theatre": {"subject": "white marble statues of Roman goddesses and robed emperors from a theatre's stage wall, carved column capitals and Roman floor mosaics, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                 "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_chogha_zanbil": {"subject": "glazed bricks incised with wedge-shaped signs, a glazed clay bull statue, glazed clay wall knobs and small bronze figurines, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                                "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_hattusa": {"subject": "a carved stone sphinx with a broad human face, a lion's body and a rounded cap, taken from a city gate, beside bronze standards topped with stags and bulls and painted clay jugs with long beak spouts, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                          "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mount_nemrut": {"subject": "a colossal carved stone head of a bearded god in a tall conical cap set on the floor, beside a colossal carved stone eagle's head and a colossal carved lion's head, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 0,
                               "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_mogao_caves": {"subject": "rolled and open paper scrolls of an ancient library, a printed scroll with a picture of a Buddha preaching, and silk banner paintings of Buddhas and bodhisattvas, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                              "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_khajuraho": {"subject": "carved sandstone figures of graceful celestial dancers and of a woman looking into a mirror, and carved sandstone temple wall panels, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                            "now": f"{_BI}/building_grand_monument.dds"},
        "trophy_hampi": {"subject": "carved granite pillars with rearing horses and lion-like beasts, a carved stone wheel from a temple chariot, and bronze statues of a god and his two consorts, on display in a museum room with pale walls and a skylight", "style": TROPHY_STYLE, "seed": 1,
                        "now": f"{_BI}/building_grand_monument.dds"},
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
