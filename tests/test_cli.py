import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autouupbuild import cli
from autouupbuild.uupdump import BuildMetadata


class CliTests(unittest.TestCase):
    def test_configure_command_updates_files(self):
        ini = """
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
        with tempfile.TemporaryDirectory() as tmp:
            config_path = Path(tmp) / "ConvertConfig.ini"
            apps_path = Path(tmp) / "CustomAppsList.txt"
            config_path.write_text(ini, encoding="utf-8")
            apps_path.write_text("# Microsoft.WindowsStore_8wekyb3d8bbwe\n", encoding="utf-8")

            exit_code = cli.main(
                [
                    "configure",
                    "--artifact",
                    "iso",
                    "--config",
                    str(config_path),
                    "--apps-list",
                    str(apps_path),
                ]
            )

            self.assertEqual(exit_code, 0)
            self.assertIn("AutoStart = 1", config_path.read_text(encoding="utf-8"))
            self.assertEqual(apps_path.read_text(encoding="utf-8"), "Microsoft.WindowsStore_8wekyb3d8bbwe\n")

    def test_fetch_command_writes_version_and_extracts_package(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            zip_path = output / "package.zip"
            zip_path.write_bytes(b"zip")

            with (
                patch("autouupbuild.cli.uupdump.fetch_latest_build", return_value=BuildMetadata("build-id", "26100.1234")),
                patch("autouupbuild.cli.uupdump.download_package", return_value=zip_path) as download_mock,
                patch("autouupbuild.cli.extract_zip_safe") as extract_mock,
            ):
                exit_code = cli.main(["fetch", "--output", str(output)])

            self.assertEqual(exit_code, 0)
            self.assertEqual((output / "version").read_text(encoding="utf-8"), "26100.1234")
            download_mock.assert_called_once()
            extract_mock.assert_called_once_with(zip_path, output)


if __name__ == "__main__":
    unittest.main()
