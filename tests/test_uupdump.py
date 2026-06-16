import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autouupbuild import uupdump


SAMPLE_HTML = """
<html>
  <body>
    <p>Build number: 26100.1234</p>
    <a href="selectlang.php?id=12345678-abcd-4abc-8def-1234567890ab">zh-cn</a>
  </body>
</html>
"""

OOBE_FIRST_HTML = """
<html>
  <body>
    <a href="selectlang.php?id=c3ae627d-7c3b-42f3-a86c-c13692444aed">
      Critical OOBE Update for Windows 11 - KB5078674 (26100.7900) (2) amd64
    </a>
    <a href="selectlang.php?id=2de8f468-d3fa-4e4f-9462-48d86f9ba7af">
      Windows 11, version 25H2 (26200.8328) amd64
    </a>
    <a href="selectlang.php?id=5662000d-11c7-40e1-bec3-357197281653">
      Windows 11, version 24H2 (26100.8328) amd64
    </a>
  </body>
</html>
"""


class UupDumpTests(unittest.TestCase):
    def test_extract_build_number_and_uuid_from_html(self):
        metadata = uupdump.parse_latest_build(SAMPLE_HTML)

        self.assertEqual(metadata.build, "26100.1234")
        self.assertEqual(metadata.uuid, "12345678-abcd-4abc-8def-1234567890ab")

    def test_parse_latest_build_has_no_file_side_effects(self):
        with tempfile.TemporaryDirectory() as tmp:
            with patch("pathlib.Path.open", wraps=Path.open) as open_mock:
                metadata = uupdump.parse_latest_build(SAMPLE_HTML)

            self.assertEqual(metadata.build, "26100.1234")
            self.assertFalse((Path(tmp) / "version").exists())
            open_mock.assert_not_called()

    def test_parse_latest_build_skips_oobe_update_and_uses_latest_full_image(self):
        metadata = uupdump.parse_latest_build(OOBE_FIRST_HTML)

        self.assertEqual(metadata.build, "26200.8328")
        self.assertEqual(metadata.uuid, "2de8f468-d3fa-4e4f-9462-48d86f9ba7af")
        self.assertIn("version 25H2", metadata.title)

    def test_fetch_latest_build_retries_transient_server_error(self):
        sleeps = []
        session = FakeSession(
            FakeResponse(status_code=500, text="server error"),
            FakeResponse(status_code=200, text=OOBE_FIRST_HTML),
        )

        metadata = uupdump.fetch_latest_build(
            arch="amd64",
            ring="rp",
            session=session,
            retries=3,
            retry_delay=5,
            sleep=sleeps.append,
        )

        self.assertEqual(metadata.build, "26200.8328")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(sleeps, [5])

    def test_download_filename_from_content_disposition(self):
        headers = {"Content-Disposition": 'attachment; filename="download.zip"'}

        self.assertEqual(uupdump.filename_from_headers(headers, "abc"), "download.zip")

    def test_download_filename_falls_back_to_id(self):
        self.assertEqual(uupdump.filename_from_headers({}, "abc"), "uupdump_abc.zip")

    def test_download_package_writes_response_chunks(self):
        response = FakeResponse(
            status_code=200,
            headers={"Content-Disposition": 'attachment; filename="uup.zip"'},
            chunks=[b"one", b"", b"two"],
        )

        with tempfile.TemporaryDirectory() as tmp:
            session = FakeSession(response)
            path = uupdump.download_package(
                "build-id",
                output_dir=Path(tmp),
                session=session,
                sleep=lambda _: None,
            )

            self.assertEqual(path.name, "uup.zip")
            self.assertEqual(path.read_bytes(), b"onetwo")
            self.assertEqual(len(session.calls), 1)
            self.assertEqual(session.calls[0]["url"], "https://uupdump.net/get.php?id=build-id&pack=zh-cn&edition=professional")


class FakeResponse:
    def __init__(self, status_code, headers=None, text="", chunks=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = text
        self.content = text.encode("utf-8")
        self._chunks = chunks or []

    def iter_content(self, chunk_size=8192):
        yield from self._chunks


class FakeSession:
    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []

    def get(self, url, timeout):
        self.calls.append({"method": "get", "url": url, "timeout": timeout})
        return self.responses.pop(0)

    def post(self, url, data, stream, timeout):
        self.calls.append({"method": "post", "url": url, "data": data, "stream": stream, "timeout": timeout})
        return self.responses.pop(0)


if __name__ == "__main__":
    unittest.main()
