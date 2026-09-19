# Victoria 3 GUI Modding Guide

Comprehensive reference for creating and modifying GUI elements in Victoria 3 mods.

## Table of Contents

1. [Overview](#overview)
2. [File Structure](#file-structure)
3. [Widget Types](#widget-types)
4. [Layout System](#layout-system)
5. [Styling & Appearance](#styling--appearance)
6. [Data Binding Expressions](#data-binding-expressions)
7. [Types & Templates](#types--templates)
8. [Blocks & Blockoverrides](#blocks--blockoverrides)
9. [Data Models & Item Repeaters](#data-models--item-repeaters)
10. [State Animations](#state-animations)
11. [Interactive Elements](#interactive-elements)
12. [Scripted GUIs](#scripted-guis)
13. [Creating Standalone Panels](#creating-standalone-panels)
14. [Modifying Existing Panels](#modifying-existing-panels)
15. [Tooltips](#tooltips)
16. [Text Icons](#text-icons)
17. [Global Accessors & Functions](#global-accessors--functions)
18. [Format Specifiers](#format-specifiers)
19. [GetVariableSystem (UI State)](#getvariablesystem-ui-state)
20. [GetDefine (Engine Constants)](#getdefine-engine-constants)
21. [MakeScope & Variable Access](#makescope--variable-access)
22. [Mod Compatibility](#mod-compatibility)
23. [Common Gotchas](#common-gotchas)
24. [Patterns from Workshop Mods](#patterns-from-workshop-mods)
25. [This Mod's GUI Files](#this-mods-gui-files)

---

## Overview

Victoria 3 uses the **Jomini** GUI framework (Clausewitz engine family). GUI is defined in `.gui` files using a declarative widget hierarchy with data binding expressions that connect to the game's data model.

**Key concepts:**
- **Widgets** — UI elements (buttons, text, icons, containers, etc.)
- **Types** — Custom widget class definitions (reusable, parameterized via blocks)
- **Templates** — Mixin-style property bundles applied via `using`
- **Blocks/Blockoverrides** — Extension points for customization without full replacement
- **Data Binding** — `"[Expression]"` syntax connecting GUI to game data
- **Scripted GUIs** — Bridge between GUI clicks and game script effects
- **Scripted Widgets** — Standalone panels registered for auto-creation at startup

**All `.gui` files must be saved in UTF-8 BOM encoding.**

---

## File Structure

### Vanilla GUI Layout (`game/gui/`)
```
gui/
├── shared/                    # Base types, templates, reusable components
│   ├── defaults.gui           # default_popup, default_block_window, etc.
│   ├── buttons.gui            # Button types
│   ├── backgrounds.gui        # Background textures/types
│   ├── animations.gui         # Shared animations
│   ├── character.gui          # Character display types
│   ├── dividers.gui           # Separator lines
│   ├── dropdown.gui           # Dropdown widgets
│   ├── flags.gui              # Country flag widgets
│   ├── layout.gui             # Layout helper types
│   ├── progressbars.gui       # Progress bar types
│   ├── selections.gui         # Selection indicators
│   ├── sounds.gui             # UI sounds
│   ├── special_buttons.gui    # Complex button types
│   ├── tab_bars.gui           # Tab bar types
│   └── textures.gui           # Texture constants
├── jomini/                    # Engine-level shared (save/load, settings)
├── scripted_widgets/          # .txt files registering standalone widgets
│   └── scripted_widgets.md    # Documentation
├── notifications/             # Notification popup definitions
├── *.gui                      # Panel definitions (80+ files)
│   ├── topbar.gui
│   ├── construction_panel.gui
│   ├── building_details_panel.gui
│   ├── politics_panel_overview.gui
│   ├── journal_entry.gui
│   ├── decisions_panel.gui
│   ├── states_panel.gui
│   └── ...
```

### Mod GUI Structure
```
gui/
├── my_panel.gui               # Overrides vanilla (same filename = replacement)
├── my_new_panel.gui           # New panel (needs scripted_widgets registration)
├── my_texticons.gui           # Additive (unique filename)
└── scripted_widgets/
    └── my_widgets.txt         # Register standalone widgets
```

**Important:** If a mod creates `gui/construction_panel.gui`, it **completely replaces** vanilla's file. There is no merge.

---

## Widget Types

### Container Widgets

| Widget | Description | Notes |
|---|---|---|
| `widget` | Generic container | No layout logic |
| `window` | Top-level window | Rarely used directly; use `default_popup` type |
| `container` | Simple grouping | Minimal overhead |
| `flowcontainer` | Auto-layout children | `direction = vertical/horizontal`. **Hidden items take zero space.** |
| `fixedgridbox` | Grid layout | `datamodel_wrap`, `flipdirection`. **Always reserves cells even for hidden items.** |
| `dynamicgridbox` | Dynamic grid | Handles visibility correctly (excludes hidden) |
| `hbox` | Horizontal box | Flexbox-like, children share horizontal space |
| `vbox` | Vertical box | Flexbox-like, children share vertical space |
| `margin_widget` | Adds margins | Wraps a single child with margin spacing |
| `scrollarea` | Scrollable region | Requires `scrollwidget = { ... }` + `scrollbar_vertical`/`scrollbar_horizontal` |

### Display Widgets

| Widget | Description | Notes |
|---|---|---|
| `textbox` | Text display | Supports data binding, rich text, multiline |
| `icon` | Image/texture | `texture = "gfx/path.dds"` |
| `background` | Background fill | Inside any widget, uses `texture` or `color` |
| `progressbar` | Horizontal bar | `value`, `min`, `max` (float 0.0–1.0 or data-bound) |
| `progresspie` | Circular progress | Same as progressbar but circular |
| `piechart` | Pie chart | `datamodel` with `PieChart.GetSlices` |
| `video_icon` | Video playback | `video = "gfx/path.bk2"` |
| `minimap` | Map preview | Engine-controlled |
| `portrait_button` | Character portrait | `portrait_texture = "[Character.GetPortrait(...)]"` |
| `cameracontrolwidget` | 3D camera | For 3D renders |
| `texticon` | Inline icon glyph | Used in text, defined globally |

### Interactive Widgets

| Widget | Description | Notes |
|---|---|---|
| `button` | Clickable button | `onclick`, `enabled`, `click_modifiers` |
| `checkbutton` | Toggle button | Checked/unchecked state |
| `editbox` | Text input | User-editable text |
| `dropDown` | Dropdown menu | Selection from list |
| `scrollbar` | Scroll control | Paired with `scrollarea` |

### Layout Widgets

| Widget | Description | Notes |
|---|---|---|
| `caligula_table` | Data table | Rows, columns, sorting, filtering |

---

## Layout System

### Size & Position

```
widget = {
    size = { 400 300 }           # width height (pixels)
    position = { 10 20 }         # x y offset from anchor
    minimumsize = { 200 100 }    # min width height
    maximumsize = { 800 600 }    # max width height
    
    # Anchoring
    parentanchor = top|left      # Where in parent this widget attaches
    widgetanchor = center        # Which point of THIS widget is used
    
    # Common parentanchor values:
    # top|left, top|right, top|hcenter
    # bottom|left, bottom|right, bottom|hcenter
    # vcenter|left, vcenter|right, vcenter|hcenter
    # center (= vcenter|hcenter)
    
    # Resize behavior (for hbox/vbox children):
    layoutpolicy_horizontal = expanding    # Fill available space
    layoutpolicy_vertical = preferred      # Use natural size
    # Values: fixed, preferred, expanding, growing
}
```

### Flowcontainer Layout

```
flowcontainer = {
    direction = vertical           # or horizontal (default)
    spacing = 5                    # Pixels between children
    margin = { 10 10 }             # Inner margin (left/right, top/bottom)
    margin_top = 5                 # Individual margins
    margin_bottom = 5
    margin_left = 10
    margin_right = 10
    ignoreinvisible = yes          # Default: yes — hidden children take no space
    
    # Children are laid out sequentially
    textbox = { ... }
    icon = { ... }
    button = { ... }
}
```

### Scrollarea

```
scrollarea = {
    size = { 400 500 }
    
    scrollwidget = {
        # Content goes here — can be larger than scrollarea
        flowcontainer = {
            direction = vertical
            # ... children
        }
    }
    
    scrollbar_vertical = {
        using = Scrollbar_Vertical   # Standard scrollbar template
    }
}
```

### hbox / vbox

```
hbox = {
    spacing = 5
    
    # Children share horizontal space
    textbox = {
        layoutpolicy_horizontal = expanding   # Takes remaining space
        text = "Label"
    }
    button = {
        size = { 30 30 }                       # Fixed size
    }
}
```

### fixedgridbox (Data-Driven Grid)

```
fixedgridbox = {
    datamodel = "[GetPlayer.AccessIdeas]"
    addcolumn = 48                # Column width
    addrow = 48                   # Row height
    datamodel_wrap = 5            # Wrap after 5 columns
    flipdirection = yes           # Fill columns first, then rows
    maxhorizontalslots = 5        # Max columns
    
    item = {
        # Repeated for each item in datamodel
        icon = {
            size = { 44 44 }
            texture = "[Idea.GetIcon]"
        }
    }
}
```

---

## Styling & Appearance

### Text

```
textbox = {
    text = "Static text"                              # Static or...
    text = "[GetPlayer.GetName]"                      # Data-bound
    raw_text = "[GetPlayer.GetGDP|D]"                 # Raw (no loc processing)
    
    # Fonts
    using = Font_Size_Medium                          # Via template
    fontsize = 18                                     # Direct
    fontsize_min = 12                                 # Minimum for auto-size
    
    # Available font families:
    # EBGaramond (headers, serif)
    # OpenSans (body, sans-serif)  
    # PlayfairDisplay (formal headers)
    # Fancy (decorative)
    # TitleFont, HeaderFont, BodyFont (aliases)
    
    # Text formatting
    align = left|top                                  # Alignment
    # Values: left, right, hcenter, top, bottom, vcenter, nobaseline
    
    elide = right                                     # Truncate with "..."
    autoresize = yes                                  # Resize widget to fit text
    multiline = yes                                   # Allow text wrapping
    max_width = 400                                   # Max width before wrapping
    
    # Colors (in loc: #bold text#!, #v value#!, #R red#!, etc.)
    fonttintcolor = "[GetPlayer.GetMapColor]"         # Data-bound color
    
    # Margin/padding
    margin = { 10 5 }
    margin_left = 5
    margin_right = 5
    margin_top = 3
    margin_bottom = 3
}
```

### Colors & Textures

```
icon = {
    texture = "gfx/interface/icons/icon.dds"
    
    # Color tinting
    color = { 1.0 0.5 0.0 1.0 }                     # RGBA float
    
    # Texture compositing
    modify_texture = {
        texture = "gfx/interface/masks/fade_horizontal.dds"
        blend_mode = alphamultiply                    # or: colordodge, overlay, multiply
        spriteType = corneredTiled
    }
    
    # Frame selection (sprite sheets)
    frame = 2
    framesize = { 40 40 }
    
    # Sprite types
    spriteType = corneredTiled                        # 9-slice scaling
    # corneredStretched, corneredTiled, Corneredtiled
}
```

### Backgrounds

```
widget = {
    background = {
        using = Background_Area_Dark                  # Template
    }
    
    # Or explicit:
    background = {
        texture = "gfx/interface/backgrounds/bg_dark.dds"
        spriteType = corneredTiled
        color = { 0.15 0.15 0.15 0.8 }
        margin = { -5 -5 }                           # Extend beyond widget bounds
    }
}
```

### Visibility & Transparency

```
widget = {
    visible = "[GetPlayer.HasTechnology('example_tech')]"   # Boolean expression
    visible = no                                             # Static hidden
    
    alpha = 0.5                                              # Transparency (0.0–1.0)
    alpha = "[TransparentIfFalse(condition)]"                # Dynamic transparency
    alpha = "[TransparentIfZero(GetPlayer.GetGDP)]"          # Dim if zero
}
```

### Common Templates (via `using`)

```
using = Font_Size_Small          # ~14px
using = Font_Size_Medium         # ~16px  
using = Font_Size_Big            # ~20px
using = Font_Type_Bold

using = Background_Area_Dark     # Dark panel background
using = Background_Area_Light    # Light panel background
using = Background_Area_Border_Solid   # Bordered background

using = Scrollbar_Vertical       # Standard vertical scrollbar
using = Scrollbar_Horizontal     # Standard horizontal scrollbar

using = Animation_FadeIn_Quick   # Quick fade-in animation
using = Animation_FadeOut        # Fade-out

using = Tooltip_Above            # Position tooltip above widget
using = Tooltip_Below            # Position tooltip below widget
```

---

## Data Binding Expressions

All dynamic values use the `"[Expression]"` syntax. Expressions can access game data, perform comparisons, format numbers, and call actions.

### Basic Access

```
text = "[GetPlayer.GetName]"                      # Country name
text = "[Country.GetFlag]"                        # Flag
text = "[Building.GetNameNoFormatting]"            # Building name
text = "[Character.GetFullName]"                   # Character name
texture = "[JournalEntry.GetIcon]"                # JE icon path
value = "[FixedPointToFloat(State.GetInfrastructureUsage)]"   # Progress bar
```

### Boolean Expressions

```
visible = "[GetPlayer.HasTechnology('example_tech')]"
visible = "[Not(Country.IsLocalPlayer)]"
visible = "[And(Country.IsAtWar, Country.IsLocalPlayer)]"
visible = "[Or(Building.IsGovernmentFunded, Building.IsPrivatelyOwned)]"
visible = "[And3(a, b, c)]"                       # 3-way AND
visible = "[And4(a, b, c, d)]"                    # 4-way AND
visible = "[Or5(a, b, c, d, e)]"                  # 5-way OR
```

### Comparisons

```
visible = "[GreaterThan_CFixedPoint(Country.GetGDP, '(CFixedPoint)1000')]"
visible = "[LessThan_int32(GetDataModelSize(list), '(int32)5')]"
visible = "[EqualTo_string(BuildingType.GetKey, 'building_factory')]"
visible = "[NotEqualTo_CFixedPoint(value, '(CFixedPoint)0')]"
```

**Literal constants:** `'(CFixedPoint)0'`, `'(int32)5'`, `'(int64)0'`, `'(float)1.0'`

### Numeric Operations

```
value = "[FixedPointToFloat(ratio)]"              # CFixedPoint → float (for progressbars)
text = "[Negate_CFixedPoint(value)|D]"            # Negate
text = "[Abs_CFixedPoint(value)|D]"               # Absolute value
text = "[Max_CFixedPoint(val1, val2)|D]"          # Maximum
text = "[IntToFloat(count)]"                      # int → float
```

### String Operations

```
visible = "[Not(StringIsEmpty(Country.GetRulerTitle))]"
text = "[Concatenate('PREFIX_', Country.GetTag)]"
text = "[Localize('loc_key')]"                    # Localize a key
text = "[SelectLocalization(condition, 'key_true', 'key_false')]"
text = "[AddLocalizationIf(condition, 'extra_text_key')]"
text = "[Concept('game_concept_key')]"            # Hoverable concept
```

### Conditional Selection

```
# Ternary for numbers
size = { [Select_int32(condition, '(int32)400', '(int32)300')] 200 }

# Ternary for colors
color = "[Select_CVector4f(condition, color1, color2)]"
```

### Datamodel Functions

```
visible = "[Not(IsDataModelEmpty(Country.AccessStates))]"
visible = "[DataModelHasItems(list)]"
text = "[GetDataModelSize(Country.AccessStates)]"
datamodel = "[DataModelSkipFirst(list)]"          # Skip first item
datamodel = "[DataModelSubSpan(list, '(int32)0', '(int32)5')]"  # First 5
```

---

## Types & Templates

### Defining Types

Types are custom widget classes. They create reusable, parameterized components.

```
# Define a type
type my_info_row = hbox {
    spacing = 5
    
    textbox = {
        layoutpolicy_horizontal = expanding
        block "label" {
            text = "Default Label"
        }
    }
    
    textbox = {
        block "value" {
            text = "0"
        }
    }
}

# Use the type
my_info_row = {
    blockoverride "label" { text = "Population" }
    blockoverride "value" { text = "[GetPlayer.GetTotalPopulation|D]" }
}
```

### Type Inheritance

```
# Base type
type base_panel = widget {
    size = { 400 600 }
    background = { using = Background_Area_Dark }
    
    block "content" {}
}

# Derived type (overrides base):
type detail_panel = base_panel {
    blockoverride "content" {
        # Custom content
    }
}
```

### Defining Templates

Templates are mixin-style property bundles — they inject properties into the widget that uses them.

```
# Define a template
template tooltip_info_style {
    using = Font_Size_Small
    fontsize = 14
    max_width = 350
    multiline = yes
    autoresize = yes
    align = left|top
}

# Use it
textbox = {
    using = tooltip_info_style
    text = "Some tooltip text"
}
```

### Template with Overridable Defaults

```
template my_button_style {
    size = { 200 40 }
    using = Font_Size_Medium
    
    block "button_text" {
        text = "Click Me"
    }
}
```

---

## Blocks & Blockoverrides

Blocks define **extension points** in types and templates. Blockoverrides fill those points.

### How It Works

```
# Type definition with blocks
type my_window = default_popup {
    blockoverride "window_header_name" {
        text = "MY_WINDOW_TITLE"
    }
    
    blockoverride "entire_scrollarea" {
        scrollarea = {
            # ... panel content
        }
    }
    
    blockoverride "header_close_button_visibility" {
        visible = yes
    }
    
    blockoverride "header_close_button" {
        onclick = "[GetVariableSystem.Clear('my_window_open')]"
    }
}
```

### Common Vanilla Blocks

The `default_popup` type (from `gui/shared/defaults.gui`) exposes these blocks:

| Block | Purpose |
|---|---|
| `"window_header_name"` | Title text |
| `"entire_scrollarea"` | Main content area |
| `"header_close_button"` | Close button onclick |
| `"header_close_button_visibility"` | Close button visibility |
| `"header_back_button_visibility"` | Back button visibility |
| `"scrollbar_visibility"` | Scrollbar type |

The `default_block_window` and `default_block_window_two_lines` types expose:

| Block | Purpose |
|---|---|
| `"window_header_name"` | Title |
| `"window_header_name_line_two"` | Subtitle |
| `"content"` | Main content |
| `"fixed_top"` | Fixed header area |
| `"fixed_bottom"` | Fixed footer area |
| `"bottom_bar"` | Bottom bar content |

### Best Practice

When overriding vanilla panels, use blockoverrides to modify specific sections rather than replacing entire files — but note that **vanilla panels often don't expose enough blocks**, so full file replacement is often necessary.

---

## Data Models & Item Repeaters

Data models are lists of game objects that drive repeated UI elements.

### Basic Pattern

```
fixedgridbox = {
    datamodel = "[GetPlayer.AccessStates]"      # List of State objects
    addcolumn = 300
    addrow = 40
    
    item = {
        # This block repeats for each State in the datamodel
        # Inside item, the datacontext is automatically set to the current State
        hbox = {
            textbox = {
                text = "[State.GetName]"          # "State" is the type name
            }
            textbox = {
                text = "[State.GetPopulationSize|D]"
            }
        }
    }
}
```

### Flowcontainer with Datamodel

```
flowcontainer = {
    direction = vertical
    datamodel = "[Country.AccessInterestGroups]"
    
    item = {
        widget = {
            size = { 300 50 }
            # InterestGroup is the data context
            textbox = { text = "[InterestGroup.GetName]" }
            textbox = { text = "[InterestGroup.GetClout|1%]" }
        }
    }
}
```

### Nested Datamodels

```
flowcontainer = {
    datamodel = "[GetPlayer.AccessStates]"
    direction = vertical
    
    item = {
        flowcontainer = {
            datamodel = "[State.AccessBuildings]"   # Nested: buildings in each state
            direction = horizontal
            
            item = {
                icon = { texture = "[Building.GetIcon]" }
            }
        }
    }
}
```

### Sorting & Filtering

The GUI has no built-in sort/filter. Use game-side `ordered_` iterators or script value sorting in scripted_guis, or rely on the game data model's own ordering.

### Charting script-held data (column charts)

**`plotline` cannot render mod data.** Its `plotpoints` property only accepts the output of `GetTrendPlotPoints` / `GetTrendPlotPointsNormalized` / `GetDynTrendPlotPoints`, and all three take an engine-side `DataTrend` (`Country.GetGDPTrend`, `Goods.GetPriceTrend`, …). No global function in `data_types_*.txt` returns a `DataTrend`, and no `DataTrend` exists for a script variable, so stored samples cannot feed a line graph. Draw a column chart instead — one bar per stored sample over a datamodel. Worked example: `gui/journal_entry_widgets/te_history_chart.gui`.

**Size a bar from data with a `progressbar`, never with `size`.** `size` takes no data expression; `progressbar` takes `value` / `min` / `max` and does.

```
progressbar = {
    size = { 100% 100% }
    direction = vertical            # fills upward from the floor
    min = 0
    max = 100
    value = "[FixedPointToFloat( ScriptContainer.GetVariableValue( 'my_value' ) )]"
    progresstexture = "gfx/interface/progressbar/progressbar_white.dds"
    noprogresstexture = "gfx/interface/icons/generic_icons/transparent.dds"
    texture_density = 2
    skip_initial_animation = yes
    color = { 0.42 0.62 0.85 1.0 }  # tints the white progress texture
}
```

Use a **bare `progressbar`**, not `white_progressbar_vertical`: that type inherits `progressbar_properties`, whose frame texture has 6 px sprite borders and whose glow animations are sized for a 300×40 bar — at a few pixels wide it renders as noise.

**Negative values: vanilla's "REVERSE HACK".** Stack two half-height bars around a zero axis. The lower one swaps `progresstexture` and `noprogresstexture` and uses a `min = -N`, `max = 0` range, so the coloured part is drawn from the far end and hangs *down* from the axis (`gui/shared/progressbars.gui` → `double_direction_progressbar`). Clamp each half's value in the expression (`Max_CFixedPoint('(CFixedPoint)0', v)` / `Min_CFixedPoint`) so a positive sample draws nothing below the axis.

**Bars that share the width.** An `hbox` of fixed width whose items are `size = { 0 100% }` + `layoutpolicy_horizontal = expanding` (+ a `maximumsize` cap) divides the width between the *visible* items — vanilla `levels_progressbar` (`gui/shared/progressbars.gui`, used by `country_panel.gui`). With `ignoreinvisible = yes` on the hbox, hiding out-of-range samples widens the remaining bars instead of leaving empty slots, which is how a 1 / 5 / 10-year range selector works without three separate layouts.

**Per-bar tooltips.** Give the item widget a `tooltip = "<loc key>"`; the loc key reads the item's datacontext (`[ScriptContainer.GetVariableValue('x')|1]`) and can branch with `[SelectLocalization( ScriptContainer.HasVariable('x'), 'key_a', 'key_b' )]` — the way to show "not recorded" rather than a misleading zero.

---

## State Animations

States provide animation and conditional triggers for widgets.

### Basic Animation

```
widget = {
    state = {
        name = _show                             # Triggered when widget becomes visible
        alpha = 1.0
        duration = 0.3
        using = Animation_Curve_Default
    }
    
    state = {
        name = _hide                             # Triggered when widget becomes hidden
        alpha = 0.0
        duration = 0.2
    }
}
```

### Conditional Trigger

```
widget = {
    state = {
        name = flash_warning
        trigger_when = "[GreaterThan_CFixedPoint(value, '(CFixedPoint)100')]"
        
        # Animation properties
        alpha = 0.5
        duration = 0.5
        next = flash_warning_back                # Chain to next state
    }
    
    state = {
        name = flash_warning_back
        alpha = 1.0
        duration = 0.5
        next = flash_warning                     # Loop
    }
}
```

### `trigger_when` + `on_finish` Pattern

Used for auto-executing effects when conditions change (invisible widget pattern):

```
widget = {
    size = { 0 0 }
    alpha = 0
    
    state = {
        trigger_when = "[SomeCondition]"
        on_finish = "[GetScriptedGui('my_effect').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
    }
}
```

### Built-in State Names

| State | When Triggered |
|---|---|
| `_show` | Widget becomes visible |
| `_hide` | Widget becomes hidden |
| `_mouse_enter` | Mouse hovers over widget |
| `_mouse_leave` | Mouse leaves widget |

---

## Interactive Elements

### Buttons

```
button = {
    size = { 200 40 }
    text = "BUTTON_LOC_KEY"
    
    # Click handler
    onclick = "[GetPlayer.ToggleIgnoreDecision(Decision.Self)]"
    
    # Dynamic enabled/disabled
    enabled = "[Decision.IsValid(GetPlayer.Self)]"
    
    # Disabled tooltip
    tooltip = "[Decision.GetTooltip(GetPlayer.Self)]"
    
    # Sound
    using = Click_Default                           # Or specific sounds
    clicksound = "event:/SFX/UI/Generic/sfx_ui_generic_confirm"
    
    # Visual style (textures for different states)
    texture = "gfx/interface/buttons/default_button.dds"
    
    # Keyboard shortcut
    shortcut = "close_window"
}
```

### Click Modifiers (Shift/Ctrl/Alt)

```
button = {
    text = "Adjust Value"
    
    click_modifiers = {
        ondefault = "[GetScriptedGui('adjust_1').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        onshift = "[GetScriptedGui('adjust_10').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        onctrl = "[GetScriptedGui('adjust_100').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        onalt = "[GetScriptedGui('adjust_neg').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
    }
    
    onrightclick = "[GetScriptedGui('reset').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
}
```

### Checkbuttons

```
checkbutton = {
    size = { 30 30 }
    checked = "[GetVariableSystem.Exists('option_enabled')]"
    onclick = "[GetVariableSystem.Toggle('option_enabled')]"
}
```

### Dropdowns

```
dropDown = {
    datamodel = "[GetPlayer.AccessAvailableLaws]"
    selected_index = 0
    
    # ... complex dropdown patterns vary
}
```

---

## Scripted GUIs

Scripted GUIs bridge the gap between GUI clicks and game script effects. They allow buttons to execute Paradox script effects.

### Definition (`common/scripted_guis/my_sgui.txt`)

```
my_button_sgui = {
    scope = country                     # ROOT scope type
    
    is_shown = {                        # Controls visibility (trigger block)
        has_technology = tech_example
    }
    
    is_valid = {                        # Controls enabled state (trigger block)
        NOT = { has_modifier = cooldown_modifier }
    }
    
    effect = {                          # What happens on click (effect block)
        add_modifier = {
            name = my_effect_modifier
            days = normal_modifier_time
        }
    }
    
    ai_is_valid = { always = no }       # AI never uses this (default)
    ai_chance = { base = 0 }           # AI activation chance
    
    # Optional: confirmation dialog
    # confirm_title = { ... }
    # confirm_text = { ... }
    
    # Optional: saved scopes from GUI (passed via AddScope if needed)
    # saved_scopes = { my_scope }
}
```

### GUI Binding

**Method 1: Via `datacontext`** (preferred for multiple references)

```
widget = {
    datacontext = "[GetScriptedGui('my_button_sgui')]"
    
    visible = "[ScriptedGui.IsShown(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
    
    button = {
        enabled = "[ScriptedGui.IsValid(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        onclick = "[ScriptedGui.Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        tooltip = "[ScriptedGui.BuildTooltip(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        text = "DO_THING"
    }
}
```

**Method 2: Inline** (for one-off calls)

```
button = {
    onclick = "[GetScriptedGui('my_sgui').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
    enabled = "[GetScriptedGui('my_sgui').IsValid(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
}
```

### ScriptedGui Methods

| Method | Returns | Purpose |
|---|---|---|
| `.IsShown(scope)` | bool | Evaluates `is_shown` trigger |
| `.IsValid(scope)` | bool | Evaluates `is_valid` trigger |
| `.Execute(scope)` | void | Runs `effect` block |
| `.ExecuteTooltip(scope)` | string | Shows effect preview tooltip |
| `.BuildTooltip(scope)` | string | Combined tooltip (is_valid + effect) |

### Scoping Pattern

The scope argument tells the engine what `ROOT` is inside the scripted_gui's triggers/effects:

```
# ROOT = player's country
GuiScope.SetRoot(GetPlayer.MakeScope).End

# ROOT = a specific character (from datamodel context)
GuiScope.SetRoot(Character.MakeScope).End

# ROOT = a specific building
GuiScope.SetRoot(Building.MakeScope).End

# ROOT = a specific state
GuiScope.SetRoot(State.MakeScope).End
```

### Tooltip Lists (Dynamic Content)

Scripted GUIs can generate dynamic tooltip lists using `custom_tooltip` in the effect:

```
# Definition
my_list_sgui = {
    scope = country
    effect = {
        every_scope_state = {
            limit = { state_population > 100000 }
            custom_tooltip = "STATE_LIST_ENTRY"    # Each generates a line
        }
    }
}
```

```yml
# Localization
STATE_LIST_ENTRY:0 "  [ROOT.GetName]: [ROOT.GetPopulationSize|D] people"
```

```
# GUI usage (in tooltip)
tooltip = "[GetScriptedGui('my_list_sgui').ExecuteTooltip(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
```

Or in localization:
```yml
MY_TOOLTIP:0 "[GetScriptedGui('my_list_sgui').ExecuteTooltip(GuiScope.SetRoot(ROOT.GetCountry.MakeScope).End)]"
```

### Click Modifiers with ScriptedGuis

Create separate scripted_gui definitions for each modifier:

```
# In common/scripted_guis/:
adjust_value_1 = { scope = country  effect = { change_variable = { name = val add = 1 } } is_valid = { always = yes } }
adjust_value_10 = { scope = country  effect = { change_variable = { name = val add = 10 } } is_valid = { always = yes } }
adjust_value_100 = { scope = country  effect = { change_variable = { name = val add = 100 } } is_valid = { always = yes } }
```

```
# In GUI:
button = {
    click_modifiers = {
        ondefault = "[GetScriptedGui('adjust_value_1').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        onshift = "[GetScriptedGui('adjust_value_10').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
        onctrl = "[GetScriptedGui('adjust_value_100').Execute(GuiScope.SetRoot(GetPlayer.MakeScope).End)]"
    }
}
```

---

## Creating Standalone Panels

To create an entirely new panel (not overriding an existing one), use the **scripted widgets** system.

### Step 1: Create the GUI File

Create `gui/my_custom_panel.gui`:

```
my_custom_panel = {
    # Using default_popup type for window chrome
    type = default_popup
    name = "my_custom_panel"
    
    visible = "[GetVariableSystem.Exists('my_custom_panel_open')]"
    parentanchor = center
    movable = yes
    layer = popups
    allow_outside = yes
    
    blockoverride "window_header_name" {
        text = "MY_PANEL_TITLE"
    }
    
    blockoverride "header_close_button_visibility" {
        visible = yes
    }
    
    blockoverride "header_close_button" {
        onclick = "[GetVariableSystem.Clear('my_custom_panel_open')]"
    }
    
    blockoverride "entire_scrollarea" {
        scrollarea = {
            layoutpolicy_horizontal = expanding
            layoutpolicy_vertical = expanding
            
            scrollwidget = {
                flowcontainer = {
                    direction = vertical
                    spacing = 10
                    margin = { 15 10 }
                    
                    # Panel content here
                    textbox = {
                        text = "Hello from custom panel!"
                        using = Font_Size_Big
                        autoresize = yes
                    }
                    
                    # Data-bound content
                    textbox = {
                        text = "[GetPlayer.GetName] Statistics"
                        autoresize = yes
                    }
                }
            }
            
            scrollbar_vertical = {
                using = Scrollbar_Vertical
            }
        }
    }
}
```

### Step 2: Register the Widget

Create `gui/scripted_widgets/my_widgets.txt`:

```
gui/my_custom_panel.gui = my_custom_panel
```

Each line is `gui_file_path = widget_name`. The widget is auto-created at startup.

### Step 3: Add an Open Button

Add a button to an existing panel (requires overriding that panel's file):

```
button = {
    text = "OPEN_MY_PANEL"
    onclick = "[GetVariableSystem.Set('my_custom_panel_open', 'open')]"
}
```

### Key Points

- `GetVariableSystem` controls client-side visibility — NOT saved in save files
- `layer = popups` ensures the panel renders above other panels
- `movable = yes` allows the player to drag the window
- `allow_outside = yes` lets the panel extend outside its parent
- The widget name in the `.gui` file and the registration `.txt` must match
- **Scripted widgets files are additive** — multiple mods can have their own files

---

## Modifying Existing Panels

### Full File Replacement (Most Common)

1. Copy the vanilla `.gui` file from `game/gui/` to your mod's `gui/` folder
2. Make modifications
3. The mod's version completely replaces vanilla

**Pros:** Full control, any change possible.
**Cons:** Breaks compatibility with other mods that modify the same file; must manually merge vanilla updates after game patches.

### What Can't Be Modified Without Replacement

- Widget hierarchy changes (adding/removing siblings)
- Datamodel sources
- Layout structure changes
- Adding new blocks to vanilla types

### TextIcon Addition (Additive)

Text icons in uniquely-named `.gui` files are additive:

```
# gui/my_texticons.gui — this file adds icons, doesn't replace anything
texticon = {
    icon = "icon_nuclear"
    texture = "gfx/interface/icons/nuclear_icon.dds"
    pointsize = 20
    fontsize = 18
}
```

---

## Tooltips

### Simple Tooltips

```
widget = {
    tooltip = "TOOLTIP_LOC_KEY"                   # Static localized text
    tooltip = "[Country.GetTooltip]"              # Dynamic from data model
}
```

### Rich Tooltips

```
widget = {
    tooltipwidget = {
        FancyTooltip_Country = {}                 # Typed tooltip widget
    }
}
```

### Custom Tooltip Widgets

```
widget = {
    tooltipwidget = {
        widget = {
            size = { 350 0 }                      # Width fixed, height auto
            
            flowcontainer = {
                direction = vertical
                
                textbox = {
                    text = "HEADER"
                    using = Font_Size_Medium
                    autoresize = yes
                    max_width = 340
                }
                
                textbox = {
                    text = "[GetPlayer.GetGDP|D]"
                    autoresize = yes
                    max_width = 340
                }
            }
        }
    }
}
```

### Tooltip Positioning

```
using = Tooltip_Above                             # Show above widget
using = Tooltip_Below                             # Show below widget
```

### Tooltip with Appended Content

```
tooltipwidget = {
    TooltipWidgetType = {
        blockoverride "tooltip_content_after" {
            # Additional content appended after standard tooltip
            my_custom_graph = {}
        }
    }
}
```

---

## Text Icons

Text icons are small inline glyphs usable within text strings. They're referenced via localization markers.

### Defining Text Icons

```
# gui/my_texticons.gui
texticon = {
    icon = "icon_my_custom"                       # Reference name
    texture = "gfx/interface/icons/my_icon.dds"
    pointsize = 20
    fontsize = 18
}
```

### Using in Localization

```yml
my_loc_key:0 "Production: @icon_my_custom! 500 units"
```

### Text icons are additive — put them in uniquely-named `.gui` files to avoid replacing vanilla.

---

## Global Accessors & Functions

### Top-Level Accessors

| Accessor | Returns | Description |
|---|---|---|
| `GetPlayer` | Country (mutable) | Player's country, can execute actions |
| `AccessPlayer` | Country (read-only) | Player's country, data access only |
| `GetMetaPlayer` | MetaPlayer | `.GetPlayedOrObservedCountry` for observer checks |
| `GetVariableSystem` | UI state | Client-side toggles (not saved) |
| `GetCurrentDate` | Date | Current in-game date |
| `GetDefine('CAT','KEY')` | CFixedPoint/string | Engine constants |
| `GetScriptedGui('name')` | ScriptedGui | Bridge to game effects |
| `GetExilePool` | Pool | Exiled characters |
| `GetBuildingType('key')` | BuildingType | Static building type lookup |
| `GetPopType('key')` | PopType | Static pop type lookup |
| `GetCountryDiplomaticAction('key')` | DiplomaticAction | Action lookup |
| `HasDlcFeature('feature')` | bool | DLC check |

### Global Functions Reference

See the full catalog in [/memories/repo/gui_data_model_notes.md](/memories/repo/gui_data_model_notes.md).

Key categories:
- **Boolean:** `Not`, `And`, `And3`, `And4`, `Or`, `Or5`
- **Comparison:** `EqualTo_*`, `GreaterThan_*`, `LessThan_*`, etc. (for `int32`, `int64`, `CFixedPoint`, `float`, `string`)
- **Numeric:** `FixedPointToFloat`, `Negate_CFixedPoint`, `Abs_CFixedPoint`, `Max_CFixedPoint`, `Min_CFixedPoint`
- **String:** `Concatenate`, `Localize`, `SelectLocalization`, `Concept`
- **Selection (ternary):** `Select_float`, `Select_int32`, `Select_CVector4f`
- **Datamodel:** `IsDataModelEmpty`, `DataModelHasItems`, `GetDataModelSize`, `DataModelFirst`, `DataModelSubSpan`
- **Transparency:** `TransparentIfFalse`, `TransparentIfZero`
- **Action:** `Execute`, `IsValid`

---

## Format Specifiers

Appended after `|` in data binding expressions. Combinable.

| Spec | Meaning | Example |
|---|---|---|
| `D` | Thousands delimiter | `1,234,567` |
| `K` | K/M abbreviation | `12.3K` |
| `v` | Value formatting | Standard number format |
| `0` | 0 decimal places | `42` |
| `1` | 1 decimal place | `42.3` |
| `+` | Always show sign | `+42` |
| `=` | Always show sign (alt) | `+42` |
| `%` | Percentage | `45%` |
| `-` | Negative/cost | `-42` |
| `*` | ×100 (fraction→%) | `0.15 → 15` |

### Common Combinations

| Format | Use Case | Result |
|---|---|---|
| `\|D` | Large numbers | `1,234,567` |
| `\|D+=` | Signed large numbers | `+1,234,567` |
| `\|%0` | Percentage (integer) | `45%` |
| `\|%1` | Percentage (1 decimal) | `45.3%` |
| `\|v1*` | Clout display (fraction→%) | `15.3` |
| `\|Kv` | Abbreviated | `12.3K` |
| `\|0+=` | Signed integer | `+42` |

---

## GetVariableSystem (UI State)

Client-side state system for UI toggles, tab selection, etc. **NOT saved in save files.** String key-value pairs.

### Methods

```
GetVariableSystem.Exists('name')                  # Does key exist? (bool)
GetVariableSystem.Toggle('name')                  # Toggle key existence
GetVariableSystem.Set('name', 'value')            # Set key to value
GetVariableSystem.HasValue('name', 'value')       # Check specific value
GetVariableSystem.Clear('name')                   # Remove key
GetVariableSystem.SetIf('name', condition)        # Set if condition true
```

### Common Patterns

```
# Panel toggle
visible = "[GetVariableSystem.Exists('my_panel_open')]"
onclick = "[GetVariableSystem.Toggle('my_panel_open')]"

# Tab selection (radio-button pattern)
onclick = "[GetVariableSystem.Set('active_tab', 'economy')]"
onclick = "[GetVariableSystem.Clear('tab_military')]"
onclick = "[GetVariableSystem.Clear('tab_diplomacy')]"
visible = "[GetVariableSystem.HasValue('active_tab', 'economy')]"

# Dynamic key from object
onclick = "[GetVariableSystem.Toggle(Concatenate('expanded_', State.GetIDString))]"
visible = "[GetVariableSystem.Exists(Concatenate('expanded_', State.GetIDString))]"
```

---

## GetDefine (Engine Constants)

Access engine defines from `common/defines/`:

```
text = "[GetDefine('NDiplomacy', 'MAX_RELATIONS')]"
visible = "[GreaterThan_CFixedPoint(value, GetDefine('NEconomy', 'COMPANY_PROSPERITY_MAX'))]"
```

### Known Categories

| Category | Example Keys |
|---|---|
| `NGUI` | `SCROLLBAR_WIDTH`, `BUILDING_CONSIDERED_FULLY_EMPLOYED` |
| `NEconomy` | `COMPANY_PROSPERITY_MAX` |
| `NDiplomacy` | `MIN_RELATIONS`, `MAX_RELATIONS`, `DIPLOMATIC_PLAY_OPENING_PHASE_END` |
| `NMilitary` | `MAX_NUM_COMMANDERS_PER_FORMATION` |
| `NPowerBlocs` | `COHESION_TARGET_MAX` |

---

## MakeScope & Variable Access

### MakeScope

Converts a typed GUI data object to a generic `Scope` reference. Required for `ScriptValue()`, `Var()`, and `ScriptedGui` scope building.

```
GetPlayer.MakeScope                               # Player country → scope
Character.MakeScope                               # Character → scope
Building.MakeScope                                # Building → scope
State.MakeScope                                   # State → scope
```

### Reading Game Variables in GUI

```
# Country variable:
text = "[GetPlayer.MakeScope.Var('my_var').GetValue|0]"

# State variable:
text = "[State.MakeScope.Var('infrastructure_bonus').GetValue|1]"
```

### Reading Script Values in GUI

```
# Via MakeScope (required — ScriptValue is on Scope, not typed objects):
text = "[GetPlayer.MakeScope.ScriptValue('my_script_value')|D]"
```

### Reading Global Variables

```
text = "[GetGlobalVariable('my_global').GetValue|1]"
```

### Typed Accessors from Var (for display)

When a variable stores a reference to a game object:

```
# Variable stores a state:
text = "[ROOT.Var('target_state').GetState.GetName]"

# Variable stores a character:
text = "[ROOT.Var('leader').GetCharacter.GetFullName]"

# Variable stores a country (via capital workaround):
text = "[ROOT.Var('ally_capital').GetState.GetCountry.GetName]"
```

### Modifier Access in GUI

```
# Get modifier value:
text = "[GetPlayer.GetModifier.GetValueFor('country_tax_income_add')|D+=]"

# Get value with hoverable breakdown:
text = "[GetPlayer.GetModifier.GetValueWithBreakdownFor('country_cultural_pull_add')]"

# Get full description:
tooltip = "[Market.GetModifier.GetFullEntryDescFor('market_land_trade_capacity_add')]"

# Check if empty:
visible = "[Not(Amendment.GetType.GetModifier.IsEmpty)]"
```

---

## Mod Compatibility

### Additive (Safe for Multi-Mod)

These can coexist across multiple mods without conflict:

| File Type | Location | Notes |
|---|---|---|
| Text icons | `gui/unique_name.gui` | Must have unique filename |
| Scripted widgets registration | `gui/scripted_widgets/*.txt` | Each mod uses own file |
| Scripted GUIs | `common/scripted_guis/*.txt` | Must have unique key names |
| New standalone panels | `gui/new_panel.gui` + scripted_widgets | Must have unique widget names |

### Destructive (Only One Mod Wins)

| File Type | Location | Notes |
|---|---|---|
| Panel overrides | `gui/existing_panel.gui` | Replaces vanilla entirely |

If two mods both override `gui/construction_panel.gui`, only one loads (load order dependent). This is the #1 source of mod incompatibility.

### Compatibility Strategies

1. **Minimize overrides** — Only override panels you must change
2. **Use scripted widgets** for new panels instead of cramming into existing ones
3. **Use scripted GUIs** for game logic instead of embedded effects
4. **Document which vanilla files are overridden** for compatibility patch creators

---

## Common Gotchas

1. **`.gui` files must be UTF-8 BOM encoded.** Missing BOM causes loading failures.

2. **File replacement is total.** `gui/x.gui` in your mod replaces the entire vanilla `x.gui`. There is no partial merge.

3. **`flowcontainer` vs `fixedgridbox` visibility:** `flowcontainer` collapses hidden children (zero space). `fixedgridbox` always reserves cells. Use `flowcontainer` when items should disappear; `fixedgridbox` for consistent grid layouts.

4. **`GetPlayer` vs `AccessPlayer`:** `GetPlayer` returns mutable (can call actions). `AccessPlayer` is read-only. Use `AccessPlayer` when you only need data.

5. **`ScriptValue` requires `MakeScope`.** `Country.ScriptValue('x')` does NOT work. Use `Country.MakeScope.ScriptValue('x')`.

6. **`AddScope` DOES exist in V3** — an earlier version of this list claimed otherwise. `TopScope.AddScope(Arg0, Arg1)` is in the engine data-type docs (`data_types_script.txt`) and vanilla uses it: `gui/journal_entry_widgets/ep2_japan_widgets.gui` and `gui/character_panel.gui` both call `GuiScope.SetRoot(X.MakeScope).AddScope('frame', MakeScopeValue('(CFixedPoint)0')).End`. The receiving scripted GUI declares `saved_scopes = { frame }` and reads `scope:frame` in its triggers/effects. This mod uses it in two places: `gui/market_panel.gui` passes a partner market (`AddScope('base_market', …)`) into a script value, and `gui/journal_entry_widgets/strategic_reserve_widget.gui` passes a small integer to **parameterize one scripted GUI across several buttons** — see the pattern note below.

7. **`@variables` are compile-time constants.** `@my_width = 400` is resolved at load time, not runtime. Use data binding for dynamic values.

8. **`datacontext` sets the implicit type for child expressions.** When you write `datacontext = "[GetPlayer.Self]"`, children can use `Country.GetName` directly. Change the datacontext and all child expressions must match the new type.

9. **Literal constant syntax:** Use `'(CFixedPoint)0'`, `'(int32)5'`, `'(float)1.0'` when functions need typed literals.

10. **JournalEntry scope:** `JournalEntry.GetCountry` returns the owning country. In JE context, `ROOT.GetCountry.MakeScope.ScriptValue('x')` is the pattern.

11. **`Var().GetCountry.GetName` is unreliable** for country variables — it rendered blank when tested in this mod, though vanilla 1.14 does ship the chain (`ep2_04_l_english.yml`, `ip4_misc_01_l_english.yml`). Two workarounds, in order of preference. (a) If the variable is yours to write, store the country's **capital** and chain `Var('cap').GetState.GetCountry.GetName` — what the covert-operations widget does with `iw_target_capital`. (b) If the variable belongs to data you must not change — a read-only view over someone else's script containers — navigate it **in script** from a `scripted_gui` and render the result with `[GetScriptedGui('x').ExecuteTooltip(GuiScope.SetRoot(<obj>.MakeScope).End)]`, printing `[THIS.GetCountry.GetName]` on each `custom_tooltip` line. That is vanilla's own shape for a country variable list (`je_hispanoamerica_not_recognized_countries_sgui` + `HISPANOAMERICA_RECOGNITION_COUNTRIES_LIST_ENTRY` in `ip4_spain_l_english.yml`), and it brings the annexed-country guard `AddLocalizationIf(THIS.GetCountry.Exists, 'FALLBACK_KEY')` with it. `gui/journal_entry_widgets/un_chamber_widget.gui` is this mod's worked example.

12. **Map markers/HUD overlays cannot be added.** The HUD is engine-level. Mods can override existing HUD files but cannot add new map layers or HUD elements.

13. **`trigger_when` + `on_finish` in state blocks** can auto-execute scripted_gui effects. This is the pattern for extracting GUI-only data (like `GetConstructionGoodsExpenses`) into game variables.

14. **A JE widget with `is_shown_when_inactive` renders for countries whose entry never activated.** The first in-game test of the UN chamber produced ~1,000 "Failed to fetch variable" errors this way: every display scripted GUI ran in the scope of countries that had none of the system's variables. Guard every `var:` read in display script (`var:X ?= { … }`, `has_variable`), and gate the widget's *root* with `visible = "[JournalEntry.IsActive]"` when its content is meaningless without an active entry. Vanilla uses the same test at `gui/journal_entry.gui:670`. The gate also stops the per-frame `ExecuteTooltip` re-render for countries that will never look at the panel.

15. **There is no verified way to list countries in a JE widget.** Vanilla ships exactly one `GetList` datamodel (`gui/journal_entry_widgets/ep2_japan_widgets.gui:527`, `JournalEntry.GetCountry.MakeScope.GetList('daimyos_list')`), its items are `Scope`s read through `Scope.GetCharacter`, and `Scope.GetCountry` — which `data_types_script.txt:774` does define — appears in **no** vanilla `.gui` file at all. Given gotcha #11, assume the country chain is the broken one until someone proves otherwise in-game. `ordered_country` with a script-value `position` (the "cycle through candidates" alternative) has no vanilla precedent either; every vanilla `position` is a literal. Until one of those is confirmed, a widget that needs to name a country should pick it **in script** and preview the pick, which is what the UN chamber's proposal rows do.

16. **`IsValidTooltip` and `ExecuteTooltip` compose with `Concatenate`.** `tooltip = "[Concatenate( ScriptedGui.IsValidTooltip( <gui scope> ), ScriptedGui.ExecuteTooltip( <gui scope> ) )]"` gives one tooltip carrying both *why the control is greyed out* (the `is_valid` custom_tooltip clauses, with ticks and crosses) and *what pressing it would do* (the effect, rendered without running). In-repo: `gui/journal_entry_widgets/banking_dashboard_widget.gui:69` and every vote / propose control in `un_chamber_widget.gui`. Loc values can reference the inherited `ScriptedGui` datacontext the same way (`st_res_policy_*_tooltip` in `te_miscellaneous_l_english.yml`), so the composed tooltip can live in either place. Note that `ExecuteTooltip` does **not** consult `is_shown`: it renders the effect regardless, so a "nothing to show here" case has to be an `if` inside the effect, not a gate beside it.

17. **Two `visible` properties on one widget is a bug, not a conjunction.** When a type instance needs to combine its own condition with one coming from a `blockoverride`, write a single `visible = "[And( A, B )]"` (vanilla: `gui/journal_entry.gui:670`). Multiple `onclick` lines on one button, by contrast, *are* ordinary vanilla and all run (`gui/panel_military.gui:715`, `gui/market_panel.gui:553`) — which is how an arm/confirm pair executes a scripted GUI and clears its `GetVariableSystem` flag in one click.

18. **Script-built tooltip text prints a scope's own lines before its nested blocks' lines.** Confirmed in-game: in an `ExecuteTooltip` block, every `custom_tooltip` at the current scope renders first, then everything produced inside nested country-scope iterations (`every_in_list` over a country list, `every_country`, …). A "header, list, header, list" structure therefore renders as both headers on top and one undivided list below. Never put a header above a script-built country list: make each entry say which group it belongs to (`#G In favour#! — X` / `#R Opposed#! — X`), and where the structure really matters, use real GUI rows — one widget and one `ExecuteTooltip` call each — instead of one script-built block.

19. **The engine already prefixes a country-scope tooltip line with that country's flag.** A `custom_tooltip` printed inside a country scope change gets a bullet and a flag for free, so adding `GetFlagTextIcon` inside that entry shows the flag twice. Lines printed at the *current* scope that merely reference a country through a saved scope (`SCOPE.sCountry('x')…`) get no automatic flag and still need the explicit one.

20. **`JournalEntry.GetCountry.GetCustom('x')` works in JE widget loc** — confirmed in-game, alongside `.MakeScope.ScriptValue('x')` and `.MakeScope.Var('x')`.

21. **A `scripted_progress_bar` already ships a full per-term breakdown tooltip — reuse it instead of mirroring the formula.** `gui/journal_entry.gui:260/281/303/…` renders every scripted bar with `tooltip = "[ScriptedProgressBar.GetPeriodicProgressBreakdown]"`, which the engine builds from the `desc =` key on each `add` in the bar's `weekly_progress` / `monthly_progress` / `yearly_progress` block. So a bar whose terms all carry a `desc` is *already* explaining itself to the player, and a widget can render the identical string — it cannot drift from the mechanic, because it is the mechanic. A JE widget reaches it the way vanilla does, through the entry's own datamodel:
    ```
    flowcontainer = {
        datamodel = "[JournalEntry.GetScriptedProgressBars]"
        item = {
            textbox = {
                text = "je_x_bar_headline"    # [JournalEntry.GetCurrentBarProgress(ScriptedProgressBar.Self)|%0]
                tooltip = "[ScriptedProgressBar.GetPeriodicProgressBreakdown]"
            }
        }
    }
    ```
    `GetCurrentBarProgress` returns a **normalised 0–1 fraction**, not the bar's own units, so render it as a percentage (`|%0`) rather than trying to scale it — scaling would mean hard-coding the bar's `min_value`/`max_value` in the `.gui`. Keep the whole thing in one self-contained container: this chain is new to the mod (`colonial_empire_widget.gui` is the first user) and **not yet confirmed in-game**, so the fallback should be deleting one block. Note the complement: `scripted_bar_progress` is a trigger with no script-value form, so *script* cannot read the bar as a number — anything numeric the widget or a chart needs has to come from a script value the bar also consumes.

---

## Patterns from Workshop Mods

### Pattern: Construction Spending Slider (PSC / FMC)

Uses scripted_guis with click_modifiers for +/- buttons, game variables for state, and an invisible widget with `state { trigger_when }` to extract GUI-only economic data into game variables.

### Pattern: One scripted GUI, several buttons (`AddScope` parameterization)

When a row of related buttons differs only by *which* action it takes, don't write one scripted GUI per button. Write one per row-entity and pass the action in as a saved scope holding a plain number:

```gui
# in the row's type — datacontext comes from the row instance,
# so this markup is identical for every row
button_icon_minus_action = {
    visible = "[ScriptedGui.IsShown( GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'dir', MakeScopeValue( '(CFixedPoint)0' ) ).End )]"
    enabled = "[ScriptedGui.IsValid(  GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'dir', MakeScopeValue( '(CFixedPoint)0' ) ).End )]"
    onclick = "[ScriptedGui.Execute(  GuiScope.SetRoot( JournalEntry.GetCountry.MakeScope ).AddScope( 'dir', MakeScopeValue( '(CFixedPoint)0' ) ).End )]"
}
```

```txt
my_sgui = {
    scope = country
    saved_scopes = { dir }
    is_valid = {
        trigger_if   = { limit = { scope:dir = 0 } <triggers for action 0> }
        trigger_else = { <triggers for the other action> }
    }
    effect = { if = { limit = { scope:dir = 0 } … } else = { … } }
}
```

Notes learned building the Strategic Reserve inventory widget:
- Set the `ScriptedGui` **datacontext on the row instance**, not on each button. The buttons inherit it, so the three control buttons can live in the shared row *type* with zero per-row markup.
- Use non-negative integers for the selector (`0/1/2`). A `'(CFixedPoint)-1'` literal is untested here; there is no vanilla precedent for a negative one.
- The mapping is an implicit contract between the `.gui` and the script. Document it in *both* file headers.
- Variable *names* can't be built from a scope (`set_variable = { name = st_res_$scope:good$_rate }` is not a thing), so a saved scope can select a branch but cannot replace per-entity script. One scripted GUI per entity with the action as the saved scope is usually the right split.
- Phrase `custom_tooltip` text inside `is_valid` as a **condition** ("Stays within the weekly cap"), not a complaint ("Cannot change rate"): `ScriptedGui.IsValidTooltip` renders it with a tick when valid and a cross when not, and a negative phrasing reads wrong in the valid case.

Notes learned adding the reserve-policy panel to the same widget:
- **One saved scope, wider op codes, beats two chained `AddScope`s.** `TopScope.AddScope` returns `TopScope`, so chaining type-checks, but no vanilla `.gui` chains it and `.gui` errors only surface in-game. A single `op` integer that encodes both the action and which setting it acts on (`0-3` select, `10-12` preset, `20-31` six +/- steppers) keeps the exact shape vanilla demonstrates while backing 20 controls from one scripted GUI.
- **A shared control panel needs only its datacontext overridden per entity.** Put the whole panel in one `type`, give it a `block` that the instance fills with `datacontext = "[GetScriptedGui('..._<entity>_sgui')]"`, and every button inside can then address the action by op code alone. In the Strategic Reserve that turned a would-be ~900-line per-good GUI into one ~270-line type plus ~20 lines per row.
- **Both composition steps vanilla actually uses are safe**, and they are what make that work: a `type` may instance another `type` and supply `blockoverride`s for it (1055 sites in vanilla), and a `blockoverride` body may itself declare a new `block` for the *instance* to fill (296 sites). That second one is how a shared stepper template can still show a per-entity value.
- **`text` accepts an inline data function**, not just a loc key — `text = "[Country.GetRank|v]"` is vanilla (`diplomatic_overview.gui`). For a value cell that only ever shows one variable, inlining `[JournalEntry.GetCountry.MakeScope.Var('x').GetValue|+0]` in the `.gui` avoids a loc key per entity per setting. Keep units in the (shared) label instead, so the value cell needs no literal `%` or `@money!` escaping.
- **Expanders are presentation-only state, and should stay that way.** `GetVariableSystem.Toggle('key_<entity>')` / `.Exists(...)` (vanilla: `states_panel.gui`, and already used in this mod's `building_details_panel.gui`) is per-client, unsaved, and invisible to script. That is the right property: collapsing a settings panel must not change what the system does, and the system must keep running with the panel — and the whole journal entry — closed.
- **`is_valid` doubles as a "you are here" indicator.** For a selector, making the *currently active* option invalid greys it out for free, with a tooltip that says why, and saves a whole parallel highlight path.
- **Verify every template name against `gui/shared/`, not `gui/frontend/`.** `window_component_library.gui` says outright that `button_standard`, `button_primary` and friends are CK3 names kept only for the frontend. The in-game text-button idiom is a plain `button` with `using = default_button_action` (see `scripted_journal_entry_button` in `journal_entry.gui`).


### Pattern: Dynamic Tooltip Lists (DAUI)

Uses `ExecuteTooltip` in localization to generate ordered lists:
```yml
tooltip_key:0 "[GetScriptedGui('my_list').ExecuteTooltip(GuiScope.SetRoot(Country.MakeScope).End)]"
```
With the scripted_gui using `ordered_country { custom_tooltip = "LINE_ENTRY" }`.

### Pattern: Tab System (Statistics Mod)

Full standalone panel with sidebar tabs using `GetVariableSystem`:
- Toggle-based tab switching
- Multiple content areas, each gated by `visible = "[GetVariableSystem.Exists('tab_X')]"`
- Clear other tabs on each tab click

### Pattern: Vanilla Panel Extension (GDP Plotline)

Overrides vanilla tooltip widget to append graph content using `blockoverride "tooltip_content_after"`.

### Pattern: Confirmation Dialogs

Scripted GUIs support `confirm_title` and `confirm_text` for confirmation windows before executing dangerous effects:
```
my_dangerous_sgui = {
    scope = country
    confirm_title = { ... }
    confirm_text = { ... }
    effect = { ... }
}
```

---

## This Mod's GUI Files

Currently 21 GUI files at the top of `gui/`: 19 full-file replacements of vanilla panels plus 2 additive files (marked below):

| File | Vanilla Panel | Purpose of Override |
|---|---|---|
| `building_browser_panel.gui` | Building browser | Custom building display |
| `building_details_panel.gui` | Building details | Enhanced building info |
| `construction_panel.gui` | Construction queue | Public/private construction slider |
| `goods_state_panel.gui` | Goods by state | Modified goods display |
| `market_panel.gui` | Market panel | Widened panel; Top Trade Partners table and import/export partner charts |
| `military_formation_panel.gui` | Military formation | Custom military info |
| `panel_military.gui` | Military overview | Modified military overview |
| `politics_panel_institutions.gui` | Institutions tab | Custom institution display |
| `politics_panel_overview.gui` | Politics overview | Modified politics |
| `power_bloc_formation_panel.gui` | Power bloc creation | Custom formation |
| `power_bloc_panel.gui` | Power bloc details | Enhanced bloc info |
| `principle_selection_window.gui` | Principle selection | Modified selection |
| `production_methods.gui` | PM display | Enhanced PM display |
| `right_click_menu.gui` | Right-click menu | Additional menu options |
| `states_panel.gui` | States list | Modified state display |
| `states_panel_buildings.gui` | State buildings tab | Enhanced building display |
| `te_trade_partner_tooltips.gui` | (additive) | Per-partner goods-breakdown tooltip used by `market_panel.gui` |
| `tooltip.gui` | Tooltip widget | Custom tooltip content |
| `treaty_draft_panel.gui` | Treaty drafting | Custom treaty interface |
| `treaty_panel.gui` | Treaty view | Enhanced treaty display |
| `zzz_extra_goods_texticons.gui` | (additive) | Custom goods text icons |

Scripted GUIs (`common/scripted_guis/`): `te_construction_market_scripted_gui.txt` — public/private construction ratio slider with +/- buttons and shift/ctrl/alt click modifiers. `st_res_scripted_gui.txt` — one `op`-parameterized handler per Strategic Reserve good. `banking_dashboard_scripted_gui.txt` — the banking policy dashboard's handlers. `un_chamber_sguis.txt` — the UN chamber's tooltip builders (called only through `ExecuteTooltip`) plus its vote/propose handlers. `te_history_scripted_gui.txt` — the history charts' marker tooltip.

Journal-entry widgets are **additive**, not overrides: a `.gui` under `gui/journal_entry_widgets/` is attached to a JE with a `widget = { gui = "..." name = "..." container = "custom_widget_container_N" }` block and renders inside vanilla's `journal_entry.gui` slots, so it costs no panel replacement. `custom_widget_container_1` sits above the status description, `_2` between the status description and the scripted-button grid, `_3` below the button grid; `_4`–`_7` are further down the panel. Keep content within `@panel_width_minus_20` (520 px) — the existing widgets use a 480 px text column plus a `margin = { 20 8 }`. The current widgets (add a row here when a journal entry gains one):

| File | Journal entry | Purpose |
|---|---|---|
| `covert_operations_widget.gui` | `je_covert_warfare` | one row per running operation (script-container datamodel) |
| `strategic_reserve_widget.gui` | `je_strategic_reserve` | per-good reserve readouts |
| `banking_dashboard_widget.gui` | `je_banking_cycle` | conditions readout + policy dashboard |
| `banking_history_widget.gui` | `je_banking_cycle` | the three banking history charts |
| `un_chamber_widget.gui` | `je_united_nations` | General Assembly chamber: standing, open resolutions, vote and propose controls |
| `te_history_chart.gui` | (type library) | reusable `te_history_chart` column-chart types, usable from any JE widget |

## GUI 3-way merge across vanilla patches

When a vanilla patch updates a GUI file the mod overrides, hand-merging is rarely needed — `git merge-file` resolves most cases automatically. The pattern:

```bash
# Stage vanilla's pre-patch and post-patch versions
git -C ~/src/vic3 show <OLD_REF>:game/gui/<file> > /tmp/<file>.old
git -C ~/src/vic3 show <NEW_REF>:game/gui/<file> > /tmp/<file>.new

# Take the mod's current (pre-patch-based) override as the work copy
cp gui/<file> /tmp/<file>.work

# 3-way merge: base = vanilla pre-patch, ours = mod, theirs = vanilla post-patch
git merge-file -p /tmp/<file>.work /tmp/<file>.old /tmp/<file>.new > /tmp/<file>.merged

# Exit code 0 = clean merge, copy to mod; non-zero = N conflicts to resolve
echo "Conflicts: $(grep -c '<<<<<<<' /tmp/<file>.merged)"
```

For the 1.13 migration this resolved 14 of 17 GUI overrides cleanly; the giants (`right_click_menu.gui` 4845-line vanilla diff, `military_formation_panel.gui` 5012-line) had only 0 and 4 conflicts respectively.

**Resolving conflicts:**
- Conflicts cluster at indentation/nesting boundaries when vanilla restructured a panel. The mod's intent (the "<<<<<<< work" side) usually goes inside the vanilla post-patch wrapper.
- For a textbox/widget that was *moved* by vanilla, take vanilla's new position and keep mod-added attributes.
- For a section vanilla *deleted entirely* (e.g. `commander_panel.gui` was deleted in 1.13), delete the mod's override; the panel content typically moved into another file (in that case, into `military_formation_panel.gui`).

**When auto-merge produces visually-broken output**: the mod may have customized a structure vanilla heavily restructured (e.g. mod's `production_methods.gui` wrapped a `fixedgridbox` in a `scrollarea` that broke when vanilla resized parents in 1.13). Take vanilla post-patch as the new baseline and re-apply only the mod's *intent* (e.g. a 3-line `visible = "[Not(EqualTo_string(ProductionMethodGroup.GetKey, 'pmg_maintenance'))]"` filter rather than a 90-line `scrollarea` wrapper). Faster and less brittle than hand-resolving deep nesting conflicts.

**Bulk-running** for all overridden files at once:

```bash
mkdir -p /tmp/gui_merge
for f in gui/*.gui; do
    name=$(basename "$f")
    git -C ~/src/vic3 show "<OLD_REF>:game/gui/$name" > "/tmp/gui_merge/$name.old" 2>/dev/null || continue
    git -C ~/src/vic3 show "<NEW_REF>:game/gui/$name" > "/tmp/gui_merge/$name.new" 2>/dev/null || continue
    cp "$f" "/tmp/gui_merge/$name.work"
    git merge-file -p "/tmp/gui_merge/$name.work" "/tmp/gui_merge/$name.old" "/tmp/gui_merge/$name.new" \
        > "/tmp/gui_merge/$name.merged" 2>/dev/null
    ec=$?
    conflicts=$(grep -c '<<<<<<<' "/tmp/gui_merge/$name.merged" 2>/dev/null || echo 0)
    printf '%-40s exit=%d conflicts=%d\n' "$name" "$ec" "$conflicts"
done
```
