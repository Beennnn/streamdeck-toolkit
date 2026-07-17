"""Plugin verifier: every check fires when it should and stays quiet otherwise.
The regression net for the two real Marketplace rejections (white icons §1,
cross-plugin references §2) plus the manifest gate (§4)."""
import json
import zipfile

import pytest
from PIL import Image

from sdplugin import spec
from sdplugin.verify import (
    verify, verify_container, counts, has_blocking, Finding,
    ERROR, WARN, INFO,
)


def codes(findings, level=None):
    return {f.code for f in findings if level is None or f.level == level}


# ── a clean plugin passes ─────────────────────────────────────────────────────

def test_clean_plugin_is_ready(plugin_factory):
    findings = verify(plugin_factory())
    assert not has_blocking(findings)
    assert counts(findings)[ERROR] == 0


# ── §1 white in-app icons — the #1 rejection ──────────────────────────────────

def test_coloured_in_app_icon_is_error(plugin_factory):
    findings = verify(plugin_factory(white_icons=False))
    assert "non-white-icon" in codes(findings, ERROR)
    assert has_blocking(findings)


def test_white_icons_pass(plugin_factory):
    assert "non-white-icon" not in codes(verify(plugin_factory(white_icons=True)))


def test_key_state_images_may_be_coloured(plugin_factory):
    # States[].Image are the key faces (colour OK) — must NOT be flagged white.
    findings = verify(plugin_factory(white_icons=True))
    assert "non-white-icon" not in codes(findings)  # key art is red in the fixture


def test_unreadable_icon_is_error(plugin_factory):
    plug = plugin_factory()
    (plug / "imgs/plugin/icon@2x.png").write_bytes(b"not a png")
    assert "icon-unreadable" in codes(verify(plug), ERROR)


# ── §2 cross-plugin references ────────────────────────────────────────────────

def test_foreign_reference_in_locale_is_error(plugin_factory):
    plug = plugin_factory(locale_extra={"x": "Connect your Bluetooth speaker"})
    errs = [f for f in verify(plug) if f.code == "foreign-reference"]
    assert errs and errs[0].level == ERROR
    assert "bluetooth" in errs[0].message.lower()


def test_foreign_reference_in_ui_is_error(plugin_factory):
    plug = plugin_factory()
    (plug / "ui" / "connect.html").write_text("<p>Also toggle Bluetooth here</p>")
    assert "foreign-reference" in codes(verify(plug), ERROR)


def test_own_feature_term_not_flagged(plugin_factory):
    # A Bluetooth plugin naming bluetooth everywhere must NOT self-flag.
    plug = plugin_factory(uuid="com.tester.bt", name="Bluetooth Switcher",
                          category="Bluetooth", description="Connect Bluetooth devices.",
                          locale_extra={"x": "Connect your Bluetooth device"})
    assert "foreign-reference" not in codes(verify(plug))


def test_bt_substring_not_false_matched(plugin_factory):
    # "bt" alias must not match inside "subtle"/"debtor" (word-boundary).
    plug = plugin_factory(locale_extra={"x": "This is a subtle debtor label"})
    assert "foreign-reference" not in codes(verify(plug))


def test_explicit_foreign_override(plugin_factory):
    plug = plugin_factory(description="A midi plugin", name="MIDI Thing")
    # midi is owned → not foreign by default; force it foreign via override
    plug_locale = plug / "en.json"
    d = json.loads(plug_locale.read_text())
    d["Localization"]["x"] = "midi note"
    plug_locale.write_text(json.dumps(d))
    assert "foreign-reference" in codes(verify(plug, foreign=["midi"]), ERROR)


# ── §4 manifest gate ──────────────────────────────────────────────────────────

def test_missing_manifest_short_circuits(tmp_path):
    plug = tmp_path / "com.x.y.sdPlugin"
    plug.mkdir()
    findings = verify(plug)
    assert findings == [Finding(ERROR, "manifest", "missing manifest.json")]


def test_bad_manifest_json(plugin_factory):
    plug = plugin_factory()
    (plug / "manifest.json").write_text("{ broken")
    assert any(f.code == "manifest" for f in verify(plug))


def test_low_sdk_version_is_error(plugin_factory):
    assert "sdk-version" in codes(verify(plugin_factory(sdk=2)), ERROR)


def test_low_software_version_is_error(plugin_factory):
    assert "software-version" in codes(verify(plugin_factory(min_sw="6.4")), ERROR)


def test_one_action_is_error(plugin_factory):
    plug = plugin_factory(actions=[
        {"UUID": "com.tester.demo.only", "Name": "Only", "Icon": "imgs/actions/only/icon",
         "States": [{"Image": "imgs/actions/only/key"}]}])
    assert "action-count" in codes(verify(plug), ERROR)


def test_nodejs_debug_enabled_is_error(plugin_factory):
    plug = plugin_factory()
    m = json.loads((plug / "manifest.json").read_text())
    m["Nodejs"]["Debug"] = "enabled"
    (plug / "manifest.json").write_text(json.dumps(m))
    assert "nodejs-debug" in codes(verify(plug), ERROR)


def test_missing_codepath_is_error(plugin_factory):
    plug = plugin_factory()
    (plug / "bin" / "plugin.js").unlink()
    assert "missing-codepath" in codes(verify(plug), ERROR)


def test_bad_uuid_is_error(plugin_factory):
    # folder name won't match either, but the UUID_RE is the ERROR
    plug = plugin_factory(uuid="NotReverseDomain")
    assert "bad-uuid" in codes(verify(plug), ERROR)


def test_bad_version_is_error(plugin_factory):
    assert "bad-version" in codes(verify(plugin_factory(version="v1")), ERROR)


def test_missing_retina_is_warning(plugin_factory):
    assert "missing-retina" in codes(verify(plugin_factory(retina=False)), WARN)


def test_missing_property_inspector_is_error(plugin_factory):
    plug = plugin_factory()
    m = json.loads((plug / "manifest.json").read_text())
    m["Actions"][0]["PropertyInspectorPath"] = "ui/missing.html"
    (plug / "manifest.json").write_text(json.dumps(m))
    assert "missing-pi" in codes(verify(plug), ERROR)


def test_missing_image_is_error(plugin_factory):
    plug = plugin_factory()
    (plug / "imgs/actions/connect/icon.png").unlink()
    (plug / "imgs/actions/connect/icon@2x.png").unlink()
    assert "missing-image" in codes(verify(plug), ERROR)


# ── strict + reporting ────────────────────────────────────────────────────────

def test_strict_promotes_warnings(plugin_factory):
    findings = verify(plugin_factory(retina=False))
    assert counts(findings)[ERROR] == 0
    assert not has_blocking(findings)
    assert has_blocking(findings, strict=True)


def test_finding_eq_repr():
    a = Finding(ERROR, "x", "m")
    assert a == Finding(ERROR, "x", "m")
    assert a != Finding(WARN, "x", "m")
    assert a != 123
    assert "Finding(" in repr(a)


# ── container ─────────────────────────────────────────────────────────────────

def _zip_plugin(plug, archive):
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as z:
        for f in plug.rglob("*"):
            if f.is_file():
                z.write(f, f"{plug.name}/{f.relative_to(plug).as_posix()}")


def test_container_roundtrip_clean(plugin_factory, tmp_path):
    plug = plugin_factory()
    archive = tmp_path / "demo.streamDeckPlugin"
    _zip_plugin(plug, archive)
    assert not has_blocking(verify_container(archive))


def test_container_catches_coloured_icon(plugin_factory, tmp_path):
    plug = plugin_factory(white_icons=False)
    archive = tmp_path / "bad.streamDeckPlugin"
    _zip_plugin(plug, archive)
    assert "non-white-icon" in codes(verify_container(archive), ERROR)


def test_container_missing_file(tmp_path):
    assert "no-container" in codes(verify_container(tmp_path / "nope.streamDeckPlugin"))


def test_container_bad_zip(tmp_path):
    bad = tmp_path / "bad.streamDeckPlugin"
    bad.write_text("not a zip")
    assert "bad-container" in codes(verify_container(bad))
