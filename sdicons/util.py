"""sdicons-specific helpers: slugging + external-tool discovery.

Coloured output lives in the shared core (`sdcommon.util`) and is re-exported
here so existing `from .util import ok, warn, err, dim` imports keep working.
"""
import re
import shutil
import sys

from sdcommon.util import ok, warn, err, dim  # re-exported for sdicons modules


def slug(name):
    """Filesystem-safe, grep-friendly slug for an icon basename."""
    s = re.sub(r"[^\w-]+", "-", name.strip().lower())
    return re.sub(r"-+", "-", s).strip("-")


def require_tool(name):
    """Fail loudly if an external binary (e.g. rsvg-convert) is missing."""
    path = shutil.which(name)
    if not path:
        sys.exit(err(f"required tool '{name}' not found on PATH. "
                     f"Install it (macOS: brew install librsvg for rsvg-convert)."))
    return path
