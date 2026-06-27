# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

A Fusion 360 Python add-in that generates Steve Peterson's "Perfect Print" gears (a
3D-print-optimized constant-width cycloidal profile) as a matched wheel + pinion pair. v1 outputs
**solid** gears (extrude + circular pattern) built from fully-constrained parametric sketches.

## Commands

```bash
# Full test suite (pure engine + settings + interference guard — no Fusion needed)
.venv/Scripts/python.exe -m pytest tests/ -q

# A subset / single test
.venv/Scripts/python.exe -m pytest tests/ -q -k "interference"

# Syntax-check the Fusion layer (it imports `adsk`, so it can't be imported/tested here;
# this is what CI runs)
.venv/Scripts/python.exe -m compileall -q core commands lib config.py PerfectPrintGears.py
```

The `.venv` has pytest, matplotlib, numpy, pymupdf, ezdxf. The Fusion layer can only be verified by
loading the add-in in Fusion (the user's job) or by exporting a DXF to `tmp/` and parsing it with the
helper scripts there.

## Architecture

Two deliberately separated layers:

- **`core/gear_math.py`** — pure-Python geometry engine. No `adsk`, no numpy. Works in **mm**. Holds
  the conjugate wheel-tip math, tooth builders, and `closed_gear_polygon` (used by the interference
  test). Unit-testable without Fusion.
- **Fusion layer** (`core/sketch_builder.py`, `commands/generateGears/entry.py`,
  `lib/fusionAddInUtils/`) — renders engine output into a fully-constrained parametric sketch, then
  extrudes + circular-patterns it into solid gears. Converts **mm → cm** (`MM_TO_CM = 0.1`).

## Critical constraints

- **The conjugate geometry is solved and validated — do not re-derive or "fix" it.** The wheel tip is
  the conjugate of the straight constant-width pinion flank; the ~12° corner at the flank/tip join is
  real and intentional (forcing tangency deviates more). Feature width is derived from the module, not
  a user input — Peterson's tip cannot be regenerated parametrically, so changing any input means
  re-running the add-in. `tests/test_interference.py` is the guard: it rolls the closed gear outlines
  through a mesh cycle and checks penetration stays at the noise floor (~0).
- **Geometry and sketch-constraint work is collaborative, one step at a time** — propose a single
  step, the user tests it in Fusion and confirms before the next; don't batch changes. Research the
  Fusion API (WebFetch the help pages) before using it — several plausible-but-wrong calls exist.
- **Releases are automated** by python-semantic-release on push to `main`, driven by **Conventional
  Commits** (`feat:` → minor, `fix:` → patch, `BREAKING CHANGE` → major). It stamps the version into
  `PerfectPrintGears.manifest` and writes `CHANGELOG.md` — don't edit those by hand. Config:
  `pyproject.toml`; CI: `.github/workflows/ci.yml`.

## Keep docs in sync

When you change what the add-in does or how it is used, update **`README.md`** and the **`description`
field in `PerfectPrintGears.manifest`** as part of the same change, so the user-facing docs and the
in-Fusion description don't drift from actual behavior.
