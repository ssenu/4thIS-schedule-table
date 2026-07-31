import pytest

from app.constants import SLOT_COUNT
from app.timeslot import describe, overlaps, slot_to_time, time_to_slot


def test_slot_zero_is_day_start():
    assert slot_to_time(0) == "06:00"


def test_slot_six_is_nine_am():
    assert slot_to_time(6) == "09:00"


def test_last_slot_boundary_is_midnight():
    assert slot_to_time(SLOT_COUNT) == "24:00"


def test_half_hour_slots():
    assert slot_to_time(1) == "06:30"
    assert slot_to_time(35) == "23:30"


@pytest.mark.parametrize("slot", range(SLOT_COUNT + 1))
def test_round_trip(slot):
    assert time_to_slot(slot_to_time(slot)) == slot


def test_time_to_slot_rejects_off_grid_minutes():
    with pytest.raises(ValueError):
        time_to_slot("09:15")


def test_time_to_slot_rejects_before_day_start():
    with pytest.raises(ValueError):
        time_to_slot("05:30")


def test_describe_reads_as_a_sentence():
    assert describe(0, 6, 14) == "월 09:00~13:00"
    assert describe(6, 0, 1) == "일 06:00~06:30"


def test_overlapping_ranges():
    assert overlaps(6, 10, 8, 12) is True
    assert overlaps(6, 10, 0, 36) is True


def test_adjacent_ranges_do_not_overlap():
    assert overlaps(6, 10, 10, 14) is False
    assert overlaps(10, 14, 6, 10) is False


def test_disjoint_ranges_do_not_overlap():
    assert overlaps(6, 10, 20, 24) is False
