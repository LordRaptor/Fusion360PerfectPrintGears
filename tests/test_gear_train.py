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
