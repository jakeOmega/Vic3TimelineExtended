"""Generate the nuclear city strike's razing: which buildings it destroys and how each is rebuilt.

A strategic strike that lands on a city destroys a share of the state's urban buildings and
leaves what survives government-owned (`nuclear_strike_raze_city`,
`common/scripted_effects/nuclear_raze_effects.txt`). The engine has no effect that removes
levels, and `create_building` takes a literal building type and a literal level, so every
building the strike can raze needs its own script: a branch of the dispatcher, a list of its
production methods (recorded before the removal and put back after) and the two ladders of
literal levels it is rebuilt from. This writes all of that to
`common/scripted_effects/nuclear_raze_generated.txt` from the merged mod and vanilla data
(the committed `vanilla_parsed/` snapshot, so no game install is needed).

Run it after a building, a building group or a production method group changes:

    .venv/bin/python scripts/generators/gen_nuclear_raze.py           # write
    .venv/bin/python scripts/generators/gen_nuclear_raze.py --check   # exit 1 when stale

`test_nuclear_raze.py` fails CI when the committed file is stale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

OUTPUT = Path("common/scripted_effects/nuclear_raze_generated.txt")

# The building groups a city strike razes, with every group below them.
URBAN_GROUPS = ("bg_manufacturing", "bg_power", "bg_urban_facilities")

# Buildings outside those groups that stand in the city: transport and the
# government's own offices. Government buildings are rebuilt smaller and stay
# the government's (they have no ownership to take).
URBAN_BUILDINGS = (
	"building_port",
	"building_railway",
	"building_network_infrastructure",
	"building_airport",
	"building_highway",
	"building_government_administration",
	"building_university",
)

# Groups under URBAN_GROUPS left standing, and why. Everything else the strike
# leaves alone is simply outside URBAN_GROUPS: farms, mines, plantations,
# ranches and logging (rural; the aftermath's throughput loss stands in for
# fallout there), the military (the tactical strike halves bases and
# fortifications; barracks and conscription centres hold units), monuments,
# Grand Monuments and wonders, canals, the Strategic Reserve, the power grid's
# stations, trade centres, subsistence buildings and company flagships.
EXCLUDED_GROUPS = {
	"bg_construction": "the construction market and direct construction set the Construction Sector's levels themselves",
	"bg_exotic": "ocean and space mines are not in the city",
	"bg_owner_buildings": "removing an ownership building (financial district, manor house, company headquarters) drops every share it holds in other buildings",
}

# Production method groups not put back: the law and the new owner choose the
# ownership method.
SKIPPED_PM_GROUP_PREFIXES = ("pmg_ownership", "pmg_additional_ownership")

# The rebuild ladder: exact levels up to EXACT, then steps of about STEP up to
# TOP. A rebuild snaps down to the rung at or below the levels left, so the
# rounding never leaves a building as large as it was.
EXACT = 20
STEP = 1.05
TOP = 20000

INDENT = "\t"


def unwrap(value):
	if isinstance(value, tuple) and len(value) == 2:
		return value[1]
	return value


def load_state(root: Path = ROOT):
	from mod_state import ModState, VANILLA_COMMON_DIRS
	from vanilla_parsed import load

	kinds = ("Buildings", "Building Groups", "PM Groups")
	snapshot = load(str(root / "vanilla_parsed"))
	state = ModState(
		{kind: "/nonexistent" for kind in kinds},
		{kind: str(root / "common" / VANILLA_COMMON_DIRS[kind]) for kind in kinds},
		vanilla_data=snapshot.data,
	)
	if state.parse_failures:
		raise ValueError(f"Cannot generate the razing from an incomplete parse: {state.parse_failures}")
	return state


def ladder(exact: int = EXACT, step: float = STEP, top: int = TOP) -> list[int]:
	rungs = list(range(1, exact + 1))
	while rungs[-1] < top:
		rungs.append(max(rungs[-1] + 1, round(rungs[-1] * step)))
	return rungs


def group_chain(groups, group):
	chain = []
	while group and group not in chain:
		chain.append(group)
		group = unwrap(unwrap(groups.get(group, ("=", {}))).get("parent_group"))
	return chain


def as_list(value):
	value = unwrap(value)
	if value is None:
		return []
	if isinstance(value, str):
		return [value]
	return list(value)


class Target:
	def __init__(self, name, body, groups, pm_groups):
		self.name = name
		self.body = body
		self.owned = unwrap(body.get("ownership_type")) == "self"
		self.techs = as_list(body.get("unlocking_technologies"))
		self.guards = [(key, unwrap(body[key])) for key in ("potential", "possible") if key in body]
		self.pms = []
		for group in as_list(body.get("production_method_groups")):
			if group.startswith(SKIPPED_PM_GROUP_PREFIXES):
				continue
			for pm in as_list(unwrap(pm_groups.get(group, ("=", {}))).get("production_methods")):
				if pm not in self.pms:
					self.pms.append(pm)


def select_targets(state):
	buildings = state.get_data("Buildings")
	groups = state.get_data("Building Groups")
	pm_groups = state.get_data("PM Groups")
	targets = []
	for name in sorted(buildings):
		body = unwrap(buildings[name])
		if not isinstance(body, dict):
			continue
		chain = group_chain(groups, unwrap(body.get("building_group")))
		if name in URBAN_BUILDINGS:
			pass
		elif not any(group in chain for group in URBAN_GROUPS):
			continue
		elif any(group in chain for group in EXCLUDED_GROUPS):
			continue
		targets.append(Target(name, body, groups, pm_groups))
	missing = sorted(set(URBAN_BUILDINGS) - {t.name for t in targets})
	if missing:
		raise ValueError(f"URBAN_BUILDINGS names buildings that do not exist: {missing}")
	for target in targets:
		check_target(target, groups)
	return targets


def check_target(target, groups):
	body = target.body
	group = unwrap(body.get("building_group"))
	if unwrap(body.get("can_switch_owner")) == "no" or any(
		unwrap(unwrap(groups.get(g, ("=", {}))).get("always_self_owning")) == "yes" for g in group_chain(groups, group)
	):
		raise ValueError(f"{target.name} can't be taken into government ownership: exclude it")
	if len(target.techs) != 1:
		raise ValueError(f"{target.name} has {len(target.techs)} unlocking technologies; the guard expects one")
	if not target.pms:
		raise ValueError(f"{target.name} has no production methods to put back")
	for key, value in target.guards:
		text = " ".join(serialize_block(value, 0))
		for word in ("root", "ROOT", "scope:", "prev", "PREV", "$"):
			if word in text:
				raise ValueError(f"{target.name}'s {key} reads {word!r}; it can't be copied into the dispatcher's limit")


def serialize_value(key, op, value, depth):
	tabs = INDENT * depth
	if isinstance(value, dict):
		return [f"{tabs}{key} {op} {{", *serialize_block(value, depth + 1), f"{tabs}}}"]
	if isinstance(value, list):
		if not all(isinstance(item, str) for item in value):
			raise ValueError(f"Cannot serialize the list under {key}: {value!r}")
		return [f"{tabs}{key} {op} {{ {' '.join(value)} }}"]
	return [f"{tabs}{key} {op} {value}"]


def serialize_block(block, depth):
	"""A parsed trigger block back to script: the parser's dict of key -> (op, value),
	with a repeated key as a list of (op, value)."""
	lines = []
	for key, entry in block.items():
		if isinstance(entry, list) and entry and all(isinstance(item, tuple) for item in entry):
			for op, value in entry:
				lines += serialize_value(key, op, value, depth)
		elif isinstance(entry, tuple) and len(entry) == 2:
			lines += serialize_value(key, entry[0], entry[1], depth)
		else:
			raise ValueError(f"Cannot serialize {key}: {entry!r}")
	return lines


def pm_list_name(target):
	return f"nd_raze_pms_{target.name}"


def render_dispatcher(targets):
	out = [
		"# State scope, from nd_raze_city_run (nuclear_raze_effects.txt): var:nd_raze_share set,",
		"# scope:nd_raze_owner saved. One branch for each building a city strike razes, guarded by",
		"# the building's own potential and possible and its unlocking technology: create_building",
		"# refuses an owner without that technology, and a refused rebuild would lose the building,",
		"# so a building that might not be rebuilt is left standing.",
		"nd_raze_all_buildings = {",
	]
	for index, target in enumerate(targets, start=1):
		out.append(f"{INDENT}if = {{")
		out.append(f"{INDENT * 2}limit = {{")
		out.append(f"{INDENT * 3}has_building = {target.name}")
		out.append(f"{INDENT * 3}owner = {{ has_technology_researched = {target.techs[0]} }}")
		for _key, value in target.guards:
			out += serialize_block(value, 3)
		out.append(f"{INDENT * 2}}}")
		build = "nd_raze_build_owned" if target.owned else "nd_raze_build_plain"
		out.append(
			f"{INDENT * 2}nd_raze_building = {{ BUILDING = {target.name} PMS = {pm_list_name(target)} BUILD = {build} INDEX = {index} }}"
		)
		out.append(f"{INDENT}}}")
	out.append("}")
	return out


def render_pm_lists(targets):
	out = [
		"# Every production method each razed building can run, outside its ownership groups. MODE:",
		"# record / restore around the rebuild (nd_raze_pm_record, nd_raze_pm_restore), and sc_arm /",
		"# sc_read for the once-a-game self-check (nuclear_raze_rebuild).",
	]
	for target in targets:
		out.append(f"{pm_list_name(target)} = {{")
		for pm in target.pms:
			out.append(f"{INDENT}nd_raze_pm_$MODE$ = {{ BUILDING = {target.name} PM = {pm} }}")
		out.append("}")
		out.append("")
	return out[:-1]


def render_ladder(name, owned, rungs):
	if owned:
		header = [
			"# State scope: rebuild $BUILDING$ at the rung at or below var:nd_raze_left (at least 1),",
			"# every level owned by the state's owner, and record the levels built in var:nd_raze_built",
			"# and in the state's levels still standing, var:nd_raze_nat. create_building's levels",
			"# are literals (scripting_best_practices.md § \"`create_building` Does NOT Accept",
			"# Variables for `level`\").",
		]
	else:
		header = [
			"# State scope: rebuild $BUILDING$, a government building, at the rung at or below",
			"# var:nd_raze_left (at least 1), and record the levels built in var:nd_raze_built and in",
			"# var:nd_raze_nat (a government building's levels are the state's already).",
		]
	out = [*header, f"{name} = {{"]
	for position, rung in enumerate(rungs):
		if owned:
			create = f"create_building = {{ building = $BUILDING$ add_ownership = {{ country = {{ country = owner levels = {rung} }} }} }}"
		else:
			create = f"create_building = {{ building = $BUILDING$ level = {rung} }}"
		record = f"set_variable = {{ name = nd_raze_built value = {rung} }}"
		if position + 1 < len(rungs):
			opener = "if" if position == 0 else "else_if"
			out.append(f"{INDENT}{opener} = {{")
			out.append(f"{INDENT * 2}limit = {{ var:nd_raze_left < {rungs[position + 1]} }}")
		else:
			out.append(f"{INDENT}else = {{")
		out.append(f"{INDENT * 2}{create}")
		out.append(f"{INDENT * 2}{record}")
		out.append(f"{INDENT}}}")
	out.append(f"{INDENT}change_variable = {{ name = nd_raze_nat add = var:nd_raze_built }}")
	out.append("}")
	return out


def render_selfcheck_reader(targets):
	out = [
		"# State scope (saved as scope:nd_raze_sc_site), from nuclear_weapon_events.34 a few days",
		"# after the self-check armed (nd_raze_selfcheck_arm): read the rebuilt building's level and",
		"# government share (the fraction read from building scope, as te_demog_um_effects.txt does) and",
		"# check each production method recorded at the rebuild is active, then give the verdict",
		"# (nd_raze_selfcheck_verdict). var:nd_raze_sc_type is the building's branch number in",
		"# nd_raze_all_buildings.",
		"nd_raze_selfcheck_read = {",
		f"{INDENT}set_variable = {{ name = nd_raze_sc_level value = -1 }}",
		f"{INDENT}set_variable = {{ name = nd_raze_sc_gov value = -1 }}",
		f"{INDENT}set_variable = {{ name = nd_raze_sc_pm_miss value = 0 }}",
		f"{INDENT}set_variable = {{ name = nd_raze_sc_pm_seen value = 0 }}",
		f"{INDENT}switch = {{",
		f"{INDENT * 2}trigger = var:nd_raze_sc_type",
	]
	for index, target in enumerate(targets, start=1):
		out.append(f"{INDENT * 2}{index} = {{")
		out.append(f"{INDENT * 3}if = {{")
		out.append(f"{INDENT * 4}limit = {{ has_building = {target.name} }}")
		out.append(f"{INDENT * 4}set_variable = {{ name = nd_raze_sc_level value = b:{target.name}.level }}")
		out.append(f"{INDENT * 4}b:{target.name} = {{")
		out.append(f"{INDENT * 5}scope:nd_raze_sc_site = {{ set_variable = {{ name = nd_raze_sc_gov value = prev.country_ownership_fraction }} }}")
		out.append(f"{INDENT * 4}}}")
		out.append(f"{INDENT * 3}}}")
		out.append(f"{INDENT * 3}{pm_list_name(target)} = {{ MODE = sc_read }}")
		out.append(f"{INDENT * 2}}}")
	out.append(f"{INDENT}}}")
	out.append(f"{INDENT}nd_raze_selfcheck_verdict = yes")
	out.append("}")
	return out


def render(targets):
	rungs = ladder()
	lines = [
		"# AUTO-GENERATED by scripts/generators/gen_nuclear_raze.py — do not edit manually.",
		"# The nuclear city strike's razing (nuclear_strike_raze_city, nuclear_raze_effects.txt): one",
		"# dispatcher branch and one production method list for each building it destroys, and the",
		"# literal-level ladders it rebuilds them from. Re-run the generator after a building, a",
		"# building group or a production method group changes; test_nuclear_raze.py fails when this",
		"# file is stale. Which buildings and why: the generator's URBAN_GROUPS, URBAN_BUILDINGS and",
		"# EXCLUDED_GROUPS.",
		"#",
		"# Branch numbers (var:nd_raze_sc_type in the self-check's log line):",
	]
	for index, target in enumerate(targets, start=1):
		ownership = "government-owned" if target.owned else "government building"
		lines.append(f"#   {index:3d}  {target.name} ({ownership})")
	lines.append("")
	lines += render_dispatcher(targets)
	lines.append("")
	lines += render_pm_lists(targets)
	lines.append("")
	lines += render_ladder("nd_raze_build_owned", True, rungs)
	lines.append("")
	lines += render_ladder("nd_raze_build_plain", False, rungs)
	lines.append("")
	lines += render_selfcheck_reader(targets)
	return "\n".join(lines) + "\n"


def plan_outputs(state=None, root: Path = ROOT):
	if state is None:
		state = load_state(root)
	return {OUTPUT: render(select_targets(state))}


def regenerate(state=None, *, root: Path = ROOT, dry_run: bool = False):
	changed = []
	for relative, text in plan_outputs(state, root).items():
		target = root / relative
		expected = text.encode("utf-8-sig")
		if not target.exists() or target.read_bytes() != expected:
			changed.append(str(relative))
			if not dry_run:
				target.write_bytes(expected)
	return changed


def main():
	parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
	mode = parser.add_mutually_exclusive_group()
	mode.add_argument("--dry-run", action="store_true", help="report the files a run would change")
	mode.add_argument("--check", action="store_true", help="exit 1 if a run would change any file")
	parser.add_argument("--root", type=Path, default=ROOT)
	args = parser.parse_args()
	changed = regenerate(root=args.root, dry_run=args.dry_run or args.check)
	for path in changed:
		print(f"{'would change' if args.dry_run or args.check else 'wrote'}: {path}")
	if not changed:
		print("nuclear razing script is current")
	return int(args.check and bool(changed))


if __name__ == "__main__":
	raise SystemExit(main())
