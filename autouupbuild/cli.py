import argparse
import sys
from pathlib import Path

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
    fetch.set_defaults(func=run_fetch)

    configure = subparsers.add_parser("configure", help="Apply AutoUUPBuild conversion settings.")
    configure.add_argument("--artifact", choices=("iso", "wim"), required=True)
    configure.add_argument("--config", default="ConvertConfig.ini", type=Path)
    configure.add_argument("--apps-list", default="CustomAppsList.txt", type=Path)
    configure.set_defaults(func=run_configure)

    return parser


def run_fetch(args):
    output = args.output
    output.mkdir(parents=True, exist_ok=True)
    latest = uupdump.fetch_latest_build(arch=args.arch, ring=args.ring)
    (output / "version").write_text(latest.build, encoding="utf-8")
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
    print(f"Extracted package to: {output}")
    return 0


def run_configure(args):
    configure_convert_config(args.config, args.artifact)
    changed = uncomment_custom_apps(args.apps_list)
    print(f"Configured {args.config} for {args.artifact.upper()} output.")
    print(f"Enabled {changed} custom app entries in {args.apps_list}.")
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
