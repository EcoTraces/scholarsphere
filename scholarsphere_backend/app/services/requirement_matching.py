"""Deterministic, rule-based requirement matching - never AI-dependent

(works identically whether or not an AI provider is configured) and never
asserts eligibility the underlying data can't actually support. Every
classification rule below is documented at the point it's applied; there
is no hidden scoring model. An ambiguous or unparseable requirement always
resolves to ``needs_verification``, never guessed into ``match``.
"""

from __future__ import annotations

import re

from app.models.applicant_background import ApplicantBackgroundEntry
from app.models.applicant_profile import ApplicantProfile, EnglishTestStatus, PassportStatus
from app.models.application_preparation import RequirementMatchStatus

_REQUIREMENT_SIGNAL_RE = re.compile(
    r"\b(must|should|required|requires?|minimum|at least|eligib\w*|applicants? (?:must|should)|"
    r"candidates? (?:must|should))\b",
    re.IGNORECASE,
)
_WORK_YEARS_RE = re.compile(r"(\d+)\s*\+?\s*years?\s+of\s+(?:relevant\s+)?(?:work\s+)?experience", re.IGNORECASE)
_DEGREE_KEYWORDS = {
    "bachelor": ("bachelor", "undergraduate", "bsc", "ba "),
    "master": ("master", "postgraduate", "msc", "ma "),
    "phd": ("phd", "doctoral", "doctorate"),
}


def extract_requirement_candidates(description: str, *, limit: int = 20) -> list[str]:
    """Splits a real opportunity description into sentence-like fragments

    and keeps only the ones that read like an actual requirement
    statement - never invents a requirement that isn't literally present
    in the opportunity's own text.
    """
    if not description:
        return []
    fragments = re.split(r"(?<=[.!?])\s+|\n+", description)
    candidates: list[str] = []
    seen: set[str] = set()
    for fragment in fragments:
        text = fragment.strip()
        if len(text) < 15 or len(text) > 500:
            continue
        if not _REQUIREMENT_SIGNAL_RE.search(text):
            continue
        key = text.lower()
        if key in seen:
            continue
        seen.add(key)
        candidates.append(text)
        if len(candidates) >= limit:
            break
    return candidates


def classify_requirement(
    requirement_text: str,
    *,
    profile: ApplicantProfile | None,
    background_entries: list[ApplicantBackgroundEntry],
) -> tuple[RequirementMatchStatus, str]:
    text = requirement_text.lower()

    if any(word in text for word in ("nationality", "citizen", "national of")):
        # Free-text nationality-list parsing is not reliable enough to
        # assert eligibility either way - always route to a human
        # verification officer, matching this platform's existing
        # "AI's role: none, today" eligibility policy
        # (docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS10).
        return (
            RequirementMatchStatus.needs_verification,
            "Nationality/citizenship eligibility must be confirmed manually against the "
            "opportunity's own published country list.",
        )

    if any(word in text for word in ("ielts", "toefl", "english language", "english proficiency")):
        if profile is None or profile.english_test_status == EnglishTestStatus.not_taken:
            return (
                RequirementMatchStatus.missing,
                "No English test result on file yet.",
            )
        if profile.english_test_status == EnglishTestStatus.completed:
            return RequirementMatchStatus.match, "English test marked completed on your profile."
        if profile.english_test_status == EnglishTestStatus.planned:
            return (
                RequirementMatchStatus.partial_match,
                "English test is planned but not yet completed.",
            )
        return RequirementMatchStatus.match, "Your profile marks an English test as not required."

    if "passport" in text:
        if profile is None or profile.passport_status == PassportStatus.unavailable:
            return RequirementMatchStatus.missing, "No valid passport on file yet."
        if profile.passport_status == PassportStatus.valid:
            return RequirementMatchStatus.match, "A valid passport is on file."
        if profile.passport_status == PassportStatus.applied:
            return RequirementMatchStatus.partial_match, "Passport application is in progress."
        return RequirementMatchStatus.missing, "Passport on file is expired."

    for level, keywords in _DEGREE_KEYWORDS.items():
        if any(keyword in text for keyword in keywords):
            qualification = (profile.highest_qualification if profile else "").lower()
            if not qualification:
                return (
                    RequirementMatchStatus.missing,
                    "No highest qualification on file to compare against this requirement.",
                )
            if level in qualification or any(k in qualification for k in keywords):
                return RequirementMatchStatus.match, "Your recorded qualification matches this level."
            return (
                RequirementMatchStatus.needs_verification,
                "Could not automatically confirm your qualification level matches this "
                "requirement - please review manually.",
            )

    years_match = _WORK_YEARS_RE.search(text)
    if years_match:
        required_years = float(years_match.group(1))
        actual_years = profile.work_experience_years if profile else 0.0
        if actual_years >= required_years:
            return (
                RequirementMatchStatus.match,
                f"{actual_years:g} years on file meets the {required_years:g}-year requirement.",
            )
        return (
            RequirementMatchStatus.missing,
            f"{actual_years:g} years on file is below the {required_years:g}-year requirement.",
        )

    if "research" in text and "propos" in text:
        has_research_background = any(
            entry.category.value in {"project", "publication"} for entry in background_entries
        )
        if has_research_background:
            return (
                RequirementMatchStatus.partial_match,
                "You have recorded research/project background - confirm it fits this "
                "specific requirement.",
            )
        return (
            RequirementMatchStatus.needs_verification,
            "No recorded research background found - review this requirement manually.",
        )

    return (
        RequirementMatchStatus.needs_verification,
        "This requirement could not be automatically evaluated - please review it manually.",
    )
