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

6. **No `AddScope` in V3.** Only `GuiScope.SetRoot(object.MakeScope).End` is available. The `AddScope` pattern seen in some workshop mods appears to be from V3 updates or CK3 crossover — vanilla V3 uses only `SetRoot`.

7. **`@variables` are compile-time constants.** `@my_width = 400` is resolved at load time, not runtime. Use data binding for dynamic values.

8. **`datacontext` sets the implicit type for child expressions.** When you write `datacontext = "[GetPlayer.Self]"`, children can use `Country.GetName` directly. Change the datacontext and all child expressions must match the new type.

9. **Literal constant syntax:** Use `'(CFixedPoint)0'`, `'(int32)5'`, `'(float)1.0'` when functions need typed literals.

10. **JournalEntry scope:** `JournalEntry.GetCountry` returns the owning country. In JE context, `ROOT.GetCountry.MakeScope.ScriptValue('x')` is the pattern.

11. **`Var().GetCountry.GetName` does NOT work** for country variables. Store the country's capital instead and chain `Var('cap').GetState.GetCountry.GetName`.

12. **Map markers/HUD overlays cannot be added.** The HUD is engine-level. Mods can override existing HUD files but cannot add new map layers or HUD elements.

13. **`trigger_when` + `on_finish` in state blocks** can auto-execute scripted_gui effects. This is the pattern for extracting GUI-only data (like `GetConstructionGoodsExpenses`) into game variables.

---

## Patterns from Workshop Mods

### Pattern: Construction Spending Slider (PSC / FMC)

Uses scripted_guis with click_modifiers for +/- buttons, game variables for state, and an invisible widget with `state { trigger_when }` to extract GUI-only economic data into game variables.

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

Currently 20 GUI files, all full-file replacements of vanilla panels:

| File | Vanilla Panel | Purpose of Override |
|---|---|---|
| `building_browser_panel.gui` | Building browser | Custom building display |
| `building_details_panel.gui` | Building details | Enhanced building info |
| `commander_panel.gui` | Commander details | Modified commander display |
| `construction_panel.gui` | Construction queue | Public/private construction slider |
| `goods_state_panel.gui` | Goods by state | Modified goods display |
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
| `tooltip.gui` | Tooltip widget | Custom tooltip content |
| `treaty_draft_panel.gui` | Treaty drafting | Custom treaty interface |
| `treaty_panel.gui` | Treaty view | Enhanced treaty display |
| `zzz_extra_goods_texticons.gui` | (additive) | Custom goods text icons |

Scripted GUIs: `fmc_construction_scripted_gui.txt` — public/private construction ratio slider with +/- buttons and shift/ctrl/alt click modifiers.

## GUI 3-way merge across vanilla patches

When a vanilla patch updates a GUI file the mod overrides, hand-merging is rarely needed — `git merge-file` resolves most cases automatically. The pattern:

```bash
# Stage vanilla's pre-patch and post-patch versions
git -C /home/jakef/src/vic3 show <OLD_REF>:game/gui/<file> > /tmp/<file>.old
git -C /home/jakef/src/vic3 show <NEW_REF>:game/gui/<file> > /tmp/<file>.new

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
    git -C /home/jakef/src/vic3 show "<OLD_REF>:game/gui/$name" > "/tmp/gui_merge/$name.old" 2>/dev/null || continue
    git -C /home/jakef/src/vic3 show "<NEW_REF>:game/gui/$name" > "/tmp/gui_merge/$name.new" 2>/dev/null || continue
    cp "$f" "/tmp/gui_merge/$name.work"
    git merge-file -p "/tmp/gui_merge/$name.work" "/tmp/gui_merge/$name.old" "/tmp/gui_merge/$name.new" \
        > "/tmp/gui_merge/$name.merged" 2>/dev/null
    ec=$?
    conflicts=$(grep -c '<<<<<<<' "/tmp/gui_merge/$name.merged" 2>/dev/null || echo 0)
    printf '%-40s exit=%d conflicts=%d\n' "$name" "$ec" "$conflicts"
done
```
