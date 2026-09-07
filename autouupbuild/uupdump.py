import re
import time
from dataclasses import dataclass
from pathlib import Path

import requests
from bs4 import BeautifulSoup


DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 3
DEFAULT_RETRY_DELAY = 5
GET_URL = "https://uupdump.net/fetchupd.php"
DOWNLOAD_URL = "https://uupdump.net/get.php"


@dataclass(frozen=True)
class BuildMetadata:
    uuid: str
    build: str
    title: str = ""


class UupDumpError(RuntimeError):
    pass


def parse_latest_build(html):
    return parse_latest_builds(html)[0]


def parse_latest_builds(html) -> list[BuildMetadata]:
    entries = parse_update_entries(html)
    if not entries:
        raise UupDumpError("Build number not found in UUP dump response")

    latest_by_branch = {}
    for entry in entries:
        if not is_full_windows_image(entry.title):
            continue
        version = build_sort_key(entry.build)
        branch = version[0]
        current = latest_by_branch.get(branch)
        if current is None or version > build_sort_key(current.build):
            latest_by_branch[branch] = entry
    if latest_by_branch:
        return sorted(latest_by_branch.values(), key=lambda entry: build_sort_key(entry.build), reverse=True)

    titles = ", ".join(entry.title or entry.uuid for entry in entries)
    raise UupDumpError(f"No full Windows image entry found in UUP dump response. Candidates: {titles}")


def parse_update_entries(html, fallback_build=None):
    soup = BeautifulSoup(html, "html.parser")
    links = []
    for link in soup.find_all("a"):
        href = link.get("href") or ""
        match = re.search(r"selectlang\.php\?id=([a-fA-F0-9-]+)", href)
        if match:
            links.append((link, match.group(1)))

    # Page-level metadata is unambiguous only for a single non-table candidate.
    if len(links) == 1 and links[0][0].find_parent("tr") is None:
        if not fallback_build:
            page_text = normalize_text(" ".join(
                text for text in soup.find_all(string=True) if text.find_parent("tr") is None
            ))
            build_match = re.search(r"Build number:\s*(\d+\.\d+)", page_text)
            fallback_build = build_match.group(1) if build_match else None
    else:
        fallback_build = None

    entries = []
    for link, uuid in links:
        title = normalize_text(link.get_text(" ", strip=True))
        build = extract_build_from_text(title)
        row = link.find_parent("tr")
        if not build and row is not None:
            # Exclude nested rows as well as siblings when resolving this entry.
            row_text = normalize_text(" ".join(
                text for text in row.find_all(string=True) if text.find_parent("tr") is row
            ))
            build = extract_build_from_text(row_text)
        build = build or fallback_build
        if not build:
            continue
        entries.append(BuildMetadata(uuid=uuid, build=build, title=title))
    return entries


def normalize_text(text):
    return re.sub(r"\s+", " ", text).strip()


def extract_build_from_text(text):
    match = re.search(r"(\d+\.\d+)", text)
    if match:
        return match.group(1)
    return None


def is_full_windows_image(title):
    normalized = title.lower()
    if not normalized.startswith("windows "):
        return False
    if " version " not in normalized and ", version " not in normalized:
        return False
    if re.search(r"\boobe\b|\bkb", normalized):
        return False
    blocked_terms = (
        "critical ",
        "cumulative update",
        "dynamic update",
        "servicing stack",
        "update for windows",
    )
    padded = f" {normalized} "
    return not any(term in padded for term in blocked_terms)


def build_sort_key(build):
    return tuple(int(part) for part in build.split("."))


def fetch_latest_build(arch="amd64", ring="retail", session=None, retries=DEFAULT_RETRIES, retry_delay=DEFAULT_RETRY_DELAY, sleep=time.sleep):
    return fetch_latest_builds(
        arch=arch,
        ring=ring,
        session=session,
        retries=retries,
        retry_delay=retry_delay,
        sleep=sleep,
    )[0]


def fetch_latest_builds(arch="amd64", ring="retail", session=None, retries=DEFAULT_RETRIES, retry_delay=DEFAULT_RETRY_DELAY, sleep=time.sleep) -> list[BuildMetadata]:
    session = session or requests
    url = f"{GET_URL}?arch={arch}&ring={ring}"
    response = request_with_retries(
        lambda: session.get(url, timeout=DEFAULT_TIMEOUT),
        retries=retries,
        retry_delay=retry_delay,
        sleep=sleep,
        action="fetch latest UUP build",
    )
    return parse_latest_builds(response.text)


def filename_from_headers(headers, build_id):
    content_disposition = headers.get("Content-Disposition", "")
    match = re.search(r'filename="?([^";]+)"?', content_disposition)
    if match:
        return Path(match.group(1)).name
    return f"uupdump_{build_id}.zip"


def download_package(
    build_id,
    output_dir,
    pack="zh-cn",
    edition="professional",
    session=None,
    retries=DEFAULT_RETRIES,
    retry_delay=DEFAULT_RETRY_DELAY,
    sleep=time.sleep,
):
    session = session or requests
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    url = f"{DOWNLOAD_URL}?id={build_id}&pack={pack}&edition={edition}"
    data = {
        "autodl": 2,
        "updates": 1,
        "cleanup": 1,
        "netfx": 1,
    }
    response = request_with_retries(
        lambda: session.post(url, data=data, stream=True, timeout=DEFAULT_TIMEOUT),
        retries=retries,
        retry_delay=retry_delay,
        sleep=sleep,
        action="download UUP package",
    )

    filename = filename_from_headers(response.headers, build_id)
    path = output_dir / filename
    with path.open("wb") as file:
        for chunk in response.iter_content(chunk_size=8192):
            if chunk:
                file.write(chunk)
    return path


def request_with_retries(request, retries, retry_delay, sleep, action):
    last_status = None
    last_error = None
    for attempt in range(retries + 1):
        try:
            response = request()
        except requests.RequestException as exc:
            last_error = exc
            if attempt < retries:
                sleep(retry_delay * (attempt + 1))
                continue
            raise UupDumpError(f"Failed to {action}: {exc}") from exc

        if response.status_code == 200:
            return response
        last_status = response.status_code
        if is_retryable_status(response.status_code) and attempt < retries:
            sleep(retry_delay * (attempt + 1))
            continue
        break

    if last_error:
        raise UupDumpError(f"Failed to {action}: {last_error}") from last_error
    raise UupDumpError(f"Failed to {action}: HTTP {last_status}")


def is_retryable_status(status_code):
    return status_code == 429 or 500 <= status_code < 600
