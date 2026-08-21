"""Port of lib/features/search/domain/opportunity_filter.dart,

opportunity_search.dart, and lib/features/search_index/data/
demo_search_index_repository.dart's matching/scoring/faceting logic.
Keep the two in sync. Operates on opaque opportunity snapshot dicts
(camelCase keys, as sent by the Flutter client) rather than a typed
model, matching how SearchIndexEntry stores them.
"""

import re
from datetime import datetime, timezone
from typing import Any

_GEOGRAPHY: dict[str, str] = {
    "united kingdom": "europe",
    "germany": "europe",
    "france": "europe",
    "italy": "europe",
    "canada": "northAmerica",
    "united states": "northAmerica",
    "mexico": "northAmerica",
    "brazil": "latinAmerica",
    "argentina": "latinAmerica",
    "ghana": "africa",
    "nigeria": "africa",
    "kenya": "africa",
    "south africa": "africa",
    "china": "asia",
    "japan": "asia",
    "india": "asia",
    "united arab emirates": "middleEast",
    "qatar": "middleEast",
    "saudi arabia": "middleEast",
    "australia": "australiaOceania",
    "new zealand": "australiaOceania",
    "remote": "globalOnline",
    "global": "globalOnline",
    "online": "globalOnline",
}

_SYNONYMS: dict[str, set[str]] = {
    "scholarship": {"funding", "award", "grant"},
    "masters": {"master", "graduate", "postgraduate"},
    "phd": {"doctorate", "doctoral"},
    "online": {"remote", "virtual"},
}

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _region_matches(country: str, requested: str) -> bool:
    normalized = country.strip().lower()
    if requested == "canada":
        return normalized == "canada"
    return _GEOGRAPHY.get(normalized) == requested


def _deadline_matches(deadline: datetime, window: str, now: datetime) -> bool:
    days = {"sevenDays": 7, "thirtyDays": 30, "ninetyDays": 90}.get(window)
    if days is None:
        return True
    from datetime import timedelta

    return deadline > now and deadline <= now + timedelta(days=days)


def _contains(source: str, expected: str) -> bool:
    return expected.lower() in source.lower()


def _contains_any(source: list[str], expected: str, allow_all: bool = False) -> bool:
    return any(
        (allow_all and _contains(value, "all nationalities")) or _contains(value, expected)
        for value in source
    )


def _optional_text(source: str, expected: str | None) -> bool:
    return expected is None or not expected.strip() or _contains(source, expected.strip())


def _optional_list(source: list[str], expected: str | None) -> bool:
    return expected is None or not expected.strip() or _contains_any(source, expected)


def _parse_dt(value: Any) -> datetime | None:
    if value is None:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00")) if isinstance(value, str) else value
    return parsed if parsed.tzinfo is not None else parsed.replace(tzinfo=timezone.utc)


def matches(data: dict[str, Any], opportunity_filter: dict[str, Any], now: datetime) -> bool:
    if opportunity_filter.get("type") and data.get("type") != opportunity_filter["type"]:
        return False
    if not _optional_text(data.get("hostCountry", ""), opportunity_filter.get("country")):
        return False
    region = opportunity_filter.get("region")
    if region and not _region_matches(data.get("hostCountry", ""), region):
        return False
    provider_filter = opportunity_filter.get("provider")
    if not _optional_text(
        data.get("provider", ""), provider_filter
    ) and not _optional_text(data.get("hostInstitution", ""), provider_filter):
        return False
    if not _optional_list(data.get("fieldsOfStudy", []), opportunity_filter.get("field")):
        return False
    if not _optional_list(data.get("studyLevels", []), opportunity_filter.get("studyLevel")):
        return False
    funding_filter = opportunity_filter.get("funding")
    if funding_filter and data.get("funding") != funding_filter:
        return False
    if opportunity_filter.get("noApplicationFee") and (data.get("applicationFee") or 0) != 0:
        return False
    eligible_nationality = opportunity_filter.get("eligibleNationality")
    if eligible_nationality and not _contains_any(
        data.get("eligibleNationalities", []), eligible_nationality, allow_all=True
    ):
        return False
    deadline = _parse_dt(data.get("deadline"))
    if deadline is not None and not _deadline_matches(
        deadline, opportunity_filter.get("deadlineWindow", "any"), now
    ):
        return False
    delivery_format = opportunity_filter.get("deliveryFormat")
    if delivery_format and data.get("deliveryFormat") != delivery_format:
        return False
    age = opportunity_filter.get("applicantAge")
    if age is not None:
        minimum_age = data.get("minimumAge")
        maximum_age = data.get("maximumAge")
        if (minimum_age is not None and age < minimum_age) or (
            maximum_age is not None and age > maximum_age
        ):
            return False
    experience = opportunity_filter.get("availableWorkExperienceYears")
    required_experience = data.get("workExperienceYearsRequired")
    if experience is not None and required_experience is not None and experience < required_experience:
        return False
    if not _optional_list(data.get("languageRequirements", []), opportunity_filter.get("language")):
        return False
    if opportunity_filter.get("verifiedOnly", True) and data.get("verificationStatus") != "verified":
        return False
    availability = opportunity_filter.get("availability", "open")
    if availability == "open" and (deadline is None or deadline <= now):
        return False
    if availability == "closed" and deadline is not None and deadline > now:
        return False
    return True


def tokenize(value: str) -> set[str]:
    return set(_TOKEN_RE.findall(value.lower()))


def expand(terms: set[str]) -> set[str]:
    expanded = set(terms)
    for term in terms:
        for key, synonyms in _SYNONYMS.items():
            if term == key or term in synonyms:
                expanded.add(key)
                expanded.update(synonyms)
    return expanded


def tolerance(term: str) -> int:
    if len(term) >= 7:
        return 2
    if len(term) >= 4:
        return 1
    return 0


def levenshtein(left: str, right: str) -> int:
    previous = list(range(len(right) + 1))
    for i, left_char in enumerate(left):
        diagonal = previous[0]
        previous[0] = i + 1
        for j, right_char in enumerate(right):
            old = previous[j + 1]
            previous[j + 1] = (
                diagonal if left_char == right_char else 1 + min(diagonal, previous[j], old)
            )
            diagonal = old
    return previous[-1]


def score(
    data: dict[str, Any],
    terms: set[str],
    eligibility: int,
    source_trust: int,
    now: datetime,
) -> tuple[float, list[str]]:
    fields: list[tuple[str, float]] = [
        (data.get("title", ""), 12),
        (data.get("provider", ""), 8),
        (data.get("hostInstitution", ""), 7),
        (data.get("hostCountry", ""), 5),
        (" ".join(data.get("fieldsOfStudy", [])), 6),
        (data.get("summary", ""), 3),
        (" ".join(data.get("eligibilityRequirements", [])), 2),
    ]
    relevance = 0.0
    matched: set[str] = set()
    for term in terms:
        for field_value, weight in fields:
            field_tokens = tokenize(field_value)
            if any(
                token == term or levenshtein(token, term) <= tolerance(term)
                for token in field_tokens
            ):
                relevance += weight
                matched.add(term)
    if terms and not matched:
        return 0.0, []
    ranking = relevance
    if data.get("verificationStatus") == "verified":
        ranking += 30
    deadline = _parse_dt(data.get("deadline"))
    if deadline is not None and deadline > now:
        ranking += 18
    ranking += eligibility * 0.2
    ranking += source_trust * 0.12
    last_verified_at = _parse_dt(data.get("lastVerifiedAt"))
    if last_verified_at is not None:
        age_days = (now - last_verified_at).days
        ranking += max(0.0, min(15.0, 15 - age_days / 30))
    if deadline is not None:
        days_to_deadline = (deadline - now).days
        if 7 <= days_to_deadline <= 90:
            ranking += 8
    return ranking, sorted(matched)


def facets(opportunities: list[dict[str, Any]]) -> dict[str, dict[str, int]]:
    countries: dict[str, int] = {}
    funding: dict[str, int] = {}
    study_levels: dict[str, int] = {}
    institutions: dict[str, int] = {}

    def bump(bucket: dict[str, int], key: str) -> None:
        if key:
            bucket[key] = bucket.get(key, 0) + 1

    for item in opportunities:
        bump(countries, item.get("hostCountry", ""))
        bump(funding, item.get("funding", ""))
        bump(institutions, item.get("hostInstitution", ""))
        for level in item.get("studyLevels", []):
            bump(study_levels, level)
    return {
        "countries": countries,
        "funding": funding,
        "studyLevels": study_levels,
        "institutions": institutions,
    }


def no_result_suggestions(index_values: list[dict[str, Any]], query: str) -> list[str]:
    terms = tokenize(query)
    candidates: set[str] = set()
    for item in index_values:
        candidates.update(item.get("fieldsOfStudy", []))
        if item.get("hostCountry"):
            candidates.add(item["hostCountry"])

    def min_distance(value: str) -> int:
        if not terms:
            return 0
        return min(levenshtein(value.lower(), term) for term in terms)

    return sorted(candidates, key=min_distance)[:5]


def autocomplete(index_values: list[dict[str, Any]], prefix: str, limit: int) -> list[str]:
    normalized = prefix.strip().lower()
    if not normalized:
        return []
    candidates: set[str] = set()
    for item in index_values:
        candidates.add(item.get("title", ""))
        candidates.add(item.get("provider", ""))
        candidates.add(item.get("hostInstitution", ""))
        candidates.add(item.get("hostCountry", ""))
        candidates.update(item.get("fieldsOfStudy", []))
    matching = [value for value in candidates if value and normalized in value.lower()]
    matching.sort(key=lambda value: (not value.lower().startswith(normalized), value))
    return matching[:limit]
