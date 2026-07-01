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
