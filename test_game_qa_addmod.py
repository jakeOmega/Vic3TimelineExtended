"""game_qa/addmod.py: a session's variant mod folder (`start --add-mod`, #1702 item 2), and the path rule it shares
with `launch --add-mod`.

A temp folder stands in for WSL's `/mnt`: `D:\\…` converts to `<tmp>/mnt/d/…`, and the user-data folder lives at
`<tmp>/mnt/c/Users/someone/Documents/Paradox Interactive/Victoria 3`, so every check runs against real folders,
links and files. No wslpath is run.
"""
import json
import tempfile
import unittest
from pathlib import Path

from game_qa import __main__ as cli
from game_qa import addmod

USER_WIN = r"C:\Users\someone\Documents\Paradox Interactive\Victoria 3"
DEPLOYED_WIN = USER_WIN + r"\mod\Vic3TimelineExtended"
VARIANT_WIN = r"D:\vic3te-data\qa-addmod-test"
META = {"name": "TE QA add-mod test", "id": "", "version": "0.0.1", "supported_game_version": "1.15.1",
        "short_description": "x", "tags": [], "relationships": [], "game_custom_data": {}}


class AddModTest(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.mnt = Path(tmp.name) / "mnt"
        self.user = self.to_wsl(USER_WIN)
        (self.user / "mod" / "Vic3TimelineExtended").mkdir(parents=True)
        self.variant = self.make_mod(VARIANT_WIN)
        self.converted: list[str] = []

    def to_wsl(self, path: str) -> Path:
        drive, rest = path[0].lower(), path[3:].rstrip("\\")
        return self.mnt.joinpath(drive, *[p for p in rest.split("\\") if p])

    def converter(self, path: str) -> Path:
        self.converted.append(path)
        return self.to_wsl(path)

    def make_mod(self, windows: str, meta=META, bom=False) -> Path:
        folder = self.to_wsl(windows)
        (folder / ".metadata").mkdir(parents=True, exist_ok=True)
        text = json.dumps(meta, indent="\t") if not isinstance(meta, str) else meta
        (folder / ".metadata" / "metadata.json").write_text(("\ufeff" if bom else "") + text, encoding="utf-8")
        return folder

    def check(self, path, **kwargs):
        kwargs.setdefault("to_wsl", self.converter)
        kwargs.setdefault("deployed", self.user / "mod" / "Vic3TimelineExtended")
        kwargs.setdefault("deployed_windows", DEPLOYED_WIN)
        return addmod.check(path, self.user, kwargs.pop("user_windows", USER_WIN), **kwargs)

    def refused(self, path, **kwargs) -> addmod.AddModError:
        with self.assertRaises(addmod.AddModError) as caught:
            self.check(path, **kwargs)
        return caught.exception

    def test_a_variant_folder_on_another_drive(self):
        found = self.check(VARIANT_WIN)
        self.assertEqual(found, addmod.AddMod(VARIANT_WIN, str(self.variant), "TE QA add-mod test", "0.0.1"))
        self.assertEqual(self.check(VARIANT_WIN + "\\").wsl, str(self.variant))     # a trailing separator
        self.make_mod(r"D:\with bom", bom=True)
        self.assertEqual(self.check(r"D:\with bom").name, "TE QA add-mod test")

    def test_spellings_that_are_not_one_plain_folder_are_refused_before_any_conversion(self):
        for path in (r"\\server\share\mod", "D:/vic3te-data/x", r"D:\vic3te-data/x", "D:\\", r"D:\a\..\b",
                     r"D:\a\.\b", r"D:\a\\b", r"D:\vic3te-data.", r"D:\vic3te-data ", r"D:\VIC3TE~1\x",
                     r"D:\a\NUL", r"D:\a\com1.txt", r"D:\a:b", r'D:\a"b', r"D:\a|b", r"D:\a?b", r"D:\a*b",
                     r"vic3te-data\x", "/mnt/d/x", "D:\\a\tb", "D:\\a\ud800b", "D:x"):
            with self.subTest(path=path):
                self.assertEqual(self.refused(path).code, "bad_argument")
        self.assertEqual(self.converted, [])

    def test_inside_or_holding_the_user_data_folder_by_its_windows_spelling(self):
        for path in (USER_WIN, USER_WIN + r"\mod\x", USER_WIN.lower() + r"\MOD\x", USER_WIN.upper() + "\\"):
            with self.subTest(path=path):
                self.assertEqual(self.refused(path).code, "inside_user_data")
        self.assertEqual(self.refused(r"C:\Users\someone\Documents").code, "holds_user_data")
        self.assertEqual(self.refused("C:\\Users").code, "holds_user_data")
        # a sibling whose name begins like the folder's is outside it
        self.make_mod(USER_WIN + " backups")
        self.assertEqual(self.check(USER_WIN + " backups").windows, USER_WIN + " backups")

    def test_inside_the_user_data_folder_by_the_folders_identity(self):
        # E:\ is the same drive folder as C:\Users\someone\Documents\Paradox Interactive under another name (a second
        # mount, say): no spelling test can see it, the identity walk does
        alias = Path(str(self.user.parent))
        self.mnt.joinpath("e").symlink_to(alias, target_is_directory=True)
        inside = self.make_mod(USER_WIN + r"\mod\inside")

        def converter(path):
            return Path(str(self.to_wsl(path)).replace(str(self.mnt / "e"), str(alias)))
        self.assertTrue(inside.is_dir())
        self.assertEqual(self.refused(r"E:\Victoria 3\mod\inside", to_wsl=converter).code, "inside_user_data")
        self.assertEqual(self.refused(r"E:\Victoria 3\mod\inside", to_wsl=converter, user_windows=None).code,
                         "inside_user_data")

    def test_a_link_anywhere_on_the_way_is_refused(self):
        real = self.make_mod(r"D:\real\variant")
        self.mnt.joinpath("d", "linked").symlink_to(real.parent, target_is_directory=True)
        self.assertEqual(self.refused(r"D:\linked\variant").code, "symlink")
        self.mnt.joinpath("d", "variant_link").symlink_to(real, target_is_directory=True)
        self.assertEqual(self.refused(r"D:\variant_link").code, "symlink")
        self.mnt.joinpath("d", "into_user").symlink_to(self.user / "mod", target_is_directory=True)
        self.assertEqual(self.refused(r"D:\into_user\Vic3TimelineExtended").code, "symlink")

    def test_a_folder_that_is_not_there_or_is_a_file(self):
        self.assertEqual(self.refused(r"D:\nothing\here").code, "no_folder")
        self.to_wsl(r"D:\a_file").write_text("x")
        self.assertEqual(self.refused(r"D:\a_file").code, "no_folder")

    def test_metadata_must_be_a_real_json_object(self):
        bare = self.to_wsl(r"D:\bare")
        bare.mkdir(parents=True)
        self.assertEqual(self.refused(r"D:\bare").code, "no_metadata")
        self.make_mod(r"D:\not_json", meta="{ name = x }")
        self.assertEqual(self.refused(r"D:\not_json").code, "bad_metadata")
        self.make_mod(r"D:\a_list", meta="[]")
        self.assertEqual(self.refused(r"D:\a_list").code, "bad_metadata")
        linked = self.to_wsl(r"D:\linked_meta")
        (linked / ".metadata").mkdir(parents=True)
        (linked / ".metadata" / "metadata.json").symlink_to(self.variant / ".metadata" / "metadata.json")
        self.assertEqual(self.refused(r"D:\linked_meta").code, "no_metadata")
        self.make_mod(r"D:\odd_fields", meta={"name": 7})
        self.assertEqual(self.check(r"D:\odd_fields").name, None)

    def test_one_the_owners_playset_enables_is_refused_under_current_only(self):
        owner = [DEPLOYED_WIN, VARIANT_WIN.lower() + "\\"]
        self.assertEqual(self.refused(VARIANT_WIN, playset="current", owner_mods=owner).code, "already_enabled")
        self.assertEqual(self.check(VARIANT_WIN, playset="mod_only", owner_mods=owner).windows, VARIANT_WIN)

    def test_the_deployed_mod_configured_outside_the_user_data_folder(self):
        deployed = self.make_mod(r"D:\deployed\Vic3TimelineExtended")
        kwargs = {"deployed": deployed, "deployed_windows": r"D:\deployed\Vic3TimelineExtended"}
        self.assertEqual(self.refused(r"d:\DEPLOYED\Vic3TimelineExtended", **kwargs).code, "is_deployed_mod")
        self.assertEqual(self.refused(r"D:\deployed", **kwargs).code, "holds_user_data")

    def test_a_conversion_that_lands_elsewhere_is_refused(self):
        self.assertEqual(self.refused(VARIANT_WIN, to_wsl=lambda p: self.variant.parent).code, "bad_argument")

        def broken(path):
            raise OSError("wslpath: not found")
        self.assertEqual(self.refused(VARIANT_WIN, to_wsl=broken).code, "bad_argument")

    def test_check_all_refuses_a_folder_given_twice(self):
        common = {"user_data": self.user, "user_data_windows": USER_WIN, "to_wsl": self.converter}
        self.assertEqual(len(addmod.check_all([VARIANT_WIN], **common)), 1)
        with self.assertRaises(addmod.AddModError) as caught:
            addmod.check_all([VARIANT_WIN, VARIANT_WIN.upper() + "\\"], **common)
        self.assertEqual(caught.exception.code, "bad_argument")


class LaunchRuleTest(unittest.TestCase):
    """`launch --add-mod` keeps its refusals, word for word, now that the rule lives in addmod.path_problem."""

    def refusal(self, path: str) -> str:
        with self.assertRaises(cli._Refused) as caught:
            cli._check_mod_paths([path])
        return caught.exception.result["detail"]

    def test_the_three_refusals(self):
        self.assertIn("the --add-mod path 'D:\\\\a\\ud800' cannot be written as UTF-8", self.refusal("D:\\a\ud800"))
        self.assertIn("the --add-mod path 'D:\\\\a\\tb' has a control character in it", self.refusal("D:\\a\tb"))
        self.assertIn("the --add-mod path '/mnt/d/x' is not a Windows path (C:\\… or \\\\server\\…): convert a WSL "
                      "path with `wslpath -w`", self.refusal("/mnt/d/x"))
        cli._check_mod_paths([r"\\server\share", r"D:\x"])     # launch's own rule takes these
        self.assertIsNone(addmod.path_problem(r"D:\x"))


if __name__ == "__main__":
    unittest.main()
