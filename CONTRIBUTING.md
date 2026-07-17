# Contributing

Thanks for your interest! This is a small, dependency-light toolkit
(Python 3 + Pillow; `rsvg-convert` for SVG rendering).

## Run the tests

```sh
python3 -m pytest tests/
```

`tests/icons/` covers `sdicons`, `tests/plugins/` covers `sdplugin`; both
exercise the shared `sdcommon` core.

## Ground rules

- Keep each module single-responsibility and under ~1000 lines.
- Any behaviour shared by both tools lives in `sdcommon/`, never duplicated.
- The Elgato constants live in `sdicons/spec.py` and `sdplugin/spec.py` — update
  those (and the docs that mirror them) if the platform changes, and say how you
  verified the new value.
- New checks return `Finding(level, code, message)`; add a test that both fires
  and stays quiet appropriately.

Issues and PRs welcome.
