"""Pure-Python compound gear-train search for exact clock ratios.

No `adsk`, no numpy. Works in tooth counts and exact `fractions.Fraction` ratios.
A *stage* is one external mesh of a driving gear and a driven gear; either may have
more teeth (both speed directions allowed). A train's overall ratio is the product of
its stage ratios. See docs/superpowers/specs/2026-06-28-gear-train-calculator-design.md.
"""
from __future__ import annotations

from itertools import combinations, permutations
from dataclasses import dataclass, field, replace
from fractions import Fraction
from math import gcd

INF = float('inf')         # "no limit" sentinel for the search's work/result thresholds,
                           #   so the hot-path checks stay bare integer comparisons

MAX_RESULTS = 200          # hard cap on returned trains; truncation is reported, never silent
MIN_TEETH = 6              # hard floor: a cycloidal pinion below this cannot be cut or printed,
                           #   and the generator command refuses to build one either
MAX_TEETH = 150            # hard ceiling: the search space grows ~quadratically with the tooth
                           #   span. A worst-case search at this span took ~13s when the limit
                           #   was set; the integer-arithmetic DFS (see candidates()) brought
                           #   that to ~0.6s, and WORK_BUDGET then spent part of that headroom
                           #   on coverage instead (worst case now ~4.5s). The ceiling is left
                           #   where it is deliberately, as an untested-above limit
GENERATE_LIMIT = 20000     # safety valve: max trains materialized per stage level (see
                           #   _generate). Measured inert at the current WORK_BUDGET -- the
                           #   fattest level materializes ~1900 trains -- so it is a pure memory
                           #   backstop, NOT a tuning knob for how much gets explored
WORK_BUDGET = 4_800_000    # safety valve: max stage placements explored per level (~1.4s at
                           #   REFERENCE_SPAN, measured ~3.5M placements/s; loose targets forced
                           #   to high stage counts return partial, truncation-flagged results
                           #   rather than hanging -- narrow ranges). Raised 8x from 600_000 once
                           #   the integer DFS made placements ~21x cheaper: the old value was
                           #   chosen against a ~13s worst case, and 8x spends part of that
                           #   headroom on COVERAGE while keeping the worst case ~4.5s. Measured
                           #   over an 8-query benchmark, distinct first stages on the queries
                           #   that used to come back under MAX_RESULTS went 42 -> 157.
                           #   ⚠️ Raising this changes WHICH trains are found (see
                           #   FIRST_STAGE_SLICE) -- it is a design change, not a tuning nit.

REFERENCE_SPAN = 80           # tooth-range span WORK_BUDGET was tuned against (e.g. teeth 8-90)
MAX_WORK_BUDGET = 24_000_000  # ceiling on the scaled budget, so the palette stays responsive.
                              #   Raised with WORK_BUDGET to keep the span scaling proportional.
                              #   NOTE it does not currently bind: the widest legal query (span
                              #   145, teeth 6-150) scales to ~15.8M, under this cap. It is a
                              #   guard in case MAX_TEETH is ever raised, not an active valve --
                              #   the real worst case is set by WORK_BUDGET x the span scale.

FIRST_STAGE_SLICE = 4000   # budget-fair exploration: starting per-first-stage work allowance.
                           #   Each distinct first stage gets this many placements, then the
                           #   allowance doubles and the cut-short ones are revisited, until the
                           #   space is exhausted or the work budget is spent. Stops one
                           #   small-gear prefix from draining the whole budget (see _enumerate).
                           #   LOAD-BEARING and non-monotonic: a LARGER slice reaches FEWER
                           #   first stages before the budget runs out, which reproduces the very
                           #   starvation this fixes. Its optimum tracks WORK_BUDGET -- it was
                           #   2000 at the 600_000 budget, and a joint sweep at 4_800_000 put the
                           #   peak here (distinct first stages on the sparse benchmark queries:
                           #   146 at 2000, 157 at 4000, 112 at 12000, 92 at 40000). Retuning
                           #   either constant must be validated by sweeping BOTH, not just by
                           #   running the suite.

MAX_PER_FIRST_STAGE = 5    # display-only: at most this many results share one input-stage gear
                           #   pair before the rest are demoted to the tail (see _diverse)


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


def _searchable_stage_counts(q: TrainQuery) -> list:
    """The stage counts search() will actually try: the requested range, raised to 2 when
    coaxial (as normalize() does), then filtered by rotation parity -- every external mesh
    reverses rotation, so 'same' admits only even counts and 'opposite' only odd ones.
    """
    lo = max(q.min_stages, 2 if q.coaxial else 1)
    return [n for n in range(lo, q.max_stages + 1)
            if not (q.direction == 'same' and n % 2)
            and not (q.direction == 'opposite' and n % 2 == 0)]


def validate(q: TrainQuery) -> list:
    """Return a list of hard-error strings (empty == valid). The coaxial min-stage bump is
    a WARNING handled in normalize(), not an error here."""
    errors = []
    if q.target_num <= 0 or q.target_den <= 0:
        errors.append('Target ratio P and Q must both be positive integers.')
    elif q.target_num == q.target_den:
        errors.append('Target ratio must not be 1:1 — a pass-through train serves '
                      'no purpose. Add a 1:1 idler manually if you only need to '
                      'reverse direction.')
    if q.teeth_min < MIN_TEETH:
        errors.append(f'Minimum tooth count must be at least {MIN_TEETH}: a cycloidal pinion '
                      f'below that cannot be cut or printed.')
    if q.teeth_max > MAX_TEETH:
        errors.append(f'Maximum tooth count must be at most {MAX_TEETH}: the search space '
                      f'grows faster than it can be explored beyond that.')
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

    # Reachability. One stage changes speed by at most teeth_max/teeth_min, so n stages reach
    # at most that to the n-th power. A target outside that window has NO exact train however
    # long we search -- reject it with the stage count it would need, instead of running a slow
    # search and handing back a bare empty list. Guarded on `not errors` because it needs the
    # ratio and range checks above to have passed before its arithmetic means anything.
    if not errors:
        counts = _searchable_stage_counts(q)
        if not counts:
            errors.append(
                f'No stage count between {q.min_stages} and {q.max_stages} can turn the output '
                f'the {q.direction} way as the input: every mesh reverses rotation, so "same" '
                f'needs an even number of stages and "opposite" an odd number.')
        else:
            span = Fraction(q.teeth_max, q.teeth_min)   # most one stage can change speed
            target = Fraction(q.target_num, q.target_den)
            reach = max(target, 1 / target)             # how far from 1:1 the train must travel
            n = max(counts)
            if span ** n < reach:
                if span == 1:
                    errors.append(
                        f'With a single tooth count ({q.teeth_min}) every stage would be 1:1, '
                        f'so no other ratio is reachable. Widen the tooth range.')
                else:
                    needed = n + 1
                    while (span ** needed < reach
                           or (q.direction == 'same' and needed % 2)
                           or (q.direction == 'opposite' and needed % 2 == 0)):
                        needed += 1
                    errors.append(
                        f'A {float(reach):g}x speed change is not reachable in {n} '
                        f'stage{"s" if n > 1 else ""} with teeth {q.teeth_min}-{q.teeth_max}: '
                        f'each stage can change speed by at most {float(span):g}x. '
                        f'It needs at least {needed} stages.')
    return errors


def normalize(q: TrainQuery):
    """Return (adjusted_query, warnings). Coaxial forces >= 2 stages. These are advisories,
    never errors -- tooth counts are hard-limited in validate()."""
    warnings = []
    min_stages = q.min_stages
    if q.coaxial and min_stages < 2:
        min_stages = 2
        warnings.append('Coaxial input/output requires at least 2 stages; '
                        'raised the minimum stage count to 2.')
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

    Recursion: `remaining` is the product the not-yet-placed stages must still equal, carried
    as a normalized (numerator, denominator) pair of plain ints -- `rn`, `rd` -- NOT a
    Fraction. The DFS only ever multiplies it by b/a, tests it against 1, and feeds its two
    halves into an integer bound formula, so a rational object buys nothing here and costs an
    allocation plus operator dispatch on every one of millions of steps (see candidates()).
    Fraction is kept where the call counts are tiny and exactness has to be self-evident:
    Stage.ratio(), _is_irreducible(), and the target/reporting arithmetic.

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
    tn, td = target.numerator, target.denominator   # the DFS threads the pair, not the object
    # R2 (monotonic): when set, tighten every stage to the target's speed direction.
    # target != 1 is guaranteed by validate() (1:1 targets are rejected).
    step_up = q.monotonic and target > 1     # every stage must be driving > driven
    step_down = q.monotonic and target < 1   # every stage must be driving < driven
    # Powers of the tooth bounds, for the ratio-range prune in candidates(): the child ratio
    # bounds are (L/H)**(k-1) and (H/L)**(k-1), i.e. pow_L[k-1]/pow_H[k-1] and its reciprocal.
    # Kept as separate integers rather than Fractions -- see candidates().
    pow_L = [L ** i for i in range(n)]
    pow_H = [H ** i for i in range(n)]

    # The two safety valves, with "no limit" folded into an infinite threshold so the hot
    # checks below are bare comparisons instead of `is not None` tests.
    cap = limit if limit is not None else INF                 # trains materialized (memory)
    budget = work_budget if work_budget is not None else INF  # stage placements (time)
    work = 0            # stage placements explored; bounded by `budget`
    slice_end = INF     # work ceiling for the current first stage (INF = no slice in force)
    ceiling = budget    # == min(budget, slice_end); what stop() compares against

    def set_slice(end):
        """Set the current first-stage work ceiling, keeping stop()'s threshold in step.
        `end` is INF to lift the slice. Kept as one function so the two can never desync."""
        nonlocal slice_end, ceiling
        slice_end = end
        ceiling = budget if end > budget else end

    def over_budget() -> bool:
        """A global safety valve tripped -- the whole enumeration is done."""
        return len(out) >= cap or work >= budget

    def stop() -> bool:
        """over_budget(), or the current first stage has spent its slice."""
        return len(out) >= cap or work >= ceiling

    def candidates(rn, rd, k, coax_sum, prev):
        """Yield the (a, b) stages placeable at depth k, in canonical ascending order.

        Charges the work counter exactly as the old inline loops did: one unit per `a`
        slice computed, one per `b` scanned.

        The bounds are computed in plain integers, not Fractions. This loop runs millions of
        times per search and was ~85% of the engine's whole runtime as Fraction arithmetic
        (four Fraction ops per `a`, each allocating an object and running gcd normalization).
        The values are identical: child remaining = remaining * b / a must lie in [lo, hi]
        with lo = (L/H)**(k-1) and hi = (H/L)**(k-1), so
            b in [ a*lo/remaining , a*hi/remaining ]
        and with remaining = rn/rd that lower bound is a * (pow_L[k-1]*rd) / (pow_H[k-1]*rn).
        Both products are loop-invariant, leaving two int multiplies and two floor-divides
        per `a`. Nothing needs reducing to lowest terms: floor and ceil of a rational do not
        depend on its representation.
        """
        nonlocal work
        pa, pb = prev                    # last placed stage; enforce (a, b) >= (pa, pb)
        e = k - 1
        lo_num, lo_den = pow_L[e] * rd, pow_H[e] * rn    # b_lo = ceil(a * lo_num / lo_den)
        hi_num, hi_den = pow_H[e] * rd, pow_L[e] * rn    # b_hi = floor(a * hi_num / hi_den)
        for a in range(max(L, pa), H + 1):
            work += 1                    # count the per-a slice computation (bounds time)
            b_lo = -((-a * lo_num) // lo_den)   # ceil(p/q) for positive p, q
            if b_lo < L:
                b_lo = L
            b_hi = (a * hi_num) // hi_den
            if b_hi > H:
                b_hi = H
            if a == pa and b_lo < pb:    # non-decreasing order: same driving -> driven >= pb
                b_lo = pb
            if step_up:
                if b_hi > a - 1:
                    b_hi = a - 1          # R2: driven < driving (step-up stage)
            elif step_down:
                if b_lo < a + 1:
                    b_lo = a + 1          # R2: driven > driving (step-down stage)
            if coax_sum is not None:
                # Coaxial stage after the first: b is forced to coax_sum - a. Test the
                # single candidate instead of scanning (and rejecting) the whole slice.
                b = coax_sum - a
                if b_lo <= b <= b_hi and b != a:   # skip 1:1 (pass-through) stages
                    yield a, b
            elif b_lo <= b_hi:
                # The guard is only a speed-up: the prune leaves most `a` with an empty
                # slice, and skipping those avoids building a range + iterator per `a`.
                for b in range(b_lo, b_hi + 1):
                    work += 1
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

    def recurse(rn: int, rd: int, k: int, stages: tuple, coax_sum, prev):
        """`rn`/`rd` is the still-unplaced ratio, normalized (see _enumerate's docstring)."""
        if stop():
            return
        if k == 0:
            if rn == rd:                  # remaining == 1: the train is exact
                leaf(stages)
            return
        for a, b in candidates(rn, rd, k, coax_sum, prev):
            # The first stage of a coaxial search fixes the shared sum S; once fixed it is
            # threaded down untouched (candidates() only forces b when coax_sum is set).
            next_sum = coax_sum if coax_sum is not None else (a + b if q.coaxial else None)
            cn, cd = rn * b, rd * a       # child remaining = remaining * b / a...
            g = gcd(cn, cd)               # ...renormalized, to keep the ints small
            recurse(cn // g, cd // g, k - 1,
                    stages + (Stage(a, b),), next_sum, (a, b))
            if stop():
                return

    if q.coaxial or n == 1:
        # Nothing to spread. The coaxial rule collapses every stage AFTER the first to a single
        # candidate (b = S - a), so no first stage can own a disproportionately expensive
        # subtree -- there is no starvation to fix. A 1-stage train has no subtree at all.
        recurse(tn, td, n, (), None, (0, 0))
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
            set_slice(work + work_budget // 2)
        pending = []
        for cand in candidates(tn, td, n, None, (0, 0)):
            pending.append(cand)
            if stop():
                break
        set_slice(INF)
        pending = _spread(pending)
        allowance = FIRST_STAGE_SLICE
        while pending and not over_budget():
            retry = []
            for a, b in pending:
                if over_budget():
                    retry.append((a, b))       # never explored this pass -> still unfinished
                    continue
                set_slice(work + allowance)
                cn, cd = tn * b, td * a
                g = gcd(cn, cd)
                recurse(cn // g, cd // g, n - 1, (Stage(a, b),), None, (a, b))
                if work >= slice_end:
                    retry.append((a, b))       # hit its ceiling -> more of this subtree remains
            set_slice(INF)
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
    stage counts, so that early stop flags truncation. Conversely truncated=False means the
    whole stage range was enumerated exhaustively.

    `dropped_total` is only ever used as a boolean ("did buildability empty the results?").
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


def _diverse(trains: list, per_first: int, cap: int) -> list:
    """Reorder `trains` so at most `per_first` share one displayed first stage at the head,
    then truncate to `cap`. Display-only -- never called from _enumerate, so the enumerated
    pool the completeness tests compare against is untouched.

    Over-quota trains are DEMOTED to the tail, not dropped: below `cap` every train is still
    returned (just reordered), and at `cap` the tail is backfilled with the most compact
    leftovers rather than leaving slots empty. `trains` must already be sorted by _sort_key,
    so the head is the most compact train of each distinct first stage.

    The key is the DISPLAYED first stage -- each train is stored in buildable input->output
    order, so stages[0] is the input arbor's mesh, which is what visibly repeats.
    """
    kept, overflow, counts = [], [], {}
    for train in trains:
        key = (train.stages[0].driving, train.stages[0].driven)
        if counts.get(key, 0) < per_first:
            counts[key] = counts.get(key, 0) + 1
            kept.append(train)
        else:
            overflow.append(train)
    return (kept + overflow)[:cap]


def search(q: TrainQuery) -> SearchResult:
    """Validate -> normalize -> search the stage-count range -> dedup -> order
    fewest-stages-then-most-compact -> spread the head across distinct first stages ->
    cap at MAX_RESULTS.

    A general (non-coaxial) search does NOT top itself up with coaxial trains. It used to:
    when the work budget was 600_000 the general DFS could be starved to the point of
    returning nothing at all on a deep reduction, and re-running the search with the coaxial
    rule -- which collapses each stage after the first to a single candidate -- was a cheap way
    to salvage some results. That was a crutch for a starved search, and the 8x budget (itself
    affordable only because the DFS runs on ints now) removed the starvation it worked around:
    the same queries return pools of 50-1900 trains. Coaxial trains are a deliberately
    requestable SUBSET, which is what the coaxial option is for -- so a general search that
    does not happen to surface one is correct, not a gap. Dropping the top-up also halves the
    worst-case search time, since it re-ran the whole stage-count loop a second time.
    """
    errors = validate(q)
    if errors:
        return SearchResult(trains=[], truncated=False, warnings=(), error='; '.join(errors))

    q, warnings = normalize(q)
    seen = {}
    truncated, dropped_total = _collect(q, seen, MAX_RESULTS)

    trains = sorted(seen.values(), key=_sort_key)
    if len(trains) > MAX_RESULTS:
        # The POOL overflowed. _diverse only ever reorders and then slices to this same
        # MAX_RESULTS, so it cannot drop a train without this flag already being set -- keep
        # the two uses of MAX_RESULTS below in step with this check.
        truncated = True
    trains = _diverse(trains, MAX_PER_FIRST_STAGE, MAX_RESULTS)
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
