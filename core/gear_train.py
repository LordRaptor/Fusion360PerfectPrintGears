"""Pure-Python compound gear-train search for exact clock ratios.

No `adsk`, no numpy. Works in tooth counts and exact `fractions.Fraction` ratios.
A *stage* is one external mesh of a driving gear and a driven gear; either may have
more teeth (both speed directions allowed). A train's overall ratio is the product of
its stage ratios. See docs/superpowers/specs/2026-06-28-gear-train-calculator-design.md.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from fractions import Fraction

MAX_RESULTS = 200          # hard cap on returned trains; truncation is reported, never silent
MIN_TEETH_WARN = 6         # cycloidal pinions below this are hard to print/cut (warning only)


@dataclass(frozen=True)
class Stage:
    driving: int           # driver tooth count
    driven: int            # driven tooth count (may be greater OR less than driving)

    def ratio(self) -> Fraction:
        return Fraction(self.driving, self.driven)

    def tooth_sum(self) -> int:
        return self.driving + self.driven


@dataclass(frozen=True)
class GearTrain:
    stages: tuple

    def ratio(self) -> Fraction:
        r = Fraction(1)
        for s in self.stages:
            r *= s.ratio()
        return r

    def num_gears(self) -> int:
        return 2 * len(self.stages)

    def total_teeth(self) -> int:
        return sum(s.driving + s.driven for s in self.stages)

    def direction(self) -> int:
        # Each external mesh reverses rotation: (-1)^(number of stages).
        return -1 if len(self.stages) % 2 else 1


@dataclass(frozen=True)
class TrainQuery:
    target_num: int            # P in the target ratio P : Q (any positive rational)
    target_den: int            # Q
    min_stages: int
    max_stages: int
    teeth_min: int             # single shared range: BOTH gears of every stage
    teeth_max: int             #   draw from [teeth_min, teeth_max]
    direction: str = 'any'     # 'same' | 'opposite' | 'any' (rotation sense, not speed)
    coaxial: bool = False      # input & output share one shaft (equal-tooth-sum rule)


def validate(q: TrainQuery) -> list:
    """Return a list of hard-error strings (empty == valid). Small teeth and the
    coaxial min-stage bump are WARNINGS handled in normalize(), not errors here."""
    errors = []
    if q.target_num <= 0 or q.target_den <= 0:
        errors.append('Target ratio P and Q must both be positive integers.')
    if q.teeth_min < 1:
        errors.append('Minimum tooth count must be at least 1.')
    if q.teeth_max < q.teeth_min:
        errors.append('Maximum tooth count must be >= minimum tooth count.')
    if q.min_stages < 1:
        errors.append('Minimum stage count must be at least 1.')
    if q.max_stages < q.min_stages:
        errors.append('Maximum stage count must be >= minimum stage count.')
    if q.direction not in ('same', 'opposite', 'any'):
        errors.append("Direction must be 'same', 'opposite', or 'any'.")
    return errors


def normalize(q: TrainQuery):
    """Return (adjusted_query, warnings). Coaxial forces >= 2 stages; very small tooth
    counts are flagged. These are advisories, never errors."""
    warnings = []
    min_stages = q.min_stages
    if q.coaxial and min_stages < 2:
        min_stages = 2
        warnings.append('Coaxial input/output requires at least 2 stages; '
                        'raised the minimum stage count to 2.')
    if q.teeth_min < MIN_TEETH_WARN:
        warnings.append(f'Tooth counts below {MIN_TEETH_WARN} are hard to make as '
                        f'cycloidal pinions; some results may be impractical to print.')
    return replace(q, min_stages=min_stages), warnings
