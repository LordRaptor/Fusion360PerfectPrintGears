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
