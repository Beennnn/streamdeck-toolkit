"""verify(): every check code fires when it should and stays quiet when it
shouldn't. This is the regression net for the Elgato rejection and the wider
pre-publication gate.
"""
import json

import pytest
from PIL import Image

from sdicons import spec
from sdicons.verify import (
    verify, verify_container, counts, has_blocking,
    ERROR, WARN, INFO,
)
from sdicons.posters import ensure_posters
from sdicons.package import package


def codes(findings, level=None):
    return {f.code for f in findings if level is None or f.level == level}


# ── the headline check: missing companion posters (Elgato's rejection) ────────

def test_missing_poster_is_error(pack_factory):
    pack = pack_factory(with_posters=False)
    findings = verify(pack)
    poster_errs = [f for f in findings if f.code == "missing-poster"]
    assert len(poster_errs) == 1
    assert poster_errs[0].level == ERROR
    assert "accordion-playing.png" in poster_errs[0].message
    assert has_blocking(findings)


def test_posters_present_clears_the_error(pack_factory):
    pack = pack_factory(with_posters=True)
    assert "missing-poster" not in codes(verify(pack))


def test_fix_then_verify_goes_green(pack_factory):
    """The user-facing loop: reproduce → --fix → clean."""
    pack = pack_factory(with_posters=False)
    assert has_blocking(verify(pack))
    ensure_posters(pack / spec.DIR_ICONS)
    findings = verify(pack)
    assert not has_blocking(findings)
    assert counts(findings)[ERROR] == 0


def test_many_animated_yields_one_error_each(pack_factory):
    icons = [{"file": f"i{n}-playing.gif", "name": f"I{n}", "tags": ["a"]}
             for n in range(10)]
    pack = pack_factory(icons=icons, with_posters=False)
    errs = [f for f in verify(pack) if f.code == "missing-poster"]
    assert len(errs) == 10


def test_poster_wrong_size_is_error(pack_factory):
    pack = pack_factory(with_posters=True)
    # clobber a poster with a 100×100 image
    p = pack / spec.DIR_ICONS / "accordion-playing.png"
    Image.new("RGBA", (100, 100), (0, 0, 0, 255)).save(p)
    assert "poster-size" in codes(verify(pack), ERROR)


# ── structural checks are folded in (verify ⊇ validate) ───────────────────────

def test_structural_missing_manifest(tmp_path):
    (tmp_path / "icons").mkdir()
    (tmp_path / "icons.json").write_text("[]")
    findings = verify(tmp_path)
    assert any("manifest" in f.message.lower() for f in findings if f.level == ERROR)


def test_poster_not_flagged_as_orphan(pack_factory):
    """A poster PNG is legitimately absent from icons.json — verify must not
    emit the 'on disk but not listed' warning for it."""
    pack = pack_factory(with_posters=True)
    orphan_warns = [f for f in verify(pack)
                    if "not listed in icons.json" in f.message
                    and "playing.png" in f.message]
    assert orphan_warns == []


# ── manifest store-quality warnings ───────────────────────────────────────────

def test_no_description_warns(pack_factory):
    pack = pack_factory(description=None)
    assert "no-description" in codes(verify(pack), WARN)


def test_thin_description_warns(pack_factory):
    pack = pack_factory(description="short")
    assert "thin-description" in codes(verify(pack), WARN)


def test_no_url_warns(pack_factory):
    pack = pack_factory(url=None)
    assert "no-url" in codes(verify(pack), WARN)


def test_no_licence_warns(pack_factory):
    pack = pack_factory(licence=None)
    assert "no-licence" in codes(verify(pack), WARN)


def test_complete_manifest_no_store_warnings(pack_factory):
    pack = pack_factory()
    c = codes(verify(pack), WARN)
    assert {"no-description", "no-url", "no-licence"}.isdisjoint(c)


# ── tags ──────────────────────────────────────────────────────────────────────

def test_empty_tags_warns(pack_factory):
    pack = pack_factory(icons=[{"file": "a.png", "name": "A", "tags": []}])
    assert "no-tags" in codes(verify(pack), WARN)


def test_tag_with_comma_space_is_error(pack_factory):
    pack = pack_factory(icons=[{"file": "a.png", "name": "A", "tags": ["x, y"]}])
    assert "bad-tag" in codes(verify(pack), ERROR)


# ── duplicates ────────────────────────────────────────────────────────────────

def test_duplicate_path_is_error(pack_factory):
    pack = pack_factory()
    ij = pack / "icons.json"
    data = json.loads(ij.read_text())
    data.append(dict(data[0]))  # duplicate the first entry's path
    ij.write_text(json.dumps(data))
    assert "dup-path" in codes(verify(pack), ERROR)


def test_duplicate_name_warns(pack_factory):
    pack = pack_factory(icons=[
        {"file": "a.png", "name": "Same", "tags": ["t"]},
        {"file": "b.png", "name": "Same", "tags": ["t"]},
    ])
    assert "dup-name" in codes(verify(pack), WARN)


# ── filenames ─────────────────────────────────────────────────────────────────

def test_uppercase_filename_warns(pack_factory):
    pack = pack_factory(icons=[{"file": "Accordion.png", "name": "A", "tags": ["t"]}])
    assert "filename-case" in codes(verify(pack), WARN)


def test_space_filename_warns(pack_factory):
    pack = pack_factory(icons=[{"file": "grand piano.png", "name": "G", "tags": ["t"]}])
    assert "filename-space" in codes(verify(pack), WARN)


# ── previews ──────────────────────────────────────────────────────────────────

def test_no_previews_is_info(pack_factory):
    pack = pack_factory(previews=0)
    assert "no-previews" in codes(verify(pack), INFO)


def test_three_previews_ok(pack_factory):
    pack = pack_factory(previews=3)
    assert "too-many-previews" not in codes(verify(pack))


def test_four_previews_warns(pack_factory):
    pack = pack_factory(previews=4)
    assert "too-many-previews" in codes(verify(pack), WARN)


# ── empty pack ────────────────────────────────────────────────────────────────

def test_empty_pack_is_error(tmp_path):
    (tmp_path / "icons").mkdir()
    (tmp_path / "manifest.json").write_text(json.dumps(
        {"Name": "E", "Author": "A", "Version": "1.0.0", "Icon": "icon.png"}))
    Image.new("RGBA", (56, 56)).save(tmp_path / "icon.png")
    (tmp_path / "icons.json").write_text("[]")
    assert "empty-pack" in codes(verify(tmp_path), ERROR)


# ── strict mode + reporting helpers ───────────────────────────────────────────

def test_strict_promotes_warnings_to_blocking(pack_factory):
    pack = pack_factory(description=None)  # yields a warning, no error
    findings = verify(pack)
    assert counts(findings)[ERROR] == 0
    assert not has_blocking(findings, strict=False)
    assert has_blocking(findings, strict=True)


def test_counts_shape(pack_factory):
    c = counts(verify(pack_factory()))
    assert set(c) == {ERROR, WARN, INFO}


# ── verify_container: the shipped bytes ───────────────────────────────────────

def test_container_roundtrip_clean(pack_factory, tmp_path):
    pack = pack_factory(with_posters=False)  # package() will add posters
    archive = package(pack, out_dir=tmp_path / "dist", pack_id="com.test.pack")
    findings = verify_container(archive)
    assert not has_blocking(findings)
    # posters must be inside the shipped container
    import zipfile
    with zipfile.ZipFile(archive) as z:
        names = z.namelist()
    assert any(n.endswith("accordion-playing.png") for n in names)


def test_container_missing_file_reports(tmp_path):
    findings = verify_container(tmp_path / "does-not-exist.streamDeckIconPack")
    assert "no-container" in {f.code for f in findings}


def test_container_bad_zip_reports(tmp_path):
    bad = tmp_path / "bad.streamDeckIconPack"
    bad.write_text("not a zip")
    assert "bad-container" in {f.code for f in verify_container(bad)}
