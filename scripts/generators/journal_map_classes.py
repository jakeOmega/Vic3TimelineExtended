"""The Map Room's class maps, one row per pop type (owner, 2026-11-23, #1975; docs/systems/mod_systems/journal_map_modes.md,
The Class Maps).

Every pop type has two maps, identical but for the class: its people, a doubling at a time (the count, the default),
and its share of the state's people (the share). Map Options' Count/Share switch decides which of a class's two the
class's button picks (te_jmap_class_mode, te_journal_map_values.txt). Three generators read this table, so a class
is one row here:

- gen_journal_map_classes.py: the family's paint, hover and "no data" branches (spliced into te_journal_maps.txt), its
  colors, its loc, the yearly walk's counts and the share values;
- gen_journal_map_scales.py: each map's curve row (the count's doubling scale, the share's fitted curve);
- gen_journal_map_picks.py: each class's two picks, in the Classes group's rows.

A row: `pop`, the pop type (is_pop_type); `name`, its plural as vanilla names it; `count_sel` and `share_sel`, the two
selectors (te_journal_map_values.txt; 41-44 were the share maps of the tenth pass, kept so a save holding one shows
it); `about`, what draws the class, for the pick's tooltip (no word of a curve or a color: PickTooltipTest); `count`,
the count's default range before the first measure (lo, hi: hi is lo times a power of two); `share`, the share's
fitted shape, ("linear", hi) straight from 0 to hi or ("knee", soft) half the color by a fifth of the range, to five
times soft, with `share_min` its narrowest range; `hue` and `high`, the colors (hsv360): each class in the hue of its
pop type's own color in vanilla's pop charts (common/pop_types), from pale at the low end to `high`; `words`, the two
colors as the tooltip names them; `walk`, the order the walk asks for it (most pops first, so the ladder stops early).
"""
import math

# The Count/Share switch's settings (te_jmap_class_mode, te_journal_map_values.txt; unset is the count).
MODE_COUNT, MODE_SHARE = 0, 1
# The count's doubling scale: the high at least this many times the low, and the low at least FLOOR people.
COUNT_MIN_RATIO = 4
COUNT_FLOOR = 10
# A class's low color: its hue, nearly white (the share's low end, and the count's fewest).
LOW_SAT, LOW_VAL = 10, 94

CLASSES = [
    # Property: land, industry and trade.
    dict(pop="aristocrats", name="Aristocrats", count_sel=48, share_sel=42,
         about="Landed estates and serfdom keep them many; land reform and industry thin them.",
         count=(250, 32000), share=("linear", 0.04), share_min=0.005,
         hue=216, high=(216, 72, 46), words=("pale blue", "deep blue"), walk=10),
    dict(pop="capitalists", name="Capitalists", count_sel=49, share_sel=41,
         about="They gather where industry and finance do, so a few great cities hold most of them.",
         count=(50, 6400), share=("knee", 0.002), share_min=0.002,
         hue=187, high=(187, 80, 42), words=("pale aqua", "teal"), walk=15),
    dict(pop="shopkeepers", name="Shopkeepers", count_sel=50, share_sel=63,
         about="Towns and trade keep them, selling what the farms and the factories make.",
         count=(250, 32000), share=("linear", 0.04), share_min=0.005,
         hue=148, high=(148, 72, 40), words=("pale mint", "emerald"), walk=7),
    # Learning, faith and the state.
    dict(pop="academics", name="Academics", count_sel=51, share_sel=44,
         about="Universities and a literate, urban people draw them.",
         count=(25, 6400), share=("knee", 0.002), share_min=0.002,
         hue=338, high=(338, 70, 45), words=("pale pink", "wine"), walk=14),
    dict(pop="clergymen", name="Clergymen", count_sel=52, share_sel=43,
         about="A state church and devout people keep them many.",
         count=(250, 32000), share=("linear", 0.04), share_min=0.005,
         hue=47, high=(44, 90, 62), words=("cream", "gold"), walk=9),
    dict(pop="bureaucrats", name="Bureaucrats", count_sel=53, share_sel=64,
         about="Government administration employs them, so capitals and well-run states hold the most.",
         count=(100, 25600), share=("linear", 0.02), share_min=0.003,
         hue=90, high=(90, 66, 40), words=("pale sage", "olive"), walk=11),
    # Industry.
    dict(pop="engineers", name="Engineers", count_sel=54, share_sel=65,
         about="Modern industry and its research employ them, so they follow the factories.",
         count=(25, 6400), share=("knee", 0.006), share_min=0.002,
         hue=25, high=(24, 85, 64), words=("pale peach", "burnt orange"), walk=13),
    dict(pop="machinists", name="Machinists", count_sel=55, share_sel=66,
         about="Factories and mechanized industry employ them, more as the machines spread.",
         count=(250, 64000), share=("knee", 0.04), share_min=0.01,
         hue=331, high=(326, 72, 52), words=("pale pink", "raspberry"), walk=5),
    dict(pop="laborers", name="Laborers", count_sel=56, share_sel=67,
         about="Mines, plantations, ports and the first factories employ them; machines and better methods thin "
               "them.",
         count=(2000, 512000), share=("linear", 0.5), share_min=0.05,
         hue=7, high=(6, 72, 44), words=("pale rose", "brick red"), walk=2),
    # The land.
    dict(pop="farmers", name="Farmers", count_sel=57, share_sel=68,
         about="Commercial farms and ranches keep them, where the land feeds a market rather than a household.",
         count=(2000, 512000), share=("linear", 0.4), share_min=0.05,
         hue=194, high=(196, 82, 52), words=("pale sky blue", "deep cerulean"), walk=3),
    dict(pop="peasants", name="Peasants", count_sel=58, share_sel=69,
         about="Subsistence farming keeps them, outside the market economy; work elsewhere draws them off the land.",
         count=(8000, 2048000), share=("linear", 1), share_min=0.1,
         hue=209, high=(207, 58, 42), words=("pale blue", "steel blue"), walk=1),
    dict(pop="slaves", name="Slaves", count_sel=59, share_sel=70,
         about="Only where the law allows slavery: plantations, mines and households hold them.",
         count=(500, 256000), share=("linear", 0.5), share_min=0.05,
         hue=40, high=(32, 45, 34), words=("pale sand", "umber"), walk=4),
    # Offices and the army.
    dict(pop="clerks", name="Clerks", count_sel=60, share_sel=71,
         about="Offices, shops, railways and services employ them, more as an economy grows.",
         count=(100, 25600), share=("linear", 0.1), share_min=0.01,
         hue=101, high=(104, 66, 38), words=("pale green", "forest green"), walk=6),
    dict(pop="officers", name="Officers", count_sel=61, share_sel=72,
         about="Barracks and naval bases employ them to lead the soldiers.",
         count=(25, 3200), share=("linear", 0.005), share_min=0.002,
         hue=43, high=(40, 72, 36), words=("pale straw", "bronze"), walk=12),
    dict(pop="soldiers", name="Soldiers", count_sel=62, share_sel=73,
         about="Barracks and naval bases employ them; Armed Forces counts them with their Officers.",
         count=(500, 64000), share=("linear", 0.04), share_min=0.005,
         hue=288, high=(286, 48, 40), words=("pale lilac", "plum"), walk=8),
]

# The class maps' rows in the Classes group (gen_journal_map_picks.py), three to a row, by theme as the table runs:
# property, learning and the state, industry, the land, offices and the army.
ROWS = [[c["pop"] for c in CLASSES[i:i + 3]] for i in range(0, len(CLASSES), 3)]

# The state variables the tenth pass's four share maps read, until #1975 renamed every class's te_dg_cls_<pop>
# (te_dg_soldiers already meant Soldiers and Officers): the walk removes them from a save that still holds them.
RETIRED_VARS = ("te_dg_capitalists", "te_dg_aristocrats", "te_dg_clergy", "te_dg_academics")


def count_var(c):
    """The walk's count of the class's people (state scope)."""
    return f"te_dg_cls_{c['pop']}"


def share_value(c):
    """The class's people over the state's, 0-1 (te_journal_map_classes_generated.txt)."""
    return f"te_jmap_share_{c['pop']}"


def count_scale(c):
    """The count map's name in gen_journal_map_scales.py's table: te_jmap_<it>_factor, _lo, _hi."""
    return f"class_{c['pop']}"


def share_scale(c):
    return f"class_{c['pop']}_share"


def count_key(c):
    """The count map's key in gen_journal_map_picks.py's MAPS: its pick is te_jmap_pick_<it>."""
    return f"class_{c['pop']}_count"


def share_key(c):
    return f"class_{c['pop']}_share"


def slot(c):
    """The class's place in a row of the Classes group: its two picks, one shown at a time by the switch."""
    return f"class_{c['pop']}"


def selectors():
    return sorted(s for c in CLASSES for s in (c["count_sel"], c["share_sel"]))


def validate():
    pops = [c["pop"] for c in CLASSES]
    walks = sorted(c["walk"] for c in CLASSES)
    if (len(set(pops)) != len(pops) or len(set(selectors())) != 2 * len(CLASSES)
            or walks != list(range(1, len(CLASSES) + 1))):
        raise ValueError("a pop type, a selector or a walk place is listed twice")
    for c in CLASSES:
        lo, hi = c["count"]
        ratio = hi / lo
        if lo < COUNT_FLOOR or ratio < COUNT_MIN_RATIO or not math.log2(ratio).is_integer():
            raise ValueError(f"{c['pop']}: a count's default range runs a whole number of doublings, at least two")
        if c["share"][0] not in ("linear", "knee"):
            raise ValueError(f"{c['pop']}: unknown share shape {c['share'][0]}")
