starting_text = r"""
update_gov_services_effect = {
    if = {
        limit = {
            AND = {
                government_service_need = 0
                has_building = building_government_services
            }
        }
        remove_building = building_government_services
    }"""

block_text = """
    else_if = {{
        limit = {{government_service_need = {level}}}
        create_building = {{
            building = building_government_services
            level = {level}
        }}
    }}"""

end_text = r"""
}"""

with open(
    r"F:\Libraries\Documents\Paradox Interactive\Victoria 3\mod\Production Methods\common\scripted_effects\gov_service_effect.txt",
    "w",
) as f:
    f.write(starting_text)
    for level in range(1, 1501):
        f.write(block_text.format(level=level))
    f.write(end_text)
