# -*- coding: utf-8 -*-
"""
Created on Tue Jul 18 20:01:15 2023

@author: jakef
"""
import re

law_re = re.compile("(law_[a-z_]+) = {")

modifier_replacements = {} #"law_religious_schools": ("foo", "bar", "nap")}

def remove_institution_blocks(input_file_path, output_file_path):
    with open(input_file_path, "r") as input_file, open(output_file_path, "w") as output_file:
        count_braces = False
        brace_count = 0
        law = None
        for line in input_file:
            stripped_line = line.strip()
            match = law_re.match(stripped_line)
            if match:
                law = match.group(1)
            if stripped_line.startswith("institution_modifier ="):
                count_braces = True
            if count_braces:
                brace_count += stripped_line.count('{')
                brace_count -= stripped_line.count('}')
            if brace_count == 0 and count_braces:  # We've exited the block.
                count_braces = False
                if law in modifier_replacements.keys():
                    output_file.write("\tinstitution_modifier = {\n")
                    for e in modifier_replacements[law]:
                        output_file.write("\t\t" + e + "\n")
                    output_file.write("\t}\n")
                continue  # Skip this line as well.
            if not count_braces:
                output_file.write(line)


# Specify the paths to the input and output files.
input_file_path = r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\laws\00_education_system.txt"
output_file_path = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\laws\00_education_system.txt"

# Remove the institution blocks.
remove_institution_blocks(input_file_path, output_file_path)

# Specify the paths to the input and output files.
input_file_path = r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\laws\00_health_system.txt"
output_file_path = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\laws\00_health_system.txt"

# Remove the institution blocks.
remove_institution_blocks(input_file_path, output_file_path)

# Specify the paths to the input and output files.
input_file_path = r"G:\SteamLibrary\steamapps\common\Victoria 3\game\common\laws\00_policing.txt"
output_file_path = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\laws\00_policing.txt"

# Remove the institution blocks.
remove_institution_blocks(input_file_path, output_file_path)