import argparse
import json
import re
import sys
from pathlib import Path
from uuid import UUID

from . import uupdump
from .archive import extract_zip_safe
from .config import configure_convert_config, uncomment_custom_apps


def build_parser():
    parser = argparse.ArgumentParser(prog="autouupbuild")
    subparsers = parser.add_subparsers(dest="command", required=True)

    fetch = subparsers.add_parser("fetch", help="Fetch and extract the latest UUP dump package.")
    fetch.add_argument("--arch", default="amd64")
    fetch.add_argument("--ring", default="retail")
    fetch.add_argument("--pack", default="zh-cn")
    fetch.add_argument("--edition", default="professional")
    fetch.add_argument("--output", default=".", type=Path)
    fetch.add_argument("--uuid", help="Download this exact UUP update UUID; requires --build.")
    fetch.add_argument("--build", help="Version paired with --uuid, for example 26100.9278.")
    fetch.set_defaults(func=run_fetch)

    latest = subparsers.add_parser("latest", help="Print the latest build metadata for a UUP dump channel.")
    latest.add_argument("--arch", default="amd64")
    latest.add_argument("--ring", default="rp")
    latest.add_argument("--all-branches", action="store_true", help="Select the latest full image in each build branch.")
    latest.add_argument("--github-output", action="store_true", help="Write version, uuid, and title to GITHUB_OUTPUT.")
    latest.set_defaults(func=run_latest)

    configure = subparsers.add_parser("configure", help="Apply AutoUUPBuild conversion settings.")
    configure.add_argument("--artifact", choices=("iso", "wim"), required=True)
    configure.add_argument("--config", default="ConvertConfig.ini", type=Path)
    configure.add_argument("--apps-list", default="CustomAppsList.txt", type=Path)
    configure.set_defaults(func=run_configure)

    return parser


def run_latest(args):
    if args.all_branches:
        builds = uupdump.fetch_latest_builds(arch=args.arch, ring=args.ring)
        if args.github_output:
            payload = [
                {"uuid": build.uuid, "version": build.build, "title": build.title}
                for build in builds
            ]
            with Path(_require_env("GITHUB_OUTPUT")).open("a", encoding="utf-8") as output:
                write_github_output(output, "builds", json.dumps(payload, ensure_ascii=True))
        else:
            for build in builds:
                print(f"Selected update: {build.title}")
                print(f"Latest build: {build.build}")
                print(f"Latest UUID: {build.uuid}")
        return 0

    latest = uupdump.fetch_latest_build(arch=args.arch, ring=args.ring)
    if args.github_output:
        output_path = Path(_require_env("GITHUB_OUTPUT"))
        with output_path.open("a", encoding="utf-8") as output:
            write_github_output(output, "version", latest.build)
            write_github_output(output, "uuid", latest.uuid)
            write_github_output(output, "title", latest.title)
    else:
        if latest.title:
            print(f"Selected update: {latest.title}")
        print(f"Latest build: {latest.build}")
        print(f"Latest UUID: {latest.uuid}")
    return 0


def run_fetch(args):
    if args.uuid is not None or args.build is not None:
        if not args.uuid or not args.build:
            raise ValueError("--uuid and --build must be provided together")
        if str(UUID(args.uuid)) != args.uuid.lower():
            raise ValueError("--uuid must be a canonical UUP update UUID")
        if not re.fullmatch(r"\d+\.\d+", args.build, flags=re.ASCII):
            raise ValueError("--build must be a version such as 26100.9278")
        latest = uupdump.BuildMetadata(uuid=args.uuid, build=args.build)
    else:
        latest = uupdump.fetch_latest_build(arch=args.arch, ring=args.ring)
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    if latest.title:
        print(f"Selected update: {latest.title}")
    print(f"Latest build: {latest.build}")
    print(f"Latest UUID: {latest.uuid}")

    package = uupdump.download_package(
        latest.uuid,
        output_dir=output,
        pack=args.pack,
        edition=args.edition,
    )
    print(f"Downloaded package: {package}")
    extract_zip_safe(package, output)
    (output / "version").write_text(latest.build, encoding="utf-8")
    print(f"Extracted package to: {output}")
    return 0


def run_configure(args):
    configure_convert_config(args.config, args.artifact)
    changed = uncomment_custom_apps(args.apps_list)
    print(f"Configured {args.config} for {args.artifact.upper()} output.")
    print(f"Enabled {changed} custom app entries in {args.apps_list}.")
    return 0


def _require_env(name):
    import os

    value = os.environ.get(name)
    if not value:
        raise RuntimeError(f"{name} is not set")
    return value


def write_github_output(output, name, value):
    value = value or ""
    if "\n" in value or "\r" in value:
        delimiter = f"EOF_{name.upper()}"
        output.write(f"{name}<<{delimiter}\n{value}\n{delimiter}\n")
    else:
        output.write(f"{name}={value}\n")


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
