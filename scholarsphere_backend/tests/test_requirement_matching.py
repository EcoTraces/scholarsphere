"""Unit tests for app/services/requirement_matching.py's rule-based
classifier - in particular a regression for a substring-matching bug in
the degree-level branch.
"""

from app.models.application_preparation import RequirementMatchStatus
from app.services.requirement_matching import classify_requirement


def test_diploma_requirement_is_not_misclassified_as_a_masters_requirement() -> None:
    """Regression test: the degree-level branch used to check for the

    abbreviation "ma " as a plain substring, which also matches inside
    ordinary, unrelated words such as "diploma " - a requirement that
    never mentions a master's degree at all was wrongly routed into the
    master's-degree-level branch (and, with no qualification on file,
    reported as "missing" a master's degree it never actually required).
    """
    text = "Applicants must hold a diploma or equivalent qualification from a recognized institution."
    status, reason = classify_requirement(text, profile=None, background_entries=[])
    assert status == RequirementMatchStatus.needs_verification
    assert "master" not in reason.lower()
    assert "bachelor" not in reason.lower()


def test_bachelor_abbreviation_false_positive_is_also_fixed() -> None:
    """Same bug, other keyword: "ba " is a substring of ordinary words like

    "alba " or "database ", which must not trigger the bachelor's-degree
    branch.
    """
    text = "The database of alumni must be updated before applications open."
    status, reason = classify_requirement(text, profile=None, background_entries=[])
    assert status == RequirementMatchStatus.needs_verification
    assert "bachelor" not in reason.lower()


def test_real_masters_requirement_still_matches_the_degree_branch() -> None:
    text = "Applicants must hold a Master's degree in a relevant field."
    status, reason = classify_requirement(text, profile=None, background_entries=[])
    assert status == RequirementMatchStatus.missing
    assert "qualification on file" in reason


def test_real_ba_abbreviation_still_matches_the_degree_branch() -> None:
    text = "A BA in a relevant discipline is required."
    status, reason = classify_requirement(text, profile=None, background_entries=[])
    assert status == RequirementMatchStatus.missing
    assert "qualification on file" in reason
