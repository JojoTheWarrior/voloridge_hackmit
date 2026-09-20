from __future__ import annotations

import io
import os
import re
import shutil
import stat
import uuid
import zipfile
import zlib
from pathlib import Path

from server.brief import KIT_GUIDE

KIT_DIR = Path(__file__).parent / "explorer_kit"
KIT_PREFIX = "kit/"
DEFAULT_ENTRY = "index.html"

MAX_ENTRIES = 200
MAX_ENTRY_BYTES = 25 * 1024 * 1024
MAX_TOTAL_BYTES = 40 * 1024 * 1024
MAX_RATIO = 100
MAX_NAME_LENGTH = 200

# Everything an explorer may contain, and what each is served as (the server adds the charset to text).
CONTENT_TYPES = {
    "html": "text/html",
    "css": "text/css",
    "js": "text/javascript",
    "mjs": "text/javascript",
    "json": "application/json",
    "geojson": "application/geo+json",
    "csv": "text/csv",
    "txt": "text/plain",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
    "webp": "image/webp",
    "gif": "image/gif",
    "svg": "image/svg+xml",
    "woff2": "font/woff2",
}
# Served as documents, so they can run script and get the sandboxing policy.
DOCUMENT_EXTENSIONS = ("html", "svg")
# The worked example sits at the root of a site; every other kit file is under `kit/`.
EXAMPLE_EXTENSIONS = ("html", "json", "geojson", "csv")
# What a Mac adds to a zip on its own. Dropped rather than held against the archive.
_JUNK_FOLDER, _JUNK_FILE = "__MACOSX", ".DS_Store"
_DRIVE = re.compile(r"^[A-Za-z]:")
# How a corrupt, truncated or exotic entry shows itself when it is read.
_UNREADABLE = (zipfile.BadZipFile, zlib.error, NotImplementedError, RuntimeError, EOFError, OSError, ValueError)


class ArchiveRejected(Exception):
    """The archive cannot be used. The message says why, in words fit for the thread."""


def unpack(data: bytes, target: Path, *, entry: str = DEFAULT_ENTRY) -> list[str]:
    """Unpack an explorer archive into `target` and return the paths written, or raise `ArchiveRejected`.

    The archive is whatever Devin attached, so it is hostile input: everything is checked against
    the central directory before a byte is written, and `target` only ever appears complete.
    """
    try:
        archive = zipfile.ZipFile(io.BytesIO(data))
    except Exception as exc:  # a mangled archive can fail in zipfile in more ways than it documents
        raise ArchiveRejected("it is not a zip archive") from exc
    with archive:
        files = _plan(archive.infolist(), entry)
        staging = target.parent / f".{target.name}.{uuid.uuid4().hex[:8]}.tmp"
        try:
            _extract(archive, files, staging)
            if target.exists():
                shutil.rmtree(target)
            os.replace(staging, target)
        finally:
            # Gone already when the move worked; otherwise nothing half-written is left behind.
            shutil.rmtree(staging, ignore_errors=True)
    return sorted(files)


def extension(path: str) -> str:
    name = path.rsplit("/", 1)[-1]
    return name.rsplit(".", 1)[-1].lower() if "." in name else ""


def content_type(path: str) -> str | None:
    return CONTENT_TYPES.get(extension(path))


def kit_paths(kit_dir: Path = KIT_DIR) -> dict[str, Path]:
    """Every kit file, keyed by the path it has inside a site (the guide keeps its own name)."""
    paths = {}
    if not kit_dir.is_dir():
        return paths
    for file in sorted(path for path in kit_dir.rglob("*") if path.is_file()):
        relative = file.relative_to(kit_dir).as_posix()
        if any(part.startswith(".") for part in relative.split("/")):
            continue
        if relative == KIT_GUIDE:
            paths[relative] = file
        elif extension(relative) in CONTENT_TYPES:
            example = "/" not in relative and extension(relative) in EXAMPLE_EXTENSIONS
            paths[relative if example else f"{KIT_PREFIX}{relative}"] = file
    return paths


def read_kit(kit_dir: Path = KIT_DIR) -> dict[str, str]:
    """The kit's text files for the explorer request: the guide first, fonts and images left out."""
    texts = {}
    for path, file in kit_paths(kit_dir).items():
        try:
            texts[path] = file.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
    return {path: texts[path] for path in sorted(texts, key=lambda path: path != KIT_GUIDE)}


def kit_file(path: str, kit_dir: Path = KIT_DIR) -> Path | None:
    """The canonical file behind a site's `kit/...` path."""
    return kit_paths(kit_dir).get(path) if path.startswith(KIT_PREFIX) else None


def site_file(root: Path, path: str, kit_dir: Path = KIT_DIR) -> Path | None:
    """The file behind a URL path of the build unpacked in `root`, or None if there is nothing to serve."""
    # Stricter than it needs to be: no path with a dot segment is served, even one that stays inside.
    plain = not any(char == "\\" or ord(char) < 32 for char in path) and not any(
        segment in ("", ".", "..") for segment in path.split("/"))
    if not plain or content_type(path) is None or not root.is_dir():
        return None
    if path.startswith(KIT_PREFIX):
        # Ours, not the copy in the archive, so a design fix reaches every explorer ever built.
        return kit_file(path, kit_dir)
    file = root / path
    # Unpacking never writes a link, so one in there did not come from an archive; it is not followed out.
    if not file.is_file() or not file.resolve().is_relative_to(root.resolve()):
        return None
    return file


def _plan(infos: list[zipfile.ZipInfo], entry: str) -> dict[str, zipfile.ZipInfo]:
    """The files to write, keyed by their path under the target. Raises on anything untoward."""
    if len(infos) > MAX_ENTRIES:
        raise ArchiveRejected(f"it has more than {MAX_ENTRIES} entries")
    named = []
    for info in infos:
        segments = _segments(info.orig_filename)
        if stat.S_ISLNK(info.external_attr >> 16):
            raise ArchiveRejected(f"{_shown(info)} is a symlink")
        if info.flag_bits & 0x1:
            raise ArchiveRejected(f"{_shown(info)} is encrypted")
        if info.is_dir() or not segments or segments[0] == _JUNK_FOLDER or segments[-1] == _JUNK_FILE:
            continue
        named.append((segments, info))
    if not named:
        raise ArchiveRejected("it has no files")

    # A single folder wrapping the whole site is how most tools zip a directory.
    tops = {segments[0] for segments, _ in named}
    if len(tops) == 1 and all(len(segments) > 1 for segments, _ in named):
        named = [(segments[1:], info) for segments, info in named]

    files: dict[str, zipfile.ZipInfo] = {}
    seen: set[str] = set()
    for segments, info in named:
        path = "/".join(segments)
        if path.startswith(KIT_PREFIX):
            continue
        if extension(path) not in CONTENT_TYPES:
            raise ArchiveRejected(f"{_shown(info)} is not an allowed kind of file")
        if info.file_size > MAX_ENTRY_BYTES:
            raise ArchiveRejected(f"{_shown(info)} is larger than {MAX_ENTRY_BYTES // (1024 * 1024)} MB")
        # Compared without case: the disk this lands on may not tell `Index.html` from `index.html`.
        if path.casefold() in seen:
            raise ArchiveRejected(f"{_shown(info)} is in the archive twice")
        seen.add(path.casefold())
        files[path] = info
    folders = {folder.as_posix().casefold() for path in files for folder in Path(path).parents}
    if clash := next((path for path in files if path.casefold() in folders), None):
        raise ArchiveRejected(f"{clash!r} is both a file and a folder")

    unpacked = sum(info.file_size for info in files.values())
    if unpacked > MAX_TOTAL_BYTES:
        raise ArchiveRejected(f"it unpacks to more than {MAX_TOTAL_BYTES // (1024 * 1024)} MB")
    if unpacked > MAX_RATIO * sum(info.compress_size for info in files.values()):
        raise ArchiveRejected(f"it is compressed more than {MAX_RATIO} times over, which looks like a zip bomb")
    if "/".join(_segments(entry)) not in files or extension(entry) != "html":
        raise ArchiveRejected(f"its entry page {entry!r} is missing")
    return files


def _segments(name: str) -> list[str]:
    """A zip entry name as safe path segments, or a rejection."""
    shown = repr(name[:80])
    if not name or len(name) > MAX_NAME_LENGTH:
        raise ArchiveRejected(f"the name {shown} is empty or too long")
    if "\\" in name:
        raise ArchiveRejected(f"the name {shown} has a backslash in it")
    if any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ArchiveRejected(f"the name {shown} has a control character in it")
    if name.startswith("/") or _DRIVE.match(name):
        raise ArchiveRejected(f"the name {shown} is an absolute path")
    segments = [segment for segment in name.split("/") if segment not in ("", ".")]
    if ".." in segments:
        raise ArchiveRejected(f"the name {shown} climbs out of the archive")
    return segments


def _shown(info: zipfile.ZipInfo) -> str:
    return repr(info.orig_filename[:80])


def _extract(archive: zipfile.ZipFile, files: dict[str, zipfile.ZipInfo], staging: Path) -> None:
    staging.mkdir(parents=True)
    root = staging.resolve()
    written = 0
    for path, info in files.items():
        destination = (root / path).resolve()
        if not destination.is_relative_to(root):
            raise ArchiveRejected(f"{_shown(info)} would land outside the explorer's folder")
        destination.parent.mkdir(parents=True, exist_ok=True)
        try:
            with archive.open(info) as source, open(destination, "xb") as out:
                # The declared sizes were checked above; this holds the archive to them.
                while chunk := source.read(64 * 1024):
                    written += len(chunk)
                    if written > MAX_TOTAL_BYTES:
                        raise ArchiveRejected(f"it unpacks to more than {MAX_TOTAL_BYTES // (1024 * 1024)} MB")
                    out.write(chunk)
        except _UNREADABLE as exc:
            raise ArchiveRejected(f"{_shown(info)} could not be read: {exc}") from exc
