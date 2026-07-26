from fractions import Fraction

from core import gear_train as gt


def test_stage_ratio_and_tooth_sum():
    s = gt.Stage(driving=48, driven=12)
    assert s.ratio() == Fraction(4, 1)
    assert s.tooth_sum() == 60


def test_stage_can_be_a_reduction():
    # driving < driven -> ratio below 1 (a step-down). Both directions are legal.
    s = gt.Stage(driving=72, driven=90)
    assert s.ratio() == Fraction(4, 5)
    assert s.tooth_sum() == 162


def test_is_irreducible_lone_stage_is_irreducible():
    # A single stage has no proper non-empty subset -> trivially irreducible.
    assert gt._is_irreducible((gt.Stage(90, 6),)) is True


def test_is_irreducible_tooth_identical_reciprocal_pair_is_reducible():
    # A reciprocal pair (8,32)+(32,8) = 1/4 * 4 = 1 as a PROPER subset of a 3-stage train
    # (third stage (24,6)=4 keeps the full product 4 != 1) -> the pair cancels -> reducible.
    stages = (gt.Stage(8, 32), gt.Stage(32, 8), gt.Stage(24, 6))
    assert gt._is_irreducible(stages) is False


def test_is_irreducible_value_equivalent_reciprocal_pair_is_reducible():
    # Value-equivalent reciprocals (8,16)+(20,10) = 1/2 * 2 = 1 as a proper subset of a
    # 3-stage train (third stage (24,6)=4) -> different teeth, same cancellation -> reducible.
    stages = (gt.Stage(8, 16), gt.Stage(20, 10), gt.Stage(24, 6))
    assert gt._is_irreducible(stages) is False


def test_is_irreducible_trimming_pair_is_irreducible():
    # (90,6) * (72,90) = 15 * 4/5 = 12. Proper subsets {15}, {4/5}; neither is 1 -> keep.
    stages = (gt.Stage(90, 6), gt.Stage(72, 90))
    assert gt._is_irreducible(stages) is True


def test_is_irreducible_three_stage_cancelling_subset_is_reducible():
    # A 4-stage train whose first THREE stages form a proper subset with product 1:
    # (12,6) * (6,18) * (18,12) = 2 * 1/3 * 3/2 = 1. The 4th stage keeps it a proper subset.
    stages = (gt.Stage(12, 6), gt.Stage(6, 18), gt.Stage(18, 12), gt.Stage(24, 12))
    assert gt._is_irreducible(stages) is False


def test_clearance_ok_single_stage_is_vacuously_true():
    assert gt._clearance_ok((gt.Stage(12, 60),), 2) is True


def test_clearance_ok_rejects_overreaching_wheel():
    # driven 60 (pitch radius 30) next to a stage of tooth-sum 48 (center distance 24):
    # 48 - 60 = -12 < g=2 -> the 60t wheel swallows the next arbor's shaft.
    order = (gt.Stage(13, 60), gt.Stage(12, 36))
    assert gt._clearance_ok(order, 2) is False


def test_clearance_ok_accepts_when_neighbour_is_large_enough():
    # driven 48 next to sum 73 (13+60): 73-48=25>=2 ; driving 13 vs sum 60 (12+48): 60-13=47
    order = (gt.Stage(12, 48), gt.Stage(13, 60))
    assert gt._clearance_ok(order, 2) is True


def test_clearance_ok_tangent_passes_at_zero_fails_positive():
    # driven 40 vs neighbour tooth-sum 40 -> gap exactly 0.
    order = (gt.Stage(8, 40), gt.Stage(8, 32))
    assert gt._clearance_ok(order, 0) is True
    assert gt._clearance_ok(order, 1) is False


def test_geartrain_ratio_is_product():
    train = gt.GearTrain(stages=(gt.Stage(36, 6), gt.Stage(40, 20)))
    assert train.ratio() == Fraction(12, 1)   # 6 * 2


def test_geartrain_mixed_direction_ratio():
    train = gt.GearTrain(stages=(gt.Stage(90, 6), gt.Stage(72, 90)))
    assert train.ratio() == Fraction(12, 1)   # 15 * 4/5


def test_geartrain_counts_and_direction():
    train = gt.GearTrain(stages=(gt.Stage(36, 6), gt.Stage(40, 20)))
    assert train.num_gears() == 4             # two gears per stage
    assert train.total_teeth() == 36 + 6 + 40 + 20
    assert train.direction() == 1             # even stage count -> same sense
    assert gt.GearTrain(stages=(gt.Stage(36, 6),)).direction() == -1


def _valid_query(**over):
    base = dict(target_num=12, target_den=1, min_stages=1, max_stages=2,
                teeth_min=6, teeth_max=90, direction='any', coaxial=False)
    base.update(over)
    return gt.TrainQuery(**base)


def test_valid_query_has_no_errors():
    assert gt.validate(_valid_query()) == []


def test_validate_rejects_nonpositive_ratio():
    errs = gt.validate(_valid_query(target_num=0))
    assert errs and any('positive' in e for e in errs)


def test_validate_allows_reduction_target():
    # P < Q is now legal (net reduction) -- no error.
    assert gt.validate(_valid_query(target_num=1, target_den=12)) == []


def test_validate_rejects_one_to_one_target():
    errors = gt.validate(_valid_query(target_num=5, target_den=5))
    assert errors, 'a 1:1 target must be rejected'
    assert any('1:1' in e for e in errors)


def test_search_reports_error_for_one_to_one_target():
    res = gt.search(_valid_query(target_num=1, target_den=1))
    assert res.error is not None
    assert not res.trains


def test_validate_rejects_bad_ranges_and_direction():
    assert gt.validate(_valid_query(teeth_max=5)) != []          # teeth_max < teeth_min
    assert gt.validate(_valid_query(max_stages=0)) != []         # max_stages < min_stages
    assert gt.validate(_valid_query(min_stages=0)) != []         # min_stages < 1
    assert gt.validate(_valid_query(direction='sideways')) != []


def test_normalize_raises_min_stages_for_coaxial():
    q, warnings = gt.normalize(_valid_query(min_stages=1, coaxial=True))
    assert q.min_stages == 2
    assert any('2 stages' in w or 'coaxial' in w.lower() for w in warnings)


def test_normalize_leaves_noncoaxial_alone():
    q, warnings = gt.normalize(_valid_query(min_stages=1, coaxial=False))
    assert q.min_stages == 1
    assert warnings == []


def test_validate_rejects_too_few_teeth():
    # Below MIN_TEETH a cycloidal pinion cannot be made; this used to be a mere warning.
    errs = gt.validate(_valid_query(teeth_min=4))
    assert any('tooth' in e.lower() for e in errs)
    assert gt.validate(_valid_query(teeth_min=1)) != []      # a 1-tooth gear is not a gear


def _ratios(trains):
    return {t.ratio() for t in trains}


def _stage_multisets(trains):
    return {tuple(sorted((s.driving, s.driven) for s in t.stages)) for t in trains}


def test_generate_single_stage_exact():
    # 4 : 1 in one stage over teeth 6..48 -> any (a, b) with a/b == 4, e.g. (24,6),(48,12)
    q = _valid_query(target_num=4, target_den=1, teeth_min=6, teeth_max=48)
    trains = gt._generate(q, 1)
    assert trains, 'expected at least one single-stage solution'
    assert _ratios(trains) == {Fraction(4, 1)}
    # _stage_multisets wraps each train's stages in a tuple, so a single-stage train's
    # key is a 1-tuple of the (driving, driven) pair.
    assert ((24, 6),) in _stage_multisets(trains)
    assert ((48, 12),) in _stage_multisets(trains)


def test_generate_two_stage_finds_known_trains():
    q = _valid_query(target_num=12, target_den=1, teeth_min=6, teeth_max=90)
    ms = _stage_multisets(gt._generate(q, 2))
    assert tuple(sorted([(36, 6), (40, 20)])) in ms      # 6 * 2
    assert tuple(sorted([(48, 8), (30, 15)])) in ms      # 6 * 2


def test_generate_finds_mixed_direction_train():
    # (90/6) * (72/90) = 15 * 4/5 = 12 : the second stage is a reduction (driving<driven).
    q = _valid_query(target_num=12, target_den=1, teeth_min=6, teeth_max=90)
    ms = _stage_multisets(gt._generate(q, 2))
    assert tuple(sorted([(90, 6), (72, 90)])) in ms


def test_generate_every_train_is_exact():
    q = _valid_query(target_num=12, target_den=1, teeth_min=6, teeth_max=60)
    for t in gt._generate(q, 2):
        assert t.ratio() == Fraction(12, 1)


def test_generate_net_reduction_target():
    # 1 : 4 over one stage -> driving < driven, e.g. (6, 24).
    q = _valid_query(target_num=1, target_den=4, teeth_min=6, teeth_max=48)
    trains = gt._generate(q, 1)
    assert _ratios(trains) == {Fraction(1, 4)}
    assert ((6, 24),) in _stage_multisets(trains)


def test_search_returns_sorted_deduped_results():
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=60)
    res = gt.search(q)
    assert res.error is None
    assert res.trains, 'expected solutions'
    # exactness
    assert all(t.ratio() == Fraction(12, 1) for t in res.trains)
    # dedup: no two trains share the same direction-aware stage multiset
    keys = [tuple(sorted((s.driving, s.driven) for s in t.stages)) for t in res.trains]
    assert len(keys) == len(set(keys))
    # ordering: (num_stages, total_teeth) non-decreasing
    order = [(len(t.stages), t.total_teeth()) for t in res.trains]
    assert order == sorted(order)


def test_search_direction_aware_dedup_keeps_reverse_stage():
    # Dedup keys on (driving, driven) ORDER, so a stage and its reverse are distinct
    # (reciprocal ratios) and must never be merged -- e.g. a step-up (90/6) vs the
    # reduction (6/90). Tested directly on _canonical (deterministic, cap-independent);
    # that a mixed-direction train is actually produced is covered by
    # test_generate_finds_mixed_direction_train.
    up = gt.GearTrain(stages=(gt.Stage(90, 6),))
    down = gt.GearTrain(stages=(gt.Stage(6, 90),))
    assert gt._canonical(up) != gt._canonical(down)


def test_search_reports_error_for_invalid_query():
    res = gt.search(_valid_query(target_num=0))
    assert res.error is not None
    assert res.trains == []


def test_search_truncates_and_flags():
    # A search that overflows the cap must set truncated and clip to MAX_RESULTS.
    # A 2-stage search for 12:1 over teeth 6..90 yields thousands of exact trains
    # (far past 200) while staying fast -- loose 3-stage searches are avoided here
    # because they blow up combinatorially.
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=90)
    res = gt.search(q)
    assert res.truncated is True
    assert len(res.trains) == gt.MAX_RESULTS


def test_search_warns_when_buildability_empties_results():
    # A clearance larger than any achievable tooth-sum gap makes every MULTI-stage train
    # unbuildable; exact 2-stage solutions exist, so the result is empty WITH a warning.
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, clearance=1000)
    res = gt.search(q)
    assert res.trains == []
    assert any('buildable' in w.lower() for w in res.warnings)


def test_search_no_buildability_warning_when_no_exact_ratio():
    # No exact train exists at all (nothing is dropped for buildability), so the buildability
    # warning must NOT fire. 7:5 over teeth 6..12 is reachable but has no exact pair in range.
    q = _valid_query(target_num=7, target_den=5, min_stages=1, max_stages=1,
                     teeth_min=6, teeth_max=12)
    res = gt.search(q)
    assert res.trains == []
    assert not any('buildable' in w.lower() for w in res.warnings)


def test_search_empty_when_no_solution():
    # 7:5 over teeth 6..12 in one stage. Reachable in principle (each stage can change speed
    # by up to 12/6 = 2x, and 7/5 = 1.4x), so it passes the reachability check -- but no exact
    # pair exists in range: (7,5) is below the minimum and (14,10) is above the maximum.
    q = _valid_query(target_num=7, target_den=5, min_stages=1, max_stages=1,
                     teeth_min=6, teeth_max=12)
    res = gt.search(q)
    assert res.trains == []
    assert res.error is None


def test_direction_same_keeps_only_even_stage_counts():
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=60, direction='same')
    res = gt.search(q)
    assert res.trains
    assert all(len(t.stages) % 2 == 0 for t in res.trains)
    assert all(t.direction() == 1 for t in res.trains)


def test_direction_opposite_keeps_only_odd_stage_counts():
    # 'opposite' keeps only ODD stage counts. With max_stages=2 the filter skips the
    # even count (n=2) entirely and searches only n=1 (fast, avoids the 3-stage blowup);
    # teeth_max=90 so 12:1 has single-stage solutions (72/6, 84/7). If the parity filter
    # were broken, n=2 would run and inject even-stage trains, failing the all-odd check.
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=90, direction='opposite')
    res = gt.search(q)
    assert res.trains
    assert all(len(t.stages) % 2 == 1 for t in res.trains)
    assert all(t.direction() == -1 for t in res.trains)


def test_coaxial_all_stages_share_tooth_sum():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, coaxial=True)
    res = gt.search(q)
    assert res.trains, 'expected coaxial solutions'
    for t in res.trains:
        sums = {s.tooth_sum() for s in t.stages}
        assert len(sums) == 1, 'every coaxial stage must share one tooth sum'


def test_coaxial_finds_the_canonical_4832_train():
    # (48/12) * (45/15) = 4 * 3 = 12, with 48+12 == 45+15 == 60.
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, coaxial=True)
    res = gt.search(q)
    ms = {tuple(sorted((s.driving, s.driven) for s in t.stages)) for t in res.trains}
    assert tuple(sorted([(48, 12), (45, 15)])) in ms


def test_coaxial_min_stage_one_is_raised_to_two():
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=90, coaxial=True)
    res = gt.search(q)
    assert res.trains
    assert all(len(t.stages) >= 2 for t in res.trains)
    assert any('2 stages' in w or 'coaxial' in w.lower() for w in res.warnings)


def test_coaxial_trains_are_still_exact():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, coaxial=True)
    res = gt.search(q)
    assert all(t.ratio() == Fraction(12, 1) for t in res.trains)


def _has_unity_stage(train):
    return any(s.driving == s.driven for s in train.stages)


def test_no_result_contains_a_unity_stage():
    # 2:1 over 6-24, up to 2 stages: padding stages like (12,12) would otherwise appear.
    q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=24)
    res = gt.search(q)
    assert res.trains, 'expected non-unity solutions to still exist'
    assert not any(_has_unity_stage(t) for t in res.trains)


def test_no_coaxial_result_contains_a_unity_stage():
    # Coaxial 2:1: a shared-sum pair like (12,12)+(16,8) (sum 24) would otherwise appear.
    q = _valid_query(target_num=2, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=24, coaxial=True)
    res = gt.search(q)
    assert res.trains, 'expected non-unity coaxial solutions to still exist'
    assert not any(_has_unity_stage(t) for t in res.trains)


import itertools


def _combo_is_irreducible(combo):
    """Independent (of gt._is_irreducible) reference check: True iff no non-empty proper
    subset of `combo` (a sequence of Stage) has a Fraction ratio-product of 1."""
    n = len(combo)
    ratios = [Fraction(s.driving, s.driven) for s in combo]
    for size in range(1, n):
        for idx in itertools.combinations(range(n), size):
            prod = Fraction(1)
            for i in idx:
                prod *= ratios[i]
            if prod == 1:
                return False
    return True


def _combo_is_monotonic(combo, target):
    """True iff every stage points the target's speed direction (target != 1 guaranteed)."""
    if target > 1:
        return all(s.driving > s.driven for s in combo)
    return all(s.driving < s.driven for s in combo)


def _combo_admits_buildable(combo, in_lo, in_hi, out_lo, out_hi, clearance):
    """Reference (independent of the engine): True iff some ordering of `combo` puts a
    driving gear in the input range first, a different-position driven gear in the output
    range last, AND satisfies the single-plane clearance rule."""
    for order in itertools.permutations(combo):
        if not (in_lo <= order[0].driving <= in_hi):
            continue
        if not (out_lo <= order[-1].driven <= out_hi):
            continue
        if all(order[i].tooth_sum() - order[i - 1].driven >= clearance and
               order[i - 1].tooth_sum() - order[i].driving >= clearance
               for i in range(1, len(order))):
            return True
    return False


def _brute_force_keys(q):
    """Obvious O(range^(2n)) reference: enumerate every stage combination, keep exact
    matches (respecting direction parity + coaxial), return their canonical keys."""
    L, H = q.teeth_min, q.teeth_max
    target = Fraction(q.target_num, q.target_den)
    all_stages = [gt.Stage(a, b)
                  for a in range(L, H + 1) for b in range(L, H + 1)
                  if a != b]                       # 1:1 stages are excluded by the solver
    keys = set()
    qn, _ = gt.normalize(q)
    for n in range(qn.min_stages, qn.max_stages + 1):
        if qn.direction == 'same' and n % 2 != 0:
            continue
        if qn.direction == 'opposite' and n % 2 == 0:
            continue
        for combo in itertools.product(all_stages, repeat=n):
            if qn.coaxial and len({s.tooth_sum() for s in combo}) != 1:
                continue
            prod = Fraction(1)
            for s in combo:
                prod *= s.ratio()
            if prod != target:
                continue
            if qn.monotonic:
                if not _combo_is_monotonic(combo, target):
                    continue
            elif not _combo_is_irreducible(combo):
                continue
            if not _combo_admits_buildable(combo, L, H, L, H, qn.clearance):
                continue
            keys.add(tuple(sorted((s.driving, s.driven) for s in combo)))
    return keys


def _search_keys(q):
    return {tuple(sorted((s.driving, s.driven) for s in t.stages))
            for t in gt.search(q).trains}


def test_search_every_returned_train_is_buildable():
    q = _valid_query(target_num=1, target_den=60, min_stages=1, max_stages=4,
                     teeth_min=8, teeth_max=90)
    res = gt.search(q)
    assert res.trains
    for t in res.trains:
        assert gt._clearance_ok(t.stages, q.clearance)


def test_search_coaxial_trains_stay_valid_under_buildability():
    q = _valid_query(target_num=1, target_den=60, min_stages=2, max_stages=4,
                     teeth_min=8, teeth_max=90, coaxial=True)
    res = gt.search(q)
    assert res.trains, 'coaxial trains are always buildable'
    for t in res.trains:
        assert gt._clearance_ok(t.stages, q.clearance)


def test_search_higher_clearance_is_a_subset():
    # Verified: 2:1 over 6..20 (2 stages) yields 88 buildable trains at clearance 0 and 84 at
    # clearance 4 -- untruncated, a genuine strict subset. (12:1 does NOT work: its trains all
    # have large tooth-sum gaps so clearance 4 removes nothing, and the set also truncates.)
    base = dict(target_num=2, target_den=1, min_stages=2, max_stages=2,
                teeth_min=6, teeth_max=20)
    loose = _search_keys(_valid_query(clearance=0, **base))
    tight = _search_keys(_valid_query(clearance=4, **base))
    assert tight <= loose            # tightening never adds trains
    assert tight != loose            # and it removes at least one near-tangent train


def test_pruned_search_matches_brute_force_small():
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=24)
    assert _search_keys(q) == _brute_force_keys(q)


def test_pruned_search_matches_brute_force_reduction():
    q = _valid_query(target_num=1, target_den=6, min_stages=1, max_stages=2,
                     teeth_min=6, teeth_max=24)
    assert _search_keys(q) == _brute_force_keys(q)


def test_pruned_search_matches_brute_force_coaxial():
    q = _valid_query(target_num=6, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=24, coaxial=True)
    assert _search_keys(q) == _brute_force_keys(q)


def test_direction_filtered_search_excludes_unity_and_matches_reference():
    # The direction parity gate (in search()) and the 1:1-stage prune (in recurse())
    # are independent mechanisms; confirm they compose. Target 2:1 over 6-20 has unity
    # padding available, so the no-unity assertion is meaningful, and both directions
    # stay well under the result cap (no truncation) so the brute-force equivalence holds.
    for direction in ('same', 'opposite'):
        q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=2,
                         teeth_min=6, teeth_max=20, direction=direction)
        res = gt.search(q)
        assert res.trains, f'expected non-empty results for direction={direction}'
        assert not any(_has_unity_stage(t) for t in res.trains)
        assert _search_keys(q) == _brute_force_keys(q)


import json


def test_result_to_dict_shape_is_json_serializable():
    res = gt.search(_valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                                 teeth_min=6, teeth_max=60))
    d = gt.result_to_dict(res)
    # Round-trips through JSON (no Fraction/tuple leaking through).
    d2 = json.loads(json.dumps(d))
    assert set(d2) == {'trains', 'truncated', 'warnings', 'error'}
    assert isinstance(d2['trains'], list) and d2['trains']
    row = d2['trains'][0]
    assert set(row) == {'stages', 'ratio', 'ratio_decimal', 'num_gears',
                        'total_teeth', 'direction', 'coaxial_sum'}
    assert row['stages'][0].keys() >= {'driving', 'driven', 'tooth_sum'}
    assert ' : ' in row['ratio']            # e.g. "12 : 1"
    assert row['direction'] in ('same', 'opposite')


def test_result_to_dict_flags_coaxial_sum():
    res = gt.search(_valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                                 teeth_min=6, teeth_max=90, coaxial=True))
    d = gt.result_to_dict(res)
    assert all(isinstance(r['coaxial_sum'], int) for r in d['trains'])


def test_result_to_dict_carries_error():
    d = gt.result_to_dict(gt.search(_valid_query(target_num=0)))
    assert d['error'] is not None
    assert d['trains'] == []


# --- Task 15: performance redesign of _generate ---------------------------------
import time


def test_generate_produces_each_multiset_once():
    # Canonical (non-decreasing) stage ordering: no more n! reorderings in the raw list.
    q = _valid_query(target_num=12, target_den=1, teeth_min=6, teeth_max=60)
    trains = gt._generate(q, 2)
    keys = [tuple(sorted((s.driving, s.driven) for s in t.stages)) for t in trains]
    assert len(keys) == len(set(keys)), 'each stage multiset must appear exactly once'


def test_search_loose_high_stage_target_terminates_fast():
    # The motivating blowup: 2:1 over teeth 6..60 forced to exactly 3 stages. Must finish
    # quickly (safety valve) instead of running for >100s, and report truncation.
    q = _valid_query(target_num=2, target_den=1, min_stages=3, max_stages=3,
                     teeth_min=6, teeth_max=60)
    t0 = time.perf_counter()
    res = gt.search(q)
    elapsed = time.perf_counter() - t0
    assert elapsed < 20.0, f'search took {elapsed:.1f}s -- safety valve not engaging'
    assert res.error is None
    assert len(res.trains) == gt.MAX_RESULTS
    assert res.truncated is True
    assert all(t.ratio() == Fraction(2, 1) for t in res.trains)


def test_search_palette_default_query_is_fast():
    # The palette's first-use default (target 12:1, stages 1..3, teeth 8..90) must not hang.
    # The cap-aware stage loop fills the cap at n=2 and never reaches the n=3 blowup.
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=8, teeth_max=90)
    t0 = time.perf_counter()
    res = gt.search(q)
    elapsed = time.perf_counter() - t0
    assert elapsed < 20.0, f'default query took {elapsed:.1f}s'
    assert res.error is None
    assert len(res.trains) == gt.MAX_RESULTS
    assert res.truncated is True


def test_validate_accepts_end_gear_bounds_within_range():
    assert gt.validate(_valid_query(input_min=8, input_max=20,
                                    output_min=60, output_max=90)) == []


def test_validate_rejects_end_gear_bound_outside_general_range():
    # general range in _valid_query is 6..90
    assert gt.validate(_valid_query(input_min=8, input_max=120)) != []   # above teeth_max
    assert gt.validate(_valid_query(output_min=1, output_max=30)) != []  # below teeth_min


def test_validate_rejects_half_specified_end_gear_bound():
    assert gt.validate(_valid_query(input_min=8)) != []      # max missing
    assert gt.validate(_valid_query(output_max=30)) != []    # min missing


def test_validate_rejects_inverted_end_gear_bound():
    assert gt.validate(_valid_query(input_min=30, input_max=10)) != []


def test_validate_accepts_end_gear_bounds_at_general_range_boundary():
    # Bounds equal to the general-range endpoints are inclusive (valid).
    assert gt.validate(_valid_query(input_min=6, input_max=90,
                                    output_min=6, output_max=90)) == []


def test_validate_explicit_none_end_bounds_is_clean():
    assert gt.validate(_valid_query(input_min=None, input_max=None,
                                    output_min=None, output_max=None)) == []


def test_arrange_buildable_single_stage_needs_both_ends():
    stages = (gt.Stage(8, 40),)
    assert gt._arrange_buildable(stages, 6, 10, 30, 50, 2) == stages
    assert gt._arrange_buildable(stages, 6, 10, 50, 60, 2) is None


def test_arrange_buildable_orders_input_first_output_last():
    stages = (gt.Stage(8, 24), gt.Stage(30, 72))
    arranged = gt._arrange_buildable(stages, 6, 10, 60, 80, 0)   # input 8, output 72
    assert arranged is not None
    assert arranged[0].driving == 8 and arranged[-1].driven == 72


def test_arrange_buildable_rejects_when_one_stage_serves_both_ends():
    stages = (gt.Stage(8, 40), gt.Stage(30, 20))
    assert gt._arrange_buildable(stages, 6, 10, 38, 42, 0) is None


def test_arrange_buildable_duplicate_qualifying_stages_pass():
    stages = (gt.Stage(8, 40), gt.Stage(8, 40))
    arranged = gt._arrange_buildable(stages, 6, 10, 38, 42, 0)
    assert arranged is not None
    assert arranged[0].driving == 8 and arranged[-1].driven == 40


def test_arrange_buildable_end_cap_blocks_the_only_clearing_order():
    # The user's real train: with output <= 44 the 60t cannot go to the output, and no
    # other stage's tooth-sum exceeds 60 by 2, so NO ordering is buildable.
    stages = (gt.Stage(12, 13), gt.Stage(12, 48), gt.Stage(13, 60), gt.Stage(12, 36))
    assert gt._arrange_buildable(stages, 8, 44, 8, 44, 2) is None
    # Without the end cap, an ordering exists (the 60t sits at the output).
    arranged = gt._arrange_buildable(stages, 8, 90, 8, 90, 2)
    assert arranged is not None
    assert gt._clearance_ok(arranged, 2)


def test_search_input_bound_orders_first_stage_driving():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, input_min=81, input_max=83)
    res = gt.search(q)
    assert res.error is None
    assert res.trains, 'expected trains with an input gear in 81..83'
    for t in res.trains:
        assert 81 <= t.stages[0].driving <= 83     # input arbor within bound AND first


def test_search_output_bound_orders_last_stage_driven():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, output_min=6, output_max=8)
    res = gt.search(q)
    assert res.trains, 'expected trains with an output gear in 6..8'
    for t in res.trains:
        assert 6 <= t.stages[-1].driven <= 8       # output arbor within bound AND last


def test_search_bounds_equal_to_general_range_keys_are_a_noop():
    # Bounds set to the FULL range must not change the result set (by canonical key).
    base = dict(target_num=12, target_den=1, min_stages=1, max_stages=2,
                teeth_min=6, teeth_max=24)
    plain = _search_keys(_valid_query(**base))
    bounded = _search_keys(_valid_query(input_min=6, input_max=24,
                                        output_min=6, output_max=24, **base))
    assert bounded == plain


def test_search_no_bounds_returns_buildable_order():
    # Buildability is always on, so with no end bounds each train is stored in a single-plane
    # buildable order (NOT necessarily canonical). Uses 3 stages so ordering is meaningful.
    q = _valid_query(target_num=12, target_den=1, min_stages=3, max_stages=3,
                     teeth_min=6, teeth_max=40)
    res = gt.search(q)
    assert res.trains, 'expected 3-stage solutions'
    for t in res.trains:
        assert gt._clearance_ok(t.stages, q.clearance), 'stored order must be buildable'


def _brute_force_keys_bounded(q):
    """Reference like _brute_force_keys, but also honours the optional end-gear bounds.

    Uses its OWN arrangement check (_combo_admits_buildable, deliberately NOT
    gear_train._arrange_buildable) so this test verifies the pruned enumeration's
    COMPLETENESS independently of the implementation it is checking. A combo counts iff some
    ordering puts a driving gear in the input range first, a DIFFERENT driven gear in the
    output range last, AND satisfies the single-plane clearance rule.
    """
    L, H = q.teeth_min, q.teeth_max
    in_lo = q.input_min if q.input_min is not None else L
    in_hi = q.input_max if q.input_max is not None else H
    out_lo = q.output_min if q.output_min is not None else L
    out_hi = q.output_max if q.output_max is not None else H
    target = Fraction(q.target_num, q.target_den)
    all_stages = [gt.Stage(a, b) for a in range(L, H + 1) for b in range(L, H + 1)
                  if a != b]                       # 1:1 stages are excluded by the solver

    keys = set()
    qn, _ = gt.normalize(q)
    for n in range(qn.min_stages, qn.max_stages + 1):
        if qn.direction == 'same' and n % 2 != 0:
            continue
        if qn.direction == 'opposite' and n % 2 == 0:
            continue
        for combo in itertools.product(all_stages, repeat=n):
            if qn.coaxial and len({s.tooth_sum() for s in combo}) != 1:
                continue
            prod = Fraction(1)
            for s in combo:
                prod *= s.ratio()
            if prod != target:
                continue
            if qn.monotonic:
                if not _combo_is_monotonic(combo, target):
                    continue
            elif not _combo_is_irreducible(combo):
                continue
            if _combo_admits_buildable(combo, in_lo, in_hi, out_lo, out_hi, qn.clearance):
                keys.add(tuple(sorted((s.driving, s.driven) for s in combo)))
    return keys


def test_pruned_search_matches_brute_force_with_end_bounds():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=28, input_min=18, input_max=24)
    bounded = _search_keys(q)
    assert bounded, 'expected some qualifying trains'
    assert bounded == _brute_force_keys_bounded(q)
    # genuine narrowing: some unbounded trains have every stage's driving > 24
    open_keys = _search_keys(_valid_query(target_num=12, target_den=1, min_stages=2,
                                          max_stages=2, teeth_min=6, teeth_max=28))
    assert bounded < open_keys


def test_pruned_search_matches_brute_force_coaxial_with_end_bounds():
    # Coaxial + an output bound must still match the independent brute-force reference,
    # and must be non-empty (guards against a vacuous empty==empty pass).
    q = _valid_query(target_num=6, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=24, coaxial=True,
                     output_min=6, output_max=12)
    bounded = _search_keys(q)
    assert bounded, 'expected non-empty coaxial+bounds result'
    assert bounded == _brute_force_keys_bounded(q)


def test_trainquery_monotonic_defaults_false():
    q = _valid_query()
    assert q.monotonic is False


def test_trainquery_monotonic_can_be_set_and_is_valid():
    q = _valid_query(monotonic=True)
    assert q.monotonic is True
    assert gt.validate(q) == []          # a plain bool needs no new validation rule


def test_trainquery_clearance_defaults_to_two():
    assert _valid_query().clearance == 2


def test_validate_rejects_negative_clearance():
    errs = gt.validate(_valid_query(clearance=-1))
    assert any('clearance' in e.lower() for e in errs)


def test_validate_accepts_zero_clearance():
    assert gt.validate(_valid_query(clearance=0)) == []


def _train_has_cancelling_subset(train):
    """Independent reducibility check for tests: True iff some non-empty proper subset of
    the train's stages has a Fraction ratio-product of exactly 1."""
    stages = train.stages
    n = len(stages)
    ratios = [Fraction(s.driving, s.driven) for s in stages]
    for size in range(1, n):
        for combo in itertools.combinations(range(n), size):
            prod = Fraction(1)
            for i in combo:
                prod *= ratios[i]
            if prod == 1:
                return True
    return False


def test_search_returns_no_reducible_trains():
    # 2:1 over 6..12 up to 3 stages. The range is deliberately small so the WHOLE result set
    # (44 trains: 1 one-stage, 7 two-stage, 36 three-stage) fits under MAX_RESULTS and is not
    # truncated -- so 3-stage trains actually reach res.trains. (With a WIDE range the 1-2
    # stage trains fill the 200-cap before any 3-stage train is generated, so R1 would never
    # be exercised through search() and this test would be vacuous.) Without R1 there are 61
    # distinct 3-stage 2:1 trains here, 25 of them reducible (padded reciprocal subsets like
    # (12,6)+(7,8)+(8,7)); R1 must drop all 25 while keeping the 36 genuine ones.
    q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=12)
    res = gt.search(q)
    assert res.trains, 'expected irreducible 2:1 solutions to still exist'
    assert not res.truncated, 'range must be small enough that 3-stage trains are not capped out'
    assert any(len(t.stages) == 3 for t in res.trains), \
        'expected 3-stage trains in results so R1 is actually exercised end-to-end'
    assert not any(_train_has_cancelling_subset(t) for t in res.trains)


def test_generate_keeps_trimming_train():
    # The mixed-direction trimming train (90,6)+(72,90) = 15 * 4/5 = 12 is irreducible and
    # must survive R1 (its proper subsets are {15} and {4/5}, neither is 1). Uses _generate
    # (uncapped) not search(): this train's tooth sum (258) is large, so search()'s
    # MAX_RESULTS/total-teeth cap would truncate it out for the wrong reason.
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90)
    ms = _stage_multisets(gt._generate(q, 2))
    assert tuple(sorted([(90, 6), (72, 90)])) in ms


def test_monotonic_stepup_target_all_stages_step_up():
    # Step-up target (2:1). With monotonic on, every stage must have driving > driven.
    q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=24, monotonic=True)
    res = gt.search(q)
    assert res.trains, 'expected monotonic step-up solutions'
    for t in res.trains:
        assert all(s.driving > s.driven for s in t.stages)


def test_monotonic_stepdown_target_all_stages_step_down():
    # Step-down target (1:2). With monotonic on, every stage must have driving < driven.
    q = _valid_query(target_num=1, target_den=2, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=24, monotonic=True)
    res = gt.search(q)
    assert res.trains, 'expected monotonic step-down solutions'
    for t in res.trains:
        assert all(s.driving < s.driven for s in t.stages)


def test_monotonic_off_still_returns_trimming_train():
    # Guards against R2 leaking on: with monotonic OFF (default), the mixed-direction
    # trimming train (90,6)+(72,90) must still appear. Uses _generate (uncapped) so the
    # large-tooth-sum train is not lost to search()'s MAX_RESULTS truncation.
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, monotonic=False)
    ms = _stage_multisets(gt._generate(q, 2))
    assert tuple(sorted([(90, 6), (72, 90)])) in ms


def test_monotonic_on_removes_trimming_train():
    # The trimming train has a step-DOWN stage (72,90); for a step-up target it must be
    # excluded when monotonic is on. _generate (uncapped) proves absence is R2, not the cap.
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, monotonic=True)
    ms = _stage_multisets(gt._generate(q, 2))
    assert tuple(sorted([(90, 6), (72, 90)])) not in ms


def test_monotonic_composes_with_coaxial():
    # Coaxial + monotonic must actually PRUNE (not just pass invariants): for 2:1 coaxial over
    # 6..30 there are 3 trains without monotonic, TWO of them mixed-direction (a step-down
    # stage) -- (10,20)+(24,6) and (16,24)+(30,10) -- vs the all-step-up (20,15)+(21,14).
    # Monotonic must remove the two mixed ones, leaving only the step-up train. This also
    # exercises R2 inside the coaxial single-candidate branch: the tightened b_lo/b_hi must
    # reject the wrong-direction candidate (a regression that moved R2 after the coaxial test
    # would fail here). Non-vacuous by construction (a mixed train demonstrably exists when
    # monotonic is off).
    base = dict(target_num=2, target_den=1, min_stages=2, max_stages=2,
                teeth_min=6, teeth_max=30, coaxial=True)
    off = gt.search(_valid_query(monotonic=False, **base))
    on = gt.search(_valid_query(monotonic=True, **base))
    assert not off.truncated and not on.truncated
    assert any(any(s.driving < s.driven for s in t.stages) for t in off.trains), \
        'expected a mixed-direction coaxial train when monotonic is off'
    assert on.trains and len(on.trains) < len(off.trains)     # monotonic strictly pruned
    for t in on.trains:
        assert len({s.tooth_sum() for s in t.stages}) == 1     # still coaxial
        assert all(s.driving > s.driven for s in t.stages)     # all step-up


def test_monotonic_composes_with_direction_parity():
    # direction='same' (even stage counts only) + monotonic must both FILTER and PRUNE: for
    # 3:1 over 6..24 with direction='same' there are mixed-direction 2-stage trains without
    # monotonic (19 of 122); monotonic removes them, keeping only all-step-up even-count
    # trains. Non-vacuous (a mixed train demonstrably exists when monotonic is off).
    base = dict(target_num=3, target_den=1, min_stages=1, max_stages=3,
                teeth_min=6, teeth_max=24, direction='same')
    off = gt.search(_valid_query(monotonic=False, **base))
    on = gt.search(_valid_query(monotonic=True, **base))
    assert not off.truncated and not on.truncated
    assert any(any(s.driving < s.driven for s in t.stages) for t in off.trains), \
        'expected a mixed-direction train when monotonic is off'
    assert on.trains and len(on.trains) < len(off.trains)     # monotonic strictly pruned
    for t in on.trains:
        assert len(t.stages) % 2 == 0                          # parity filter still holds
        assert all(s.driving > s.driven for s in t.stages)     # all step-up


def test_pruned_search_matches_brute_force_three_stage_irreducible():
    # 2:1 over 6..12 up to 3 stages: at n=3, reducible padded trains (a cancelling
    # reciprocal subset plus a real stage) exist in a naive enumeration. R1 must drop them
    # in BOTH search() and the reference; parity confirms they agree. Small range keeps the
    # O(range^6) reference fast (all_stages ~ 42, 42**3 ~ 74k combos).
    q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=12)
    keys = _search_keys(q)
    assert keys, 'expected irreducible solutions'
    # Independent of R1: no returned train has a cancelling subset (rebuild a train per key).
    for k in keys:
        train = gt.GearTrain(tuple(gt.Stage(a, b) for a, b in k))
        assert not _train_has_cancelling_subset(train)
    assert keys == _brute_force_keys(q)


def test_pruned_search_matches_brute_force_monotonic():
    # Monotonic 2:1 over 6..12 up to 3 stages: every stage step-up in both search() and
    # the reference; parity confirms the R2 prune matches an exhaustive same-direction scan.
    q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=12, monotonic=True)
    keys = _search_keys(q)
    assert keys, 'expected monotonic solutions'
    for k in keys:
        assert all(a > b for a, b in k)         # every stage step-up
    assert keys == _brute_force_keys(q)


def test_monotonic_composes_with_coaxial_stepdown():
    # Step-DOWN coaxial + monotonic (mirror of the step-up coaxial test): for 1:2 coaxial over
    # 6..30 there are 3 trains without monotonic, two of them mixed-direction (a step-up
    # stage); monotonic keeps only the all-step-down train. Exercises R2's step_down branch in
    # the coaxial single-candidate path. Non-vacuous (a mixed train exists when monotonic off).
    base = dict(target_num=1, target_den=2, min_stages=2, max_stages=2,
                teeth_min=6, teeth_max=30, coaxial=True)
    off = gt.search(_valid_query(monotonic=False, **base))
    on = gt.search(_valid_query(monotonic=True, **base))
    assert not off.truncated and not on.truncated
    assert any(any(s.driving > s.driven for s in t.stages) for t in off.trains), \
        'expected a mixed-direction (step-up) coaxial train when monotonic is off'
    assert on.trains and len(on.trains) < len(off.trains)     # monotonic strictly pruned
    for t in on.trains:
        assert len({s.tooth_sum() for s in t.stages}) == 1     # still coaxial
        assert all(s.driving < s.driven for s in t.stages)     # all step-down


def test_monotonic_composes_with_end_gear_bounds():
    # R2 + end-gear bounds: 12:1 with the input gear bounded to 81..83 over 6..90. Without
    # monotonic, some qualifying trains contain a step-down stage; monotonic removes those and
    # keeps only all-step-up trains, all still honoring the input bound (first stage's driving
    # gear in 81..83). Non-vacuous (a bounded mixed-direction train exists when monotonic off).
    base = dict(target_num=12, target_den=1, min_stages=2, max_stages=2,
                teeth_min=6, teeth_max=90, input_min=81, input_max=83)
    off = gt.search(_valid_query(monotonic=False, **base))
    on = gt.search(_valid_query(monotonic=True, **base))
    assert not off.truncated and not on.truncated
    assert any(any(s.driving < s.driven for s in t.stages) for t in off.trains), \
        'expected a mixed-direction train among the bounded results when monotonic is off'
    assert on.trains and len(on.trains) < len(off.trains)     # monotonic strictly pruned
    for t in on.trains:
        assert 81 <= t.stages[0].driving <= 83                 # input bound still honored
        assert all(s.driving > s.driven for s in t.stages)     # all step-up


def test_spread_is_a_permutation():
    # Exact powers of two (4, 8, 16) and the sizes either side of them: the reversed index
    # can only overshoot `n` when n is NOT a power of two, so both cases must be covered or
    # a regression in the bit-width could silently drop or duplicate first stages.
    for n in (3, 4, 7, 8, 9, 16, 17, 100):
        items = list(range(n))
        assert sorted(gt._spread(items)) == items, f'not a permutation for n={n}'


def test_spread_handles_tiny_lists():
    assert gt._spread([]) == []
    assert gt._spread([7]) == [7]
    assert gt._spread([7, 8]) == [7, 8]


def test_spread_is_deterministic():
    items = list(range(100))
    assert gt._spread(items) == gt._spread(items)


def test_spread_prefix_covers_the_whole_range():
    # The point of the reordering: a short PREFIX must reach the far end of the list, which
    # ascending order never does. With 100 items, the first 8 spread out instead of being 0..7.
    order = gt._spread(list(range(100)))
    prefix = order[:8]
    assert max(prefix) > 50, f'prefix stayed in the low corner: {prefix}'
    assert len({p // 25 for p in prefix}) >= 3, f'prefix did not cover quarters: {prefix}'


def _repro_query(**over):
    """The user-reported deep-reduction query (design spec 2026-07-25, section 1).

    Palette input: ratio 60:1, exactly 4 stages, teeth 12-90, input gear 12-44, output gear
    12-44, rotation 'same as input', same-direction stages only, clearance 2. The engine's
    ratio is driving/driven -- the RECIPROCAL of the UI's input:output -- hence 1/60.
    """
    base = dict(target_num=1, target_den=60, min_stages=4, max_stages=4,
                teeth_min=12, teeth_max=90, direction='same',
                input_min=12, input_max=44, output_min=12, output_max=44,
                monotonic=True, clearance=2, coaxial=False)
    base.update(over)
    return gt.TrainQuery(**base)


def test_search_reaches_large_first_stage_trains():
    # Budget-fair exploration. Before it, this query returned ZERO trains: the DFS drained its
    # whole 600k work budget into the small-driven corner (first stage (12,13)) and truncated
    # before reaching any first stage with a large driven gear. Verified after: 10 trains, all
    # built on a first stage of (12,45) or (18,54) -- deep in the ascending enumeration order.
    res = gt.search(_repro_query())
    assert res.trains, 'budget-fair exploration must reach this deep reduction'
    keys = {tuple(sorted((s.driving, s.driven) for s in t.stages)) for t in res.trains}
    assert ((12, 45), (12, 45), (12, 48), (30, 32)) in keys
    # The exact key above is tied to FIRST_STAGE_SLICE's default; this is the property that
    # must hold regardless of tuning -- some train is built on a first stage whose driven gear
    # is far above the small corner the old DFS never escaped (its first stage was (12,13)).
    assert any(t.stages[0].driven >= 40 for t in res.trains), \
        f'no train reached a large-driven first stage: {sorted(keys)}'


def _first_stages(trains):
    return {(t.stages[0].driving, t.stages[0].driven) for t in trains}


def test_search_results_span_many_first_stages():
    # The "200 clones" complaint, pinned. Measured on the OLD engine this exact query returned
    # 200 trains sharing exactly ONE displayed first stage; budget-fair exploration returns
    # trains spanning ~38. This is the anti-clone property the whole change exists for, and it
    # is what makes the lower train COUNT on such queries a feature, not a regression: the two
    # result sets are disjoint -- clones traded for variety.
    q = _valid_query(target_num=1, target_den=60, min_stages=4, max_stages=4,
                     teeth_min=8, teeth_max=90)
    res = gt.search(q)
    assert res.trains
    assert len(_first_stages(res.trains)) >= 15, \
        f'results clustered on {len(_first_stages(res.trains))} first stage(s)'


def test_work_budget_scales_with_the_tooth_range():
    # Calls _work_budget directly, so the teeth values here intentionally bypass validate()'s
    # 6-150 limits -- this tests the scaling arithmetic, not what the UI accepts.
    # A span at or below REFERENCE_SPAN keeps exactly WORK_BUDGET, so narrow queries -- every
    # completeness parity test included -- are bit-for-bit unaffected by the scaling.
    narrow = _valid_query(teeth_min=6, teeth_max=24)
    assert gt._work_budget(narrow) == gt.WORK_BUDGET
    assert gt._work_budget(_valid_query(teeth_min=8, teeth_max=87)) == gt.WORK_BUDGET
    # A wider span buys proportionally more budget (quadratic in the span)...
    wide = _valid_query(teeth_min=8, teeth_max=167)          # span 160 == 2x REFERENCE_SPAN
    assert gt._work_budget(wide) == 4 * gt.WORK_BUDGET
    # ...but never more than the responsiveness ceiling.
    assert gt._work_budget(_valid_query(teeth_min=1, teeth_max=2000)) == gt.MAX_WORK_BUDGET


def test_search_wide_tooth_range_still_finds_varied_trains():
    # A wide-but-plausible range (teeth 8-120, well past the 8-90 palette default) is where the
    # fixed 600k budget used to spread too thinly to reach any leaf. With the span-scaled budget
    # it returns trains across many first stages. Measured: ~101 trains over ~44 first stages.
    q = _valid_query(target_num=1, target_den=60, min_stages=4, max_stages=4,
                     teeth_min=8, teeth_max=120)
    t0 = time.perf_counter()
    res = gt.search(q)
    elapsed = time.perf_counter() - t0
    assert elapsed < 25.0, f'wide range took {elapsed:.1f}s'
    assert res.trains, 'a wide range must still return trains'
    assert all(t.ratio() == Fraction(1, 60) for t in res.trains)
    assert len(_first_stages(res.trains)) >= 10, \
        f'wide-range results clustered on {len(_first_stages(res.trains))} first stage(s)'


def test_search_general_results_include_the_coaxial_ones():
    # Invariant: every coaxial train is single-plane buildable, so the general (buildable)
    # search must be a SUPERSET of the coaxial one. Verified violated without the merge: the
    # general search returns 72 trains here and misses BOTH of the 2 coaxial ones. Uses
    # teeth_max=60, a cheaper variant of the reported query, to keep the two searches near 10s.
    q = _repro_query(teeth_max=60)
    coaxial = _search_keys(_repro_query(teeth_max=60, coaxial=True))
    general = _search_keys(q)
    assert coaxial, 'the coaxial search must find trains here or this test is vacuous'
    assert coaxial <= general, f'general search missed coaxial trains: {coaxial - general}'


def test_search_finds_the_reported_deep_reduction_train():
    # The exact train from the bug report: 60:1 in 4 monotonic step-down stages, every tooth
    # sum 68, end gears within 12-44, clearance 2. The coaxial search found it; the general
    # search returned ZERO trains. It is reachable only via the coaxial-merge -- budget-fair
    # exploration alone does not reach it (verified: that finds 10 other trains, not this one).
    res = gt.search(_repro_query())
    keys = {tuple(sorted((s.driving, s.driven) for s in t.stages)) for t in res.trains}
    assert ((12, 56), (17, 51), (17, 51), (28, 40)) in keys


def _first_stage_counts(trains):
    counts = {}
    for t in trains:
        key = (t.stages[0].driving, t.stages[0].driven)
        counts[key] = counts.get(key, 0) + 1
    return counts


def test_diverse_demotes_over_quota_trains_instead_of_dropping_them():
    # Unit test on the helper. Six trains share first stage (10,20) and one has (30,15).
    # With per_first=2, the four over-quota (10,20) trains move to the TAIL -- the list keeps
    # all seven, it is only reordered.
    clones = [gt.GearTrain((gt.Stage(10, 20), gt.Stage(30, 15 + i))) for i in range(6)]
    other = gt.GearTrain((gt.Stage(30, 15), gt.Stage(10, 20)))
    result = gt._diverse(clones + [other], per_first=2, cap=100)
    assert len(result) == 7, 'nothing may be dropped below the cap'
    assert result[2] is other, 'the distinct first stage must be promoted past the clones'
    assert result[:2] == clones[:2]


def test_diverse_truncates_to_the_cap():
    clones = [gt.GearTrain((gt.Stage(10, 20), gt.Stage(30, 15 + i))) for i in range(10)]
    assert len(gt._diverse(clones, per_first=3, cap=4)) == 4


def test_search_caps_results_per_first_stage():
    # The palette's first-use default fills the 200-cap. Before the diversity cap, 9 results
    # shared one displayed first stage across 115 distinct ones; after, at most 5.
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=8, teeth_max=90)
    res = gt.search(q)
    assert len(res.trains) == gt.MAX_RESULTS
    counts = _first_stage_counts(res.trains)
    assert max(counts.values()) <= gt.MAX_PER_FIRST_STAGE
    assert len(counts) >= 100, 'expected the results to span many distinct first stages'


def test_diversity_cap_keeps_every_train_when_under_the_result_cap():
    # The cap DEMOTES, it never deletes: with a pool smaller than MAX_RESULTS every train is
    # still returned. Verified: 2:1 over 6..12 up to 3 stages yields exactly 44 trains, 8 of
    # which share one first stage -- more than MAX_PER_FIRST_STAGE, and all 8 must survive.
    # This is also the guard that the display cap never shrinks the pool the parity tests
    # compare against.
    q = _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=6, teeth_max=12)
    res = gt.search(q)
    assert len(res.trains) == 44
    assert max(_first_stage_counts(res.trains).values()) > gt.MAX_PER_FIRST_STAGE
    assert not res.truncated, 'the diversity cap must never flag truncation'


def _general_pass_truncated(q):
    """Run ONLY the general (non-coaxial) pass of `q`, as search() does, and return its
    truncation flag -- the reference the merged flag must match."""
    qn, _ = gt.normalize(q)
    return gt._collect(qn, {}, gt.MAX_RESULTS)[0]


def test_search_truncation_reflects_only_the_general_pass():
    # The coaxial-merge must never raise the partial-results flag on its own. If the general
    # pass was exhaustive it already contains every coaxial train that exists, so the probe
    # running out of budget says nothing about the user's query -- and the palette renders
    # truncated=True as directive advice ("narrow the tooth range"), which would be wrong.
    # Structural guard: _merge_coaxial has no truncation channel at all -- it returns only a
    # dropped count. This is what makes the property below hold by construction, and it fails
    # loudly if someone re-adds truncation to its return value.
    dropped = gt._merge_coaxial(_repro_query(teeth_max=60), {})
    assert isinstance(dropped, int), \
        f'_merge_coaxial must report only a dropped count, got {dropped!r}'

    for q in (_valid_query(target_num=1, target_den=6, min_stages=1, max_stages=2,
                           teeth_min=6, teeth_max=24),
              _valid_query(target_num=2, target_den=1, min_stages=1, max_stages=3,
                           teeth_min=6, teeth_max=12),
              _valid_query(target_num=1, target_den=60, min_stages=1, max_stages=2,
                           teeth_min=6, teeth_max=60),
              _repro_query()):
        assert gt.search(q).truncated == _general_pass_truncated(q), \
            f'truncation flag diverged from the general pass for {q}'


def test_coaxial_merge_is_skipped_once_the_pool_is_full():
    # Documents the merge gate's scope, so nobody reads buildable >= coaxial as unconditional.
    # On the palette default the general pass alone overflows MAX_RESULTS, so the coaxial pass
    # never runs and some coaxial trains are absent from the pool. That is deliberate: the
    # extra pass costs ~6s on wide queries, every train in the full pool has <= 2 stages and
    # outranks late 3-stage coaxial finds on _sort_key, and such a search already reports
    # truncated=True so the user knows the list is partial.
    q = _valid_query(target_num=12, target_den=1, min_stages=1, max_stages=3,
                     teeth_min=8, teeth_max=90)
    res = gt.search(q)
    assert res.truncated, 'this query must overflow the cap or the test is vacuous'
    seen = {}
    gt._collect(*(gt.normalize(q)[0], seen, gt.MAX_RESULTS))
    assert len(seen) >= gt.MAX_RESULTS, 'the general pass alone must fill the pool here'


def test_search_is_deterministic():
    # Budget-fair exploration picks its visit order with _spread (bit reversal), not an RNG,
    # and iterative broadening is a fixed schedule -- so repeated searches must be identical
    # down to the ORDER of the results, not just the set. The palette re-runs searches freely,
    # so a user changing an unrelated input and changing it back must see the same list.
    q = _repro_query(teeth_max=60)
    first = [tuple((s.driving, s.driven) for s in t.stages) for t in gt.search(q).trains]
    second = [tuple((s.driving, s.driven) for s in t.stages) for t in gt.search(q).trains]
    assert first, 'expected results or this test is vacuous'
    assert first == second


def test_search_deep_reduction_query_terminates_fast():
    # The reported query runs a budget-fair general pass AND a coaxial-merge pass (the general
    # pass comes up far short of the 200-cap, so the merge fires). The palette blocks while
    # this runs, so guard the ceiling. Also re-checks that every constraint still holds on the
    # trains this newly-reachable region produces.
    t0 = time.perf_counter()
    res = gt.search(_repro_query())
    elapsed = time.perf_counter() - t0
    assert elapsed < 25.0, f'deep-reduction search took {elapsed:.1f}s'
    assert res.trains
    assert all(t.ratio() == Fraction(1, 60) for t in res.trains)
    for t in res.trains:
        assert gt._clearance_ok(t.stages, 2)                # still single-plane buildable
        assert 12 <= t.stages[0].driving <= 44              # input bound honored
        assert 12 <= t.stages[-1].driven <= 44              # output bound honored
        assert all(s.driving < s.driven for s in t.stages)  # monotonic step-down
        assert len(t.stages) == 4                           # exactly the requested stage count


def test_validate_rejects_too_many_teeth():
    errs = gt.validate(_valid_query(teeth_max=gt.MAX_TEETH + 1))
    assert any('tooth' in e.lower() for e in errs)


def test_validate_accepts_the_tooth_limits_exactly():
    # The limits are inclusive.
    assert gt.validate(_valid_query(teeth_min=gt.MIN_TEETH, teeth_max=gt.MAX_TEETH)) == []


def test_searchable_stage_counts_honours_parity_and_coaxial():
    q = _valid_query(min_stages=1, max_stages=4)
    assert gt._searchable_stage_counts(q) == [1, 2, 3, 4]
    assert gt._searchable_stage_counts(_valid_query(
        min_stages=1, max_stages=4, direction='same')) == [2, 4]
    assert gt._searchable_stage_counts(_valid_query(
        min_stages=1, max_stages=4, direction='opposite')) == [1, 3]
    # Coaxial needs >= 2 stages, matching what normalize() enforces.
    assert gt._searchable_stage_counts(_valid_query(
        min_stages=1, max_stages=3, coaxial=True)) == [2, 3]


def test_validate_rejects_unreachable_ratio():
    # 3600:1 in 2 stages over teeth 8-150: each stage reaches at most 150/8 = 18.75x, so two
    # stages reach 351.6x -- far short of 3600. The message must name the stages needed (3).
    errs = gt.validate(_valid_query(target_num=3600, target_den=1, min_stages=2, max_stages=2,
                                    teeth_min=8, teeth_max=150))
    assert errs, 'an unreachable ratio must be rejected'
    assert any('not reachable' in e for e in errs)
    assert any('at least 3 stages' in e for e in errs)


def test_validate_accepts_reachable_ratio():
    # The same 3600:1 target with enough stages: 18.75**4 is ~123000 >= 3600.
    assert gt.validate(_valid_query(target_num=3600, target_den=1, min_stages=4, max_stages=4,
                                    teeth_min=8, teeth_max=150)) == []


def test_validate_reachability_respects_direction_parity():
    # direction='same' searches only EVEN stage counts, so the suggested minimum must be even
    # too. 3600:1 needs 3 stages by magnitude, but 'same' cannot use 3 -> it must say 4.
    errs = gt.validate(_valid_query(target_num=3600, target_den=1, min_stages=2, max_stages=2,
                                    teeth_min=8, teeth_max=150, direction='same'))
    assert any('at least 4 stages' in e for e in errs)


def test_validate_rejects_when_no_stage_count_matches_the_direction():
    # 'same' needs an even stage count, but the range 3..3 offers only an odd one.
    errs = gt.validate(_valid_query(min_stages=3, max_stages=3, direction='same'))
    assert errs
    assert any('reverses rotation' in e for e in errs)


def test_validate_rejects_single_tooth_count_range():
    # teeth_min == teeth_max makes every stage 1:1, so nothing but 1:1 is reachable.
    errs = gt.validate(_valid_query(teeth_min=20, teeth_max=20))
    assert any('1:1' in e for e in errs)


def test_search_reports_unreachable_ratio_as_an_error():
    # End to end: an unreachable query is an ERROR with an explanation, not a slow empty list.
    res = gt.search(_valid_query(target_num=3600, target_den=1, min_stages=2, max_stages=2,
                                 teeth_min=8, teeth_max=150))
    assert res.error is not None
    assert res.trains == []
