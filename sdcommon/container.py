"""Verify the real bytes inside a shipped container (a `.streamDeckIconPack` or
`.streamDeckPlugin` zip), shared by both tools.

`verify_container` unzips to a temp dir, locates the inner wrapper folder by its
suffix (`.sdIconPack` / `.sdPlugin`), and runs the caller's `verify_fn` on it —
catching a container built before a fix that a directory check would miss.
"""
import tempfile
import zipfile
from pathlib import Path

from .findings import Finding, ERROR


def verify_container(archive, locate_suffix, verify_fn, **kw):
    """Unzip `archive`, find the `*locate_suffix` wrapper dir, verify it.

    Extra keyword args are forwarded to `verify_fn` (e.g. the plugin verifier's
    `foreign=`). Returns a `[Finding]` list; a missing/invalid archive is itself
    reported as a Finding rather than raised.
    """
    archive = Path(archive)
    if not archive.exists():
        return [Finding(ERROR, "no-container", f"{archive} does not exist")]
    try:
        with tempfile.TemporaryDirectory() as tmp:
            with zipfile.ZipFile(archive) as z:
                z.extractall(tmp)
            root = Path(tmp)
            subs = [d for d in root.rglob("*")
                    if d.is_dir() and d.name.endswith(locate_suffix)]
            inner = subs[0] if subs else root
            return verify_fn(inner, **kw)
    except zipfile.BadZipFile:
        return [Finding(ERROR, "bad-container",
                        f"{archive} is not a valid zip / container")]
