"""Pure-Python compound gear-train search for exact clock ratios.

No `adsk`, no numpy. Works in tooth counts and exact `fractions.Fraction` ratios.
A *stage* is one external mesh of a driving gear and a driven gear; either may have
more teeth (both speed directions allowed). A train's overall ratio is the product of
its stage ratios. See docs/superpowers/specs/2026-06-28-gear-train-calculator-design.md.
"""
from __future__ import annotations

import math
from itertools import combinations, permutations
from dataclasses import dataclass, field, replace
from fractions import Fraction

MAX_RESULTS = 200          # hard cap on returned trains; truncation is reported, never silent
MIN_TEETH_WARN = 6         # cycloidal pinions below this are hard to print/cut (warning only)
GENERATE_LIMIT = 20000     # safety valve: max trains materialized per stage level (see _generate)
WORK_BUDGET = 600_000      # safety valve: max stage placements explored per level (~4s worst
                           #   case; loose targets forced to high stage counts return partial,
                           #   truncation-flagged results rather than hanging -- narrow ranges)

REFERENCE_SPAN = 80          # tooth-range span WORK_BUDGET was tuned against (e.g. teeth 8-90)
MAX_WORK_BUDGET = 3_000_000  # ceiling on the scaled budget, so the palette stays responsive

FIRST_STAGE_SLICE = 2000   # budget-fair exploration: starting per-first-stage work allowance.
                           #   Each distinct first stage gets this many placements, then the
                           #   allowance doubles and the cut-short ones are revisited, until the
                           #   space is exhausted or the work budget is spent. Stops one
                           #   small-gear prefix from draining the whole budget (see _enumerate).
                           #   LOAD-BEARING and non-monotonic: a LARGER slice reaches FEWER
                           #   first stages before the budget runs out, which reproduces the very
                           #   starvation this fixes (measured: at 20000 the deep-reduction
                           #   regression test finds nothing again). Retuning it must be
                           #   validated by sweeping the value, not just by running the suite.


def _work_budget(q: TrainQuery) -> int:
    """Work budget for `q`, scaled by how big its search space is.

    The number of candidate first stages grows ~quadratically with the tooth-range span, so a
    fixed budget explores a vanishing fraction of a wide range: budget-fair exploration then
    hands every first stage a slice too thin to reach any leaf, and the search comes back empty.
    Scale with the span, capped by MAX_WORK_BUDGET for responsiveness. A span at or below
    REFERENCE_SPAN keeps exactly WORK_BUDGET, so narrow queries -- including every completeness
    parity test -- are bit-for-bit unaffected.
    """
    span = q.teeth_max - q.teeth_min + 1
    scale = max(1.0, (span / REFERENCE_SPAN) ** 2)
    return min(MAX_WORK_BUDGET, int(WORK_BUDGET * scale))


BUILDABILITY_EMPTY_WARNING = (
    'No single-frame-buildable train found. Try raising the end-gear limit, adding a '
    'stage, widening the tooth range, or lowering the clearance.')


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

    # If True, every stage must match the target's SPEED direction (all step-up for a
    # step-up target, all step-down for a step-down target). Strictly stronger than the
    # always-on irreducibility rule. NOT the same as `direction` (which is rotation sense).
    monotonic: bool = False

    # Single-plane buildability clearance, in TEETH (a dimensionless multiple of the
    # module: g = 2*addendum + 2*shaft_radius/module + 2*safety). At each internal arbor a
    # wheel must clear the NON-meshing neighbouring shaft by at least this many teeth of
    # tooth-sum. Default 2 ~= one module of air. Always applied (see _clearance_ok).
    clearance: int = 2


def validate(q: TrainQuery) -> list:
    """Return a list of hard-error strings (empty == valid). Small teeth and the
    coaxial min-stage bump are WARNINGS handled in normalize(), not errors here."""
    errors = []
    if q.target_num <= 0 or q.target_den <= 0:
        errors.append('Target ratio P and Q must both be positive integers.')
    elif q.target_num == q.target_den:
        errors.append('Target ratio must not be 1:1 — a pass-through train serves '
                      'no purpose. Add a 1:1 idler manually if you only need to '
                      'reverse direction.')
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
    if q.clearance < 0:
        errors.append('Clearance (teeth) must be 0 or greater.')
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


def _arrange_buildable(stages, in_lo, in_hi, out_lo, out_hi, clearance):
    """Return an ordering of `stages` (input-first ... output-last) whose first DRIVING
    gear lies in [in_lo, in_hi], last DRIVEN gear lies in [out_lo, out_hi], AND which
    satisfies the single-plane clearance rule (see _clearance_ok). Return None if none.

    A train is an unordered multiset of stages, so this searches permutations; stage counts
    are tiny. This unifies the end-gear-bounds arrangement and buildability into one test.
    When no end bounds are set the caller passes the full tooth range, so only clearance
    constrains the ordering.
    """
    for order in permutations(stages):
        if not (in_lo <= order[0].driving <= in_hi):
            continue
        if not (out_lo <= order[-1].driven <= out_hi):
            continue
        if _clearance_ok(order, clearance):
            return order
    return None


def _is_irreducible(stages) -> bool:
    """True iff NO non-empty proper subset of `stages` has an exact Fraction ratio-product
    of 1. A reducible train has such a subset -- you could delete those stages and get a
    strictly shorter train with the identical overall ratio, so they are dead weight.

    `stages` is a tuple of Stage. Stage counts are tiny (a handful), so iterating the
    2**n - 2 proper non-empty subsets is cheap. Uses exact Fraction arithmetic (no
    tolerance). A 1-stage train has no proper non-empty subset -> trivially irreducible.
    A size-1 subset equal to 1 would be a unity stage (already pruned at placement);
    the general check harmlessly covers it too.
    """
    n = len(stages)
    ratios = [s.ratio() for s in stages]
    for size in range(1, n):                 # proper (size < n), non-empty (size >= 1)
        for combo in combinations(range(n), size):
            prod = Fraction(1)
            for i in combo:
                prod *= ratios[i]
            if prod == 1:
                return False
    return True


def _clearance_ok(order, clearance) -> bool:
    """True iff, laid out input->output as `order` (a sequence of Stage), every wheel's
    pitch radius clears the NON-meshing neighbouring arbor shaft by at least `clearance`
    teeth of tooth-sum.

    Derivation: the physical rule is wheel_radius + K < center_distance, i.e. N/2 + K < M/2,
    i.e. M - N >= 2K. With g = 2K in tooth units, at each internal arbor A_i (between
    order[i-1] and order[i]):
        sum(order[i])   - driven(order[i-1])  >= g   # driven wheel clears the FAR arbor
        sum(order[i-1]) - driving(order[i])   >= g   # driving wheel clears the NEAR arbor
    End arbors carry a single gear (no opposite neighbour), so a large wheel there is free.
    """
    for i in range(1, len(order)):
        if order[i].tooth_sum() - order[i - 1].driven < clearance:
            return False
        if order[i - 1].tooth_sum() - order[i].driving < clearance:
            return False
    return True


def _stage_key(stages) -> tuple:
    """Direction-aware, order-independent identity of a stage multiset: the (driving, driven)
    pairs, sorted. Two trains with the same key are the same train laid out differently, so
    this is what both _enumerate and search() dedup on. `(72, 90)` and `(90, 72)` are
    reciprocal stages and must stay distinct -- hence pairs, not sums.
    """
    return tuple(sorted((s.driving, s.driven) for s in stages))


def _spread(items) -> list:
    """Return `items` reordered so that any PREFIX samples the whole list evenly.

    Bit-reversal (van der Corput) order: index i of the output is the input index whose
    bit pattern is i reversed. Deterministic -- no RNG -- so searches stay reproducible.

    Used to pick the order in which _enumerate visits first stages. Ascending (a, b) order
    spends the whole work budget in the small-gear corner and never reaches the large-driven
    first stages that deep reductions need; a low-discrepancy order reaches them immediately.
    """
    n = len(items)
    if n < 3:
        return list(items)
    bits = (n - 1).bit_length()      # narrowest width with 2**bits >= n
    width = f'0{bits}b'
    order = []
    for i in range(1 << bits):
        r = int(format(i, width)[::-1], 2)
        if r < n:                    # reversal can overshoot when n is not a power of two
            order.append(items[r])
    return order


def _enumerate(q: TrainQuery, n: int, limit=None, work_budget=None):
    """Enumerate exact `n`-stage trains; return (trains, truncated, dropped).

    `dropped` counts distinct exact trains rejected for having no single-plane-buildable
    arrangement.

    All exact `n`-stage trains over [teeth_min, teeth_max], both directions.
    When q.coaxial is set, the first stage fixes the tooth sum S and every later stage
    must satisfy driving + driven == S (equal center distance at one module).

    Stages are placed in canonical non-decreasing (driving, driven) order, so each stage
    multiset is reached exactly once. Results are collected in a dict keyed by that multiset
    so that re-exploring a subtree (see the budget-fair driver in the next task) cannot
    produce duplicates. `search()` still dedups across stage counts as a backstop.

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
    there is no point exploring further.
    """
    out = {}                             # stage-multiset key -> GearTrain (dedups re-exploration)
    dropped = set()                      # keys of exact trains with no buildable arrangement
    L, H = q.teeth_min, q.teeth_max
    in_lo = q.input_min if q.input_min is not None else L
    in_hi = q.input_max if q.input_max is not None else H
    out_lo = q.output_min if q.output_min is not None else L
    out_hi = q.output_max if q.output_max is not None else H
    target = Fraction(q.target_num, q.target_den)
    # R2 (monotonic): when set, tighten every stage to the target's speed direction.
    # target != 1 is guaranteed by validate() (1:1 targets are rejected).
    step_up = q.monotonic and target > 1     # every stage must be driving > driven
    step_down = q.monotonic and target < 1   # every stage must be driving < driven
    work = [0]                           # stage placements explored; bounded by work_budget
    slice_end = [None]                   # work[0] ceiling for the current first stage, or None

    def over_budget() -> bool:
        """A global safety valve tripped -- the whole enumeration is done."""
        return ((limit is not None and len(out) >= limit) or
                (work_budget is not None and work[0] >= work_budget))

    def stop() -> bool:
        return over_budget() or (slice_end[0] is not None and work[0] >= slice_end[0])

    def candidates(remaining, k, coax_sum, prev):
        """Yield the (a, b) stages placeable at depth k, in canonical ascending order.

        Charges the work counter exactly as the old inline loops did: one unit per `a`
        slice computed, one per `b` scanned.
        """
        pa, pb = prev                    # last placed stage; enforce (a, b) >= (pa, pb)
        lo = Fraction(L, H) ** (k - 1)   # child ratio-range lower bound
        hi = Fraction(H, L) ** (k - 1)   # child ratio-range upper bound
        for a in range(max(L, pa), H + 1):
            work[0] += 1                 # count the per-a slice computation (bounds time)
            # child remaining = remaining * b / a must be in [lo, hi]  =>
            #   b in [ a*lo/remaining , a*hi/remaining ]
            b_lo = max(L, math.ceil(a * lo / remaining))
            b_hi = min(H, math.floor(a * hi / remaining))
            if a == pa:                  # non-decreasing order: same driving -> driven >= pb
                b_lo = max(b_lo, pb)
            if step_up:
                b_hi = min(b_hi, a - 1)   # R2: driven < driving (step-up stage)
            elif step_down:
                b_lo = max(b_lo, a + 1)   # R2: driven > driving (step-down stage)
            if coax_sum is not None:
                # Coaxial stage after the first: b is forced to coax_sum - a. Test the
                # single candidate instead of scanning (and rejecting) the whole slice.
                b = coax_sum - a
                if b_lo <= b <= b_hi and b != a:   # skip 1:1 (pass-through) stages
                    yield a, b
            else:
                for b in range(b_lo, b_hi + 1):
                    work[0] += 1
                    if b != a:                     # skip 1:1 (pass-through) stages
                        yield a, b

    def leaf(stages):
        """Gate a completed exact train and file it under its stage-multiset key."""
        if not q.monotonic and not _is_irreducible(stages):
            return                        # reducible -> drop, do not count
        key = _stage_key(stages)
        # Always-on single-plane buildability: keep the train only if some ordering
        # satisfies the end-gear bounds AND the clearance rule; store it in that order
        # (input -> output). in_lo..out_hi default to the full range when no end bounds
        # are set, so this also picks a buildable display order.
        arranged = _arrange_buildable(stages, in_lo, in_hi, out_lo, out_hi, q.clearance)
        if arranged is not None:
            out.setdefault(key, GearTrain(arranged))
        else:
            dropped.add(key)              # exact but not single-plane buildable

    def recurse(remaining: Fraction, k: int, stages: tuple, coax_sum, prev):
        if stop():
            return
        if k == 0:
            if remaining == 1:
                leaf(stages)
            return
        for a, b in candidates(remaining, k, coax_sum, prev):
            # The first stage of a coaxial search fixes the shared sum S; once fixed it is
            # threaded down untouched (candidates() only forces b when coax_sum is set).
            next_sum = coax_sum if coax_sum is not None else (a + b if q.coaxial else None)
            recurse(remaining * Fraction(b, a), k - 1,
                    stages + (Stage(a, b),), next_sum, (a, b))
            if stop():
                return

    if q.coaxial or n == 1:
        # Nothing to spread. The coaxial rule collapses every stage AFTER the first to a single
        # candidate (b = S - a), so no first stage can own a disproportionately expensive
        # subtree -- there is no starvation to fix. A 1-stage train has no subtree at all.
        recurse(target, n, (), None, (0, 0))
        cut_short = False
    else:
        # Budget-fair exploration (iterative broadening). Visit first stages in a
        # low-discrepancy order so a short run still reaches the large-gear region, and cap
        # each one's subtree; then double the allowance and revisit the ones that were cut
        # off. Re-exploring repeats work, but `out`/`dropped` are keyed so it cannot
        # duplicate results, and the doubling keeps the total near 2x the LAST allowance used
        # (up to ~4x a subtree's true cost, when that cost sits just past a doubling step).
        # When the space is small every first stage completes on some pass, `pending` empties,
        # and the result set is exactly what an unbounded plain DFS would produce.
        # Listing the first stages is itself work, and on a very wide range it alone can cost
        # more than the whole budget (measured ~4M units for teeth 1-2000). Cap it at half, so
        # exploring the stages we did find always keeps a share -- otherwise the listing spends
        # everything and the loop below never runs, returning nothing.
        if work_budget is not None:
            slice_end[0] = work[0] + work_budget // 2
        pending = []
        for cand in candidates(target, n, None, (0, 0)):
            pending.append(cand)
            if stop():
                break
        slice_end[0] = None
        pending = _spread(pending)
        allowance = FIRST_STAGE_SLICE
        while pending and not over_budget():
            retry = []
            for a, b in pending:
                if over_budget():
                    retry.append((a, b))       # never explored this pass -> still unfinished
                    continue
                slice_end[0] = work[0] + allowance
                recurse(target * Fraction(b, a), n - 1, (Stage(a, b),), None, (a, b))
                if work[0] >= slice_end[0]:
                    retry.append((a, b))       # hit its ceiling -> more of this subtree remains
            slice_end[0] = None
            pending = retry
            allowance *= 2
        cut_short = bool(pending)

    return list(out.values()), over_budget() or cut_short, len(dropped)


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
    return _stage_key(train.stages)


def _sort_key(train: GearTrain) -> tuple:
    return (len(train.stages), train.total_teeth(), _canonical(train))


def _collect(q: TrainQuery, seen: dict, cap: int):
    """Run the stage-count loop for `q`, filing trains into `seen` by canonical key.

    Returns (truncated, dropped_total). Stops climbing once `seen` holds `cap` trains:
    results sort by (num_stages, ...), so every higher-stage-count train sorts strictly
    after these and can never enter the top MAX_RESULTS. More solutions may exist at higher
    stage counts, so that early stop flags truncation.
    """
    truncated = False
    dropped_total = 0
    for n in range(q.min_stages, q.max_stages + 1):
        if q.direction == 'same' and n % 2 != 0:
            continue
        if q.direction == 'opposite' and n % 2 == 0:
            continue
        level, level_truncated, level_dropped = _enumerate(q, n, limit=GENERATE_LIMIT,
                                                           work_budget=_work_budget(q))
        dropped_total += level_dropped
        if level_truncated:
            truncated = True          # a safety valve tripped -> this level was cut short
        for train in level:
            seen.setdefault(_canonical(train), train)
        if len(seen) >= cap:
            truncated = True
            break
    return truncated, dropped_total


def search(q: TrainQuery) -> SearchResult:
    """Validate -> normalize -> generate across the stage-count range -> dedup -> order
    -> cap. Fewest stages first, then most compact (smallest total tooth count)."""
    errors = validate(q)
    if errors:
        return SearchResult(trains=[], truncated=False, warnings=(), error='; '.join(errors))

    q, warnings = normalize(q)
    seen = {}
    truncated, dropped_total = _collect(q, seen, MAX_RESULTS)

    if not q.coaxial and len(seen) < MAX_RESULTS:
        # Coaxial-merge. Every coaxial train is single-plane buildable, so the general
        # (buildable) result set must contain the coaxial one -- but the coaxial rule
        # collapses branching (b = S - a is a single candidate), letting it reach deep trains
        # the general DFS cannot afford within the work budget. Run it and merge, which makes
        # buildable >= coaxial hold soundly without an infeasible full enumeration.
        # Only when the general pass came up short: a full pool would outrank these on
        # compactness anyway, and the extra pass is not free (measured ~6s on wide queries).
        coax_seen = {}
        cq, _ = normalize(replace(q, coaxial=True))    # bumps min_stages to >= 2
        coax_truncated, coax_dropped = _collect(cq, coax_seen, MAX_RESULTS)
        dropped_total += coax_dropped
        if coax_truncated:
            truncated = True
        for key, train in coax_seen.items():
            seen.setdefault(key, train)

    trains = sorted(seen.values(), key=_sort_key)
    if len(trains) > MAX_RESULTS:
        truncated = True
        trains = trains[:MAX_RESULTS]
    if not trains and dropped_total:
        warnings.append(BUILDABILITY_EMPTY_WARNING)
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
