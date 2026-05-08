import re
from pathlib import Path
from zipfile import BadZipFile, ZipFile


def unsafe_zip_members(names):
    unsafe = []
    for name in names:
        candidate = Path(name)
        if name.startswith(("/", "\\")) or re.match(r"^[A-Za-z]:", name) or candidate.is_absolute() or ".." in candidate.parts:
            unsafe.append(name)
    return unsafe


def extract_zip_safe(zip_path, output_dir):
    zip_path = Path(zip_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        with ZipFile(zip_path, "r") as archive:
            unsafe = unsafe_zip_members(archive.namelist())
            if unsafe:
                raise ValueError(f"Refusing to extract unsafe ZIP members: {', '.join(unsafe)}")
            archive.extractall(output_dir)
    except BadZipFile as exc:
        raise ValueError(f"{zip_path} is not a valid ZIP file") from exc
