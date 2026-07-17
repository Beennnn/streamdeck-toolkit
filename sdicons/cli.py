"""Command-line dispatch for the icon-pack toolkit.

Subcommands (each maps to one cohesive module):
  new       scaffold an empty spec-shaped pack
  render    SVG source dir -> 144x144 icons in pack/icons/
  meta      (re)generate icons.json from icons/ + optional tags.json sidecar
  validate  lint the pack against the Elgato spec
  verify    pre-publication gate: validate + Maker-Console rejection checks
  posters   generate companion poster PNGs for animated icons (Icon Library)
  contact   build a contact-sheet PNG of the whole palette
  package   zip a validated pack into a submit-ready .streamDeckIconPack
  build     render + meta + validate + contact + package, end to end
  repair    fix an Icon Pack Man export (inject names/tags from tags.json)
  maker-media  generate Maker Console upload assets (thumbnail/previews/gallery)
  animate   assemble a folder of frames into a GIF/WEBP animated icon
"""
import argparse
import sys

from . import __version__

# Kept in sync with render.RESAMPLE — hardcoded here so argparse choices don't
# force an eager import of render (and Pillow) on every invocation.
_RESAMPLE_CHOICES = ("nearest", "bilinear", "bicubic", "lanczos")


def main(argv=None):
    p = argparse.ArgumentParser(
        prog="sdicons",
        description="Generate & publish Elgato Stream Deck icon packs.")
    p.add_argument("--version", action="version", version=f"sdicons {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    sp = sub.add_parser("new", help="scaffold an empty pack")
    sp.add_argument("pack"); sp.add_argument("--name"); sp.add_argument("--author")

    sp = sub.add_parser("render", help="render source SVGs into the pack")
    sp.add_argument("src"); sp.add_argument("pack")
    sp.add_argument("--keep-svg", action="store_true",
                    help="keep vector SVGs instead of rasterizing to PNG")
    sp.add_argument("--resample", choices=list(_RESAMPLE_CHOICES),
                    help="resize filter override (default: lanczos static, "
                         "nearest animated — nearest keeps pixel-art crisp)")

    sp = sub.add_parser("meta", help="regenerate icons.json")
    sp.add_argument("pack")

    sp = sub.add_parser("validate", help="lint the pack against the spec")
    sp.add_argument("pack")

    sp = sub.add_parser("verify",
                        help="pre-publication gate — check only, never writes")
    sp.add_argument("pack", help="pack directory OR a .streamDeckIconPack container")
    sp.add_argument("--strict", action="store_true",
                    help="treat warnings as blocking (exit non-zero on any warning)")
    sp.add_argument("--fix", action="store_true",
                    help="alias for the `fix` command: auto-repair, then verify")

    sp = sub.add_parser("fix",
                        help="auto-repair safe defects (posters, comma-tags), then verify")
    sp.add_argument("pack", help="pack directory")
    sp.add_argument("--strict", action="store_true",
                    help="treat warnings as blocking")

    sp = sub.add_parser("posters",
                        help="generate companion poster PNGs for animated icons")
    sp.add_argument("pack")

    sp = sub.add_parser("contact", help="build a contact-sheet PNG")
    sp.add_argument("pack"); sp.add_argument("--out")

    sp = sub.add_parser("package", help="build a submit-ready .streamDeckIconPack")
    sp.add_argument("pack"); sp.add_argument("--out-dir", default="dist")
    sp.add_argument("--id", help="reverse-domain pack id (default: com.<author>.<name>)")

    sp = sub.add_parser("build", help="render+meta+validate+contact+package")
    sp.add_argument("src"); sp.add_argument("pack")
    sp.add_argument("--keep-svg", action="store_true")
    sp.add_argument("--resample", choices=list(_RESAMPLE_CHOICES))
    sp.add_argument("--out-dir", default="dist")
    sp.add_argument("--name"); sp.add_argument("--author"); sp.add_argument("--id")

    sp = sub.add_parser("repair",
                        help="fix an Icon Pack Man export's icons.json names/tags")
    sp.add_argument("export", help="the exported .streamDeckIconPack (or .zip)")
    sp.add_argument("--tags", required=True,
                    help="tags.json mapping slug -> {name, tags}")
    sp.add_argument("--license", help="overwrite manifest License (e.g. CC-BY-4.0)")
    sp.add_argument("--url", help="overwrite manifest URL")
    sp.add_argument("--out", help="output path (default: overwrite input)")

    sp = sub.add_parser("maker-media",
                        help="generate Maker Console upload assets from a pack")
    sp.add_argument("pack")
    sp.add_argument("--out-dir", default="maker-media")
    sp.add_argument("--title", help="hero title (default: manifest Name)")
    sp.add_argument("--subtitle", help="hero subtitle line")
    sp.add_argument("--previews",
                    help="comma-separated icon slugs for the 5 preview tiles")
    sp.add_argument("--animated",
                    help="override: dir to source the animated gallery from "
                         "(default: auto — the pack's own gif/webp icons)")

    sp = sub.add_parser("animate",
                        help="assemble frame images into a GIF/WEBP animated icon")
    sp.add_argument("frames", help="directory of frame images (sorted by name)")
    sp.add_argument("--out", required=True, help="output .webp or .gif")
    sp.add_argument("--fps", type=int, default=15)

    args = p.parse_args(argv)

    # Lazy imports keep each subcommand's deps out of unrelated invocations.
    if args.cmd == "new":
        from .scaffold import new_pack
        new_pack(args.pack, args.name, args.author)

    elif args.cmd == "render":
        from .render import render_dir
        render_dir(args.src, args.pack, keep_svg=args.keep_svg,
                   resample=args.resample)

    elif args.cmd == "meta":
        from .meta import build_icons_json
        build_icons_json(args.pack)

    elif args.cmd == "validate":
        from .validate import validate, print_report
        errors, warnings = validate(args.pack)
        print_report(args.pack, errors, warnings)
        sys.exit(1 if errors else 0)

    elif args.cmd in ("verify", "fix"):
        from pathlib import Path as _P
        from . import spec as _spec
        from .verify import verify, verify_container, print_report, has_blocking
        target = args.pack
        is_container = _P(target).is_file() and target.endswith(_spec.PACK_EXT)
        # `fix` (or the `verify --fix` alias) auto-repairs a pack directory first.
        do_fix = args.cmd == "fix" or getattr(args, "fix", False)
        if do_fix and is_container:
            sys.exit("fix: operates on a pack directory, not a "
                     ".streamDeckIconPack container. Fix the source, then package.")
        if do_fix:
            from .autofix import autofix
            fixes = autofix(target)
            if fixes:
                print(f"→ auto-fixed {len(fixes)} issue(s):")
                for code, detail in fixes:
                    print(f"    [{code}] {detail}")
            else:
                print("→ nothing to auto-fix")
        findings = verify_container(target) if is_container else verify(target)
        print_report(target, findings, strict=args.strict)
        sys.exit(1 if has_blocking(findings, strict=args.strict) else 0)

    elif args.cmd == "posters":
        from pathlib import Path as _P
        from .posters import ensure_posters
        from . import spec as _spec
        made = ensure_posters(_P(args.pack) / _spec.DIR_ICONS, verbose=True)
        print(f"→ {len(made)} poster(s) generated")

    elif args.cmd == "contact":
        from .contact import contact_sheet
        contact_sheet(args.pack, args.out)

    elif args.cmd == "package":
        from .package import package
        package(args.pack, args.out_dir, args.id)

    elif args.cmd == "repair":
        from .repair import repair_export
        repair_export(args.export, args.tags,
                      license=args.license, url=args.url, out=args.out)

    elif args.cmd == "maker-media":
        from .makermedia import maker_media
        previews = args.previews.split(",") if args.previews else None
        maker_media(args.pack, args.out_dir, title=args.title,
                    subtitle=args.subtitle, previews=previews,
                    animated=args.animated)

    elif args.cmd == "animate":
        from .animate import animate_frames_dir
        animate_frames_dir(args.frames, args.out, fps=args.fps)

    elif args.cmd == "build":
        from .scaffold import ensure_skeleton
        from .render import render_dir
        from .meta import build_icons_json
        from .validate import validate, print_report
        from .contact import contact_sheet
        from .package import package
        print("→ scaffold"); ensure_skeleton(args.pack, args.name, args.author)
        print("→ render");   render_dir(args.src, args.pack, keep_svg=args.keep_svg,
                                         resample=args.resample)
        print("→ meta");     build_icons_json(args.pack)
        print("→ contact");  contact_sheet(args.pack)
        print("→ validate")
        errors, warnings = validate(args.pack)
        print_report(args.pack, errors, warnings)
        if errors:
            sys.exit(1)
        print("→ package");  package(args.pack, args.out_dir, args.id)


if __name__ == "__main__":
    main()
