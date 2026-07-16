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
GENERATE_LIMIT = 20000     # safety valve: max trains materialized per stage level (see _generate)
WORK_BUDGET = 600_000      # safety valve: max stage placements explored per level (~4s worst
                           #   case; loose targets forced to high stage counts return partial,
                           #   truncation-flagged results rather than hanging -- narrow ranges)


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

    # Optional end-gear bounds (None -> use the general range). Input gear = the first
    # stage's DRIVING gear; output gear = the last stage's DRIVEN gear. Each must be a
    # complete pair, within [teeth_min, teeth_max]. See validate().
    input_min: int | None = None
    input_max: int | None = None
    output_min: int | None = None
    output_max: int | None = None


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
    for name, lo, hi in (('Input', q.input_min, q.input_max),
                         ('Output', q.output_min, q.output_max)):
        if lo is None and hi is None:
            continue
        if lo is None or hi is None:
            errors.append(f'{name} gear bound needs both a min and a max (or neither).')
            continue
        if hi < lo:
            errors.append(f'{name} gear max must be >= its min.')
        if lo < q.teeth_min or hi > q.teeth_max:
            errors.append(f'{name} gear bound must stay within the general tooth '
                          f'range ({q.teeth_min}-{q.teeth_max}).')
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


def _arrange_for_ends(stages, in_lo, in_hi, out_lo, out_hi):
    """Reorder `stages` (a tuple/sequence of Stage) as input-first ... output-last so the
    first stage's DRIVING gear lies in [in_lo, in_hi] and the last stage's DRIVEN gear lies
    in [out_lo, out_hi]. Return the reordered tuple, or None if no such arrangement exists.

    A single stage cannot be both the input arbor and the output arbor, so for >= 2 stages
    the input and output stages must sit at DIFFERENT positions. Middle stages keep their
    (canonical) order. Duplicate identical stages are distinct positions, so they qualify.
    """
    n = len(stages)
    if n == 1:
        s = stages[0]
        if in_lo <= s.driving <= in_hi and out_lo <= s.driven <= out_hi:
            return tuple(stages)
        return None
    in_idx = [k for k, s in enumerate(stages) if in_lo <= s.driving <= in_hi]
    out_idx = [k for k, s in enumerate(stages) if out_lo <= s.driven <= out_hi]
    for i in in_idx:
        for j in out_idx:
            if i != j:
                middle = [stages[k] for k in range(n) if k != i and k != j]
                return (stages[i],) + tuple(middle) + (stages[j],)
    return None


def _enumerate(q: TrainQuery, n: int, limit=None, work_budget=None):
    """Enumerate exact `n`-stage trains; return (trains, truncated).

    All exact `n`-stage trains over [teeth_min, teeth_max], both directions.
    When q.coaxial is set, the first stage fixes the tooth sum S and every later stage
    must satisfy driving + driven == S (equal center distance at one module).

    Stages are placed in canonical non-decreasing (driving, driven) order, so each stage
    multiset is emitted exactly once -- no n! reorderings (the raw list is already
    duplicate-free). `search()` still dedups across stage counts as a backstop.

    Recursion: `remaining` is the product the not-yet-placed stages must still equal.
    Placing stage (a, b) consumes a factor, leaving remaining * b / a for the rest.
    Prune: after placing a stage, k-1 remain, so the child's remaining must lie in
    [(L/H)^(k-1), (H/L)^(k-1)]. Solving that for b bounds the inner loop to a slice of
    the range instead of the whole range (and collapses the final stage to exact
    divisors). Accept a leaf iff remaining == 1. A coaxial stage after the first has its
    sum fixed, so b = S - a is a single value, not a loop.

    Safety valves (both report truncation via search() when they trip): `limit` caps the
    number of trains materialized (memory); `work_budget` caps stage placements explored
    (time). Gear-train search is NP-hard in general and loose targets over wide ranges
    have astronomically many exact solutions; since search() only keeps MAX_RESULTS,
    there is no point exploring further. The known-better algorithm for the overlapping
    subproblems is DP/memoization on the remaining-ratio state, but with a small result
    cap the bounded DFS is sufficient.
    """
    out = []
    L, H = q.teeth_min, q.teeth_max
    in_lo = q.input_min if q.input_min is not None else L
    in_hi = q.input_max if q.input_max is not None else H
    out_lo = q.output_min if q.output_min is not None else L
    out_hi = q.output_max if q.output_max is not None else H
    # Apply end-gear filtering/ordering if ANY bound field is set. validate() guarantees
    # complete pairs via search(); keying on all four (not just the mins) also makes a
    # direct _enumerate() call honour a lone max instead of silently dropping it.
    bounded = any(v is not None for v in
                  (q.input_min, q.input_max, q.output_min, q.output_max))
    target = Fraction(q.target_num, q.target_den)
    work = [0]                           # stage placements explored; bounded by work_budget

    def stop() -> bool:
        return ((limit is not None and len(out) >= limit) or
                (work_budget is not None and work[0] >= work_budget))

    def recurse(remaining: Fraction, k: int, stages: tuple, coax_sum, prev):
        if stop():
            return
        if k == 0:
            if remaining == 1:
                if bounded:
                    arranged = _arrange_for_ends(stages, in_lo, in_hi, out_lo, out_hi)
                    if arranged is not None:
                        out.append(GearTrain(arranged))
                else:
                    out.append(GearTrain(stages))
            return
        lo = Fraction(L, H) ** (k - 1)   # child ratio-range lower bound
        hi = Fraction(H, L) ** (k - 1)   # child ratio-range upper bound
        pa, pb = prev                    # last placed stage; enforce (a, b) >= (pa, pb)
        for a in range(max(L, pa), H + 1):
            work[0] += 1                 # count the per-a slice computation (bounds time)
            # child remaining = remaining * b / a must be in [lo, hi]  =>
            #   b in [ a*lo/remaining , a*hi/remaining ]
            b_lo = max(L, math.ceil(a * lo / remaining))
            b_hi = min(H, math.floor(a * hi / remaining))
            if a == pa:                  # non-decreasing order: same driving -> driven >= pb
                b_lo = max(b_lo, pb)
            if coax_sum is not None:
                # Coaxial stage after the first: b is forced to coax_sum - a. Test the
                # single candidate instead of scanning (and rejecting) the whole slice.
                b = coax_sum - a
                if b_lo <= b <= b_hi:
                    recurse(remaining * Fraction(b, a), k - 1,
                            stages + (Stage(a, b),), coax_sum, (a, b))
            else:
                for b in range(b_lo, b_hi + 1):
                    work[0] += 1
                    # The first stage of a coaxial search fixes the shared sum S.
                    next_sum = a + b if q.coaxial else None
                    recurse(remaining * Fraction(b, a), k - 1,
                            stages + (Stage(a, b),), next_sum, (a, b))
            if stop():
                return

    recurse(target, n, (), None, (0, 0))
    truncated = ((limit is not None and len(out) >= limit) or
                 (work_budget is not None and work[0] >= work_budget))
    return out, truncated


def _generate(q: TrainQuery, n: int, limit=None, work_budget=None) -> list:
    """Backward-compatible wrapper returning just the train list (see `_enumerate`)."""
    return _enumerate(q, n, limit=limit, work_budget=work_budget)[0]


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
    truncated = False
    for n in range(q.min_stages, q.max_stages + 1):
        if q.direction == 'same' and n % 2 != 0:
            continue
        if q.direction == 'opposite' and n % 2 == 0:
            continue
        level, level_truncated = _enumerate(q, n, limit=GENERATE_LIMIT,
                                             work_budget=WORK_BUDGET)
        if level_truncated:
            truncated = True          # a safety valve tripped -> this level was cut short
        for train in level:
            key = _canonical(train)
            if key not in seen:
                seen[key] = train
        if len(seen) >= MAX_RESULTS:
            # Results sort by (num_stages, ...), so every higher-stage-count train sorts
            # strictly after these -- it can never enter the top MAX_RESULTS. Stop
            # climbing; more solutions may exist at higher stage counts, so flag truncation.
            truncated = True
            break

    trains = sorted(seen.values(), key=_sort_key)
    if len(trains) > MAX_RESULTS:
        truncated = True
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
