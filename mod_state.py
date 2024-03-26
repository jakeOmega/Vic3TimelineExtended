from paradox_file_parser import ParadoxFileParser
import os


class ModState:
    def __init__(self, base_game_dir, mod_dir, diff=False):
        self.base_parsers = {}
        self.mod_parsers = {}
        self.load_directory_files(base_game_dir, mod_dir, diff)

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
            if file_name.startswith("_"):
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
