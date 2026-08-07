from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError, post_json
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource
from app.services.parsing import parse_date, safe_float, sanitize_html

SORT_FIELDS = {"post_date", "close_date"}
SORT_DIRECTIONS = {"ascending", "descending"}


class SimplerGrantsSource(OpportunitySource):
    source_code = "simpler_grants"

    def __init__(self) -> None:
        settings = get_settings()
        configured_key = settings.simpler_grants_api_key
        self.api_key = (
            configured_key.get_secret_value()
            if hasattr(configured_key, "get_secret_value")
            else str(configured_key)
        )
        self.search_url = (
            f"{settings.simpler_grants_base_url.rstrip('/')}"
            "/v1/opportunities/search"
        )

    def _headers(self) -> dict[str, str]:
        if not self.api_key:
            raise ExternalAPIError("SIMPLER_GRANTS_API_KEY is not configured.")
        return {
            "X-API-Key": self.api_key,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    async def search_raw(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        statuses: list[str] | None = None,
        sort_field: str = "post_date",
        sort_direction: str = "descending",
        filters: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        _validate_pagination(page, page_size)
        if sort_field not in SORT_FIELDS or sort_direction not in SORT_DIRECTIONS:
            raise ValueError("Unsupported sort field or direction")
        merged_filters = {
            "opportunity_status": {
                "one_of": statuses or ["posted", "forecasted"]
            }
        }
        if filters:
            merged_filters.update(filters)
        payload = {
            "query": keyword or "",
            "filters": merged_filters,
            "pagination": {
                # Simpler.Grants.gov uses one-based page offsets.
                "page_offset": page,
                "page_size": page_size,
                "sort_order": [
                    {
                        "order_by": sort_field,
                        "sort_direction": sort_direction,
                    }
                ],
            },
        }
        return await post_json(self.search_url, json=payload, headers=self._headers())

    async def collect(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        statuses: list[str] | None = None,
        sort_field: str = "post_date",
        sort_direction: str = "descending",
    ) -> list[NormalizedExternalOpportunity]:
        response = await self.search_raw(
            keyword=keyword,
            page=page,
            page_size=page_size,
            statuses=statuses,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        data = response.get("data")
        if isinstance(data, dict):
            records = data.get("opportunities") or data.get("results") or []
        else:
            records = data or response.get("opportunities") or []
        normalized: list[NormalizedExternalOpportunity] = []
        if not isinstance(records, list):
            return normalized
        for record in records:
            if not isinstance(record, dict):
                continue
            try:
                normalized.append(self._normalize(record))
            except ValidationError:
                continue
        return normalized

    async def collect_for_import(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        statuses: list[str] | None = None,
        sort_field: str = "post_date",
        sort_direction: str = "descending",
    ) -> list[NormalizedExternalOpportunity | dict[str, Any]]:
        """Retain malformed records so the import pipeline can audit failures."""
        response = await self.search_raw(
            keyword=keyword,
            page=page,
            page_size=page_size,
            statuses=statuses,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        data = response.get("data")
        records = (
            data.get("opportunities") or data.get("results") or []
            if isinstance(data, dict)
            else data or response.get("opportunities") or []
        )
        candidates: list[NormalizedExternalOpportunity | dict[str, Any]] = []
        if not isinstance(records, list):
            return candidates
        for record in records:
            if not isinstance(record, dict):
                continue
            try:
                candidates.append(self._normalize(record))
            except ValidationError:
                candidates.append(
                    {
                        "source_code": self.source_code,
                        "external_id": str(record.get("opportunity_id") or ""),
                        "title": "",
                        "raw_payload": record,
                    }
                )
        return candidates

    def _normalize(self, record: dict[str, Any]) -> NormalizedExternalOpportunity:
        external_id = str(record.get("opportunity_id") or "").strip()
        reference = str(record.get("opportunity_number") or "").strip() or None
        official_url = (
            "https://simpler.grants.gov/opportunity/"
            + quote(external_id, safe="")
            if external_id
            else None
        )
        floor = safe_float(record.get("award_floor"))
        ceiling = safe_float(record.get("award_ceiling"))
        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            external_reference=reference,
            title=str(
                record.get("opportunity_title") or "Untitled opportunity"
            ).strip(),
            opportunity_type="grant",
            provider_name=str(
                record.get("agency_name")
                or record.get("agency_code")
                or "United States Government"
            ).strip(),
            provider_code=str(record.get("agency_code") or "").strip() or None,
            country="United States",
            description=sanitize_html(
                record.get("summary_description")
                or record.get("summary")
                or record.get("description")
            ),
            opening_date=parse_date(record.get("post_date")),
            deadline=parse_date(record.get("close_date")),
            opportunity_status=str(record.get("opportunity_status") or "unknown").lower(),
            award_floor=floor,
            award_ceiling=ceiling,
            currency="USD",
            official_source_url=official_url,
            official_application_url=official_url,
            raw_payload=record,
        )


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
