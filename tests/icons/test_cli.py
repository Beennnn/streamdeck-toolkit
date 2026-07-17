"""CLI modes: `verify` (check only) and `fix` (repair, then verify)."""
import pytest

from sdicons.cli import main
from sdicons import spec


def _run(argv):
    with pytest.raises(SystemExit) as e:
        main(argv)
    return e.value.code


def test_verify_clean_exits_zero(pack_factory):
    assert _run(["verify", str(pack_factory(with_posters=True))]) == 0


def test_verify_missing_poster_exits_one(pack_factory, capsys):
    assert _run(["verify", str(pack_factory(with_posters=False))]) == 1
    assert "missing-poster" in capsys.readouterr().out


def test_verify_does_not_write(pack_factory):
    pack = pack_factory(with_posters=False)
    _run(["verify", str(pack)])
    poster = pack / spec.DIR_ICONS / "accordion-playing.png"
    assert not poster.exists()  # verify never repairs


def test_fix_generates_posters_then_green(pack_factory, capsys):
    pack = pack_factory(with_posters=False)
    code = _run(["fix", str(pack)])
    out = capsys.readouterr().out
    assert "auto-fixed" in out
    assert (pack / spec.DIR_ICONS / "accordion-playing.png").exists()
    assert code == 0


def test_fix_nothing_to_do(pack_factory, capsys):
    assert _run(["fix", str(pack_factory(with_posters=True))]) == 0
    assert "nothing to auto-fix" in capsys.readouterr().out


def test_verify_fix_alias_matches_fix(pack_factory):
    pack = pack_factory(with_posters=False)
    assert _run(["verify", str(pack), "--fix"]) == 0
    assert (pack / spec.DIR_ICONS / "accordion-playing.png").exists()
