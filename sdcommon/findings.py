"""The `Finding` model + reporting, shared by `sdicons verify` and
`sdplugin verify`.

A check appends `Finding(level, code, message)` — never a bare string — so
callers can group/filter by severity and code. `counts`/`has_blocking` drive the
exit policy; `print_report` renders a grouped, colour-coded report. ERROR blocks
publication, WARN is guidance, INFO is context; `--strict` promotes WARN to
blocking.
"""
from .util import ok, warn, err, dim

ERROR, WARN, INFO = "ERROR", "WARN", "INFO"


class Finding:
    __slots__ = ("level", "code", "message")

    def __init__(self, level, code, message):
        self.level = level
        self.code = code
        self.message = message

    def __repr__(self):
        return f"Finding({self.level}, {self.code!r}, {self.message!r})"

    def __eq__(self, other):
        return (isinstance(other, Finding) and self.level == other.level
                and self.code == other.code and self.message == other.message)


def counts(findings):
    c = {ERROR: 0, WARN: 0, INFO: 0}
    for f in findings:
        c[f.level] = c.get(f.level, 0) + 1
    return c


def has_blocking(findings, strict=False):
    c = counts(findings)
    return c[ERROR] > 0 or (strict and c[WARN] > 0)


def print_report(target, findings, strict=False,
                 clean_msg="publication-ready — no issues"):
    """Print findings grouped by severity, then a one-line verdict.

    `clean_msg` is the tail shown when there are no errors or warnings (each tool
    phrases its "all good" line slightly differently).
    """
    style = {ERROR: err, WARN: warn, INFO: dim}
    glyph = {ERROR: "✖", WARN: "⚠", INFO: "·"}
    for lvl in (ERROR, WARN, INFO):
        for f in [x for x in findings if x.level == lvl]:
            print(style[lvl](f"  {glyph[lvl]} [{f.code}] {f.message}"))
    c = counts(findings)
    if c[ERROR] == 0 and c[WARN] == 0:
        print(ok(f"  ✓ {target}: {clean_msg}"))
    elif c[ERROR] == 0:
        tail = " (blocking under --strict)" if strict and c[WARN] else ""
        print((err if (strict and c[WARN]) else ok)(
            f"  {'✖' if strict and c[WARN] else '✓'} {target}: "
            f"{c[WARN]} warning(s){tail}, {c[INFO]} info"))
    else:
        print(err(f"  ✖ {target}: {c[ERROR]} error(s), {c[WARN]} warning(s) — "
                  f"NOT ready to publish"))
