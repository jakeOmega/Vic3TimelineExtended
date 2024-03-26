# -*- coding: utf-8 -*-
"""
Created on Sat Nov 26 14:02:35 2022

@author: jakef
"""

from pyparsing import nestedExpr, Word, alphanums, OneOrMore, ParseResults
import os

jobs = ["academics", "aristocrats", "bureaucrats", "capitalists", "clergymen", "clerks", "engineers",
        "farmers", "laborers", "machinists", "officers", "peasants", "professionals", "shopkeepers", "soldiers"]
required_text = "building_employment_{job}_add"
directories = [r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\production_methods",
               "G:\SteamLibrary\steamapps\common\Victoria 3\game\common\production_methods"]
structure = OneOrMore(Word(alphanums+'_-') + '=' + nestedExpr('{', '}'))
result = ""
output_file = r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\scripted_triggers\extra.txt"


def method_contains(method, text):
    if type(method) is not ParseResults:
        return False
    elif text in [method[i] for i in range(len(method))]:
        method_list = [method[i] for i in range(len(method))]
        if int(method_list[method_list.index(text)+2]) > 0:
            return True
        else:
            return method_contains(method[method_list.index(text)+1:], text)
    else:
        return any([method_contains(method_elem, text) for method_elem in method])


for job in jobs:
    failed_files = []
    method_success = []
    for directory in directories:
        for file in os.listdir(directory):
            with open(directory+'\\'+file, encoding='utf-8-sig') as file_obj:
                try:
                    file_text = file_obj.readlines()
                    file_text = '\n'.join(
                        [line for line in file_text if line[0] != '#'])
                    file_struct = structure.parseString(file_text)
                    for i in range(0, len(file_struct), 3):
                        method = file_struct[i]
                        if method_contains(file_struct[i+2], required_text.format(job=job)):
                            print(job, method)
                            method_success += [method]
                except Exception as e:
                    failed_files += [(directory+'\\'+file, e)]
    result += "employs_{job} = {{\n".format(job=job)
    result += "    OR = {\n"
    method_success = list(set(method_success))
    method_success.sort()
    for x in method_success:
        result += "        has_active_production_method = " + x + "\n"
    result += "    }\n"
    result += "}\n\n"
    if len(failed_files) > 1:
        print("failed files: ", failed_files)

with open(output_file, 'w') as file_obj:
    file_obj.write(result)
