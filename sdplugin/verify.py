"""Pre-publication verifier for a Stream Deck plugin — the plugin sibling of
`sdicons verify`.

It encodes the automatable half of docs/MARKETPLACE-REVIEW.md's checklist so a
plugin never gets rejected for something a script could have caught:

  * WHITE in-app icons (§1) — plugin Icon, CategoryIcon and every action Icon
    must be white-monochrome on transparent (the #1 plugin rejection).
  * NO cross-plugin / stale references (§2) — a user-visible file naming a
    feature the plugin doesn't ship ("mention of a bluetooth action we don't
    see included").
  * Manifest gate (§4) — SDKVersion, Software.MinimumVersion, 2–30 actions,
    no Nodejs.Debug, valid UUID matching the folder, referenced images (@1x+@2x)
    and Property Inspector files present.

`verify(plugin_dir)` checks a `<UUID>.sdPlugin` directory; `verify_container`
unzips a shipped `.streamDeckPlugin` and checks the real bytes. Levels:
ERROR blocks, WARN is guidance, INFO is context. Human-only steps (demo video,
gallery re-shoot, the final Submit) stay in the doc — the tool never claims
those are done.
"""
import json
import re
from pathlib import Path

from PIL import Image

from . import spec
from sdcommon.findings import (Finding, ERROR, WARN, INFO,
                               counts, has_blocking, print_report as _print_report)
from sdcommon.container import verify_container as _verify_container


# ── helpers ──────────────────────────────────────────────────────────────────

def _resolve_pair(plugin: Path, ref: str):
    """(‹ref›.png, ‹ref›@2x.png) paths for a manifest image reference.

    Manifest image values omit the extension (e.g. "imgs/plugin/icon"); Elgato
    resolves .png and, for retina, the `@2x` variant.
    """
    base = plugin / ref
    return base.with_suffix(".png"), base.parent / f"{base.name}{spec.RETINA_SUFFIX}.png"


def _is_white_monochrome(png: Path):
    """(is_white, detail). White = every opaque pixel ≥ WHITE_MIN on all
    channels, within WHITE_NONWHITE_TOLERANCE. Returns (None, err) if unreadable."""
    try:
        with Image.open(png) as im:
            raw = im.convert("RGBA").tobytes()
    except Exception as e:
        return None, f"cannot read ({e})"
    opaque = nonwhite = 0
    # Iterate the raw RGBA bytes in 4-byte pixels (avoids the deprecated
    # Image.getdata() iterator and is faster for a full-image scan).
    for i in range(0, len(raw), 4):
        r, g, b, a = raw[i], raw[i + 1], raw[i + 2], raw[i + 3]
        if a >= spec.ICON_ALPHA_OPAQUE:
            opaque += 1
            if not (r >= spec.WHITE_MIN and g >= spec.WHITE_MIN and b >= spec.WHITE_MIN):
                nonwhite += 1
    if opaque == 0:
        return False, "fully transparent (no glyph)"
    frac = nonwhite / opaque
    return frac <= spec.WHITE_NONWHITE_TOLERANCE, f"{nonwhite}/{opaque} non-white px"


def _own_terms(manifest: dict) -> set:
    """Feature terms the plugin legitimately owns (from its identity blob)."""
    blob = " ".join(str(manifest.get(k, "")) for k in
                    ("Name", "Category", "UUID", "Description")).lower()
    owned = set()
    for canon, aliases in spec.KNOWN_FEATURE_TERMS.items():
        if any(a in blob for a in aliases):
            owned.add(canon)
    return owned


# ── checks ───────────────────────────────────────────────────────────────────

def check_manifest(plugin, ctx):
    out = []
    m = ctx["manifest"]
    if ctx["manifest_error"]:
        return [Finding(ERROR, "manifest", ctx["manifest_error"])]
    for field in spec.MANIFEST_REQUIRED:
        if not m.get(field):
            out.append(Finding(ERROR, "missing-field",
                               f"manifest: missing required field '{field}'"))
    uuid = m.get("UUID", "")
    if uuid and not re.match(spec.UUID_RE, uuid):
        out.append(Finding(ERROR, "bad-uuid",
                           f"manifest: UUID {uuid!r} is not reverse-domain"))
    if uuid and ctx["dirname"] and ctx["dirname"] != f"{uuid}{spec.SDPLUGIN_SUFFIX}":
        out.append(Finding(WARN, "uuid-folder",
                           f"folder {ctx['dirname']!r} != '{uuid}{spec.SDPLUGIN_SUFFIX}'"))
    ver = str(m.get("Version", ""))
    if ver and not re.match(spec.VERSION_RE, ver):
        out.append(Finding(ERROR, "bad-version",
                           f"manifest: Version {ver!r} must be 2–4 numbers (x.y.z.b)"))
    sdk = m.get("SDKVersion")
    if isinstance(sdk, int) and sdk < spec.MIN_SDK_VERSION:
        out.append(Finding(ERROR, "sdk-version",
                           f"manifest: SDKVersion {sdk} < {spec.MIN_SDK_VERSION}"))
    sw = (m.get("Software") or {}).get("MinimumVersion")
    if sw:
        try:
            tup = tuple(int(x) for x in str(sw).split("."))
            if tup < spec.MIN_SOFTWARE_VERSION:
                out.append(Finding(ERROR, "software-version",
                                   f"manifest: Software.MinimumVersion {sw} < "
                                   f"{'.'.join(map(str, spec.MIN_SOFTWARE_VERSION))}"))
        except ValueError:
            out.append(Finding(WARN, "software-version",
                               f"manifest: Software.MinimumVersion {sw!r} not numeric"))
    actions = m.get("Actions") or []
    n = len(actions)
    if n < spec.ACTIONS_MIN or n > spec.ACTIONS_MAX:
        out.append(Finding(ERROR, "action-count",
                           f"manifest: {n} actions (Elgato requires "
                           f"{spec.ACTIONS_MIN}–{spec.ACTIONS_MAX})"))
    if (m.get("Nodejs") or {}).get("Debug") == spec.FORBIDDEN_NODEJS_DEBUG:
        out.append(Finding(ERROR, "nodejs-debug",
                           "manifest: Nodejs.Debug='enabled' must not ship"))
    cp = m.get("CodePath")
    if cp and not (plugin / cp).exists():
        out.append(Finding(ERROR, "missing-codepath",
                           f"manifest: CodePath '{cp}' does not exist"))
    if not m.get("Category"):
        out.append(Finding(WARN, "no-category",
                           "manifest: no Category (actions list ungrouped)"))
    return out


def check_white_icons(plugin, ctx):
    """§1 — the in-app icons must be white monochrome on transparent."""
    out = []
    m = ctx["manifest"]
    refs = []
    for f in spec.WHITE_ICON_FIELDS:
        if m.get(f):
            refs.append((f, m[f]))
    for a in (m.get("Actions") or []):
        if a.get(spec.WHITE_ACTION_ICON):
            refs.append((f"action:{a.get('UUID', a.get('Name', '?'))}",
                         a[spec.WHITE_ACTION_ICON]))
    for label, ref in refs:
        for png in _resolve_pair(plugin, ref):
            if not png.exists():
                continue  # existence handled by check_images
            white, detail = _is_white_monochrome(png)
            rel = png.relative_to(plugin).as_posix()
            if white is None:
                out.append(Finding(ERROR, "icon-unreadable", f"{rel}: {detail}"))
            elif not white:
                out.append(Finding(
                    ERROR, "non-white-icon",
                    f"{rel} ({label}): not white monochrome ({detail}) — in-app "
                    f"icons must be #FFFFFF on transparent (Elgato §1)"))
    return out


def check_images(plugin, ctx):
    """Every referenced image (in-app icons + key State images) needs @1x+@2x."""
    out = []
    m = ctx["manifest"]
    refs = set()
    for f in ("Icon", "CategoryIcon"):
        if m.get(f):
            refs.add(m[f])
    for a in (m.get("Actions") or []):
        if a.get("Icon"):
            refs.add(a["Icon"])
        for st in (a.get("States") or []):
            if st.get("Image"):
                refs.add(st["Image"])
    for ref in sorted(refs):
        one, two = _resolve_pair(plugin, ref)
        if not one.exists():
            out.append(Finding(ERROR, "missing-image",
                               f"manifest image '{ref}' → {one.name} missing"))
        if not two.exists():
            out.append(Finding(WARN, "missing-retina",
                               f"manifest image '{ref}' → {two.name} (@2x) missing"))
    return out


def check_property_inspectors(plugin, ctx):
    out = []
    m = ctx["manifest"]
    pis = set()
    if m.get("PropertyInspectorPath"):
        pis.add(m["PropertyInspectorPath"])
    for a in (m.get("Actions") or []):
        if a.get("PropertyInspectorPath"):
            pis.add(a["PropertyInspectorPath"])
    for pi in sorted(pis):
        if not (plugin / pi).exists():
            out.append(Finding(ERROR, "missing-pi",
                               f"PropertyInspectorPath '{pi}' does not exist"))
    return out


def check_foreign_refs(plugin, ctx):
    """§2 — no user-visible mention of a feature the plugin doesn't ship."""
    out = []
    foreign = ctx["foreign_terms"]
    if not foreign:
        return out
    # Build one alias→canonical map for the foreign set.
    alias_to_canon = {}
    for canon in foreign:
        for a in spec.KNOWN_FEATURE_TERMS[canon]:
            alias_to_canon[a] = canon
    # Word-boundary patterns (so "bt" doesn't match "subtle"; "wifi"/"wi-fi" ok).
    patterns = {a: re.compile(rf"(?<![a-z0-9]){re.escape(a)}(?![a-z0-9])", re.I)
                for a in alias_to_canon}

    files = []
    for g in spec.VISIBLE_GLOBS:
        files.extend(plugin.glob(g))
    for f in sorted(set(files)):
        if f.name == spec.MANIFEST:
            continue  # manifest scanned separately below
        try:
            text = f.read_text(errors="ignore")
        except Exception:
            continue
        for a, pat in patterns.items():
            if pat.search(text):
                out.append(Finding(
                    ERROR, "foreign-reference",
                    f"{f.relative_to(plugin).as_posix()}: mentions "
                    f"'{a}' ({alias_to_canon[a]}) — a feature this plugin "
                    f"doesn't ship (Elgato §2). Remove the stray reference."))
    # manifest user-visible strings
    m = ctx["manifest"]
    mblob = " ".join(
        [str(m.get("Description", "")), str(m.get("Name", ""))]
        + [str(a.get("Name", "")) + " " + str(a.get("Tooltip", ""))
           for a in (m.get("Actions") or [])])
    for a, pat in patterns.items():
        if pat.search(mblob):
            out.append(Finding(ERROR, "foreign-reference",
                               f"manifest.json: mentions '{a}' "
                               f"({alias_to_canon[a]}) — not a shipped feature (§2)"))
    return out


_CHECKS = (
    check_manifest,
    check_white_icons,
    check_images,
    check_property_inspectors,
    check_foreign_refs,
)


def verify(plugin_dir, foreign=None) -> list:
    """Verify a `<UUID>.sdPlugin` directory.

    `foreign` overrides the auto-derived foreign-term set (a list of canonical
    KNOWN_FEATURE_TERMS keys). Default: every KNOWN term the plugin does NOT own.
    """
    plugin = Path(plugin_dir)
    mpath = plugin / spec.MANIFEST
    manifest, manifest_error = {}, None
    if not mpath.exists():
        manifest_error = f"missing {spec.MANIFEST}"
    else:
        try:
            manifest = json.loads(mpath.read_text())
        except json.JSONDecodeError as e:
            manifest_error = f"{spec.MANIFEST} is not valid JSON: {e}"
    if foreign is not None:
        foreign_terms = set(foreign) & set(spec.KNOWN_FEATURE_TERMS)
    else:
        foreign_terms = set(spec.KNOWN_FEATURE_TERMS) - _own_terms(manifest)
    ctx = {"manifest": manifest, "manifest_error": manifest_error,
           "dirname": plugin.name, "foreign_terms": foreign_terms}
    findings = []
    for chk in _CHECKS:
        findings.extend(chk(plugin, ctx))
        if chk is check_manifest and manifest_error:
            break  # nothing else is checkable without a manifest
    return findings


def verify_container(archive, foreign=None) -> list:
    """Unzip a shipped `.streamDeckPlugin` and verify the real bytes inside.

    Delegates the zip mechanics to the shared `sdcommon.container` helper.
    """
    return _verify_container(archive, spec.SDPLUGIN_SUFFIX, verify, foreign=foreign)


def print_report(target, findings, strict=False):
    """Report with the plugin-specific "no automatable issues" clean line."""
    _print_report(target, findings, strict=strict,
                  clean_msg="publication-ready — no automatable issues")


# `counts`, `has_blocking` are imported from sdcommon.findings and re-exported
# here so `from .verify import counts, has_blocking` keeps working.
