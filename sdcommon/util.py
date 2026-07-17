"""Console colour helpers (TTY-only, so piped output stays clean)."""
import sys

_TTY = sys.stdout.isatty()


def _c(code, s):
    return f"\033[{code}m{s}\033[0m" if _TTY else s


def ok(s):   return _c("32", s)   # green
def warn(s): return _c("33", s)   # yellow
def err(s):  return _c("31", s)   # red
def dim(s):  return _c("2", s)    # dim
