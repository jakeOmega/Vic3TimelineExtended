"""Generate batched private investment's per-building script: the dispatcher and the local-goods list.

When the investors of a very large economy queue a level, the mod queues more levels of the same
building beside it (`te_bi_hook`, `common/scripted_effects/te_batch_investment_effects.txt`), so
the engine's weekly investment pass makes a few dozen decisions where it made a thousand.
`start_privately_funded_building_construction` takes a literal building type, and a building holds
no variables, so every building investors can build needs its own branch: one that queues the
levels and keeps the state's once-a-week mark for that type. This writes those branches to
`common/scripted_effects/te_batch_investment_generated.txt`, and the list of buildings that make
a local good (which get a smaller batch) to
`common/scripted_triggers/te_batch_investment_generated_triggers.txt`, from the merged mod and
vanilla data (the committed `vanilla_parsed/` snapshot, so no game install is needed).

Run it after a building, a building group, a production method or a good changes:

    .venv/bin/python scripts/generators/gen_batch_investment.py           # write
    .venv/bin/python scripts/generators/gen_batch_investment.py --check   # exit 1 when stale

`test_batch_investment.py` fails CI when a committed file is stale.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

EFFECTS = Path("common/scripted_effects/te_batch_investment_generated.txt")
TRIGGERS = Path("common/scripted_triggers/te_batch_investment_generated_triggers.txt")

KINDS = ("Buildings", "Building Groups", "PM Groups", "PMs", "Goods")

# Where a production method keeps what it makes.
MODIFIER_BLOCKS = ("workforce_scaled", "level_scaled", "unscaled")

INDENT = "\t"


def unwrap(value):
	if isinstance(value, tuple) and len(value) == 2:
		return value[1]
	return value


def as_list(value):
	value = unwrap(value)
	if value is None:
		return []
	if isinstance(value, str):
		return [value]
	return list(value)


def body_of(table, name):
	body = unwrap(table.get(name))
	return body if isinstance(body, dict) else {}


def load_state(root: Path = ROOT):
	from mod_state import ModState, VANILLA_COMMON_DIRS
	from vanilla_parsed import load

	snapshot = load(str(root / "vanilla_parsed"))
	state = ModState(
		{kind: "/nonexistent" for kind in KINDS},
		{kind: str(root / "common" / VANILLA_COMMON_DIRS[kind]) for kind in KINDS},
		vanilla_data=snapshot.data,
	)
	if state.parse_failures:
		raise ValueError(f"Cannot generate the batches from an incomplete parse: {state.parse_failures}")
	return state


def group_chain(groups, group):
	chain = []
	while group and group not in chain:
		chain.append(group)
		group = unwrap(body_of(groups, group).get("parent_group"))
	return chain


def government_funded(groups, group):
	"""The nearest group up the chain that says, as the engine reads an inherited key."""
	for name in group_chain(groups, group):
		value = unwrap(body_of(groups, name).get("is_government_funded"))
		if value is not None:
			return value == "yes"
	return False


def never_private(body):
	"""`can_build_private = { always = no }`: the company flagships, which only their company's country builds."""
	block = unwrap(body.get("can_build_private"))
	return isinstance(block, dict) and list(block) == ["always"] and unwrap(block["always"]) == "no"


def why_not(name, body, groups):
	"""Why investors never queue this building, or None when they can."""
	if government_funded(groups, unwrap(body.get("building_group"))):
		return "its group is government funded"
	if unwrap(body.get("expandable")) == "no":
		return "it cannot be expanded"
	if never_private(body):
		return "can_build_private is always = no"
	return None


def select_buildings(state):
	"""Every building the engine's investment pass could queue a level of. A building too many here
	is a branch never taken; one missing is a pick that stays a single level (the hook counts it as
	`unknown`), so the test is the engine's own three gates and nothing narrower."""
	buildings = state.get_data("Buildings")
	groups = state.get_data("Building Groups")
	names = []
	for name in sorted(buildings):
		body = body_of(buildings, name)
		if body and why_not(name, body, groups) is None:
			names.append(name)
	if not names:
		raise ValueError("No building investors can build: the parse is empty or the gates are wrong")
	return names


def local_goods(state):
	goods = state.get_data("Goods")
	return sorted(name for name in goods if unwrap(body_of(goods, name).get("local")) == "yes")


def goods_made(state, building):
	"""The goods any production method of the building puts out."""
	buildings = state.get_data("Buildings")
	pm_groups = state.get_data("PM Groups")
	pms = state.get_data("PMs")
	made = set()
	for group in as_list(body_of(buildings, building).get("production_method_groups")):
		for pm in as_list(body_of(pm_groups, group).get("production_methods")):
			modifiers = unwrap(body_of(pms, pm).get("building_modifiers"))
			if not isinstance(modifiers, dict):
				continue
			for block in MODIFIER_BLOCKS:
				scaled = unwrap(modifiers.get(block))
				if not isinstance(scaled, dict):
					continue
				for key in scaled:
					if key.startswith("goods_output_") and key.endswith("_add"):
						made.add(key[len("goods_output_"):-len("_add")])
	return made


def select_local(state, names):
	local = set(local_goods(state))
	if not local:
		raise ValueError("No local good found: the batches would treat every building alike")
	return [name for name in names if goods_made(state, name) & local]


def render_effects(names):
	lines = [
		"# AUTO-GENERATED by scripts/generators/gen_batch_investment.py — do not edit manually.",
		"# Batched private investment (te_batch_investment_effects.txt): one branch for each building",
		"# investors can build, because start_privately_funded_building_construction takes a literal",
		"# building type. Re-run the generator after a building or a building group changes;",
		"# test_batch_investment.py fails when this file is stale. Which buildings: the generator's",
		"# why_not (not government funded, expandable, and not can_build_private = { always = no }).",
		"",
		"# Building scope, from te_bi_place: local_var:te_bi_n levels to queue. Each branch hands the",
		"# state its own building type (te_bi_queue_in_state keeps the once-a-week mark under it). A",
		"# building with no branch leaves local_var:te_bi_did at 0, which the caller counts as unknown.",
		"te_bi_queue_batch = {",
	]
	for position, name in enumerate(names):
		opener = "if" if position == 0 else "else_if"
		lines.append(f"{INDENT}{opener} = {{")
		lines.append(f"{INDENT * 2}limit = {{ is_building_type = {name} }}")
		lines.append(f"{INDENT * 2}state = {{ te_bi_queue_in_state = {{ B = {name} }} }}")
		lines.append(f"{INDENT}}}")
	lines.append("}")
	return "\n".join(lines) + "\n"


def render_triggers(local, goods):
	lines = [
		"# AUTO-GENERATED by scripts/generators/gen_batch_investment.py — do not edit manually.",
		"# Batched private investment: the buildings investors can build that make a good no market",
		"# carries, which get the smaller batch (te_bi_batch_extra). Re-run the generator after a",
		"# production method or a good changes; test_batch_investment.py fails when this file is stale.",
		f"# The local goods: {', '.join(goods)}.",
		"",
		"# Building scope.",
		"te_bi_local_goods_building = {",
		f"{INDENT}OR = {{",
	]
	lines += [f"{INDENT * 2}is_building_type = {name}" for name in local]
	lines += [f"{INDENT}}}", "}"]
	return "\n".join(lines) + "\n"


def plan_outputs(state=None, root: Path = ROOT):
	if state is None:
		state = load_state(root)
	names = select_buildings(state)
	local = select_local(state, names)
	if not local:
		raise ValueError("No investable building makes a local good: te_bi_local_goods_building would be empty")
	return {EFFECTS: render_effects(names), TRIGGERS: render_triggers(local, local_goods(state))}


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
		print("batched investment script is current")
	return int(args.check and bool(changed))


if __name__ == "__main__":
	raise SystemExit(main())
