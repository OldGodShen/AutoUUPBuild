import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from autouupbuild import uupdump


SAMPLE_HTML = """
<html>
  <body>
    <p>Build number: 26100.1234</p>
    <a href="selectlang.php?id=12345678-abcd-4abc-8def-1234567890ab">
      Windows 11, version 24H2 (26100.1234) amd64
    </a>
  </body>
</html>
"""

# Update lists link full Windows titles, not language names such as "zh-cn".
OOBE_FIRST_HTML = """
<html>
  <body>
    <table>
      <tr><td>
        <a href="selectlang.php?id=c3ae627d-7c3b-42f3-a86c-c13692444aed">
          Critical OOBE Update for Windows 11 - KB5078674 (26100.7900) (2) amd64
        </a>
      </td><td>Build number: 26100.7900</td></tr>
      <tr><td>
        <a href="selectlang.php?id=2de8f468-d3fa-4e4f-9462-48d86f9ba7af">
          Windows 11, version 25H2 (26200.9278) amd64
        </a>
      </td><td>Build number: 26200.9278</td></tr>
      <tr><td>
        <a href="selectlang.php?id=5662000d-11c7-40e1-bec3-357197281653">
          Windows 11, version 24H2 (26100.9278) amd64
        </a>
      </td><td>Build number: 26100.9278</td></tr>
    </table>
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

        self.assertEqual(metadata.build, "26200.9278")
        self.assertEqual(metadata.uuid, "2de8f468-d3fa-4e4f-9462-48d86f9ba7af")
        self.assertIn("version 25H2", metadata.title)

    def test_parse_latest_builds_real_list_keeps_25h2_and_24h2_with_matching_uuids(self):
        metadata = uupdump.parse_latest_builds(OOBE_FIRST_HTML)

        self.assertEqual(
            [(entry.build, entry.uuid) for entry in metadata],
            [
                ("26200.9278", "2de8f468-d3fa-4e4f-9462-48d86f9ba7af"),
                ("26100.9278", "5662000d-11c7-40e1-bec3-357197281653"),
            ],
        )
        self.assertTrue(all(uupdump.is_full_windows_image(entry.title) for entry in metadata))

    def test_parse_latest_builds_groups_numeric_branches_and_deduplicates_unordered_links(self):
        candidates = [
            ("26100.9999", "24H2", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa1"),
            ("26200.9", "25H2", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb1"),
            ("26100.10000", "24H2", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa2"),
            ("26200.10", "25H2", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"),
            ("26200.10", "25H2", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbb2"),
            ("26100.10000", "25H2", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaa3"),
        ]

        for ordered in (candidates, list(reversed(candidates)), candidates[2:] + candidates[:2]):
            with self.subTest(order=ordered):
                html = "".join(
                    f'<a href="selectlang.php?id={uuid}">'
                    f"Windows 11, version {version} ({build}) amd64</a>"
                    for build, version, uuid in ordered
                )

                metadata = uupdump.parse_latest_builds(html)

                self.assertEqual([entry.build for entry in metadata], ["26200.10", "26100.10000"])
                for entry in metadata:
                    self.assertIn((entry.build, entry.uuid), [(build, uuid) for build, _, uuid in candidates])

    def test_parse_latest_builds_sorts_branches_numerically(self):
        html = """
        <a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">
          Windows 11, version 24H2 (9999.9999) amd64
        </a>
        <a href="selectlang.php?id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb">
          Windows 11, version 25H2 (10000.1) amd64
        </a>
        """

        self.assertEqual(
            [entry.build for entry in uupdump.parse_latest_builds(html)],
            ["10000.1", "9999.9999"],
        )

    def test_parse_latest_builds_accepts_one_full_image(self):
        metadata = uupdump.parse_latest_builds(SAMPLE_HTML)

        self.assertEqual(
            metadata,
            [
                uupdump.BuildMetadata(
                    uuid="12345678-abcd-4abc-8def-1234567890ab",
                    build="26100.1234",
                    title="Windows 11, version 24H2 (26100.1234) amd64",
                )
            ],
        )

    def test_single_full_image_can_use_page_build_number(self):
        html = SAMPLE_HTML.replace(" (26100.1234)", "")

        self.assertEqual(uupdump.parse_latest_build(html).build, "26100.1234")
        self.assertEqual([entry.build for entry in uupdump.parse_latest_builds(html)], ["26100.1234"])

    def test_single_oobe_or_kb_only_candidate_is_rejected(self):
        titles = [
            "Critical OOBE Update for Windows 11 - KB5078674 (26100.7900) (2) amd64",
            "Windows 11, version 25H2 OOBE (26200.9999) amd64",
            "Windows 11, version 25H2 (26200.9999) KB5078674 amd64",
            "Windows 11, version 25H2 (26200.9999) (KB5078674) amd64",
            "Windows 11, version 25H2 [OOBE] (26200.9999) amd64",
            "Cumulative Update for Windows 11 (26200.9999) amd64",
            "KB5078674 (26200.9999) amd64",
            "zh-cn",
        ]
        for title in titles:
            html = (
                "<p>Build number: 26200.9999</p>"
                '<a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">'
                f"{title}</a>"
            )
            for name in ("parse_latest_build", "parse_latest_builds"):
                with self.subTest(title=title, parser=name):
                    with self.assertRaisesRegex(uupdump.UupDumpError, "No full Windows image"):
                        getattr(uupdump, name)(html)

    def test_parse_latest_builds_excludes_newer_update_only_entries(self):
        html = OOBE_FIRST_HTML + """
        <a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">
          Windows 11, version 25H2 (26200.9999) KB5078674 amd64
        </a>
        <a href="selectlang.php?id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb">
          Windows 11, version 24H2 OOBE (26100.9999) amd64
        </a>
        """

        self.assertEqual(
            [entry.build for entry in uupdump.parse_latest_builds(html)],
            ["26200.9278", "26100.9278"],
        )

    def test_no_full_images_raises_instead_of_returning_empty_or_update(self):
        pages = [
            "<html><body>No updates found.</body></html>",
            """
            <a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">
              Critical OOBE Update for Windows 11 (26100.7900) amd64
            </a>
            <a href="selectlang.php?id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb">
              KB5078674 (26200.9999) amd64
            </a>
            """,
        ]
        for html in pages:
            for name in ("parse_latest_build", "parse_latest_builds"):
                with self.subTest(html=html, parser=name):
                    with self.assertRaises(uupdump.UupDumpError):
                        getattr(uupdump, name)(html)

    def test_each_candidate_uses_only_its_own_table_row_build(self):
        html = """
        <p>Build number: 99999.9999</p>
        <table>
          <tr><td>
            <a href="selectlang.php?id=cccccccc-cccc-4ccc-8ccc-cccccccccccc">
              Critical OOBE Update for Windows 11 - KB5078674 amd64
            </a>
          </td><td>Build number: 26100.7900</td></tr>
          <tr><td>
            <a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">
              Windows 11, version 24H2 amd64
            </a>
          </td><td>Build number: 26100.9278</td></tr>
          <tr><td>
            <a href="selectlang.php?id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb">
              Windows 11, version 25H2 amd64
            </a>
          </td><td>Build number: 26200.9278</td></tr>
        </table>
        """

        expected = [
            ("26200.9278", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"),
            ("26100.9278", "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"),
        ]
        self.assertEqual(uupdump.parse_latest_build(html).build, "26200.9278")
        self.assertEqual(
            [(entry.build, entry.uuid) for entry in uupdump.parse_latest_builds(html)],
            expected,
        )

    def test_missing_build_never_uses_another_row_or_page_build_in_multi_entry_list(self):
        for unknown in (
            '<tr><td><a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">'
            "Windows 11, version 25H2 amd64</a></td></tr>",
            '<a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">'
            "Windows 11, version 25H2 amd64</a>",
        ):
            with self.subTest(unknown=unknown):
                html = f"""
                <p>Build number: 99999.9999</p>
                <table>
                  <tr><td>
                    <a href="selectlang.php?id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb">
                      Windows 11, version 24H2 (26100.9278) amd64
                    </a>
                  </td><td>Build number: 26100.9278</td></tr>
                  {unknown}
                </table>
                """

                self.assertEqual(uupdump.parse_latest_build(html).build, "26100.9278")
                self.assertEqual(
                    [(entry.build, entry.uuid) for entry in uupdump.parse_latest_builds(html)],
                    [("26100.9278", "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb")],
                )

    def test_unversioned_full_image_cannot_borrow_the_only_versioned_oobe_row(self):
        html = """
        <table>
          <tr><td>
            <a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">
              Critical OOBE Update for Windows 11 amd64
            </a>
          </td><td>Build number: 26100.7900</td></tr>
          <tr><td>
            <a href="selectlang.php?id=bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb">
              Windows 11, version 25H2 amd64
            </a>
          </td></tr>
        </table>
        """

        for name in ("parse_latest_build", "parse_latest_builds"):
            with self.subTest(parser=name):
                with self.assertRaises(uupdump.UupDumpError):
                    getattr(uupdump, name)(html)

    def test_single_candidate_never_borrows_build_from_another_table_row(self):
        link = (
            '<a href="selectlang.php?id=aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa">'
            "Windows 11, version 25H2 amd64</a>"
        )
        pages = [
            f"<table><tr><td>Build number: 26200.9278</td></tr><tr><td>{link}</td></tr></table>",
            f"<table><tr><td>Build number: 26200.9278</td></tr></table>{link}",
            f"<table><tr><td>{link}<table><tr><td>Build number: 26200.9278</td></tr></table></td></tr></table>",
        ]
        for html in pages:
            for name in ("parse_latest_build", "parse_latest_builds"):
                with self.subTest(html=html, parser=name):
                    with self.assertRaises(uupdump.UupDumpError):
                        getattr(uupdump, name)(html)

    def test_title_build_takes_precedence_over_row_and_page_builds(self):
        html = f"""
        <p>Build number: 99999.9999</p>
        <table><tr><td>{SAMPLE_HTML}</td><td>Build number: 26200.9278</td></tr></table>
        """

        self.assertEqual(
            [(entry.build, entry.uuid) for entry in uupdump.parse_latest_builds(html)],
            [("26100.1234", "12345678-abcd-4abc-8def-1234567890ab")],
        )

    def test_parse_latest_build_reuses_plural_parser(self):
        latest = uupdump.BuildMetadata("latest-id", "26200.9278")
        older = uupdump.BuildMetadata("older-id", "26100.9278")
        with patch.object(uupdump, "parse_latest_builds", return_value=[latest, older]) as parse:
            self.assertIs(uupdump.parse_latest_build(SAMPLE_HTML), latest)

        parse.assert_called_once_with(SAMPLE_HTML)

    def test_fetch_latest_builds_requests_selected_rp_channel_once(self):
        sleeps = []
        session = FakeSession(FakeResponse(status_code=200, text=OOBE_FIRST_HTML))

        metadata = uupdump.fetch_latest_builds(
            arch="arm64",
            ring="rp",
            session=session,
            retries=3,
            retry_delay=7,
            sleep=sleeps.append,
        )

        self.assertEqual(
            [(entry.build, entry.uuid) for entry in metadata],
            [
                ("26200.9278", "2de8f468-d3fa-4e4f-9462-48d86f9ba7af"),
                ("26100.9278", "5662000d-11c7-40e1-bec3-357197281653"),
            ],
        )
        self.assertEqual(
            session.calls,
            [{
                "method": "get",
                "url": "https://uupdump.net/fetchupd.php?arch=arm64&ring=rp",
                "timeout": uupdump.DEFAULT_TIMEOUT,
            }],
        )
        self.assertEqual(sleeps, [])

    def test_fetch_latest_build_reuses_plural_fetcher_and_forwards_all_arguments(self):
        latest = uupdump.BuildMetadata("latest-id", "26200.9278")
        older = uupdump.BuildMetadata("older-id", "26100.9278")
        session = FakeSession()
        sleeps = []
        kwargs = {
            "arch": "arm64",
            "ring": "rp",
            "session": session,
            "retries": 2,
            "retry_delay": 7,
            "sleep": sleeps.append,
        }
        with patch.object(uupdump, "fetch_latest_builds", return_value=[latest, older]) as fetch:
            self.assertIs(uupdump.fetch_latest_build(**kwargs), latest)

        fetch.assert_called_once_with(**kwargs)
        self.assertEqual(session.calls, [])

    def test_fetch_latest_build_returns_global_latest_with_one_request(self):
        session = FakeSession(FakeResponse(status_code=200, text=OOBE_FIRST_HTML))

        metadata = uupdump.fetch_latest_build(ring="rp", session=session)

        self.assertEqual(metadata.build, "26200.9278")
        self.assertEqual(metadata.uuid, "2de8f468-d3fa-4e4f-9462-48d86f9ba7af")
        self.assertEqual(len(session.calls), 1)
        self.assertEqual(session.calls[0]["url"], "https://uupdump.net/fetchupd.php?arch=amd64&ring=rp")

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

        self.assertEqual(metadata.build, "26200.9278")
        self.assertEqual(len(session.calls), 2)
        self.assertEqual(sleeps, [5])

    def test_fetch_latest_builds_retries_transient_server_error(self):
        sleeps = []
        session = FakeSession(
            FakeResponse(status_code=500, text="server error"),
            FakeResponse(status_code=200, text=OOBE_FIRST_HTML),
        )

        metadata = uupdump.fetch_latest_builds(
            ring="rp",
            session=session,
            retries=3,
            retry_delay=5,
            sleep=sleeps.append,
        )

        self.assertEqual([entry.build for entry in metadata], ["26200.9278", "26100.9278"])
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
