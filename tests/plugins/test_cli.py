"""CLI: the two modes (verify / fix), exit codes, dispatch, --strict/--foreign."""
import zipfile

import pytest

from sdplugin.cli import main


def _run(argv):
    with pytest.raises(SystemExit) as e:
        main(argv)
    return e.value.code


# ── verify mode (never writes) ────────────────────────────────────────────────

def test_verify_clean_exits_zero(plugin_factory, capsys):
    assert _run(["verify", str(plugin_factory())]) == 0
    assert "publication-ready" in capsys.readouterr().out


def test_verify_coloured_icon_exits_one(plugin_factory, capsys):
    assert _run(["verify", str(plugin_factory(white_icons=False))]) == 1
    assert "non-white-icon" in capsys.readouterr().out


def test_verify_does_not_mutate(plugin_factory):
    plug = plugin_factory(white_icons=False)
    before = (plug / "imgs/plugin/icon@2x.png").read_bytes()
    _run(["verify", str(plug)])
    assert (plug / "imgs/plugin/icon@2x.png").read_bytes() == before  # unchanged


def test_verify_strict_blocks_on_warning(plugin_factory):
    assert _run(["verify", str(plugin_factory(retina=False)), "--strict"]) == 1
    assert _run(["verify", str(plugin_factory(retina=False))]) == 0


def test_verify_foreign_override(plugin_factory):
    plug = plugin_factory(name="MIDI Thing", description="A midi plugin")
    (plug / "ui" / "connect.html").write_text("<p>midi note here</p>")
    assert _run(["verify", str(plug), "--foreign", "midi"]) == 1


def test_verify_container_dispatch(plugin_factory, tmp_path):
    plug = plugin_factory()
    archive = tmp_path / "demo.streamDeckPlugin"
    with zipfile.ZipFile(archive, "w") as z:
        for f in plug.rglob("*"):
            if f.is_file():
                z.write(f, f"{plug.name}/{f.relative_to(plug).as_posix()}")
    assert _run(["verify", str(archive)]) == 0


# ── fix mode (repairs, then verifies) ─────────────────────────────────────────

def test_fix_whitens_then_passes(plugin_factory, capsys):
    plug = plugin_factory(white_icons=False)
    code = _run(["fix", str(plug)])
    out = capsys.readouterr().out
    assert "auto-fixed" in out and "whiten-icon" in out
    assert code == 0                       # green after the fix
    assert "publication-ready" in out


def test_fix_nothing_to_do(plugin_factory, capsys):
    assert _run(["fix", str(plugin_factory())]) == 0
    assert "nothing to auto-fix" in capsys.readouterr().out


def test_fix_refuses_container(plugin_factory, tmp_path):
    plug = plugin_factory()
    archive = tmp_path / "demo.streamDeckPlugin"
    with zipfile.ZipFile(archive, "w") as z:
        for f in plug.rglob("*"):
            if f.is_file():
                z.write(f, f"{plug.name}/{f.relative_to(plug).as_posix()}")
    code = _run(["fix", str(archive)])
    assert code != 0  # sys.exit(str) → code 1, with an explanatory message


def test_fix_leaves_foreign_reference_for_human(plugin_factory, capsys):
    plug = plugin_factory(locale_extra={"x": "Connect your Bluetooth speaker"})
    code = _run(["fix", str(plug)])
    assert code == 1  # foreign reference is NOT auto-fixed → still blocks
    assert "foreign-reference" in capsys.readouterr().out
