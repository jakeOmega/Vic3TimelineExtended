"""The one-shot journal entry converter (scripts/generators/convert_je_outcomes.py, vanilla 1.15).

Fixtures in each old shape the mod used, with the outcome text each must become; then the
real tree: no mod journal entry keeps a field 1.15 dropped, so a rerun changes nothing."""

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "scripts" / "generators"))
import convert_je_outcomes as conv  # noqa: E402

BOM = "﻿"

FULL_OLD = """je_x = {
	icon = "gfx/x.dds"

	# completes on the law
	complete = {
		has_law = law_type:law_a # inline
	}

	# the reward
	on_complete = {
		add_modifier = { name = m }
		custom_tooltip = { text = "#b x } y#!" }
	}

	invalid = {
		is_country_type = decentralized
	}

	fail = { has_law = law_type:law_b }

	on_fail = {
		set_variable = x_done
	}

	timeout = 7300 # 20 years

	on_timeout = {
		set_variable = x_done
	}

	weight = 100
}
"""

FULL_NEW = """je_x = {
	icon = "gfx/x.dds"

	outcome = {
		header = je_standard_completion_header
		effect_header = je_standard_on_completion_header
		color = "gold_positive"
		conclusion_desc = je_x_complete_conclusion_desc
		# completes on the law
		trigger = {
			has_law = law_type:law_a # inline
		}
		# the reward
		effect = {
			add_modifier = { name = m }
			custom_tooltip = { text = "#b x } y#!" }
		}
	}

	outcome = {
		header = je_standard_failure_header
		effect_header = je_standard_on_failure_header
		color = "blue_negative"
		conclusion_desc = je_x_fail_conclusion_desc
		trigger = { has_law = law_type:law_b }
		effect = {
			set_variable = x_done
		}
	}

	outcome = {
		flags = { hidden invalid_outcome }
		conclusion_desc = je_x_invalid_conclusion_desc
		trigger = {
			is_country_type = decentralized
		}
	}

	outcome = {
		header = JOURNAL_ENTRY_TIMEOUT
		effect_header = JOURNAL_ENTRY_ON_TIMEOUT
		flags = { timeout }
		conclusion_desc = je_x_timeout_conclusion_desc
		effect = {
			set_variable = x_done
		}
	}

	timeout = 7300 # 20 years

	weight = 100
}
"""

HEADERS_OLD = """je_sr = {
	complete = {
		var:p >= 1
	}

	on_complete = {
		trigger_event = { id = sr.2 }
	}

	fail = {
		has_variable = lost
	}

	on_monthly_pulse = {
		effect = { change_variable = { name = p add = 1 } }
	}

	event_outcome_completed_effect_desc = {
		header = first_header
		effect = {
			custom_tooltip = first_tt
		}
	}
	event_outcome_completed_effect_desc = {
		header = later_header
		effect = {
			custom_tooltip = later_tt
		}
	}
	event_outcome_failed_effect_desc = {
		header = setback_header
		effect = {
			custom_tooltip = setback_tt
		}
	}

	custom_completion_header    = sr_completion_header
	custom_failure_header       = sr_failure_header
	custom_on_completion_header = sr_on_completion_header
	custom_on_failure_header    = sr_on_failure_header

	weight = 100
}
"""

HEADERS_NEW = """je_sr = {
	outcome = {
		header = sr_completion_header
		effect_header = sr_on_completion_header
		color = "gold_positive"
		conclusion_desc = je_sr_complete_conclusion_desc
		trigger = {
			var:p >= 1
		}
		effect = {
			trigger_event = { id = sr.2 }
		}
		event_outcome_effect_desc = {
			header = first_header
			effect = {
				custom_tooltip = first_tt
			}
		}
		event_outcome_effect_desc = {
			header = later_header
			effect = {
				custom_tooltip = later_tt
			}
		}
	}

	outcome = {
		header = sr_failure_header
		effect_header = sr_on_failure_header
		color = "blue_negative"
		conclusion_desc = je_sr_fail_conclusion_desc
		trigger = {
			has_variable = lost
		}
		event_outcome_effect_desc = {
			header = setback_header
			effect = {
				custom_tooltip = setback_tt
			}
		}
	}

	on_monthly_pulse = {
		effect = { change_variable = { name = p add = 1 } }
	}

	weight = 100
}
"""

NEVER_OLD = """je_n = {
	possible = { always = yes }

	# never concludes
	complete = {
		# not through this block
		always = no
	}

	on_complete = {
		custom_tooltip = { text = "X" }
	}

	fail = { }

	weight = 5
}
"""

NEVER_NEW = """je_n = {
	possible = { always = yes }

	weight = 5
}
"""

LAST_OLD = """je_last = {
	weight = 1

	complete = {
		always = yes
	}
}
"""

LAST_NEW = """je_last = {
	weight = 1

	outcome = {
		header = je_standard_completion_header
		effect_header = je_standard_on_completion_header
		color = "gold_positive"
		conclusion_desc = je_last_complete_conclusion_desc
		trigger = {
			always = yes
		}
	}
}
"""

DESC_OLD = """je_d = {
	complete = {
		has_variable = done
	}
	on_complete = {
		trigger_event = { id = d.1 }
	}
	event_outcome_completed_desc = {
		first_valid = {
			triggered_desc = { desc = d_1_tt }
		}
	}
	timeout = 365
	event_outcome_timeout_desc = {
		first_valid = {
			triggered_desc = { desc = d_3_tt }
		}
	}
}
"""

DESC_NEW = """je_d = {
	outcome = {
		header = je_standard_completion_header
		effect_header = je_standard_on_completion_header
		color = "gold_positive"
		conclusion_desc = je_d_complete_conclusion_desc
		trigger = {
			has_variable = done
		}
		effect = {
			trigger_event = { id = d.1 }
		}
		event_outcome_desc = {
			first_valid = {
				triggered_desc = { desc = d_1_tt }
			}
		}
	}

	outcome = {
		header = JOURNAL_ENTRY_TIMEOUT
		effect_header = JOURNAL_ENTRY_ON_TIMEOUT
		flags = { timeout }
		conclusion_desc = je_d_timeout_conclusion_desc
		event_outcome_desc = {
			first_valid = {
				triggered_desc = { desc = d_3_tt }
			}
		}
	}

	timeout = 365
}
"""


def convert(text):
    return conv.convert_text(text)[0]


class FixtureTest(unittest.TestCase):
    def check(self, old, new):
        out = convert(BOM + old)
        self.assertEqual(out, BOM + new)
        # a second run changes nothing
        self.assertEqual(convert(out), out)

    def test_every_old_block_becomes_an_outcome_in_vanilla_order(self):
        self.check(FULL_OLD, FULL_NEW)

    def test_custom_headers_and_event_outcome_effect_descs_go_into_their_outcome(self):
        self.check(HEADERS_OLD, HEADERS_NEW)

    def test_a_trigger_that_never_passes_gives_no_outcome_and_takes_its_effect_with_it(self):
        self.check(NEVER_OLD, NEVER_NEW)
        dropped = conv.convert_text(NEVER_OLD)[1][0].dropped
        self.assertEqual([key for key, _ in dropped], ["complete", "fail", "on_complete"])

    def test_the_last_field_of_an_entry(self):
        self.check(LAST_OLD, LAST_NEW)

    def test_event_outcome_descs_and_a_timeout_with_no_effect(self):
        self.check(DESC_OLD, DESC_NEW)

    def test_a_file_without_a_bom_gets_one_only_when_it_changes(self):
        self.assertEqual(convert(FULL_OLD), BOM + FULL_NEW)
        self.assertEqual(convert(NEVER_NEW), NEVER_NEW)

    def test_a_copy_of_a_vanilla_entry_is_left_for_a_rebuild(self):
        text = BOM + "REPLACE:" + FULL_OLD
        self.assertEqual(convert(text), text)

    def test_an_unmapped_field_stops_the_run(self):
        with self.assertRaises(conv.LayoutError):
            convert("je_u = {\n\tcomplete = { always = yes }\n\ton_complete_all_involved = { }\n}\n")

    def test_two_fields_on_one_line_stop_the_run(self):
        with self.assertRaises(conv.LayoutError):
            convert("je_t = {\n\tweight = 1 complete = { always = yes }\n}\n")
        with self.assertRaises(conv.LayoutError):
            convert("je_t = {\n\tcomplete = { always = yes } weight = 1\n}\n")


class TreeTest(unittest.TestCase):
    """Every mod journal entry is in the 1.15 shape."""

    def test_no_entry_keeps_a_field_vanilla_dropped(self):
        files = sorted((ROOT / "common" / "journal_entries").glob("*.txt"))
        self.assertGreater(len(files), 15)
        for path in files:
            text = path.read_text(encoding="utf-8")
            body = text[1:] if text.startswith(BOM) else text
            masked = conv.mask(body)
            for entry in conv.parse(masked):
                old = sorted({child.key for child in entry.children} & (conv.OLD_FIELDS | conv.UNSUPPORTED))
                with self.subTest(file=path.name, entry=entry.key):
                    self.assertEqual(old, [])

    def test_a_rerun_changes_nothing(self):
        self.assertEqual(conv.main(["--check"]), 0)

    def test_every_entry_declares_activation_description(self):
        """1.15 logs "missing an activation_description trigger" for an entry without one (29 mod entries on the
        first 1.15 game); vanilla's default is `activation_description = { always = yes }`."""
        for path in sorted((ROOT / "common" / "journal_entries").glob("*.txt")):
            text = path.read_text(encoding="utf-8")
            body = text[1:] if text.startswith(BOM) else text
            for entry in conv.parse(conv.mask(body)):
                if entry.key.startswith("INJECT:"):  # takes the field from its target; a REPLACE: needs its own
                    continue
                with self.subTest(file=path.name, entry=entry.key):
                    self.assertIn("activation_description", {child.key for child in entry.children})


if __name__ == "__main__":
    unittest.main()
