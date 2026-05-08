import configparser
import tempfile
import unittest
from pathlib import Path

from autouupbuild.config import configure_convert_config, uncomment_custom_apps


BASE_INI = """
[convert-UUP]
AutoStart = 0
ResetBase = 0
SkipISO = 0
SkipWinRE = 0
AutoExit = 0

[Store_Apps]
StubAppsFull = 0
CustomList = 0

[create_virtual_editions]
vAutoStart = 1
"""


class ConfigTests(unittest.TestCase):
    def test_applies_iso_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "ConvertConfig.ini"
            config_path.write_text(BASE_INI, encoding="utf-8")

            configure_convert_config(config_path, "iso")

            config = read_config(config_path)
            self.assertEqual(config["convert-UUP"]["AutoStart"], "1")
            self.assertEqual(config["convert-UUP"]["SkipISO"], "0")
            self.assertEqual(config["Store_Apps"]["CustomList"], "1")
            self.assertEqual(config["create_virtual_editions"]["vAutoStart"], "0")

    def test_applies_wim_preset(self):
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "ConvertConfig.ini"
            config_path.write_text(BASE_INI, encoding="utf-8")

            configure_convert_config(config_path, "wim")

            config = read_config(config_path)
            self.assertEqual(config["convert-UUP"]["AutoStart"], "3")
            self.assertEqual(config["convert-UUP"]["SkipISO"], "1")

    def test_uncomment_custom_apps_preserves_unrelated_lines(self):
        content = "\n".join(
            [
                "# Microsoft.WindowsStore_8wekyb3d8bbwe",
                "# Unrelated.App",
                "Already.Enabled",
                "",
            ]
        )
        with tempfile.TemporaryDirectory() as tmp:
            apps_path = Path(tmp) / "CustomAppsList.txt"
            apps_path.write_text(content, encoding="utf-8")

            changed = uncomment_custom_apps(apps_path)

            self.assertEqual(changed, 1)
            self.assertEqual(
                apps_path.read_text(encoding="utf-8").splitlines(),
                [
                    "Microsoft.WindowsStore_8wekyb3d8bbwe",
                    "# Unrelated.App",
                    "Already.Enabled",
                ],
            )


def read_config(path):
    config = configparser.ConfigParser()
    config.optionxform = str
    config.read(path, encoding="utf-8")
    return config


if __name__ == "__main__":
    unittest.main()
