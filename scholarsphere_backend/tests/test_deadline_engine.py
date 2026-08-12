from datetime import date, timedelta

import pytest

from app.services.deadline_engine import DeadlinePriority, assess_deadline

TODAY = date(2026, 8, 12)


@pytest.mark.parametrize(
    "offset_days,expected_priority",
    [
        (31, DeadlinePriority.normal),
        (30, DeadlinePriority.upcoming),
        (15, DeadlinePriority.upcoming),
        (14, DeadlinePriority.important),
        (7, DeadlinePriority.important),
        (6, DeadlinePriority.urgent),
        (3, DeadlinePriority.urgent),
        (2, DeadlinePriority.critical),
        (1, DeadlinePriority.critical),
        (0, DeadlinePriority.last_chance),
        (-1, DeadlinePriority.expired),
        (-100, DeadlinePriority.expired),
    ],
)
def test_priority_boundaries(offset_days: int, expected_priority: DeadlinePriority) -> None:
    deadline = TODAY + timedelta(days=offset_days)
    result = assess_deadline(deadline, today=TODAY)
    assert result.days_remaining == offset_days
    assert result.priority == expected_priority


def test_missing_deadline_is_unknown() -> None:
    result = assess_deadline(None, today=TODAY)
    assert result.days_remaining is None
    assert result.priority == DeadlinePriority.unknown
