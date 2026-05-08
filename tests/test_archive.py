import tempfile
import unittest
import zipfile
from pathlib import Path

from autouupbuild.archive import unsafe_zip_members, extract_zip_safe


class ArchiveTests(unittest.TestCase):
    def test_rejects_zip_path_traversal(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "bad.zip"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("../escape.txt", "bad")

            with self.assertRaises(ValueError):
                extract_zip_safe(zip_path, Path(tmp) / "out")

            self.assertFalse((Path(tmp).parent / "escape.txt").exists())

    def test_rejects_absolute_zip_member(self):
        self.assertEqual(unsafe_zip_members(["/absolute.txt"]), ["/absolute.txt"])

    def test_extracts_safe_zip(self):
        with tempfile.TemporaryDirectory() as tmp:
            zip_path = Path(tmp) / "safe.zip"
            output = Path(tmp) / "out"
            with zipfile.ZipFile(zip_path, "w") as archive:
                archive.writestr("folder/file.txt", "ok")

            extract_zip_safe(zip_path, output)

            self.assertEqual((output / "folder" / "file.txt").read_text(encoding="utf-8"), "ok")


if __name__ == "__main__":
    unittest.main()
