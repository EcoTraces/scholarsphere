"""Mastercard Foundation Scholars Program - a global initiative that has
committed over 58,000 scholarships, delivered entirely through partner
higher-education institutions rather than one central application. Every
other source in this project is (at most) one program per organization;
this is the first that legitimately produces one opportunity record per
*partner institution* from a single foundation-run index.

Previously investigated (docs/AUTHORITATIVE_SOURCES.md, "Sources
evaluated and deliberately not integrated") and left unintegrated because
the institution listing was a client-side widget with no server-rendered
fallback and no locatable underlying API - re-investigated 2026-09-05
after the foundation's site was restructured (the old `/where-to-apply/`
URL under `/all/scholars-program/` now 404s; the program lives at
`/en/what-we-do/our-programs/mastercard-foundation-scholars-program/`)
and the actual blocker resolved differently than expected: the listing's
data comes from a **plain static JSON asset**,
`/assets/json/institution.json` - a normal `GET`, no JavaScript execution
needed at all, confirmed via `curl` returning the real per-institution
data directly. `robots.txt` explicitly `Allow: /` for `User-agent:
ClaudeBot` (and `GPTBot`/`OAI-SearchBot`/`ChatGPT-User`).

That JSON mixes English and French locale duplicates of every institution
in one flat array (`__languageCode: "en"` vs `"fr"` - e.g. "Cape Town"
appears twice, once as itself and once as its French rendering "Le Cap")
- filtered to `__languageCode == "en"` only, which yields exactly 31
unique institutions with no duplicate slugs (live-verified 2026-09-05;
the foundation's own program page separately advertises "62 Global
partners" as a headline stat, but that figure spans every kind of
partner across the foundation's many programs, not just this specific
Scholars Program institution list - the 31 is what this adapter can
actually verify and extract, not the round headline number).

Deliberately does not fetch each institution's own detail page
(`.../where-to-apply/<slug>/`) or follow through to the institution's own
external site - out of proportion with what this adapter needs, the same
reasoning `erasmus_mundus_source.py` and `educationusa_source.py` already
document for not chasing their own per-row "more information" links. The
foundation's own institution detail page at that URL *is* the accurate,
stable "how to apply" record (it explicitly instructs the applicant to
apply through the institution directly and links to its site) - used
as-is for both `official_source_url` and `official_application_url`,
matching `uaeu_scholarships_source.py`'s same single-URL choice.

Every institution is extracted regardless of current `application_window`
("open"/"closed") - a program with no live currently-open cohort is still
a real, verifiable Mastercard Foundation Scholars Program partner
institution, and the field itself is recorded verbatim in `description`
and `raw_payload` rather than used to silently drop a record - matching
this project's "never invent, never silently filter" rule (see
docs/OPPORTUNITY_VERIFICATION_SYSTEM.md SS10).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError, get_html
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource

logger = logging.getLogger(__name__)

_PROVIDER_NAME = "The Mastercard Foundation"
_PROGRAM_NAME = "Mastercard Foundation Scholars Program"


def _first_country(fields: dict[str, Any]) -> str | None:
    countries = fields.get("country") or []
    for entry in countries:
        if isinstance(entry, dict) and entry.get("name"):
            return str(entry["name"])
    return None


def _build_description(fields: dict[str, Any]) -> str:
    parts: list[str] = []
    city = (fields.get("city") or "").strip()
    if city:
        parts.append(f"Location: {city}.")
    levels = []
    if fields.get("level_of_study_undergraduate"):
        levels.append("Undergraduate")
    if fields.get("level_of_study_postgraduate"):
        levels.append("Postgraduate")
    if levels:
        parts.append(f"Level of study: {', '.join(levels)}.")
    circumstances = []
    if fields.get("circumstances_refugees_displaced_persons"):
        circumstances.append("refugees and displaced persons")
    if fields.get("circumstances_disability"):
        circumstances.append("applicants with disabilities")
    if circumstances:
        parts.append(
            "Personal circumstances explicitly supported: "
            + " and ".join(circumstances) + "."
        )
    window = (fields.get("application_window") or "").strip().lower()
    if window == "open":
        parts.append("Applications are currently open at this institution.")
    elif window == "closed":
        parts.append("Applications are currently closed at this institution.")
    return " ".join(parts) or (
        f"A {_PROGRAM_NAME} partner institution. See the official page for current "
        "admissions details."
    )


class MastercardFoundationScholarsSource(OpportunitySource):
    source_code = "mastercard_foundation_scholars"

    def __init__(self) -> None:
        self.base_url = get_settings().mastercard_foundation_base_url.rstrip("/")

    async def collect(
        self, **_: object
    ) -> list[NormalizedExternalOpportunity]:
        json_url = f"{self.base_url}/assets/json/institution.json"
        try:
            raw_text = await get_html(json_url)
            payload = json.loads(raw_text)
        except ExternalAPIError as error:
            logger.warning(
                "%s_fetch_failed url=%s error=%s", self.source_code, json_url, error
            )
            return []
        except (json.JSONDecodeError, TypeError) as error:
            logger.warning(
                "%s_invalid_json url=%s error=%s", self.source_code, json_url, error
            )
            return []

        if not isinstance(payload, list):
            logger.warning(
                "%s_unexpected_payload_shape url=%s", self.source_code, json_url
            )
            return []

        where_to_apply_base = (
            f"{self.base_url}/en/what-we-do/our-programs/"
            "mastercard-foundation-scholars-program/where-to-apply"
        )

        opportunities: list[NormalizedExternalOpportunity] = []
        seen_slugs: set[str] = set()
        for entry in payload:
            if not isinstance(entry, dict) or entry.get("__languageCode") != "en":
                continue
            slug = entry.get("slug")
            name = entry.get("name")
            if not slug or not name or slug in seen_slugs:
                continue
            seen_slugs.add(slug)

            fields = entry.get("fields") or {}
            detail_url = f"{where_to_apply_base}/{slug}/"
            window = (fields.get("application_window") or "").strip().lower()

            try:
                opportunities.append(
                    NormalizedExternalOpportunity(
                        source_code=self.source_code,
                        external_id=detail_url,
                        title=f"{name} — {_PROGRAM_NAME}",
                        opportunity_type="scholarship",
                        provider_name=_PROVIDER_NAME,
                        country=_first_country(fields),
                        description=_build_description(fields),
                        opportunity_status="posted" if window != "closed" else "closed",
                        official_source_url=detail_url,
                        official_application_url=detail_url,
                        raw_payload={
                            "slug": slug,
                            "name": name,
                            "country": _first_country(fields),
                            "city": fields.get("city"),
                            "level_of_study_undergraduate": fields.get(
                                "level_of_study_undergraduate"
                            ),
                            "level_of_study_postgraduate": fields.get(
                                "level_of_study_postgraduate"
                            ),
                            "application_window": fields.get("application_window"),
                            "circumstances_refugees_displaced_persons": fields.get(
                                "circumstances_refugees_displaced_persons"
                            ),
                            "circumstances_disability": fields.get(
                                "circumstances_disability"
                            ),
                        },
                    )
                )
            except ValidationError as error:
                logger.warning(
                    "%s_normalize_failed slug=%r error=%s",
                    self.source_code,
                    slug,
                    error,
                )
                continue
        return opportunities

    async def collect_for_import(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        return await self.collect(keyword=keyword, page=page, page_size=page_size)
