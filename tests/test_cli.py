import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autouupbuild import cli
from autouupbuild.uupdump import BuildMetadata


class CliTests(unittest.TestCase):
    def test_latest_all_branches_writes_json_github_output(self):
        builds = [
            BuildMetadata("c1c737c2-f2d9-4824-bb5b-1af515179099", "26200.9278", "Windows 11, version 25H2"),
            BuildMetadata("d922b79f-142d-4cf8-896b-515abfd01e66", "26100.9278", "Windows 11, version 24H2"),
        ]
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "github-output.txt"
            with (
                patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_path)}),
                patch("autouupbuild.cli.uupdump.fetch_latest_builds", return_value=builds, create=True) as fetch,
                patch("autouupbuild.cli.uupdump.download_package") as download,
            ):
                result = cli.main(["latest", "--all-branches", "--ring", "rp", "--github-output"])

            self.assertEqual(result, 0)
            fetch.assert_called_once_with(arch="amd64", ring="rp")
            download.assert_not_called()
            name, value = output_path.read_text(encoding="utf-8").strip().split("=", 1)
            self.assertEqual(name, "builds")
            self.assertEqual(json.loads(value), [
                {"uuid": build.uuid, "version": build.build, "title": build.title}
                for build in builds
            ])

    def test_latest_all_branches_prints_both_versions(self):
        builds = [
            BuildMetadata("25h2-id", "26200.9278", "Windows 11, version 25H2"),
            BuildMetadata("24h2-id", "26100.9278", "Windows 11, version 24H2"),
        ]
        with (
            patch("autouupbuild.cli.uupdump.fetch_latest_builds", return_value=builds, create=True),
            contextlib.redirect_stdout(io.StringIO()) as output,
        ):
            result = cli.main(["latest", "--all-branches"])
        self.assertEqual(result, 0)
        for build in builds:
            self.assertIn(build.build, output.getvalue())
            self.assertIn(build.uuid, output.getvalue())

    def test_fetch_pinned_version_never_queries_channel_latest(self):
        build_uuid = "d922b79f-142d-4cf8-896b-515abfd01e66"
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp)
            package = output / "package.zip"
            with (
                patch("autouupbuild.cli.uupdump.fetch_latest_build") as latest,
                patch("autouupbuild.cli.uupdump.download_package", return_value=package) as download,
                patch("autouupbuild.cli.extract_zip_safe") as extract,
            ):
                result = cli.main([
                    "fetch", "--uuid", build_uuid, "--build", "26100.9278",
                    "--ring", "rp", "--pack", "en-us", "--edition", "professional",
                    "--output", str(output),
                ])
            self.assertEqual(result, 0)
            latest.assert_not_called()
            download.assert_called_once_with(
                build_uuid, output_dir=output, pack="en-us", edition="professional",
            )
            extract.assert_called_once_with(package, output)
            self.assertEqual((output / "version").read_text(encoding="utf-8"), "26100.9278")

    def test_fetch_rejects_partial_or_invalid_pinned_metadata(self):
        valid_uuid = "d922b79f-142d-4cf8-896b-515abfd01e66"
        for arguments in [
            ["--uuid", valid_uuid],
            ["--build", "26100.9278"],
            ["--uuid", "../bad", "--build", "26100.9278"],
            ["--uuid", valid_uuid, "--build", "26100.9278\nEVIL=1"],
        ]:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as tmp:
                with (
                    patch("autouupbuild.cli.uupdump.fetch_latest_build") as latest,
                    patch("autouupbuild.cli.uupdump.download_package") as download,
                    contextlib.redirect_stderr(io.StringIO()),
                ):
                    result = cli.main(["fetch", "--output", tmp, *arguments])
                self.assertNotEqual(result, 0)
                latest.assert_not_called()
                download.assert_not_called()
                self.assertFalse((Path(tmp) / "version").exists())

    def test_latest_all_branches_failure_writes_no_builds(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "github-output.txt"
            with (
                patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_path)}),
                patch(
                    "autouupbuild.cli.uupdump.fetch_latest_builds",
                    side_effect=cli.uupdump.UupDumpError("HTTP 500"),
                    create=True,
                ),
                contextlib.redirect_stderr(io.StringIO()),
            ):
                result = cli.main(["latest", "--all-branches", "--github-output"])
            self.assertEqual(result, 1)
            self.assertFalse(output_path.exists())

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

    def test_latest_command_writes_github_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            output_path = Path(tmp) / "github-output.txt"
            with (
                patch.dict("os.environ", {"GITHUB_OUTPUT": str(output_path)}),
                patch("autouupbuild.cli.uupdump.fetch_latest_build", return_value=BuildMetadata("build-id", "26200.8328", "Windows 11, version 25H2")),
            ):
                exit_code = cli.main(["latest", "--arch", "amd64", "--ring", "rp", "--github-output"])

            self.assertEqual(exit_code, 0)
            self.assertEqual(
                output_path.read_text(encoding="utf-8").splitlines(),
                [
                    "version=26200.8328",
                    "uuid=build-id",
                    "title=Windows 11, version 25H2",
                ],
            )


if __name__ == "__main__":
    unittest.main()
