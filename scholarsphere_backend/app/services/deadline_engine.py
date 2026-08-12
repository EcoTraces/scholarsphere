"""Deadline intelligence: days-remaining and priority classification.

Boundaries follow the product specification exactly:

    > 30 days   = NORMAL
    15-30 days  = UPCOMING
    7-14 days   = IMPORTANT
    3-6 days    = URGENT
    1-2 days    = CRITICAL
    < 24 hours  = LAST_CHANCE
    passed      = EXPIRED
    no deadline = UNKNOWN

``ExternalOpportunity.deadline`` is stored as a calendar ``date`` (no time
component), because none of the three integrated sources publish a
deadline time. LAST_CHANCE is therefore approximated as "the deadline is
today, local calendar day at the evaluation instant" rather than a true
sub-24-hour countdown. This is a known precision limitation, not a bug:
see the backend README "Known limitations" section.
"""

import enum
from dataclasses import dataclass
from datetime import date


class DeadlinePriority(str, enum.Enum):
    unknown = "UNKNOWN"
    normal = "NORMAL"
    upcoming = "UPCOMING"
    important = "IMPORTANT"
    urgent = "URGENT"
    critical = "CRITICAL"
    last_chance = "LAST_CHANCE"
    expired = "EXPIRED"


@dataclass(frozen=True)
class DeadlineAssessment:
    days_remaining: int | None
    priority: DeadlinePriority


def assess_deadline(deadline: date | None, *, today: date) -> DeadlineAssessment:
    """Classify a deadline's urgency relative to ``today``.

    ``today`` must be supplied by the caller (rather than computed here)
    so results are deterministic and testable.
    """
    if deadline is None:
        return DeadlineAssessment(days_remaining=None, priority=DeadlinePriority.unknown)

    days_remaining = (deadline - today).days

    if days_remaining < 0:
        priority = DeadlinePriority.expired
    elif days_remaining == 0:
        priority = DeadlinePriority.last_chance
    elif days_remaining <= 2:
        priority = DeadlinePriority.critical
    elif days_remaining <= 6:
        priority = DeadlinePriority.urgent
    elif days_remaining <= 14:
        priority = DeadlinePriority.important
    elif days_remaining <= 30:
        priority = DeadlinePriority.upcoming
    else:
        priority = DeadlinePriority.normal

    return DeadlineAssessment(days_remaining=days_remaining, priority=priority)
