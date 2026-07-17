"""`sdplugin` — pre-publication tooling for a Stream Deck plugin. Two modes:

    sdplugin verify <UUID>.sdPlugin            # check only, never writes
    sdplugin verify dist/foo.streamDeckPlugin  # check the shipped bytes
    sdplugin fix    <UUID>.sdPlugin            # auto-repair, then re-verify

Common flags: --strict (warnings block), --foreign a,b (override foreign terms).
`verify` mutates nothing; `fix` applies the safe, unambiguous repairs (whiten
in-app icons, generate missing @2x) and then runs verify so you see what's left.
Exit non-zero on any ERROR (or any WARN under --strict).
"""
import argparse
import sys
from pathlib import Path

from . import __version__
from .verify import verify, verify_container, print_report, has_blocking


def _add_common(sp):
    sp.add_argument("target",
                    help="a <UUID>.sdPlugin directory (or, for verify, a "
                         ".streamDeckPlugin container)")
    sp.add_argument("--strict", action="store_true",
                    help="treat warnings as blocking")
    sp.add_argument("--foreign",
                    help="comma-separated foreign feature terms to forbid "
                         "(default: auto — every known term the plugin doesn't own)")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="sdplugin",
        description="Verify / auto-fix an Elgato Stream Deck plugin before publishing.")
    p.add_argument("--version", action="version", version=f"sdplugin {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)
    _add_common(sub.add_parser("verify", help="check the plugin (never writes)"))
    _add_common(sub.add_parser("fix", help="auto-repair safe defects, then verify"))
    args = p.parse_args(argv)

    foreign = args.foreign.split(",") if args.foreign else None
    t = Path(args.target)
    is_container = t.is_file() and t.name.endswith(".streamDeckPlugin")

    if args.cmd == "fix":
        if is_container:
            sys.exit("sdplugin fix: operates on a <UUID>.sdPlugin directory, "
                     "not a .streamDeckPlugin container. Fix the source, then repack.")
        from .autofix import autofix
        fixes = autofix(args.target)
        if fixes:
            print(f"→ auto-fixed {len(fixes)} issue(s):")
            for code, detail in fixes:
                print(f"    [{code}] {detail}")
        else:
            print("→ nothing to auto-fix")

    if is_container:
        findings = verify_container(args.target, foreign=foreign)
    else:
        findings = verify(args.target, foreign=foreign)
    print_report(args.target, findings, strict=args.strict)
    sys.exit(1 if has_blocking(findings, strict=args.strict) else 0)


if __name__ == "__main__":
    main()
