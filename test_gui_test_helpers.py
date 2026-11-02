"""gui_test_helpers.assert_wide_matches_narrow, on made-up markup (spec
docs/superpowers/specs/2026-11-02-te-window-wide-mode-design.md § 9.5).

A wide composer must place exactly the narrow composers' sections, in their
order read down each column and then across, on te_ui_columns_three or
te_ui_columns_two, and keep every gate the narrow layout puts on a section.
The real calls are in each system's layout test (test_demographics_layout.py
for the Census Data window).
"""
import unittest

from gui_test_helpers import _children, assert_wide_matches_narrow

NARROW = """
types fixture {
	type te_x_status_sections = flowcontainer {
		direction = vertical
		visible = "[JournalEntry.IsActive]"

		te_x_sec_a = {}
		# te_x_sec_commented = {}
		flowcontainer = {
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
}
"""
NARROW_TYPES = ["te_x_overview", "te_x_status_sections", "te_x_reference_sections"]


def fixture(wide):
    return NARROW + "\ntypes wide {\n" + wide + "\n}\n"


# The sections in the narrow order, every gate kept: IsActive on the root,
# Not( IsLight ) on a wrapper, HasC on the instance.
GOOD = """
	type te_x_wide_sections = te_ui_columns_three {
		visible = "[JournalEntry.IsActive]"
		blockoverride "column_1" {
			te_x_overview = {}
			te_x_sec_a = {}
		}
		blockoverride "column_2" {
			flowcontainer = {
				visible = "[Not( IsLight )]"
				te_x_sec_b = {}
				te_x_summary = {}
			}
		}
		blockoverride "column_3" {
			te_x_sec_c = { visible = "[HasC]" }
			te_x_sec_how = {}
		}
	}
"""


class WideMatchesNarrowTest(unittest.TestCase):
    def check(self, wide, **kw):
        return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES, text=fixture(wide), **kw)

    def fails(self, wide, **kw):
        with self.assertRaises(AssertionError):
            self.check(wide, **kw)

    def test_a_matching_layout_passes_and_returns_its_columns(self):
        self.assertEqual(self.check(GOOD), [["te_x_overview", "te_x_sec_a"], ["te_x_sec_b", "te_x_summary"],
                                            ["te_x_sec_c", "te_x_sec_how"]])

    def test_a_section_left_out(self):
        self.fails(GOOD.replace("te_x_sec_how = {}", ""))

    def test_a_section_out_of_order(self):
        self.fails(GOOD.replace("te_x_overview = {}\n\t\t\tte_x_sec_a = {}", "te_x_sec_a = {}\n\t\t\tte_x_overview = {}"))

    def test_the_columns_are_read_by_number_not_by_where_they_are_written(self):
        moved = GOOD.replace('blockoverride "column_1"', 'blockoverride "column_tmp"')
        moved = moved.replace('blockoverride "column_3"', 'blockoverride "column_1"')
        self.fails(moved.replace('blockoverride "column_tmp"', 'blockoverride "column_3"'))

    def test_a_gate_on_the_narrow_root_dropped(self):
        self.fails(GOOD.replace('visible = "[JournalEntry.IsActive]"', ""))

    def test_a_gate_on_a_narrow_wrapper_dropped(self):
        self.fails(GOOD.replace('visible = "[Not( IsLight )]"', ""))

    def test_a_gate_on_a_narrow_instance_dropped(self):
        self.fails(GOOD.replace('te_x_sec_c = { visible = "[HasC]" }', "te_x_sec_c = {}"))

    def test_a_gate_may_sit_on_the_columns_instance_or_an_outer_wrapper(self):
        wide = """
	type te_x_wide_sections = flowcontainer {
		flowcontainer = {
			visible = "[JournalEntry.IsActive]"
			te_ui_columns_three = {
				visible = "[Not( IsLight )]"
				blockoverride "column_1" {
					te_x_overview = {}
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
					te_x_sec_how = {}
				}
			}
		}
	}
"""
        self.check(wide)

    def test_a_wide_layout_may_add_a_gate(self):
        self.check(GOOD.replace("te_x_sec_how = {}", 'te_x_sec_how = { visible = "[Pending]" }'))

    def test_gates_compare_without_their_spacing(self):
        self.check(GOOD.replace('"[Not( IsLight )]"', '"[Not(IsLight)]"').replace(
            'visible = "[HasC]"', 'visible = "[ HasC ]"'))

    def test_an_empty_column(self):
        self.fails(GOOD.replace("te_x_sec_c = { visible = \"[HasC]\" }\n\t\t\tte_x_sec_how = {}", "")
                   .replace("te_x_summary = {}", "te_x_summary = {}\n\t\t\t\tte_x_sec_c = { visible = \"[HasC]\" }"
                            "\n\t\t\t\tte_x_sec_how = {}"))

    def test_a_column_the_type_lacks(self):
        self.fails(GOOD.replace("te_ui_columns_three", "te_ui_columns_two"))

    def test_two_columns(self):
        wide = """
	type te_x_wide_sections = te_ui_columns_two {
		visible = "[JournalEntry.IsActive]"
		blockoverride "column_1" {
			te_x_overview = {}
			te_x_sec_a = {}
			flowcontainer = {
				visible = "[Not( IsLight )]"
				te_x_sec_b = {}
				te_x_summary = {}
			}
		}
		blockoverride "column_2" {
			te_x_sec_c = { visible = "[HasC]" }
			te_x_sec_how = {}
		}
	}
"""
        self.assertEqual(len(self.check(wide)), 2)

    def test_no_column_type(self):
        self.fails(GOOD.replace("te_ui_columns_three", "flowcontainer"))

    def test_sections_outside_the_columns_count_in_place(self):
        """The Census Data window's pending line sits above its columns."""
        wide = GOOD.replace("type te_x_wide_sections = te_ui_columns_three {",
                            "type te_x_wide_sections = flowcontainer {\n\t\tte_x_overview = {}\n\t\tte_ui_columns_three = {")
        wide = wide.replace("\t\t\tte_x_overview = {}\n", "").rstrip() + "\n\t}\n"
        self.assertEqual(self.check(wide)[0], ["te_x_sec_a"])

    def test_extra_skips_a_wide_only_instance(self):
        wide = GOOD.replace("te_x_sec_how = {}", "te_x_sec_how = {}\n\t\t\tte_x_divider = {}")
        self.fails(wide)
        self.check(wide, extra=("te_x_divider",))

    def test_an_extra_the_layout_no_longer_has(self):
        self.fails(GOOD, extra=("te_x_divider",))

    def test_composers_names_what_expands(self):
        """By default a type named *_sections is a composer, on either side; others are sections."""
        self.fails(GOOD, composers=("te_x_status_sections",))
        wide = GOOD.replace("te_x_sec_how = {}", "te_x_reference_sections = {}")
        self.check(wide)
        self.check(wide, composers=("te_x_status_sections",))

    def test_an_and_gate_counts_as_its_two_parts(self):
        """Global Warming's reference sections: And( IsActive, the rule ). A wide layout may put the two parts on
        different wrappers, or keep the And whole."""
        narrow = NARROW.replace('visible = "[Not( IsLight )]"', 'visible = "[And( IsBig, Not( IsLight ) )]"')

        def check(wide):
            return assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES,
                                              text=narrow + "\ntypes wide {\n" + wide + "\n}\n")

        with self.assertRaises(AssertionError):
            check(GOOD)                                              # IsBig is on nothing
        split = GOOD.replace("type te_x_wide_sections = te_ui_columns_three {",
                             'type te_x_wide_sections = flowcontainer {\n\t\tvisible = "[IsBig]"\n\t\tte_ui_columns_three = {')
        check(split.rstrip() + "\n\t}\n")
        check(GOOD.replace('"[Not( IsLight )]"', '"[And( IsBig, Not( IsLight ) )]"'))


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
		visible = "[JournalEntry.IsActive]"
		blockoverride "column_1" {
			te_x_overview = {}
			te_x_goal_bar = { visible = "[HasGoal]" }
			te_x_sec_a = {}
		}
		blockoverride "column_2" {
			flowcontainer = {
				visible = "[Not( IsLight )]"
				te_x_sec_b = {}
			}
		}
		blockoverride "column_3" {
			te_x_sec_c = { visible = "[HasC]" }
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
        with self.assertRaises(AssertionError):
            self.check(LAID_OUT.replace('te_x_goal_bar = { visible = "[HasGoal]" }', "te_x_goal_bar = {}"))

    def test_a_block_the_body_blanks_is_not_wanted(self):
        with self.assertRaises(AssertionError):
            self.check(LAID_OUT.replace("te_x_sec_b = {}", "te_x_sec_b = {}\n\t\t\t\tte_x_summary = {}"))

    def test_a_wide_layout_may_place_a_composer_whole(self):
        wide = LAID_OUT.replace("te_x_sec_c = { visible = \"[HasC]\" }\n\t\t\tte_x_sec_how = {}",
                                "te_x_sec_c = { visible = \"[HasC]\" }\n\t\t\tte_x_reference_sections = {}")
        self.check(wide)

    def test_names_or_a_layout_not_both(self):
        with self.assertRaises(AssertionError):
            assert_wide_matches_narrow(self, "te_x_wide_sections", NARROW_TYPES, layout=("te_x_tab_body", "te_x_tab_layout"),
                                       text=fixture(LAID_OUT) + BODY)


class ChildrenTest(unittest.TestCase):
    def test_a_blockoverride(self):
        self.assertEqual(_children('blockoverride "column_1" {\n\tte_a = {}\n}\n'),
                         [("blockoverride", "column_1", "\n\tte_a = {}\n")])


if __name__ == "__main__":
    unittest.main()
