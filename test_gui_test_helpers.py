"""gui_test_helpers.assert_wide_matches_narrow, on made-up markup (spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.5).

A wide composer must place exactly the narrow layout's sections, in their
order read down each column and then across (or, with columns=, in the columns
the owner set), on te_ui_columns_three or te_ui_columns_two, each under exactly
the gates the narrow layout gives it.
The real calls are in each system's layout test (test_demographics_layout.py
for the Census Data window). Each failing case names the message it expects,
so a case can't pass on some other failure.
"""
import os
import tempfile
import unittest

from gui_test_helpers import (ScriptedGuis, _children, assert_wide_matches_narrow, loc_closure, loc_keys_of,
                              own_branch_spans, printed_keys, scripted_guis, scripted_keys, tooltip_calls)

NARROW = """
types fixture {
	type te_x_status_sections = flowcontainer {
		direction = vertical
		spacing = 4
		visible = "[JournalEntry.IsActive]"

		te_x_sec_a = {}
		# te_x_sec_commented = {}
		flowcontainer = {
			spacing = 4
			visible = "[Not( IsLight )]"
			te_x_sec_b = {}
			block "summary" {
				te_x_summary = {}
			}
		}
		te_x_sec_c = {
			visible = "[HasC]"
		}
	}

	type te_x_reference_sections = flowcontainer {
		te_x_sec_how = {}
	}

	# a section with a visible of its own, which an instance's would replace (gotcha #17)
	type te_x_sec_gated = flowcontainer {
		visible = "[OwnGate]"
	}
}
"""
NARROW_TYPES = ["te_x_overview", "te_x_status_sections", "te_x_reference_sections"]


# What every wrapper in a wide layout carries (the D PRs' wrappers): vertical, hidden sections taking no space, and its
# narrow composer's spacing. fixture() adds it to each multi-line wrapper, so the cases below stay short.
WRAPPER = "direction = vertical parentanchor = hcenter ignoreinvisible = yes spacing = 4"


def fixture(wide, wrapper=WRAPPER):
    wide = wide.replace("flowcontainer = {\n", f"flowcontainer = {{ {wrapper}\n")
    return NARROW + "\ntypes wide {\n" + wide + "\n}\n"


# The sections in the narrow order, each under exactly its narrow gates: IsActive (the status composer's root) on
# wrappers, Not( IsLight ) on a wrapper, HasC on the instance; the overview and How under none.
GOOD = """
	type te_x_wide_sections = te_ui_columns_three {
		blockoverride "column_1" {
			te_x_overview = {}
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_a = {}
			}
		}
		blockoverride "column_2" {
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				flowcontainer = {
					visible = "[Not( IsLight )]"
					te_x_sec_b = {}
					te_x_summary = {}
				}
			}
		}
		blockoverride "column_3" {
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_c = { visible = "[HasC]" }
			}
			te_x_sec_how = {}
		}
	}
"""
COLUMNS = [["te_x_overview", "te_x_sec_a"], ["te_x_sec_b", "te_x_summary"], ["te_x_sec_c", "te_x_sec_how"]]


class WideMatchesNarrowTest(unittest.TestCase):
    def check(self, wide, wrapper=WRAPPER, **kw):
        return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES, text=fixture(wide, wrapper), **kw)

    def fails(self, message, wide, **kw):
        with self.assertRaisesRegex(AssertionError, message):
            self.check(wide, **kw)

    def test_a_matching_layout_passes_and_returns_its_columns(self):
        self.assertEqual(self.check(GOOD), COLUMNS)

    def test_a_section_left_out(self):
        self.fails("the narrow layout's sections", GOOD.replace("te_x_sec_how = {}", ""))

    def test_a_section_out_of_order(self):
        self.fails("the narrow layout's sections",
                   GOOD.replace("te_x_sec_b = {}\n\t\t\t\t\tte_x_summary = {}", "te_x_summary = {}\n\t\t\t\t\tte_x_sec_b = {}"))

    def test_the_columns_are_read_by_number_not_by_where_they_are_written(self):
        moved = GOOD.replace('blockoverride "column_1"', 'blockoverride "column_tmp"')
        moved = moved.replace('blockoverride "column_3"', 'blockoverride "column_1"')
        self.fails("the narrow layout's sections", moved.replace('blockoverride "column_tmp"', 'blockoverride "column_3"'))

    # columns= (owner, 2026-11-03): a layout balanced by hand may read in another order than the narrow one, but must
    # place each narrow section once, under the same gates, in exactly the columns named.
    REORDERED = GOOD.replace("\t\t\tte_x_overview = {}\n", "\t\t\tte_x_sec_how = {}\n", 1).replace(
        "\t\t\tte_x_sec_how = {}\n\t\t}\n\t}", "\t\t\tte_x_overview = {}\n\t\t}\n\t}", 1)
    REORDERED_COLUMNS = [["te_x_sec_how", "te_x_sec_a"], ["te_x_sec_b", "te_x_summary"], ["te_x_sec_c", "te_x_overview"]]

    def test_columns_let_a_layout_leave_the_narrow_order(self):
        self.assertNotEqual(self.REORDERED, GOOD)
        self.fails("the narrow layout's sections", self.REORDERED)
        self.assertEqual(self.check(self.REORDERED, columns=self.REORDERED_COLUMNS), self.REORDERED_COLUMNS)

    def test_columns_must_be_the_layouts(self):
        self.fails("the columns the owner set", self.REORDERED, columns=COLUMNS)

    def test_columns_still_want_every_section_once(self):
        left_out = [["te_x_sec_how", "te_x_sec_a"], ["te_x_sec_b", "te_x_summary"], ["te_x_sec_c"]]
        self.fails("each once, in any order",
                   self.REORDERED.replace("\t\t\tte_x_overview = {}\n", ""), columns=left_out)
        twice = [["te_x_sec_how", "te_x_sec_a"], ["te_x_sec_b", "te_x_summary"],
                 ["te_x_sec_c", "te_x_overview", "te_x_sec_how"]]
        self.fails("each once, in any order",
                   self.REORDERED.replace("\t\t\tte_x_overview = {}\n", "\t\t\tte_x_overview = {}\n"
                                          "\t\t\tte_x_sec_how = {}\n"), columns=twice)

    def test_columns_compare_gates_section_by_section(self):
        self.fails(r"te_x_sec_c shows in the narrow layout only while \['HasC'\]",
                   self.REORDERED.replace('te_x_sec_c = { visible = "[HasC]" }', "te_x_sec_c = {}"),
                   columns=self.REORDERED_COLUMNS)

    def test_a_composers_gate_dropped(self):
        self.fails(r"te_x_sec_a shows in the narrow layout only while \['JournalEntry.IsActive'\]",
                   GOOD.replace('visible = "[JournalEntry.IsActive]"\n\t\t\t\tte_x_sec_a', "te_x_sec_a", 1))

    def test_a_wrappers_gate_dropped(self):
        self.fails(r"te_x_sec_b shows in the narrow layout only while \['Not\(IsLight\)'\]",
                   GOOD.replace('visible = "[Not( IsLight )]"', ""))

    def test_an_instances_gate_dropped(self):
        self.fails(r"te_x_sec_c shows in the narrow layout only while \['HasC'\]",
                   GOOD.replace('te_x_sec_c = { visible = "[HasC]" }', "te_x_sec_c = {}"))

    # A column's own visible (column_<n>_visible, help-button-everywhere PR) closes up a column whose sections all
    # hide, instead of leaving its 520: one more gate on each of its sections, held to the narrow ones.
    COLUMN_2_SHOWN = 'blockoverride "column_2_visible" {\n\t\t\tvisible = "[Not( IsLight )]"\n\t\t}\n\t\tblockoverride "column_2" {'

    def test_a_columns_visible_its_sections_already_carry_passes(self):
        self.assertEqual(self.check(GOOD.replace('blockoverride "column_2" {', self.COLUMN_2_SHOWN)), COLUMNS)

    def test_a_columns_visible_is_a_gate_on_each_of_its_sections(self):
        wide = GOOD.replace('blockoverride "column_2" {', self.COLUMN_2_SHOWN.replace("Not( IsLight )", "Other"))
        self.fails(r"te_x_sec_b shows in the wide layout only while \['Other'\]", wide)
        self.assertEqual(self.check(wide, added_gates=("te_x_sec_b", "te_x_summary")), COLUMNS)

    def test_a_columns_visible_holds_only_its_visible(self):
        self.fails("column_2_visible holds a visible and nothing else",
                   GOOD.replace('blockoverride "column_2" {',
                                self.COLUMN_2_SHOWN.replace('visible = "[Not( IsLight )]"',
                                                            'visible = "[Not( IsLight )]"\n\t\t\tspacing = 4')))

    def test_no_visible_for_a_column_the_type_lacks(self):
        self.fails("te_ui_columns_three has no such column visible",
                   GOOD.replace('blockoverride "column_2" {', self.COLUMN_2_SHOWN.replace("column_2_visible", "column_4_visible")))

    def test_a_gate_may_sit_on_the_columns_instance_or_an_outer_wrapper(self):
        """No overview or How here, so IsActive can gate the whole row."""
        narrow = ["te_x_status_sections"]
        wide = """
	type te_x_wide_sections = flowcontainer {
		flowcontainer = {
			visible = "[JournalEntry.IsActive]"
			te_ui_columns_three = {
				visible = "[Not( IsLight )]"
				blockoverride "column_1" {
					te_x_sec_a = {}
				}
				blockoverride "column_2" {
					te_x_sec_b = {}
					te_x_summary = {}
				}
				blockoverride "column_3" {
					te_x_sec_c = {
						visible = "[HasC]"
					}
				}
			}
		}
	}
"""
        # sec_a and sec_c gain Not( IsLight ): an added gate, named
        assert_wide_matches_narrow(self, "te_x_wide_sections", narrow, text=fixture(wide),
                                   added_gates=("te_x_sec_a", "te_x_sec_c"))

    def test_an_added_gate_fails_unless_named(self):
        """A gate the narrow layout lacks hides the section where the narrow one shows it: every overview draws ungated,
        so a row gated on IsActive would hide it for an inactive entry."""
        gated = GOOD.replace("type te_x_wide_sections = te_ui_columns_three {",
                             'type te_x_wide_sections = te_ui_columns_three {\n\t\tvisible = "[JournalEntry.IsActive]"')
        self.fails(r"te_x_overview shows in the wide layout only while \['JournalEntry.IsActive'\]", gated)
        how = GOOD.replace("te_x_sec_how = {}", 'te_x_sec_how = { visible = "[Pending]" }')
        self.fails(r"te_x_sec_how shows in the wide layout only while \['Pending'\]", how)
        self.check(how, added_gates=("te_x_sec_how",))

    def test_an_added_gate_named_for_a_section_that_has_none(self):
        self.fails(r"added_gates names \['te_x_sec_a'\], which the wide layout gates no further",
                   GOOD, added_gates=("te_x_sec_a",))

    def test_gates_compare_without_their_spacing(self):
        self.check(GOOD.replace('"[Not( IsLight )]"', '"[Not(IsLight)]"').replace(
            'visible = "[HasC]"', 'visible = "[ HasC ]"'))

    def test_an_empty_column(self):
        two = GOOD.replace('\t\t\tflowcontainer = {\n\t\t\t\tvisible = "[JournalEntry.IsActive]"\n\t\t\t\tte_x_sec_c = { visible = "[HasC]" }\n'
                           '\t\t\t}\n\t\t\tte_x_sec_how = {}\n', "")
        two = two.replace("\t\t\t\t\tte_x_summary = {}\n\t\t\t\t}\n\t\t\t}\n",
                          '\t\t\t\t\tte_x_summary = {}\n\t\t\t\t}\n\t\t\t\tte_x_sec_c = { visible = "[HasC]" }\n\t\t\t}\n'
                          '\t\t\tte_x_sec_how = {}\n')
        self.fails("column_3 is empty", two)

    def test_a_column_the_type_lacks(self):
        self.fails("te_ui_columns_two fills column_1 to column_2", GOOD.replace("te_ui_columns_three", "te_ui_columns_two"))

    def test_two_columns(self):
        wide = """
	type te_x_wide_sections = te_ui_columns_two {
		blockoverride "column_1" {
			te_x_overview = {}
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_a = {}
				flowcontainer = {
					visible = "[Not( IsLight )]"
					te_x_sec_b = {}
					te_x_summary = {}
				}
			}
		}
		blockoverride "column_2" {
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_c = { visible = "[HasC]" }
			}
			te_x_sec_how = {}
		}
	}
"""
        self.assertEqual(len(self.check(wide)), 2)

    def test_no_column_type(self):
        self.fails("lays its sections out on te_ui_columns_three or te_ui_columns_two",
                   GOOD.replace("te_ui_columns_three", "flowcontainer").replace('blockoverride "column_', 'block "column_'))

    def test_a_section_outside_the_columns_must_be_named(self):
        """The Census Data window's pending line sits above its columns, by name."""
        wide = GOOD.replace("type te_x_wide_sections = te_ui_columns_three {",
                            "type te_x_wide_sections = flowcontainer {\n\t\tte_x_overview = {}\n\t\tte_ui_columns_three = {")
        wide = wide.replace("\t\t\tte_x_overview = {}\n", "").rstrip() + "\n\t}\n"
        self.fails(r"places \['te_x_overview'\] outside its columns", wide)
        self.assertEqual(self.check(wide, outside=("te_x_overview",))[0], ["te_x_sec_a"])

    def test_columns_keep_an_outside_section_where_it_draws(self):
        """With columns=, the pending line may not move below the columns: it still draws where the narrow layout has
        it, first."""
        above = GOOD.replace("type te_x_wide_sections = te_ui_columns_three {",
                             "type te_x_wide_sections = flowcontainer {\n\t\tte_x_overview = {}\n\t\tte_ui_columns_three = {")
        above = above.replace("\t\t\tte_x_overview = {}\n", "").rstrip() + "\n\t}\n"
        columns = [["te_x_sec_a"], ["te_x_sec_b", "te_x_summary"], ["te_x_sec_c", "te_x_sec_how"]]
        self.assertEqual(self.check(above, outside=("te_x_overview",), columns=columns), columns)
        below = above.replace("\n\t\tte_x_overview = {}\n\t\tte_ui_columns_three = {", "\n\t\tte_ui_columns_three = {")
        below = below.rstrip()[:-1].rstrip() + "\n\t\tte_x_overview = {}\n\t}\n"
        self.fails("draws outside the columns at another place", below, outside=("te_x_overview",), columns=columns)

    def test_an_outside_the_layout_no_longer_has(self):
        self.fails(r"outside names \['te_x_gone'\], which it doesn't place outside its columns", GOOD, outside=("te_x_gone",))

    def test_extra_skips_a_wide_only_instance(self):
        wide = GOOD.replace("te_x_sec_how = {}", "te_x_sec_how = {}\n\t\t\tte_x_divider = {}")
        self.fails("the narrow layout's sections", wide)
        self.check(wide, extra=("te_x_divider",))

    def test_an_extra_the_layout_no_longer_has(self):
        self.fails(r"extra names \['te_x_divider'\]", GOOD, extra=("te_x_divider",))

    # The Space Race's solar colonization tabs (owner, 2026-11-05): a part the
    # narrow layout draws inside one section (te_x_sec_b here), in a column of
    # its own full screen.
    SPLIT = """
	type te_x_wide_sections = te_ui_columns_three {
		blockoverride "column_1" {
			te_x_overview = {}
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_a = {}
				flowcontainer = {
					visible = "[Not( IsLight )]"
					te_x_sec_b = {}
					te_x_summary = {}
				}
			}
		}
		blockoverride "column_2_visible" {
			visible = "[And( JournalEntry.IsActive, Not( IsLight ) )]"
		}
		blockoverride "column_2" {
			te_x_part = {}
		}
		blockoverride "column_3" {
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_c = { visible = "[HasC]" }
			}
			te_x_sec_how = {}
		}
	}
"""
    SPLIT_COLUMNS = [["te_x_overview", "te_x_sec_a", "te_x_sec_b", "te_x_summary"], ["te_x_part"],
                     ["te_x_sec_c", "te_x_sec_how"]]

    def test_split_gives_a_part_a_column_of_its_own(self):
        self.fails("the narrow layout's sections", self.SPLIT)
        self.fails("column_2 is empty", self.SPLIT, extra=("te_x_part",))
        self.assertEqual(self.check(self.SPLIT, split={"te_x_part": "te_x_sec_b"}), self.SPLIT_COLUMNS)
        self.assertEqual(self.check(self.SPLIT, split={"te_x_part": "te_x_sec_b"}, columns=self.SPLIT_COLUMNS),
                         self.SPLIT_COLUMNS)

    def test_a_split_part_keeps_its_sections_gates(self):
        """It may carry more (te_x_sec_b has no HasC), but not fewer."""
        more = self.SPLIT.replace("[And( JournalEntry.IsActive, Not( IsLight ) )]",
                                  "[And( JournalEntry.IsActive, And( Not( IsLight ), HasC ) )]")
        self.check(more, split={"te_x_part": "te_x_sec_b"})
        fewer = self.SPLIT.replace("[And( JournalEntry.IsActive, Not( IsLight ) )]", "[JournalEntry.IsActive]")
        self.fails(r"te_x_part shows in the narrow layout, inside te_x_sec_b, only while \['Not\(IsLight\)'\]",
                   fewer, split={"te_x_part": "te_x_sec_b"})

    def test_a_split_the_layout_no_longer_has(self):
        self.fails("split names te_x_gone, which it doesn't place", GOOD, split={"te_x_gone": "te_x_sec_b"})
        self.fails("split out of te_x_nowhere, which the narrow layout doesn't place", self.SPLIT,
                   split={"te_x_part": "te_x_nowhere"})
        self.fails("split names te_x_sec_a, which the narrow layout places", GOOD, split={"te_x_sec_a": "te_x_sec_b"})

    def test_composers_names_what_expands(self):
        """By default a type named *_sections is a composer, on either side; others are sections."""
        self.fails("the narrow layout's sections", GOOD, composers=("te_x_status_sections",))
        wide = GOOD.replace("te_x_sec_how = {}", "te_x_reference_sections = {}")
        self.check(wide)
        self.check(wide, composers=("te_x_status_sections",))

    def test_an_and_gate_counts_as_its_two_parts(self):
        """Global Warming's reference sections: And( IsActive, the rule ). A wide layout may put the two parts on
        different wrappers, or keep the And whole."""
        narrow = NARROW.replace('visible = "[Not( IsLight )]"', 'visible = "[And( IsBig, Not( IsLight ) )]"')

        def check(wide):
            return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES,
                                              text=narrow + fixture(wide)[len(NARROW):])

        with self.assertRaisesRegex(AssertionError, r"te_x_sec_b shows in the narrow layout only while \['IsBig'\]"):
            check(GOOD)
        check(GOOD.replace('visible = "[Not( IsLight )]"',
                           'visible = "[Not( IsLight )]"\n\t\t\t\t\tflowcontainer = {\n\t\t\t\t\t\tvisible = "[IsBig]"')
              .replace("te_x_summary = {}\n", "te_x_summary = {}\n\t\t\t\t\t}\n", 1))
        check(GOOD.replace('"[Not( IsLight )]"', '"[And( IsBig, Not( IsLight ) )]"'))

    def test_an_instances_visible_over_its_types_own(self):
        """An instance's visible replaces its type's (gotcha #17): the section would draw where its own gate hides it."""
        narrow = NARROW_TYPES + ["te_x_sec_gated"]
        wide = GOOD.replace("te_x_sec_how = {}", 'te_x_sec_how = {}\n\t\t\tte_x_sec_gated = { visible = "[Other]" }')
        with self.assertRaisesRegex(AssertionError, "te_x_sec_gated's visible replaces its type's own"):
            assert_wide_matches_narrow(self, "te_x_wide_sections", narrow, text=fixture(wide))
        wide = GOOD.replace("te_x_sec_how = {}",
                            "te_x_sec_how = {}\n\t\t\tte_x_status_sections = {\n\t\t\t\tvisible = \"[Pending]\"\n\t\t\t}")
        with self.assertRaisesRegex(AssertionError, "te_x_status_sections's visible replaces its type's own"):
            assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES + ["te_x_status_sections"],
                                       text=fixture(wide))

    def test_a_widget_that_is_not_a_wrapper_or_a_section(self):
        """A heading drawn inline (the UN's status block) would go unchecked: it must be a te_* section."""
        self.fails(r"draws textbox inline", GOOD.replace("te_x_sec_how = {}", 'te_x_sec_how = {}\n\t\t\ttextbox = { text = "x" }'))
        self.fails(r"draws divider_clean inline", GOOD.replace("te_x_sec_how = {}", "te_x_sec_how = {}\n\t\t\tdivider_clean = {}"))
        narrow = NARROW.replace("te_x_sec_how = {}", "te_x_sec_how = {}\n\t\tsection_header = {\n\t\t\tsize = { 1 2 }\n\t\t}")
        with self.assertRaisesRegex(AssertionError, r"the narrow layout draws section_header inline"):
            assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES,
                                       text=narrow + "\ntypes wide {\n" + GOOD + "\n}\n")

    def test_a_one_line_wrapper_is_walked(self):
        wide = GOOD.replace('flowcontainer = {\n\t\t\t\tvisible = "[JournalEntry.IsActive]"\n\t\t\t\tte_x_sec_a = {}\n\t\t\t}',
                            f'flowcontainer = {{ {WRAPPER} visible = "[JournalEntry.IsActive]" te_x_sec_a = {{}} }}')
        self.assertEqual(self.check(wide), COLUMNS)

    def test_a_wrapper_that_keeps_a_hidden_sections_space(self):
        """Without ignoreinvisible, a hidden section still takes its place and the spacing around it."""
        self.fails("without ignoreinvisible = yes keeps a hidden section's space", GOOD,
                   wrapper="direction = vertical parentanchor = hcenter spacing = 4")

    def test_a_wrapper_that_runs_across(self):
        """A flowcontainer runs horizontally by default; in a 520 column its sections would sit side by side."""
        self.fails("a flowcontainer wrapper runs vertically", GOOD,
                   wrapper="parentanchor = hcenter ignoreinvisible = yes spacing = 4")

    def test_a_wrapper_with_a_context_or_a_margin_of_its_own(self):
        """A wide wrapper only gates and spaces its sections: a datacontext changes what they read, a margin where
        they sit."""
        self.fails(r"a wrapper carries \['datacontext'\]", GOOD,
                   wrapper=WRAPPER + ' datacontext = "[GetPlayer]"')
        self.fails(r"a wrapper carries \['margin_left'\]", GOOD, wrapper=WRAPPER + " margin_left = 200")

    def test_a_wrapper_that_is_not_a_flowcontainer(self):
        """An hbox sets its sections side by side in the 520 column, a widget or a container draws them over each
        other, and the column, a flowcontainer, can't hold a vbox (#1338). The narrow side may use any: its wrappers
        are what the game already draws."""
        opener = 'flowcontainer = {\n\t\t\t\tvisible = "[JournalEntry.IsActive]"\n\t\t\t\tte_x_sec_a = {}'
        self.assertEqual(GOOD.count(opener), 1)
        for kind in ("hbox", "widget", "container", "vbox"):
            with self.subTest(kind=kind):
                self.fails(f"wraps sections in `{kind}`", GOOD.replace(opener, opener.replace(
                    "flowcontainer = {\n", f"{kind} = {{ {WRAPPER}\n")))
        narrow = NARROW.replace("flowcontainer = {\n\t\t\tspacing = 4", "widget = {\n\t\t\tspacing = 4")
        self.assertNotEqual(narrow, NARROW)
        self.assertEqual(assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES,
                                                    text=narrow + fixture(GOOD)[len(NARROW):]), COLUMNS)

    def test_a_wrappers_size_limit_is_its_columns(self):
        """{ 900 -1 } would run out of its 520 column (#1338); the one real use is { 520 -1 }."""
        for limit in ("minimumsize", "maximumsize"):
            with self.subTest(limit=limit):
                self.fails(rf"a wrapper's {limit} is {{ 900 -1 }}", GOOD, wrapper=f"{WRAPPER} {limit} = {{ 900 -1 }}")
                self.fails(rf"a wrapper's {limit} is {{ 520 40 }}", GOOD, wrapper=f"{WRAPPER} {limit} = {{ 520 40 }}")
                self.assertEqual(self.check(GOOD, wrapper=f"{WRAPPER} {limit} = {{ 520 -1 }}"), COLUMNS)

    # The spacing rule (#1338): a wrapper's spacing draws between the sections it holds, so one that holds two or more
    # directly spaces them as the widget that holds them in the narrow layout does.
    BARE = "direction = vertical parentanchor = hcenter ignoreinvisible = yes"

    def test_a_wrappers_spacing_against_its_sections_narrow_one(self):
        """te_x_sec_b and te_x_summary sit 4 apart in the narrow layout, in its inner wrapper."""
        self.fails(r"the wrapper around \['te_x_sec_b', 'te_x_summary'\] spaces its sections 30 apart, "
                   r"the narrow layout \['4'\]", GOOD, wrapper=f"{self.BARE} spacing = 30")
        self.fails(r"the wrapper around \['te_x_sec_b', 'te_x_summary'\] spaces its sections None apart", GOOD,
                   wrapper=self.BARE)

    # te_x_sec_a and te_x_sec_c directly in one wrapper, with the wrapper around te_x_sec_b and te_x_summary between
    # them; te_x_sec_z from a second narrow composer under the same gate, which sets no spacing.
    MORE = """
	type te_x_more_sections = flowcontainer {
		visible = "[JournalEntry.IsActive]"
		te_x_sec_z = {}
	}
"""
    HELD = """
	type te_x_wide_sections = te_ui_columns_two {
		blockoverride "column_1" {
			te_x_overview = {}
			flowcontainer = { OUTER
				visible = "[JournalEntry.IsActive]"
				te_x_sec_a = {}
				flowcontainer = {
					visible = "[Not( IsLight )]"
					te_x_sec_b = {}
					te_x_summary = {}
				}
				te_x_sec_c = { visible = "[HasC]" }
			}
		}
		blockoverride "column_2" {
			te_x_sec_how = {}
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_z = {}
			}
		}
	}
"""

    def test_spacing_is_matched_by_the_sections_a_wrapper_holds_not_by_its_gates(self):
        """The narrow layout has a second composer under JournalEntry.IsActive that sets no spacing. Matched by gate
        set, that let the wrapper around te_x_sec_a and te_x_sec_c drop its 4 (#1338: the Space Race wrapper around
        Space Powers and Orbit)."""
        def check(outer):
            return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES + ["te_x_more_sections"],
                                              text=fixture(self.HELD.replace("OUTER", outer) + self.MORE))

        self.assertEqual(len(check(WRAPPER)), 2)
        with self.assertRaisesRegex(AssertionError, r"the wrapper around \['te_x_sec_a', 'te_x_sec_c'\] spaces its "
                                                    r"sections None apart, the narrow layout \['4'\]"):
            check(self.BARE)

    def test_a_wrapper_around_one_section_needs_no_spacing(self):
        """Spacing draws between two: a one-section wrapper had to carry a spacing that draws nothing (#1338)."""
        one = 'flowcontainer = {\n\t\t\t\tvisible = "[JournalEntry.IsActive]"\n\t\t\t\tte_x_sec_a = {}'
        self.assertEqual(GOOD.count(one), 1)
        for bare in (self.BARE, f"{self.BARE} spacing = 30"):
            with self.subTest(wrapper=bare):
                self.assertEqual(self.check(GOOD.replace(one, one.replace("flowcontainer = {\n", f"flowcontainer = {{ {bare}\n"))),
                                 COLUMNS)

    def test_a_section_alone_in_a_narrow_wrapper_sits_at_the_spacing_around_it(self):
        """A narrow wrapper around one section draws no spacing: the section sits at the spacing of the next widget
        out that holds two or more. Here te_x_sec_c, alone in a wrapper that only gates it, is 4 from its neighbours,
        the status composer's spacing. (te_x_sec_how, alone in its composer, sits at a spacing the check can't read.)"""
        lone = '\t\tflowcontainer = {\n\t\t\tvisible = "[HasC]"\n\t\t\tte_x_sec_c = {}\n\t\t}\n'
        narrow = NARROW.replace('\t\tte_x_sec_c = {\n\t\t\tvisible = "[HasC]"\n\t\t}\n', lone)
        self.assertNotEqual(narrow, NARROW)
        pair = ('\t\t\tflowcontainer = {\n\t\t\t\tvisible = "[JournalEntry.IsActive]"\n'
                '\t\t\t\tte_x_sec_c = { visible = "[HasC]" }\n\t\t\t}\n\t\t\tte_x_sec_how = {}\n')
        self.assertEqual(GOOD.count(pair), 1)

        def check(spacing):
            wide = GOOD.replace(pair, f"\t\t\tflowcontainer = {{ {self.BARE} spacing = {spacing}\n"
                                      '\t\t\t\tvisible = "[JournalEntry.IsActive]"\n'
                                      '\t\t\t\tte_x_sec_c = { visible = "[HasC]" }\n\t\t\t\tte_x_sec_how = {}\n\t\t\t}\n')
            return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES, added_gates=("te_x_sec_how",),
                                              text=narrow + fixture(wide)[len(NARROW):])

        self.assertEqual(check(4), COLUMNS)
        with self.assertRaisesRegex(AssertionError, r"the wrapper around \['te_x_sec_c', 'te_x_sec_how'\] spaces its "
                                                    r"sections 30 apart, the narrow layout \['4'\]"):
            check(30)

    def test_a_section_alone_in_a_narrow_composer_sits_at_the_spacing_around_it(self):
        """The same through a composer: te_x_q and te_x_r, each the one section of its composer, sit 6 apart, the
        spacing of the composer that holds the two."""
        more = ("\ttype te_x_outer_sections = flowcontainer {\n\t\tspacing = 6\n\t\tte_x_one_sections = {}\n"
                "\t\tte_x_two_sections = {}\n\t}\n"
                "\ttype te_x_one_sections = flowcontainer {\n\t\tspacing = 99\n\t\tte_x_q = {}\n\t}\n"
                "\ttype te_x_two_sections = flowcontainer {\n\t\tte_x_r = {}\n\t}\n")

        def check(spacing):
            wide = GOOD.replace("\t\t\tte_x_sec_how = {}\n",
                                f"\t\t\tte_x_sec_how = {{}}\n\t\t\tflowcontainer = {{ {self.BARE} spacing = {spacing}\n"
                                "\t\t\t\tte_x_q = {}\n\t\t\t\tte_x_r = {}\n\t\t\t}\n")
            return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES + ["te_x_outer_sections"],
                                              text=fixture(wide + more))

        check(6)
        with self.assertRaisesRegex(AssertionError, r"the wrapper around \['te_x_q', 'te_x_r'\] spaces its sections "
                                                    r"30 apart, the narrow layout \['6'\]"):
            check(30)

    def test_a_wrapper_with_no_visible_of_its_own_is_spaced_too(self):
        """Only a gated wrapper used to be held to the narrow spacing (#1338)."""
        pair = "\t\t\t\t\tte_x_sec_b = {}\n\t\t\t\t\tte_x_summary = {}\n"
        self.assertEqual(GOOD.count(pair), 1)

        def ungated(spacing):
            return GOOD.replace(pair, f"\t\t\t\t\tflowcontainer = {{ {self.BARE} spacing = {spacing}\n"
                                      f"\t{pair[:-1].replace(chr(10), chr(10) + chr(9))}\n\t\t\t\t\t}}\n")

        self.assertEqual(self.check(ungated(4)), COLUMNS)
        self.fails(r"the wrapper around \['te_x_sec_b', 'te_x_summary'\] spaces its sections 30 apart", ungated(30))

    def test_an_instance_with_a_context_or_a_margin_of_its_own(self):
        """What a wrapper may not carry, an instance may not either (#1338): a datacontext changes what the section
        reads, a margin, a position or a size where it sits. A visible, a blockoverride and a child widget stay."""
        self.fails(r"te_x_reference_sections carries \['datacontext', 'margin_left'\]",
                   GOOD.replace("te_x_sec_how = {}",
                                'te_x_reference_sections = { datacontext = "[GetPlayer]" margin_left = 200 }'))
        self.fails(r"te_x_sec_how carries \['size'\]", GOOD.replace("te_x_sec_how = {}", "te_x_sec_how = { size = { 520 38 } }"))
        self.fails(r"te_x_divider carries \['position'\]",
                   GOOD.replace("te_x_sec_how = {}", "te_x_sec_how = {}\n\t\t\tte_x_divider = { position = { 0 4 } }"),
                   extra=("te_x_divider",))
        self.assertEqual(self.check(GOOD.replace("te_x_sec_how = {}", 'te_x_sec_how = {\n\t\t\t\tblockoverride "note" {}\n'
                                                 '\t\t\t\tte_x_text = {\n\t\t\t\t\ttext = "x"\n\t\t\t\t}\n\t\t\t}')), COLUMNS)

    # Both narrow composers placed whole: te_x_status_sections' inner wrapper has no direction and no ignoreinvisible.
    WHOLE = """
	type te_x_wide_sections = te_ui_columns_two {
		blockoverride "column_1" {
			te_x_overview = {}
			te_x_status_sections = {}
		}
		blockoverride "column_2" {
			te_x_reference_sections = {}
		}
	}
"""

    def test_a_composer_both_layouts_place_is_not_held_to_the_wide_rules(self):
        """Its type draws the same in both frames, so its inner wrappers and instances are the narrow layout's
        (#1338: the guard checked them, under the wide composer's name)."""
        self.assertEqual(self.check(self.WHOLE), [["te_x_overview", "te_x_sec_a", "te_x_sec_b", "te_x_summary", "te_x_sec_c"],
                                                  ["te_x_sec_how"]])
        narrow = NARROW.replace("te_x_sec_how = {}", "hbox = {\n\t\t\tmargin_left = 200\n\t\t\tte_x_sec_how = { size = { 520 38 } }\n\t\t}")
        self.assertNotEqual(narrow, NARROW)
        assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES, text=narrow + fixture(self.WHOLE)[len(NARROW):])

    def test_what_the_wide_layout_fills_a_shared_composers_block_with_is_held_to_them(self):
        """A blockoverride is the markup of the layout that writes it."""
        def filled(wrapper):
            return self.WHOLE.replace("te_x_status_sections = {}",
                                      'te_x_status_sections = {\n\t\t\t\tblockoverride "summary" {\n'
                                      f"\t\t\t\t\t{wrapper}\n\t\t\t\t\t\tte_x_summary = {{}}\n\t\t\t\t\t}}\n\t\t\t\t}}\n\t\t\t}}")

        self.assertEqual(len(self.check(filled("flowcontainer = {"))), 2)
        self.fails("wraps sections in `hbox`", filled("hbox = {"))
        self.fails(r"a wrapper carries \['margin_left'\]", filled("flowcontainer = {"), wrapper=WRAPPER + " margin_left = 200")

    def test_a_composer_only_the_wide_layout_places_is_held_to_them(self):
        """It is the wide layout's own, and a failure in it names it."""
        own = self.WHOLE.replace("te_x_reference_sections = {}", "te_x_wide_only_sections = {}")
        self.fails("te_x_wide_sections's te_x_wide_only_sections wraps sections in `hbox`",
                   own + "\ttype te_x_wide_only_sections = flowcontainer {\n\t\thbox = {\n\t\t\tte_x_sec_how = {}\n\t\t}\n\t}\n")
        self.fails(r"te_x_wide_sections's te_x_wide_only_sections: te_x_sec_how carries \['margin_left'\]",
                   own + "\ttype te_x_wide_only_sections = flowcontainer {\n\t\tte_x_sec_how = { margin_left = 200 }\n\t}\n")
        self.check(own + "\ttype te_x_wide_only_sections = flowcontainer {\n\t\tte_x_sec_how = {}\n\t}\n")

    def test_two_rows_of_columns(self):
        """A wide layout is one row of columns, read down each and then across (#1338)."""
        rows = """
	type te_x_wide_sections = flowcontainer {
		te_ui_columns_two = {
			blockoverride "column_1" {
				te_x_overview = {}
			}
			blockoverride "column_2" {
				flowcontainer = {
					visible = "[JournalEntry.IsActive]"
					te_x_sec_a = {}
				}
			}
		}
		te_ui_columns_two = {
			blockoverride "column_1" {
				flowcontainer = {
					visible = "[And( JournalEntry.IsActive, Not( IsLight ) )]"
					te_x_sec_b = {}
					te_x_summary = {}
				}
			}
			blockoverride "column_2" {
				flowcontainer = {
					visible = "[JournalEntry.IsActive]"
					te_x_sec_c = { visible = "[HasC]" }
				}
				te_x_sec_how = {}
			}
		}
	}
"""
        self.fails("places a second row of columns; a wide layout is one row", rows)
        nested = GOOD.replace("\t\t\tte_x_sec_how = {}\n", '\t\t\tte_ui_columns_two = {\n\t\t\t\tblockoverride "column_1" {\n'
                              '\t\t\t\t\tte_x_sec_how = {}\n\t\t\t\t}\n\t\t\t\tblockoverride "column_2" {\n'
                              '\t\t\t\t\tte_x_divider = {}\n\t\t\t\t}\n\t\t\t}\n')
        self.assertNotEqual(nested, GOOD)
        self.fails("places a second row of columns", nested, split={"te_x_divider": "te_x_sec_how"})


BODY = """
types body {
	type te_x_tab_body = te_system_tab_frame {
		blockoverride "tab_gate" {
			visible = "[TabShown]"
		}
		blockoverride "tab_content" {
			block "te_x_tab_layout" {
				te_x_overview = {}
				flowcontainer = {
					visible = "[HasGoal]"
					te_x_goal_bar = {}
				}
				te_x_status_sections = {
					blockoverride "summary" {}
				}
				te_x_reference_sections = {}
			}
		}
	}
}
"""

# The body's layout: the goal bar's inline wrapper gates it, and the body blanks the summary.
LAID_OUT = """
	type te_x_wide_sections = te_ui_columns_three {
		blockoverride "column_1" {
			te_x_overview = {}
			te_x_goal_bar = { visible = "[HasGoal]" }
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_a = {}
			}
		}
		blockoverride "column_2" {
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				flowcontainer = {
					visible = "[Not( IsLight )]"
					te_x_sec_b = {}
				}
			}
		}
		blockoverride "column_3" {
			flowcontainer = {
				visible = "[JournalEntry.IsActive]"
				te_x_sec_c = { visible = "[HasC]" }
			}
			te_x_sec_how = {}
		}
	}
"""


class LayoutTest(unittest.TestCase):
    """layout=(body, block): the narrow layout read from a tab body's layout block."""

    def check(self, wide, **kw):
        return assert_wide_matches_narrow(self, "te_x_wide_sections", layout=("te_x_tab_body", "te_x_tab_layout"),
                                          text=fixture(wide) + BODY, **kw)

    def test_a_body_layout_with_an_inline_wrapper_and_a_blanked_block(self):
        self.check(LAID_OUT)

    def test_the_inline_wrappers_gate_is_kept(self):
        with self.assertRaisesRegex(AssertionError, r"te_x_goal_bar shows in the narrow layout only while \['HasGoal'\]"):
            self.check(LAID_OUT.replace('te_x_goal_bar = { visible = "[HasGoal]" }', "te_x_goal_bar = {}"))

    def test_a_block_the_body_blanks_is_not_wanted(self):
        with self.assertRaisesRegex(AssertionError, "the narrow layout's sections"):
            self.check(LAID_OUT.replace("te_x_sec_b = {}", "te_x_sec_b = {}\n\t\t\t\t\tte_x_summary = {}"))

    def test_a_wide_layout_may_place_a_composer_whole(self):
        self.check(LAID_OUT.replace("te_x_sec_how = {}", "te_x_reference_sections = {}"))

    def test_a_gate_on_a_composers_instance_still_sets_its_sections_spacing(self):
        """te_x_pair_sections has no visible of its own; the body gates its instance. Its sections' 6 was never
        recorded, so a wrapper under that gate spaced them as it liked (#1338)."""
        pair = "\ttype te_x_pair_sections = flowcontainer {\n\t\tspacing = 6\n\t\tte_x_p = {}\n\t\tte_x_q = {}\n\t}\n"
        body = BODY.replace("te_x_reference_sections = {}",
                            'te_x_reference_sections = {}\n\t\t\t\tte_x_pair_sections = {\n\t\t\t\t\tvisible = "[Shown]"\n\t\t\t\t}')
        self.assertNotEqual(body, BODY)

        def check(spacing):
            wide = LAID_OUT.replace("te_x_sec_how = {}",
                                    f"te_x_sec_how = {{}}\n\t\t\tflowcontainer = {{ direction = vertical ignoreinvisible = yes "
                                    f'spacing = {spacing}\n\t\t\t\tvisible = "[Shown]"\n\t\t\t\tte_x_p = {{}}\n'
                                    f"\t\t\t\tte_x_q = {{}}\n\t\t\t}}")
            return assert_wide_matches_narrow(self, "te_x_wide_sections", layout=("te_x_tab_body", "te_x_tab_layout"),
                                              text=fixture(wide + pair) + body)

        check(6)
        with self.assertRaisesRegex(AssertionError, r"the wrapper around \['te_x_p', 'te_x_q'\] spaces its sections 30 "
                                                    r"apart, the narrow layout \['6'\]"):
            check(30)

    def test_sections_the_frame_spaces_set_no_spacing(self):
        """The frame around a body's layout block spaces what sits straight in it, which the check can't read: the
        overview, and the goal bar, alone in a wrapper that only gates it (a wrapper around one draws no spacing).
        So a wide wrapper around the two is not held to a spacing."""
        wide = LAID_OUT.replace('\t\t\tte_x_overview = {}\n\t\t\tte_x_goal_bar = { visible = "[HasGoal]" }\n',
                                "\t\t\tflowcontainer = { direction = vertical ignoreinvisible = yes spacing = 10\n"
                                '\t\t\t\tte_x_overview = {}\n\t\t\t\tte_x_goal_bar = { visible = "[HasGoal]" }\n\t\t\t}\n')
        self.assertNotEqual(wide, LAID_OUT)
        self.check(wide)

    def test_names_or_a_layout_not_both(self):
        with self.assertRaisesRegex(AssertionError, "give narrow_types or layout, not both"):
            assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES, layout=("te_x_tab_body", "te_x_tab_layout"),
                                       text=fixture(LAID_OUT) + BODY)


class ChildrenTest(unittest.TestCase):
    def test_a_blockoverride(self):
        self.assertEqual(_children('blockoverride "column_1" {\n\tte_a = {}\n}\n'),
                         [("blockoverride", "column_1", "\n\tte_a = {}\n")])

    def test_two_properties_on_one_line(self):
        """Budget Breakdown's `blockoverride "layout" { parentanchor = hcenter size = { 520 38 } }`."""
        self.assertEqual(_children(' parentanchor = hcenter size = { 520 38 } '),
                         [("property", "parentanchor", "hcenter"), ("property", "size", "{ 520 38 }")])

    def test_a_one_line_block_of_widgets_is_a_widget(self):
        """A one-line `x = { … }` is a property when it holds only numbers (size, margin), else a widget."""
        self.assertEqual([k for k, _, _ in _children('te_a = {}\nflowcontainer = { te_b = {} }\nsize = { 100% 38 }\n'
                                                     'margin = { 10 6 }\n')],
                         ["widget", "widget", "property", "property"])

    def test_a_quoted_value_with_spaces(self):
        self.assertEqual(_children('visible = "[Not( X )]" text = "a b"\n'),
                         [("property", "visible", '"[Not( X )]"'), ("property", "text", '"a b"')])


class LocClosureTest(unittest.TestCase):
    def test_a_formatted_splice_is_followed(self):
        """1.15 escapes a spliced key as `$key|q$`; the closure still reaches it."""
        loc = {"a": "see $b|q$ and $c$", "b": "B", "c": "C"}
        self.assertEqual(loc_closure({"a"}, loc), {"a", "b", "c"})


SGUIS = """\
# a comment that names custom_tooltip = fx_commented
fx_hover_sgui = {
	scope = country
	is_shown = {
		custom_tooltip = {
			text = fx_shown_tt
			fx_is_far = yes
		}
		fx_is_near = no
	}
	ai_is_valid = { custom_tooltip = fx_ai_tt }
	is_valid = {
		fx_is_far = yes
		custom_tooltip = {
			text = "fx_valid_tt"
			always = yes
		}
	}
	effect = {
		custom_tooltip = fx_line_a
		custom_tooltip_no_bullet = fx_line_b # custom_tooltip = fx_commented
		if = {
			limit = { fx_is_far = yes }
			fx_print = { KEY = fx_line_c B = pacific }
		}
		fx_print = { KEY = "fx_line_d" B = arctic }
		hidden_effect = { custom_tooltip = fx_hidden }
		fx_loose = yes
	}
}
fx_other_sgui = {
	effect = { custom_tooltip = fx_other_line }
}
"""

EFFECTS = """\
fx_print = {
	custom_tooltip = $KEY$
	custom_tooltip_no_bullet = fx_head_$B$
	fx_again = { KEY = $KEY$ }
}
fx_again = {
	custom_tooltip = { text = $KEY$_more }
	fx_again = { KEY = $KEY$ }
}
fx_loose = {
	custom_tooltip = fx_basin_$B$
	custom_tooltip = $ALL$
}
"""

TRIGGERS = """\
fx_is_far = {
	custom_tooltip = {
		text = fx_far_tt
		fx_is_deep = yes
	}
}
fx_is_deep = {
	custom_tooltip = fx_deep_tt
}
	fx_is_near = {
		custom_tooltip = fx_near_tt
	}
"""


class ScriptedTooltipTest(unittest.TestCase):
    """What a scripted GUI's tooltip prints (ScriptedGuis, #1361), and the
    tooltips a markup or loc text asks for (tooltip_calls)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        for folder, text in (("scripted_guis", SGUIS), ("scripted_effects", EFFECTS), ("scripted_triggers", TRIGGERS)):
            os.makedirs(os.path.join(cls.tmp.name, "common", folder))
            with open(os.path.join(cls.tmp.name, "common", folder, "fx.txt"), "w", encoding="utf-8-sig") as fh:
                fh.write(text)
        cls.scripted = ScriptedGuis(cls.tmp.name)
        names = ("fx_shown_tt fx_valid_tt fx_far_tt fx_deep_tt fx_ai_tt fx_line_a fx_line_b fx_line_c fx_line_d "
                 "fx_line_c_more fx_line_d_more fx_head_pacific fx_head_arctic fx_head_indian fx_basin_pacific "
                 "fx_basin_indian fx_hidden fx_commented fx_other_line fx_spliced fx_near_tt")
        cls.loc = {name: name.upper() for name in names.split()}

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_each_function_renders_its_own_block(self):
        """ExecuteTooltip the effect, IsValidTooltip is_valid (not
        ai_is_valid), IsShownTooltip is_shown."""
        self.assertEqual(self.scripted.printed("fx_hover_sgui", "IsShownTooltip"), {"fx_shown_tt", "fx_near_tt"})
        self.assertEqual(self.scripted.printed("fx_hover_sgui", "IsValidTooltip"), {"fx_far_tt", "fx_valid_tt"})
        self.assertEqual(self.scripted.printed("fx_other_sgui"), {"fx_other_line"})
        self.assertEqual(self.scripted.printed("fx_no_such_sgui"), set())
        self.assertEqual(ScriptedGuis(None).keys("fx_hover_sgui", "ExecuteTooltip", self.loc), set())

    def test_a_custom_tooltips_text_stands_for_what_it_holds(self):
        """`custom_tooltip = { text = x  <triggers> }` shows x in place of the
        triggers' own lines, and a hidden_effect shows nothing: the Colonial
        Empire's unlock checklist doesn't print is_separated_from_capital's
        line, which says "our capital"."""
        self.assertNotIn("fx_deep_tt", self.scripted.printed("fx_hover_sgui", "IsValidTooltip"))
        self.assertNotIn("fx_far_tt", self.scripted.printed("fx_hover_sgui", "IsShownTooltip"))
        self.assertNotIn("fx_hidden", self.scripted.printed("fx_hover_sgui"))
        self.assertNotIn("fx_commented", self.scripted.printed("fx_hover_sgui"))
        self.assertEqual(printed_keys("custom_tooltip = { text = fx_a  custom_tooltip = fx_b }\ncustom_tooltip = fx_c",
                                      {}), {"fx_a", "fx_c"})

    def test_the_effects_and_triggers_it_calls_are_followed_with_their_arguments(self):
        """A scripted effect's `custom_tooltip = $KEY$` and `fx_head_$B$` take
        the call's arguments (Seabed's te_seabed_build_in_head_$B$), a quoted
        one too; an effect that calls itself ends; a trigger in a `limit`
        counts (the walk errs wide there)."""
        got = self.scripted.keys("fx_hover_sgui", "ExecuteTooltip", self.loc)
        self.assertEqual(got, {"fx_line_a", "fx_line_b", "fx_line_c", "fx_line_d", "fx_line_c_more", "fx_line_d_more",
                               "fx_head_pacific", "fx_head_arctic", "fx_far_tt", "fx_basin_pacific", "fx_basin_indian"})

    def test_a_trigger_called_no_and_an_indented_definition_are_followed(self):
        """`fx_is_near = no` prints fx_is_near's line, negated; fx_is_near is
        defined tab-indented at the top of its file (build_effects.txt's
        first effect is), and a nested `name = {` is no definition."""
        self.assertIn("fx_near_tt", self.scripted.printed("fx_hover_sgui", "IsShownTooltip"))
        self.assertIn("fx_is_near", self.scripted.calls)
        self.assertEqual(set(self.scripted.guis), {"fx_hover_sgui", "fx_other_sgui"})
        self.assertNotIn("custom_tooltip", self.scripted.calls)
        self.assertIn("extended_timeline_extra_construction_building", scripted_guis().calls)

    def test_a_name_with_an_argument_left_out_is_any_key_it_could_spell(self):
        """fx_loose is called with no B: fx_basin_$B$ is every fx_basin_ key.
        A name that is all arguments would be every key, so it gives none."""
        self.assertEqual(self.scripted.printed("fx_hover_sgui") & {"fx_basin_$B$", "$ALL$"}, {"fx_basin_$B$", "$ALL$"})
        self.assertEqual(loc_keys_of({"fx_basin_$B$", "$ALL$", "fx_line_a", "fx_gone"}, self.loc),
                         {"fx_basin_pacific", "fx_basin_indian", "fx_line_a"})
        self.assertEqual(loc_keys_of({"fx_$A$_$B$"}, {"fx_a_b": "", "fx_ab": "", "fx__": ""}), {"fx_a_b"})

    def test_the_tooltips_a_text_asks_for(self):
        named = "[GetScriptedGui('fx_hover_sgui').ExecuteTooltip( GuiScope.SetRoot( Country.MakeScope ).End )]"
        self.assertEqual(tooltip_calls(named), [("fx_hover_sgui", "ExecuteTooltip", 1)])
        self.assertEqual([c[:2] for c in tooltip_calls("[Concatenate( ScriptedGui.IsValidTooltip( X ), "
                                                       "ScriptedGui.IsShownTooltip( X ) )]")],
                         [(None, "IsValidTooltip"), (None, "IsShownTooltip")])
        self.assertEqual(tooltip_calls("[GetScriptedGui('fx_hover_sgui').Execute( X )] [ScriptedGui.IsValid( X )]"), [],
                         "a control and a test are no tooltip")
        # a loc value escapes nothing, but a quoted call in a loc-in-markup string does
        self.assertEqual(tooltip_calls("GetScriptedGui(\\'fx_a\\').ExecuteTooltip( X )")[0][:2], ("fx_a", "ExecuteTooltip"))

    def test_a_tooltip_in_the_players_own_branch_is_left_out(self):
        """Tax Code's Pass checklist: the tooltip is the first branch of a
        SelectLocalization on Country.IsLocalPlayer, alone or first in an And."""
        call = "GetScriptedGui('fx_hover_sgui').IsValidTooltip( X )"
        for cond, own in (("Country.IsLocalPlayer", True), ("And( Country.IsLocalPlayer, Not( Y ) )", True),
                          ("And( Not( Y ), Country.IsLocalPlayer )", False), ("Or( Country.IsLocalPlayer, Y )", False),
                          ("Country.IsAtWar", False)):
            with self.subTest(condition=cond):
                first = f"[SelectLocalization( {cond}, Concatenate( 'a', {call} ), 'b' )]"
                self.assertEqual(len(tooltip_calls(first, own=False)), 0 if own else 1)
                self.assertEqual(len(tooltip_calls(first)), 1)
                second = f"[SelectLocalization( {cond}, 'a', {call} )]"
                self.assertEqual(len(tooltip_calls(second, own=False)), 1, "the other branch is everyone's")
                added = f"[AddLocalizationIf( {cond}, {call} )]"
                self.assertEqual(len(tooltip_calls(added, own=False)), 0 if own else 1)
        nested = (f"[SelectLocalization( Y, 'a', SelectLocalization( Country.IsLocalPlayer, {call}, "
                  f"GetScriptedGui('fx_other_sgui').ExecuteTooltip( X ) ) )]")
        self.assertEqual([c[0] for c in tooltip_calls(nested, own=False)], ["fx_other_sgui"])
        text = "[SelectLocalization( Country.IsLocalPlayer, 'a', 'b' )]"
        self.assertEqual([text[a:b].strip() for a, b in own_branch_spans(text)], ["'a'"])

    def test_the_scripted_gui_in_context(self):
        """`ScriptedGui.` is the nearest `datacontext = "[GetScriptedGui('x')]"`
        around the call; the panel's (contexts) where the body has none, and
        with it where a blockoverride lies between, since the override's
        contents sit where its block is."""
        body = """
		widget = {
			datacontext = "[GetScriptedGui('fx_other_sgui')]"
			button = {
				datacontext = "[GetScriptedGui('fx_hover_sgui')]"
				tooltip = "[ScriptedGui.IsShownTooltip( X )]"
			}
			@MORE@
		}
		textbox = { tooltip = "[ScriptedGui.ExecuteTooltip( X )]" }
"""
        def keys(more="", contexts=()):
            return scripted_keys(body.replace("@MORE@", more), self.loc, self.scripted, contexts, markup=True)
        self.assertEqual(keys(), {"fx_shown_tt", "fx_near_tt"}, "the nearest; none for the textbox, with no context given")
        self.assertEqual(keys(contexts={"fx_other_sgui"}), {"fx_shown_tt", "fx_near_tt", "fx_other_line"})
        inner = 'textbox = { tooltip = "[ScriptedGui.ExecuteTooltip( X )]" }'
        self.assertEqual(keys(inner), {"fx_shown_tt", "fx_near_tt", "fx_other_line"}, "the outer widget's")
        over = 'fx_row = { blockoverride "slot" { tooltip = "[ScriptedGui.IsValidTooltip( X )]" } }'
        self.assertEqual(keys(over), {"fx_shown_tt", "fx_near_tt"}, "fx_other_sgui's is_valid prints nothing")
        # fx_hover_sgui's is_valid, asked only in the override: the panel's, with the body's own
        self.assertIn("fx_valid_tt", keys(over, {"fx_hover_sgui"}))
        self.assertNotIn("fx_valid_tt", keys("", {"fx_hover_sgui"}))
        # as plain text (a loc value) there is no markup to read: the contexts given
        self.assertEqual(scripted_keys("[ScriptedGui.ExecuteTooltip( X )]", self.loc, self.scripted, {"fx_other_sgui"}),
                         {"fx_other_line"})

    def test_the_loc_closure_follows_a_scripted_tooltip(self):
        loc = dict(self.loc, fx_tt="Header\n[GetScriptedGui('fx_other_sgui').ExecuteTooltip( X )]",
                   fx_other_line="A line and $fx_spliced$",
                   fx_bare="[ScriptedGui.ExecuteTooltip( X )]",
                   fx_own="[SelectLocalization( Country.IsLocalPlayer, GetScriptedGui('fx_other_sgui')"
                          ".ExecuteTooltip( X ), '' )]")
        self.assertEqual(loc_closure({"fx_tt"}, loc, scripted=self.scripted), {"fx_tt", "fx_other_line", "fx_spliced"})
        self.assertEqual(loc_closure({"fx_tt"}, loc, scripted=ScriptedGuis(None)), {"fx_tt"})
        self.assertEqual(loc_closure({"fx_bare"}, loc, scripted=self.scripted), {"fx_bare"})
        self.assertEqual(loc_closure({"fx_bare"}, loc, scripted=self.scripted, contexts={"fx_other_sgui"}),
                         {"fx_bare", "fx_other_line", "fx_spliced"})
        self.assertEqual(loc_closure({"fx_own"}, loc, scripted=self.scripted), {"fx_own", "fx_other_line", "fx_spliced"})
        self.assertEqual(loc_closure({"fx_own"}, loc, own=False, scripted=self.scripted), {"fx_own"})

    def test_the_repos_scripted_guis(self):
        """Seabed's Free hover prints a head, a state and a more line for each
        basin (te_seabed_build_in_sgui, through te_seabed_build_in_lines's
        $B$), the Colonial Empire's unlock checklist its four lines."""
        from gui_test_helpers import load_loc, scripted_guis
        loc = load_loc()
        seabed = scripted_guis().keys("te_seabed_build_in_sgui", "ExecuteTooltip", loc)
        for key in ("te_seabed_build_in_head_pacific", "te_seabed_build_in_none_arctic", "te_seabed_build_in_state_1"):
            self.assertIn(key, seabed)
        self.assertEqual(scripted_guis().keys("te_window_colonial_empire_entry_unlock_sgui", "IsValidTooltip", loc),
                         {"ce_unlock_colonies_tt", "ce_unlock_not_secured_tt", "ce_unlock_no_collapse_tt",
                          "ce_unlock_no_recent_end_tt"})


if __name__ == "__main__":
    unittest.main()
