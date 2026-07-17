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


def test_normalize_warns_on_small_teeth():
    q, warnings = gt.normalize(_valid_query(teeth_min=4))
    assert any('cycloidal' in w.lower() or str(gt.MIN_TEETH_WARN) in w for w in warnings)


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


def test_search_empty_when_no_solution():
    # 7 : 1 with a prime 7 that cannot be formed from teeth 8..12 in one stage.
    q = _valid_query(target_num=7, target_den=1, min_stages=1, max_stages=1,
                     teeth_min=8, teeth_max=12)
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


import itertools


def _brute_force_keys(q):
    """Obvious O(range^(2n)) reference: enumerate every stage combination, keep exact
    matches (respecting direction parity + coaxial), return their canonical keys."""
    L, H = q.teeth_min, q.teeth_max
    target = Fraction(q.target_num, q.target_den)
    all_stages = [gt.Stage(a, b)
                  for a in range(L, H + 1) for b in range(L, H + 1)]
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
            if prod == target:
                keys.add(tuple(sorted((s.driving, s.driven) for s in combo)))
    return keys


def _search_keys(q):
    return {tuple(sorted((s.driving, s.driven) for s in t.stages))
            for t in gt.search(q).trains}


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


def test_arrange_single_stage_needs_both_ends_on_one_stage():
    stages = (gt.Stage(8, 40),)
    # input gear 8 in [6,10] and output gear 40 in [30,50] -> keep
    assert gt._arrange_for_ends(stages, 6, 10, 30, 50) == stages
    # output gear 40 not in [50,60] -> no arrangement
    assert gt._arrange_for_ends(stages, 6, 10, 50, 60) is None


def test_arrange_two_stage_orders_input_first_output_last():
    stages = (gt.Stage(8, 24), gt.Stage(30, 72))
    arranged = gt._arrange_for_ends(stages, 6, 10, 60, 80)   # input 8, output 72
    assert arranged is not None
    assert arranged[0].driving == 8      # input arbor is first
    assert arranged[-1].driven == 72     # output arbor is last


def test_arrange_two_stage_rejects_when_only_one_stage_serves_both_ends():
    # stage 0 is the ONLY input-qualifier (driving 8 in [6,10]) AND the ONLY
    # output-qualifier (driven 40 in [38,42]); one stage cannot be both arbors -> None.
    stages = (gt.Stage(8, 40), gt.Stage(30, 20))
    assert gt._arrange_for_ends(stages, 6, 10, 38, 42) is None


def test_arrange_duplicate_qualifying_stages_pass():
    # Two identical qualifying stages are distinct POSITIONS, so a valid i != j exists.
    stages = (gt.Stage(8, 40), gt.Stage(8, 40))
    arranged = gt._arrange_for_ends(stages, 6, 10, 38, 42)
    assert arranged is not None
    assert arranged[0].driving == 8 and arranged[-1].driven == 40


def test_search_input_bound_orders_first_stage_driving():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=90, input_min=18, input_max=20)
    res = gt.search(q)
    assert res.error is None
    assert res.trains, 'expected trains with an input gear in 18..20'
    for t in res.trains:
        assert 18 <= t.stages[0].driving <= 20     # input arbor within bound AND first


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


def test_search_no_bounds_keeps_canonical_stage_order():
    # The disabled (None) path must NOT reorder stages: each train's stored stages stay in
    # canonical non-decreasing (driving, driven) order. Uses 3 stages so a reorder bug
    # would actually show (with 2 stages the arranged tuple equals the canonical one).
    q = _valid_query(target_num=12, target_den=1, min_stages=3, max_stages=3,
                     teeth_min=6, teeth_max=40)
    res = gt.search(q)
    assert res.trains, 'expected 3-stage solutions'
    for t in res.trains:
        pairs = [(s.driving, s.driven) for s in t.stages]
        assert pairs == sorted(pairs), 'no-bounds path must keep canonical order'


def _brute_force_keys_bounded(q):
    """Reference like _brute_force_keys, but also honours the optional end-gear bounds.

    Uses its OWN arrangement check (deliberately NOT gear_train._arrange_for_ends) so this
    test verifies the pruned enumeration's COMPLETENESS independently of the implementation
    it is checking. A combo counts iff some ordering puts a driving gear in the input range
    first and a DIFFERENT driven gear in the output range last (1-stage: one stage does both).
    """
    L, H = q.teeth_min, q.teeth_max
    in_lo = q.input_min if q.input_min is not None else L
    in_hi = q.input_max if q.input_max is not None else H
    out_lo = q.output_min if q.output_min is not None else L
    out_hi = q.output_max if q.output_max is not None else H
    target = Fraction(q.target_num, q.target_den)
    all_stages = [gt.Stage(a, b) for a in range(L, H + 1) for b in range(L, H + 1)]

    def admits(combo):
        in_ok = [k for k, s in enumerate(combo) if in_lo <= s.driving <= in_hi]
        out_ok = [k for k, s in enumerate(combo) if out_lo <= s.driven <= out_hi]
        if len(combo) == 1:
            return bool(in_ok) and bool(out_ok)     # one stage must satisfy both ends
        return any(i != j for i in in_ok for j in out_ok)

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
            if admits(combo):
                keys.add(tuple(sorted((s.driving, s.driven) for s in combo)))
    return keys


def test_pruned_search_matches_brute_force_with_end_bounds():
    q = _valid_query(target_num=12, target_den=1, min_stages=2, max_stages=2,
                     teeth_min=6, teeth_max=24, input_min=18, input_max=20)
    bounded = _search_keys(q)
    assert bounded, 'expected some qualifying trains'
    assert bounded == _brute_force_keys_bounded(q)
    # genuine narrowing: some unbounded trains have every stage's driving > 20
    open_keys = _search_keys(_valid_query(target_num=12, target_den=1, min_stages=2,
                                          max_stages=2, teeth_min=6, teeth_max=24))
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
