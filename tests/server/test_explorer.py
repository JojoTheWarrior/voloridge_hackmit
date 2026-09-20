"""Tests for server.explorer: unpacking an archive Devin attached, which is hostile input, and reading the kit."""
from __future__ import annotations

import io
import stat
import zipfile

import pytest

from server import explorer
from server.explorer import ArchiveRejected, content_type, kit_file, kit_paths, read_kit, site_file, unpack

PAGE = b"<!doctype html><title>Explorer</title>"
ALLOWED = "html css js mjs json geojson csv txt png jpg jpeg webp gif svg woff2".split()


def _zip(files, *, compression=zipfile.ZIP_DEFLATED) -> bytes:
    """A zip of (name or ZipInfo, bytes) pairs, in order. Names are written exactly as given."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression) as archive:
        for name, data in files.items() if isinstance(files, dict) else files:
            if isinstance(name, str):
                info = zipfile.ZipInfo(name)
                info.compress_type = compression
                # ZipInfo tidies names as it is built; hostile archives are not that polite.
                info.filename = name
            else:
                info = name
            archive.writestr(info, data)
    return buffer.getvalue()


def _tree(root) -> dict[str, bytes]:
    return {path.relative_to(root).as_posix(): path.read_bytes() for path in sorted(root.rglob("*")) if path.is_file()}


@pytest.fixture
def target(tmp_path):
    return tmp_path / "explorers" / "m_1" / "1"


def _rejected(data, target, match, **kwargs):
    with pytest.raises(ArchiveRejected, match=match):
        unpack(data, target, **kwargs)
    # Nothing at all is left behind: not the target, not a staging folder next to it.
    assert not target.exists()
    assert not target.parent.exists() or list(target.parent.iterdir()) == []


# ---------- what is accepted ----------

def test_unpacks_a_site(target):
    files = {"index.html": PAGE, "data.json": b'{"rows": [1, 2]}', "assets/map.js": b"export default 1"}
    assert unpack(_zip(files), target) == ["assets/map.js", "data.json", "index.html"]
    assert _tree(target) == files


def test_every_allowed_extension_is_accepted_whatever_its_case(target):
    files = {"index.html": PAGE, **{f"files/f{i}.{ext.upper() if i % 2 else ext}": b"x" for i, ext in enumerate(ALLOWED)}}
    unpack(_zip(files), target)
    assert set(_tree(target)) == set(files)


def test_the_allowlist_is_exactly_the_contract(target):
    assert sorted(explorer.CONTENT_TYPES) == sorted(ALLOWED)


def test_a_single_top_level_folder_is_stripped(target):
    files = {"site/": b"", "site/index.html": PAGE, "site/data/rows.json": b"[]"}
    assert unpack(_zip(files), target) == ["data/rows.json", "index.html"]
    assert _tree(target) == {"index.html": PAGE, "data/rows.json": b"[]"}


def test_only_one_level_of_wrapping_is_stripped(target):
    _rejected(_zip({"a/b/index.html": PAGE}), target, "entry page 'index.html' is missing")
    assert unpack(_zip({"a/b/index.html": PAGE}), target, entry="b/index.html") == ["b/index.html"]


def test_a_top_level_folder_next_to_a_root_file_is_kept(target):
    unpack(_zip({"index.html": PAGE, "site/more.html": PAGE}), target)
    assert set(_tree(target)) == {"index.html", "site/more.html"}


def test_two_top_level_folders_are_kept(target):
    unpack(_zip({"a/index.html": PAGE, "b/data.json": b"{}"}), target, entry="a/index.html")
    assert set(_tree(target)) == {"a/index.html", "b/data.json"}


def test_anything_under_kit_is_discarded_even_if_it_would_not_be_allowed(target):
    files = {"index.html": PAGE, "kit/kit.css": b"body { color: red }", "kit/kit.js": b"evil()",
             "kit/fonts/readme.md": b"not allowed elsewhere", "kit/": b""}
    assert unpack(_zip(files), target) == ["index.html"]
    assert _tree(target) == {"index.html": PAGE}


def test_kit_is_discarded_after_the_wrapping_folder_is_stripped(target):
    unpack(_zip({"site/index.html": PAGE, "site/kit/kit.css": b"x", "site/toolkit/kit.css": b"kept"}), target)
    assert _tree(target) == {"index.html": PAGE, "toolkit/kit.css": b"kept"}


def test_an_archive_of_nothing_but_kit_has_no_entry(target):
    _rejected(_zip({"index.html.txt": b"x", "kit/index.html": PAGE}), target, "entry page")


def test_what_a_mac_adds_is_dropped_quietly(target):
    files = {"site/index.html": PAGE, "__MACOSX/site/._index.html": b"junk", "site/.DS_Store": b"junk"}
    assert unpack(_zip(files), target) == ["index.html"]


def test_unicode_names_survive(target):
    files = {"index.html": PAGE, "données/café ☕.json": b"{}", "地図/データ.geojson": b"{}"}
    unpack(_zip(files), target)
    assert _tree(target) == files


def test_dot_segments_and_doubled_slashes_are_harmless(target):
    unpack(_zip({"./index.html": PAGE, "data//./rows.json": b"[]"}), target)
    assert set(_tree(target)) == {"index.html", "data/rows.json"}


def test_a_custom_entry(target):
    unpack(_zip({"pages/start.html": PAGE, "x.json": b"{}"}), target, entry="pages/start.html")
    assert (target / "pages" / "start.html").read_bytes() == PAGE


def test_an_existing_version_is_replaced_whole(target):
    unpack(_zip({"index.html": b"old", "old.json": b"{}"}), target)
    unpack(_zip({"index.html": b"new"}), target)
    assert _tree(target) == {"index.html": b"new"}


def test_a_rejected_archive_leaves_an_existing_version_alone(target):
    unpack(_zip({"index.html": b"good"}), target)
    with pytest.raises(ArchiveRejected):
        unpack(_zip({"index.html": b"bad", "run.exe": b"MZ"}), target)
    assert _tree(target) == {"index.html": b"good"}
    assert [path.name for path in target.parent.iterdir()] == [target.name]


def test_files_are_written_as_plain_files_whatever_the_archive_says(target):
    info = zipfile.ZipInfo("index.html")
    info.external_attr = (stat.S_IFREG | 0o4777) << 16
    unpack(_zip([(info, PAGE)]), target)
    mode = (target / "index.html").stat().st_mode
    assert stat.S_ISREG(mode) and not mode & (stat.S_ISUID | stat.S_IXUSR)


def test_stored_entries_are_fine(target):
    unpack(_zip({"index.html": PAGE, "big.json": b"0" * 100_000}, compression=zipfile.ZIP_STORED), target)
    assert (target / "big.json").stat().st_size == 100_000


# ---------- names ----------

@pytest.mark.parametrize("name", [
    "../evil.html", "site/../../evil.html", "a/b/../../../evil.html", "..", "../", "data/..",
])
def test_zip_slip_is_rejected(target, tmp_path, name):
    _rejected(_zip({"index.html": PAGE, name: b"x"}), target, "climbs out of the archive")
    assert not list(tmp_path.rglob("evil.html"))


@pytest.mark.parametrize("name", ["/etc/cron.d/evil.html", "/index.html", "C:/Windows/evil.html", "c:evil.html"])
def test_absolute_paths_are_rejected(target, name):
    _rejected(_zip({"index.html": PAGE, name: b"x"}), target, "absolute path")


@pytest.mark.parametrize("name", ["..\\evil.html", "data\\rows.json", "\\\\server\\share\\x.html"])
def test_backslashes_are_rejected(target, name):
    _rejected(_zip({"index.html": PAGE, name: b"x"}), target, "backslash")


@pytest.mark.parametrize("name", ["evil\x00.html", "line\nbreak.html", "tab\t.html", "del\x7f.html"])
def test_control_characters_are_rejected(target, name):
    _rejected(_zip({"index.html": PAGE, name: b"x"}), target, "control character")


def test_overlong_names_are_rejected(target):
    _rejected(_zip({"index.html": PAGE, f"{'a' * 300}.html": b"x"}), target, "too long")


@pytest.mark.parametrize("link_target", ["/etc/passwd", "../../../etc/passwd", "index.html"])
def test_symlink_entries_are_rejected(target, link_target):
    link = zipfile.ZipInfo("passwd.txt")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    _rejected(_zip([("index.html", PAGE), (link, link_target.encode())]), target, "symlink")


def test_a_symlinked_folder_is_rejected_even_under_kit(target):
    link = zipfile.ZipInfo("kit/")
    link.external_attr = (stat.S_IFLNK | 0o777) << 16
    _rejected(_zip([("index.html", PAGE), (link, b"/etc")]), target, "symlink")


@pytest.mark.parametrize("names", [
    ["index.html", "index.html"], ["index.html", "INDEX.HTML"], ["index.html", "./index.html"],
    ["index.html", "data/a.json", "data//a.json"], ["index.html", "Data/a.json", "data/A.json"],
])
def test_duplicate_names_are_rejected(target, names):
    with pytest.warns(UserWarning) if len(set(names)) < len(names) else _nothing():
        data = _zip([(name, PAGE) for name in names])
    _rejected(data, target, "twice")


class _nothing:
    def __enter__(self):
        return None

    def __exit__(self, *exc):
        return False


def test_a_name_that_is_both_a_file_and_a_folder_is_rejected(target):
    _rejected(_zip({"index.html": PAGE, "data.json": b"{}", "data.json/rows.json": b"[]"}), target, "both a file and a folder")


# ---------- kinds of file ----------

@pytest.mark.parametrize("name", [
    "run.exe", "script.php", "page.htm", "notes.md", "lib.wasm", "font.woff", "font.ttf", "archive.zip", "app.js.map",
    "Makefile", "noextension", ".htaccess", ".gitignore", "trailingdot.", "index.html.bak", "data.json ", "a.html/",
])
def test_other_extensions_are_rejected(target, name):
    if name.endswith("/"):
        # A folder may be called anything; it is never written as such.
        assert unpack(_zip({"index.html": PAGE, name: b""}), target) == ["index.html"]
    else:
        _rejected(_zip({"index.html": PAGE, name: b"x"}), target, "not an allowed kind of file")


def test_encrypted_entries_are_rejected(target):
    info = zipfile.ZipInfo("index.html")
    data = bytearray(_zip([(info, PAGE)]))
    # Set the "encrypted" flag bit in both the local header and the central directory.
    local, central = data.find(b"PK\x03\x04"), data.find(b"PK\x01\x02")
    data[local + 6] |= 1
    data[central + 8] |= 1
    _rejected(bytes(data), target, "encrypted")


# ---------- size ----------

def test_too_many_entries_are_rejected(target):
    files = {"index.html": PAGE, **{f"f{i}.txt": b"x" for i in range(explorer.MAX_ENTRIES)}}
    _rejected(_zip(files), target, "more than 200 entries")


def test_exactly_the_entry_limit_is_accepted(target):
    files = {"index.html": PAGE, **{f"f{i}.txt": b"x" for i in range(explorer.MAX_ENTRIES - 1)}}
    assert len(unpack(_zip(files), target)) == explorer.MAX_ENTRIES


def test_folders_and_discarded_files_count_as_entries(target):
    files = {"index.html": PAGE, **{f"kit/f{i}.css": b"x" for i in range(100)}, **{f"d{i}/": b"" for i in range(100)}}
    _rejected(_zip(files), target, "more than 200 entries")


def test_an_oversize_entry_is_rejected(target, monkeypatch):
    monkeypatch.setattr(explorer, "MAX_ENTRY_BYTES", 1000)
    stored = zipfile.ZIP_STORED
    _rejected(_zip({"index.html": PAGE, "big.json": b"x" * 1001}, compression=stored), target, "'big.json' is larger than")
    assert unpack(_zip({"index.html": PAGE, "big.json": b"x" * 1000}, compression=stored), target)


def test_the_real_entry_limit_is_25_mb_and_the_total_40(target):
    assert (explorer.MAX_ENTRY_BYTES, explorer.MAX_TOTAL_BYTES) == (25 * 1024 * 1024, 40 * 1024 * 1024)
    assert (explorer.MAX_ENTRIES, explorer.MAX_RATIO) == (200, 100)


def test_an_oversize_total_is_rejected(target, monkeypatch):
    monkeypatch.setattr(explorer, "MAX_TOTAL_BYTES", 3000)
    stored = zipfile.ZIP_STORED
    files = {"index.html": b"x" * 1000, "a.json": b"x" * 1000, "b.json": b"x" * 1000}
    _rejected(_zip({**files, "c.json": b"x"}, compression=stored), target, "unpacks to more than")
    assert unpack(_zip(files, compression=stored), target)


def test_discarded_kit_files_do_not_count_towards_the_total(target, monkeypatch):
    monkeypatch.setattr(explorer, "MAX_TOTAL_BYTES", 3000)
    files = {"index.html": b"x" * 1000, "kit/kit.css": b"x" * 5000}
    assert unpack(_zip(files, compression=zipfile.ZIP_STORED), target) == ["index.html"]


def test_a_zip_bomb_is_rejected_by_its_ratio(target):
    bomb = _zip({"index.html": PAGE, "bomb.json": b"0" * (5 * 1024 * 1024)})
    assert len(bomb) < 10_000
    _rejected(bomb, target, "zip bomb")


def test_ordinary_compression_is_not_a_bomb(target):
    rows = b"".join(b'{"id": %d, "score": %d},\n' % (i, i * 7 % 101) for i in range(20_000))
    assert unpack(_zip({"index.html": PAGE, "rows.json": rows}), target)


def test_a_size_that_lies_in_the_header_cannot_write_more_than_it_declared(target):
    data = bytearray(_zip({"index.html": PAGE, "rows.json": b"0123456789" * 1000}, compression=zipfile.ZIP_STORED))
    central = data.find(b"PK\x01\x02", data.find(b"rows.json"))
    # Uncompressed size lives 24 bytes into a central directory record.
    data[central + 24:central + 28] = (10).to_bytes(4, "little")
    try:
        unpack(bytes(data), target)
    except ArchiveRejected:
        assert not target.exists()
    else:
        assert (target / "rows.json").stat().st_size <= 10


# ---------- not an archive, or not a whole one ----------

@pytest.mark.parametrize("data", [b"", b"not a zip", b"PK\x03\x04", b"<html>", b"\x00" * 1000, b"PK\x05\x06" + b"\xff" * 18])
def test_bytes_that_are_not_a_zip_are_rejected(target, data):
    _rejected(data, target, "not a zip archive")


def test_an_empty_zip_is_rejected(target):
    _rejected(_zip({}), target, "has no files")


def test_a_zip_of_nothing_but_folders_is_rejected(target):
    _rejected(_zip({"site/": b"", "site/assets/": b"", "empty/": b""}), target, "has no files")


def test_a_truncated_archive_is_rejected(target):
    whole = _zip({"index.html": PAGE, "data.json": b"{}" * 1000})
    _rejected(whole[: len(whole) // 2], target, "not a zip archive")


def test_a_corrupt_entry_is_rejected_and_nothing_is_kept(target):
    data = bytearray(_zip({"index.html": PAGE, "data.json": bytes(range(256)) * 40}, compression=zipfile.ZIP_STORED))
    data[data.find(bytes(range(256))) + 5] ^= 0xFF
    _rejected(bytes(data), target, "'data.json' could not be read")


@pytest.mark.parametrize("entry, files", [
    ("index.html", {"main.html": PAGE}),
    ("index.html", {"Index.html": PAGE}),
    ("index.html", {"a/index.html": PAGE, "b/x.json": b"{}"}),
    ("start.html", {"index.html": PAGE}),
    ("data.json", {"index.html": PAGE, "data.json": b"{}"}),
    ("", {"index.html": PAGE}),
    ("../index.html", {"index.html": PAGE}),
    ("kit/index.html", {"index.html": PAGE, "kit/index.html": PAGE}),
])
def test_a_missing_or_unusable_entry_is_rejected(target, entry, files):
    with pytest.raises(ArchiveRejected):
        unpack(_zip(files), target, entry=entry)
    assert not target.exists()


def test_reasons_never_echo_a_long_hostile_name_in_full(target):
    with pytest.raises(ArchiveRejected) as caught:
        unpack(_zip({"index.html": PAGE, "x" * 190 + ".exe": b"x"}), target)
    assert len(str(caught.value)) < 160


# ---------- content types ----------

@pytest.mark.parametrize("path, expected", [
    ("index.html", "text/html"), ("a/b/style.CSS", "text/css"), ("app.js", "text/javascript"),
    ("app.mjs", "text/javascript"), ("rows.csv", "text/csv"), ("notes.txt", "text/plain"),
    ("data.json", "application/json"), ("map.geojson", "application/geo+json"), ("font.woff2", "font/woff2"),
    ("pin.svg", "image/svg+xml"), ("photo.JPG", "image/jpeg"),
    ("GUIDE.md", None), ("noext", None), ("dir.html/file", None),
])
def test_content_types(path, expected):
    assert content_type(path) == expected


# ---------- the kit ----------

@pytest.fixture
def kit(tmp_path):
    root = tmp_path / "kit"
    (root / "fonts").mkdir(parents=True)
    (root / "GUIDE.md").write_text("the guide")
    (root / "kit.css").write_text("body {}")
    (root / "kit.js").write_text("export {}")
    (root / "index.html").write_text("<p>example</p>")
    (root / "data.json").write_text("{}")
    (root / "fonts" / "geist.woff2").write_bytes(b"\xff\xfe\x00binary")
    (root / "fonts" / "sample.json").write_text("[]")
    (root / "NOTES.md").write_text("internal")
    (root / ".DS_Store").write_bytes(b"junk")
    return root


def test_kit_paths_put_the_example_at_the_root_and_the_rest_under_kit(kit):
    assert {path: file.relative_to(kit).as_posix() for path, file in kit_paths(kit).items()} == {
        "GUIDE.md": "GUIDE.md", "index.html": "index.html", "data.json": "data.json",
        "kit/kit.css": "kit.css", "kit/kit.js": "kit.js",
        "kit/fonts/geist.woff2": "fonts/geist.woff2", "kit/fonts/sample.json": "fonts/sample.json"}


def test_read_kit_is_the_text_files_with_the_guide_first(kit):
    texts = read_kit(kit)
    assert list(texts)[0] == "GUIDE.md"
    assert texts == {"GUIDE.md": "the guide", "data.json": "{}", "index.html": "<p>example</p>",
                     "kit/fonts/sample.json": "[]", "kit/kit.css": "body {}", "kit/kit.js": "export {}"}


def test_a_missing_kit_is_empty(tmp_path):
    assert kit_paths(tmp_path / "nope") == {} and read_kit(tmp_path / "nope") == {}


@pytest.mark.parametrize("path, found", [
    ("kit/kit.css", "kit.css"), ("kit/fonts/geist.woff2", "fonts/geist.woff2"),
    ("kit/index.html", None), ("kit/GUIDE.md", None), ("kit/NOTES.md", None), ("kit/.DS_Store", None),
    ("kit/../GUIDE.md", None), ("kit/../../etc/passwd", None), ("kit//kit.css", None), ("kit/", None),
    ("kit.css", None), ("index.html", None), ("Kit/kit.css", None),
])
def test_kit_file_only_answers_for_real_kit_paths(kit, path, found):
    assert kit_file(path, kit) == (kit / found if found else None)


# ---------- serving a build ----------

@pytest.fixture
def build(target):
    unpack(_zip({"index.html": PAGE, "assets/map.js": b"1", "kit/kit.css": b"from the archive"}), target)
    return target


@pytest.mark.parametrize("path, found", [
    ("index.html", "index.html"), ("assets/map.js", "assets/map.js"),
    ("missing.html", None), ("assets", None), ("assets/", None), ("", None), ("index.htm", None),
    ("INDEX.html.bak", None), ("../1/index.html", None), ("assets/../index.html", None), ("./index.html", None),
    ("/index.html", None), ("assets//map.js", None), ("assets\\map.js", None), ("index.html\x00.png", None),
    ("/etc/passwd", None), ("../../../../../../etc/hosts.txt", None),
])
def test_site_file_only_answers_for_plain_paths_to_real_files(build, kit, path, found):
    assert site_file(build, path, kit) == (build / found if found else None)


def test_site_file_serves_kit_paths_from_the_kit(build, kit):
    assert site_file(build, "kit/kit.css", kit) == kit / "kit.css"
    assert site_file(build, "kit/GUIDE.md", kit) is None and site_file(build, "kit/nope.css", kit) is None
    assert site_file(build.parent / "9", "kit/kit.css", kit) is None


def test_site_file_does_not_follow_a_link_out_of_the_build(build, tmp_path):
    secret = tmp_path / "secret.txt"
    secret.write_text("secret")
    (build / "link.txt").symlink_to(secret)
    (build / "inside.html").symlink_to(build / "index.html")
    assert site_file(build, "link.txt") is None
    assert site_file(build, "inside.html") == build / "inside.html"


def test_the_real_kit_has_a_guide_and_an_example_that_unpacks(target):
    """Checks the kit's shape, never its contents: those belong to whoever maintains the kit."""
    paths = kit_paths()
    assert {"GUIDE.md", "index.html", "kit/kit.css", "kit/kit.js"} <= set(paths)
    example = {path: file.read_bytes() for path, file in paths.items() if path != "GUIDE.md"}
    assert "index.html" in unpack(_zip(example, compression=zipfile.ZIP_STORED), target)
    assert not (target / "kit").exists()
