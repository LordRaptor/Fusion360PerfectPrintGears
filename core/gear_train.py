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


def _generate(q: TrainQuery, n: int) -> list:
    """All exact `n`-stage trains over [teeth_min, teeth_max], both directions.
    When q.coaxial is set, the first stage fixes the tooth sum S and every later stage
    must satisfy driving + driven == S (equal center distance at one module).

    Raw list -- may contain reorderings/duplicates; dedup/order happens in search().

    Recursion: `remaining` is the product the not-yet-placed stages must still equal.
    Placing stage (a, b) consumes a factor, leaving remaining * b / a for the rest.
    Prune: after placing a stage, k-1 remain, so the child's remaining must lie in
    [(L/H)^(k-1), (H/L)^(k-1)]. Solving that for b bounds the inner loop to a slice of
    the range instead of the whole range (and collapses the final stage to exact
    divisors). Accept a leaf iff remaining == 1.
    """
    out = []
    L, H = q.teeth_min, q.teeth_max
    target = Fraction(q.target_num, q.target_den)

    def recurse(remaining: Fraction, k: int, stages: tuple, coax_sum):
        if k == 0:
            if remaining == 1:
                out.append(GearTrain(stages))
            return
        lo = Fraction(L, H) ** (k - 1)   # child ratio-range lower bound
        hi = Fraction(H, L) ** (k - 1)   # child ratio-range upper bound
        for a in range(L, H + 1):
            # child remaining = remaining * b / a must be in [lo, hi]  =>
            #   b in [ a*lo/remaining , a*hi/remaining ]
            b_lo = max(L, math.ceil(a * lo / remaining))
            b_hi = min(H, math.floor(a * hi / remaining))
            for b in range(b_lo, b_hi + 1):
                if coax_sum is not None and a + b != coax_sum:
                    continue
                # First stage of a coaxial search fixes the shared sum for the rest.
                next_sum = coax_sum if coax_sum is not None else (a + b if q.coaxial else None)
                recurse(remaining * Fraction(b, a), k - 1,
                        stages + (Stage(a, b),), next_sum)

    recurse(target, n, (), None)
    return out


@dataclass(frozen=True)
class SearchResult:
    trains: list = field(default_factory=list)   # list[GearTrain], ordered
    truncated: bool = False
    warnings: tuple = ()
    error: object = None                          # str | None


def _canonical(train: GearTrain) -> tuple:
    # Direction-aware, order-independent key: (driving, driven) pairs, sorted.
    return tuple(sorted((s.driving, s.driven) for s in train.stages))


def _sort_key(train: GearTrain) -> tuple:
    return (len(train.stages), train.total_teeth(), _canonical(train))


def search(q: TrainQuery) -> SearchResult:
    """Validate -> normalize -> generate across the stage-count range -> dedup -> order
    -> cap. Fewest stages first, then most compact (smallest total tooth count)."""
    errors = validate(q)
    if errors:
        return SearchResult(trains=[], truncated=False, warnings=(), error='; '.join(errors))

    q, warnings = normalize(q)
    seen = {}
    for n in range(q.min_stages, q.max_stages + 1):
        if q.direction == 'same' and n % 2 != 0:
            continue
        if q.direction == 'opposite' and n % 2 == 0:
            continue
        for train in _generate(q, n):
            key = _canonical(train)
            if key not in seen:
                seen[key] = train

    trains = sorted(seen.values(), key=_sort_key)
    truncated = len(trains) > MAX_RESULTS
    if truncated:
        trains = trains[:MAX_RESULTS]
    return SearchResult(trains=trains, truncated=truncated,
                        warnings=tuple(warnings), error=None)


def _is_coaxial(train: GearTrain) -> bool:
    return len(train.stages) >= 2 and len({s.tooth_sum() for s in train.stages}) == 1


def _train_to_dict(train: GearTrain) -> dict:
    r = train.ratio()
    return {
        'stages': [{'driving': s.driving, 'driven': s.driven, 'tooth_sum': s.tooth_sum()}
                   for s in train.stages],
        'ratio': f'{r.numerator} : {r.denominator}',
        'ratio_decimal': float(r),
        'num_gears': train.num_gears(),
        'total_teeth': train.total_teeth(),
        'direction': 'same' if train.direction() == 1 else 'opposite',
        'coaxial_sum': train.stages[0].tooth_sum() if _is_coaxial(train) else None,
    }


def result_to_dict(result: SearchResult) -> dict:
    """JSON-ready dict matching the Palette message protocol."""
    return {
        'trains': [_train_to_dict(t) for t in result.trains],
        'truncated': result.truncated,
        'warnings': list(result.warnings),
        'error': result.error,
    }
