"""Edge branches: malformed inputs, unreadable files, and the reporting layer."""
import json

from PIL import Image

from sdicons import spec
from sdicons.verify import (
    verify, verify_container, print_report, counts,
    Finding, ERROR, WARN, INFO,
)
from sdicons.package import package


def _codes(findings):
    return {f.code for f in findings}


def test_finding_repr_and_eq():
    a = Finding(ERROR, "x", "msg")
    b = Finding(ERROR, "x", "msg")
    assert a == b
    assert a != Finding(WARN, "x", "msg")
    assert a != "not a finding"
    assert "Finding(" in repr(a)


def test_icons_json_not_json(pack_factory):
    pack = pack_factory()
    (pack / "icons.json").write_text("{ not json")
    findings = verify(pack)
    assert any("not valid JSON" in f.message for f in findings)


def test_icons_json_not_array(pack_factory):
    pack = pack_factory()
    (pack / "icons.json").write_text(json.dumps({"path": "x"}))
    findings = verify(pack)
    assert any("must be a JSON array" in f.message for f in findings)


def test_manifest_not_json_is_handled(pack_factory):
    pack = pack_factory()
    (pack / "manifest.json").write_text("{ broken")
    # verify must not crash; structural check surfaces the JSON error
    findings = verify(pack)
    assert any(f.level == ERROR for f in findings)


def test_poster_unreadable_is_error(pack_factory):
    pack = pack_factory(with_posters=True)
    # replace a valid poster with garbage bytes → cannot open as image
    p = pack / spec.DIR_ICONS / "accordion-playing.png"
    p.write_bytes(b"\x89PNG\r\n\x1a\n garbage not really a png")
    assert "poster-unreadable" in _codes(verify(pack))


def test_poster_wrong_format_is_error(pack_factory):
    pack = pack_factory(with_posters=True)
    # write a real JPEG but keep the .png name → format mismatch
    p = pack / spec.DIR_ICONS / "accordion-playing.png"
    Image.new("RGB", (spec.ICON_SIZE, spec.ICON_SIZE), (1, 2, 3)).save(p, format="JPEG")
    codes = _codes(verify(pack))
    assert "poster-format" in codes


def test_bad_version_is_error(pack_factory):
    pack = pack_factory(version="1.2")  # must be x.y.z
    assert any("Version" in f.message for f in verify(pack) if f.level == ERROR)


def test_oversize_filename_is_error(pack_factory):
    long = "a" * 90 + ".png"
    pack = pack_factory(icons=[{"file": long, "name": "L", "tags": ["t"]}])
    assert any(f">{spec.MAX_FILENAME_LEN}" in f.message or "chars" in f.message
               for f in verify(pack) if f.level == ERROR)


def test_wrong_icon_size_is_error(pack_factory):
    pack = pack_factory()
    # overwrite a static icon with a 50×50 image
    p = pack / spec.DIR_ICONS / "accordion.png"
    Image.new("RGBA", (50, 50)).save(p)
    assert any("must be" in f.message for f in verify(pack) if f.level == ERROR)


def test_print_report_smoke(capsys, pack_factory):
    pack = pack_factory(with_posters=False)
    findings = verify(pack)
    print_report(str(pack), findings, strict=False)
    out = capsys.readouterr().out
    assert "missing-poster" in out
    assert "NOT ready" in out


def test_print_report_clean_smoke(capsys, pack_factory):
    pack = pack_factory(with_posters=True, previews=3)
    findings = verify(pack)
    print_report(str(pack), findings)
    out = capsys.readouterr().out
    assert "publication-ready" in out or "warning" in out


def test_print_report_strict_blocks_on_warning(capsys, pack_factory):
    pack = pack_factory(description=None)
    findings = verify(pack)
    print_report(str(pack), findings, strict=True)
    out = capsys.readouterr().out
    assert "blocking under --strict" in out
