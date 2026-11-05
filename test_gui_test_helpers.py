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
import unittest

from gui_test_helpers import _children, assert_wide_matches_narrow

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

    def test_a_wrappers_spacing_against_its_narrow_composers(self):
        """The wrapper standing in for a narrow composer under the same gates spaces its sections as the composer
        does."""
        self.fails(r"spaces its sections 30 apart under \['JournalEntry.IsActive'\], the narrow layout \['4'\]", GOOD,
                   wrapper="direction = vertical parentanchor = hcenter ignoreinvisible = yes spacing = 30")

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


if __name__ == "__main__":
    unittest.main()
