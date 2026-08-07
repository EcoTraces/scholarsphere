from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import post_json
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource
from app.services.parsing import parse_date


class GrantsGovSource(OpportunitySource):
    source_code = "grants_gov"

    def __init__(self) -> None:
        self.search_url = f"{get_settings().grants_gov_base_url.rstrip('/')}/search2"

    async def search_raw(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        statuses: list[str] | None = None,
        agencies: list[str] | None = None,
        funding_categories: list[str] | None = None,
        eligibility_codes: list[str] | None = None,
        assistance_listing: str | None = None,
        opportunity_number: str | None = None,
    ) -> dict[str, Any]:
        _validate_pagination(page, page_size)
        payload = {
            "rows": page_size,
            "startRecordNum": (page - 1) * page_size,
            "keyword": keyword or "",
            "oppNum": opportunity_number or "",
            "eligibilities": "|".join(eligibility_codes or []),
            "agencies": "|".join(agencies or []),
            "oppStatuses": "|".join(statuses or ["posted", "forecasted"]),
            "aln": assistance_listing or "",
            "fundingCategories": "|".join(funding_categories or []),
        }
        return await post_json(
            self.search_url,
            json=payload,
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
        )

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        response = await self.search_raw(keyword=keyword, page=page, page_size=page_size)
        data = response.get("data")
        hits = data.get("oppHits", []) if isinstance(data, dict) else []
        normalized: list[NormalizedExternalOpportunity] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            try:
                normalized.append(self._normalize(hit))
            except ValidationError:
                continue
        return normalized

    async def collect_for_import(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity | dict[str, Any]]:
        """Retain malformed records so the import pipeline can audit failures."""
        response = await self.search_raw(keyword=keyword, page=page, page_size=page_size)
        data = response.get("data")
        hits = data.get("oppHits", []) if isinstance(data, dict) else []
        candidates: list[NormalizedExternalOpportunity | dict[str, Any]] = []
        for hit in hits:
            if not isinstance(hit, dict):
                continue
            try:
                candidates.append(self._normalize(hit))
            except ValidationError:
                candidates.append(
                    {
                        "source_code": self.source_code,
                        "external_id": str(hit.get("id") or hit.get("number") or ""),
                        "title": "",
                        "raw_payload": hit,
                    }
                )
        return candidates

    def _normalize(self, hit: dict[str, Any]) -> NormalizedExternalOpportunity:
        external_id = str(hit.get("id") or hit.get("number") or "").strip()
        number = str(hit.get("number") or "").strip() or None
        official_url = (
            f"https://www.grants.gov/search-results-detail/{quote(number, safe='')}"
            if number
            else None
        )
        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            external_reference=number,
            title=str(hit.get("title") or "Untitled opportunity").strip(),
            opportunity_type="grant",
            provider_name=str(
                hit.get("agencyName")
                or hit.get("agencyCode")
                or "United States Government"
            ).strip(),
            provider_code=str(hit.get("agencyCode") or "").strip() or None,
            country="United States",
            opening_date=parse_date(hit.get("openDate")),
            deadline=parse_date(hit.get("closeDate")),
            opportunity_status=str(hit.get("oppStatus") or "unknown").lower(),
            official_source_url=official_url,
            official_application_url=official_url,
            raw_payload=hit,
        )


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
