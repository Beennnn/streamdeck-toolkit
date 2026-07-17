"""Edge branches + reporting layer for the plugin verifier."""
from sdplugin.verify import (
    verify, print_report, counts, ERROR, WARN, INFO,
)


def codes(findings):
    return {f.code for f in findings}


def test_fully_transparent_in_app_icon_is_flagged(plugin_factory):
    from PIL import Image
    plug = plugin_factory()
    # a blank (all-transparent) in-app icon has no glyph → not white monochrome
    Image.new("RGBA", (56, 56), (0, 0, 0, 0)).save(plug / "imgs/plugin/icon@2x.png")
    assert "non-white-icon" in codes(verify(plug))


def test_uuid_folder_mismatch_warns(plugin_factory):
    plug = plugin_factory(uuid="com.tester.demo")
    # rename the folder so it no longer matches <UUID>.sdPlugin
    renamed = plug.parent / "wrongname.sdPlugin"
    plug.rename(renamed)
    assert "uuid-folder" in codes(verify(renamed))


def test_non_numeric_software_version_warns(plugin_factory):
    plug = plugin_factory(min_sw="six.nine")
    assert "software-version" in codes(verify(plug))


def test_no_category_warns(plugin_factory):
    import json
    plug = plugin_factory()
    m = json.loads((plug / "manifest.json").read_text())
    del m["Category"]
    (plug / "manifest.json").write_text(json.dumps(m))
    assert "no-category" in codes(verify(plug))


def test_foreign_reference_in_manifest_tooltip(plugin_factory):
    # bluetooth appears in a user-visible Action Tooltip but NOT in the plugin's
    # identity (Name/Category/UUID/Description) — so it stays foreign and the
    # manifest scan flags it.
    import json
    plug = plugin_factory(name="Wi-Fi Switcher", description="Switch Wi-Fi networks.")
    m = json.loads((plug / "manifest.json").read_text())
    m["Actions"][0]["Tooltip"] = "Also pairs your Bluetooth speaker"
    (plug / "manifest.json").write_text(json.dumps(m))
    errs = [f for f in verify(plug) if f.code == "foreign-reference"
            and "manifest.json" in f.message]
    assert errs


def test_print_report_clean_smoke(capsys, plugin_factory):
    print_report("p", verify(plugin_factory()))
    assert "publication-ready" in capsys.readouterr().out


def test_print_report_errors_smoke(capsys, plugin_factory):
    print_report("p", verify(plugin_factory(white_icons=False)))
    out = capsys.readouterr().out
    assert "non-white-icon" in out and "NOT ready" in out


def test_print_report_strict_smoke(capsys, plugin_factory):
    print_report("p", verify(plugin_factory(retina=False)), strict=True)
    assert "blocking under --strict" in capsys.readouterr().out
