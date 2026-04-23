"""Generate cleanup effects for invalid company buildings."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from paradox_file_parser import ParadoxFileParser
from path_constants import mod_path


BUILDINGS_PATH = Path(mod_path) / "common" / "buildings" / "company_buildings.txt"
COMPANY_TYPES_DIR = Path(mod_path) / "common" / "company_types"
OUTPUT_PATH = (
	Path(mod_path)
	/ "common"
	/ "scripted_effects"
	/ "company_building_cleanup_effects.txt"
)
DIRECTIVE_PREFIXES = ("INJECT:", "REPLACE:", "REPLACE_OR_CREATE:")
TOP_LEVEL_BLOCK_PATTERN = re.compile(r"(?m)^([A-Za-z0-9_:\-]+)\s*=\s*\{")
BUILDING_TOKEN_PATTERN = re.compile(r"(?<![\w])building_[A-Za-z0-9_]+(?![\w])")


def unwrap(value):
	if isinstance(value, tuple):
		return value[1]
	return value


def collect_company_types(node) -> set[str]:
	node = unwrap(node)
	if isinstance(node, str):
		return set()
	if isinstance(node, list):
		company_types: set[str] = set()
		for item in node:
			company_types.update(collect_company_types(item))
		return company_types
	if isinstance(node, dict):
		company_types: set[str] = set()
		for key, value in node.items():
			if key == "has_company":
				unwrapped_value = unwrap(value)
				if isinstance(unwrapped_value, str):
					company_types.add(unwrapped_value)
				else:
					company_types.update(collect_company_types(unwrapped_value))
				continue
			company_types.update(collect_company_types(value))
		return company_types
	return set()


def strip_comments(text: str) -> str:
	return "\n".join(line.split("#", 1)[0] for line in text.splitlines())


def normalize_company_id(raw_key: str) -> str:
	for prefix in DIRECTIVE_PREFIXES:
		if raw_key.startswith(prefix):
			return raw_key[len(prefix) :]
	return raw_key


def iter_top_level_blocks(text: str):
	clean_text = strip_comments(text)
	position = 0
	while True:
		match = TOP_LEVEL_BLOCK_PATTERN.search(clean_text, position)
		if match is None:
			return

		brace_depth = 1
		index = match.end()
		while index < len(clean_text) and brace_depth > 0:
			character = clean_text[index]
			if character == "{":
				brace_depth += 1
			elif character == "}":
				brace_depth -= 1
			index += 1

		if brace_depth != 0:
			raise ValueError(f"Unbalanced braces in {match.group(1)} block")

		yield match.group(1), clean_text[match.end() : index - 1]
		position = index


def load_company_building_references() -> dict[str, list[str]]:
	building_references: dict[str, set[str]] = {}
	for file_path in sorted(COMPANY_TYPES_DIR.glob("*.txt")):
		text = file_path.read_text(encoding="utf-8-sig")
		for raw_key, block_text in iter_top_level_blocks(text):
			company_id = normalize_company_id(raw_key)
			for building_name in set(BUILDING_TOKEN_PATTERN.findall(block_text)):
				building_references.setdefault(building_name, set()).add(company_id)

	return {
		building_name: sorted(company_ids)
		for building_name, company_ids in sorted(building_references.items())
	}


def load_company_building_map() -> dict[str, list[str]]:
	parser = ParadoxFileParser()
	parser.parse_file(str(BUILDINGS_PATH), apply_directives=False)
	company_references = load_company_building_references()
	building_map: dict[str, list[str]] = {}

	for building_name, raw_definition in sorted(parser.data.items()):
		definition = unwrap(raw_definition)
		if not isinstance(definition, dict):
			continue

		building_group = unwrap(definition.get("building_group"))
		if building_group != "bg_company_buildings":
			continue

		potential = unwrap(definition.get("potential"))
		company_types = company_references.get(building_name, [])
		if not company_types and isinstance(potential, dict) and "owner" in potential:
			company_types = sorted(collect_company_types(potential["owner"]))
		if not company_types:
			if isinstance(potential, dict) and unwrap(potential.get("always")) == "no":
				building_map[building_name] = []
				continue
			raise ValueError(f"{building_name} has no company type reference")

		building_map[building_name] = company_types

	if not building_map:
		raise ValueError("No bg_company_buildings entries found")

	return building_map


def render_company_requirement(company_types: list[str], indent: str) -> list[str]:
	if len(company_types) == 1:
		return [f"{indent}has_company = {company_types[0]}"]

	lines = [f"{indent}OR = {{"]
	for company_type in company_types:
		lines.append(f"{indent}\thas_company = {company_type}")
	lines.append(f"{indent}}}")
	return lines


def render_cleanup_effect(building_map: dict[str, list[str]]) -> str:
	lines = [
		"# ============================================================================",
		"# COMPANY BUILDING CLEANUP",
		"# Generated from common/buildings/company_buildings.txt by",
		"# gen_company_building_cleanup.py.",
		"# Removes company buildings that are no longer valid for the state's owner.",
		"# ============================================================================",
		"remove_invalid_company_buildings_effect = {",
	]

	for building_name, company_types in building_map.items():
		if company_types:
			lines.extend(
				[
					"\tif = {",
					"\t\tlimit = {",
					f"\t\t\thas_building = {building_name}",
					"\t\t\tNOT = {",
					"\t\t\t\towner = {",
				]
			)
			lines.extend(render_company_requirement(company_types, "\t\t\t\t\t"))
			lines.extend(
				[
					"\t\t\t\t}",
					"\t\t\t}",
					"\t\t}",
					f"\t\tremove_building = {building_name}",
					"\t}",
				]
			)
		else:
			lines.extend(
				[
					"\tif = {",
					"\t\tlimit = {",
					f"\t\t\thas_building = {building_name}",
					"\t\t}",
					f"\t\tremove_building = {building_name}",
					"\t}",
				]
			)

	lines.extend(
		[
			"}",
			"",
			"# Backward-compatible wrapper used by on_company_disbanded.",
			"remove_disbanded_company_buildings_effect = {",
			"\tremove_invalid_company_buildings_effect = yes",
			"}",
		]
	)

	return "\n".join(lines) + "\n"


def main() -> int:
	argument_parser = argparse.ArgumentParser()
	argument_parser.add_argument(
		"--check",
		action="store_true",
		help="Fail if the cleanup effect file is out of date.",
	)
	arguments = argument_parser.parse_args()

	building_map = load_company_building_map()
	content = render_cleanup_effect(building_map)

	if arguments.check:
		current_content = OUTPUT_PATH.read_text(encoding="utf-8-sig")
		if current_content != content:
			print(
				"company_building_cleanup_effects.txt is out of date. "
				"Run python gen_company_building_cleanup.py"
			)
			return 1
		print(
			f"company_building_cleanup_effects.txt is up to date "
			f"for {len(building_map)} company building types."
		)
		return 0

	OUTPUT_PATH.write_text(content, encoding="utf-8-sig", newline="\n")
	print(
		f"Wrote company_building_cleanup_effects.txt "
		f"for {len(building_map)} company building types."
	)
	return 0


if __name__ == "__main__":
	raise SystemExit(main())