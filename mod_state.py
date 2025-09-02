import os

from paradox_file_parser import ParadoxFileParser


class ModState:
    def __init__(self, base_game_dir, mod_dir, diff=False):
        self.base_parsers = {}
        self.mod_parsers = {}
        self.localization = {}
        self.load_directory_files(base_game_dir, mod_dir, diff)

    def add_localization(self, loc_path):
        for file_name in os.listdir(loc_path):
            if not file_name.endswith(".yml"):
                continue
            file_path = os.path.join(loc_path, file_name)
            with open(file_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("#") or (":" not in line):
                        continue
                    key, value = line.split(":", 1)
                    key = key.strip()
                    quote_locations = [i for i, c in enumerate(value) if c == '"']
                    if len(quote_locations) >= 2:
                        value = value[
                            quote_locations[0] + 1 : quote_locations[1]
                        ].strip()
                    self.localization[key] = value

    def load_directory_files(self, base_game_dir, mod_dir, diff=False):
        for entity_type, dir_path in base_game_dir.items():
            self.base_parsers[entity_type] = ParadoxFileParser()
            self.mod_parsers[entity_type] = ParadoxFileParser()
            self.load_files_from_directory(entity_type, dir_path, base_game=True)

            if diff:
                self.mod_parsers[entity_type].set_data_from_changes_json(
                    self.base_parsers[entity_type],
                    mod_dir + os.sep + entity_type + ".json",
                )
            else:
                if entity_type in mod_dir:
                    self.load_files_from_directory(
                        entity_type, mod_dir[entity_type], base_game=False
                    )

    def load_files_from_directory(self, entity_type, dir_path, base_game=True):
        for file_name in os.listdir(dir_path):
            if file_name.startswith("_") or (file_name[-3:] == ".md"):
                print("skipping file:", file_name)
                continue
            file_path = os.path.join(dir_path, file_name)
            if os.path.isfile(file_path):
                print("reading file:", file_path)
                if base_game:
                    self.base_parsers[entity_type].parse_file(file_path)
                    self.mod_parsers[entity_type].parse_file(file_path)
                else:
                    mod_data = self.parse_mod_file(file_path)
                    self.mod_parsers[entity_type].merge_data(mod_data)

    def parse_mod_file(self, file_path):
        parser = ParadoxFileParser()
        parser.parse_file(file_path)
        return parser.data

    def get_data(self, entity_type):
        return (
            self.mod_parsers[entity_type].data
            if entity_type in self.mod_parsers
            else None
        )

    def get_string_form(self, entity_type):
        return (
            str(self.mod_parsers[entity_type])
            if entity_type in self.mod_parsers
            else None
        )

    def update_and_write_file(self, entity_type, file_path):
        if entity_type in self.mod_parsers:
            self.mod_parsers[entity_type].write_file(
                file_path, self.base_parsers[entity_type]
            )
        else:
            raise Exception(f"entity_type {entity_type} not found")

    def save_changes_to_json(self, file_path, entity_type=None):
        if entity_type is None:
            for entity_type in self.mod_parsers:
                self.mod_parsers[entity_type].save_changes_to_json(
                    self.base_parsers[entity_type],
                    file_path + os.sep + entity_type + ".json",
                )
        else:
            if entity_type in self.mod_parsers:
                self.mod_parsers[entity_type].save_changes_to_json(
                    self.base_parsers[entity_type], file_path
                )
            else:
                raise Exception(f"entity_type {entity_type} not found")

    def localize(self, text):
        if text in self.localization:
            return self.localization[text]
        return text

    def get_description(self, text):
        desc_key = text + "_desc"
        if desc_key in self.localization:
            return self.localization[desc_key]
        return None
