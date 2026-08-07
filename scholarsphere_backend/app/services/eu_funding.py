import html
import json
from typing import Any
from urllib.parse import quote

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import post_json
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource
from app.services.parsing import (
    as_list,
    earliest_date,
    first_value,
    nested_value,
    parse_date,
    safe_float,
    safe_https_url,
    sanitize_html,
)


class EUFundingSource(OpportunitySource):
    source_code = "eu_funding_tenders"

    def __init__(self) -> None:
        settings = get_settings()
        self.search_url = settings.eu_funding_api_url
        configured_key = settings.eu_funding_api_key
        self.api_key = (
            configured_key.get_secret_value()
            if hasattr(configured_key, "get_secret_value")
            else str(configured_key)
        )
        self.type_filters = list(settings.eu_funding_type_codes)
        self.status_filters = list(settings.eu_funding_status_codes)
        self.type_codes = dict(settings.eu_funding_type_mappings)
        self.status_codes = dict(settings.eu_funding_status_mappings)
        self.programme_period = settings.eu_funding_programme_period
        self.language = settings.eu_funding_language
        self.display_fields = list(settings.eu_funding_display_fields)

    async def search_raw(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        type_codes: list[str] | None = None,
        status_codes: list[str] | None = None,
        programme_period: str | None = None,
        language: str | None = None,
        sort_field: str = "startDate",
        sort_direction: str = "DESC",
    ) -> dict[str, Any]:
        _validate_pagination(page, page_size)
        if sort_field not in {"startDate", "deadlineDate"}:
            raise ValueError("Unsupported EU sort field")
        normalized_direction = sort_direction.upper()
        if normalized_direction not in {"ASC", "DESC"}:
            raise ValueError("Unsupported EU sort direction")

        selected_types = type_codes or self.type_filters
        selected_statuses = status_codes or self.status_filters
        if not set(selected_types).issubset(self.type_codes):
            raise ValueError("Unsupported EU type code")
        if not set(selected_statuses).issubset(self.status_codes):
            raise ValueError("Unsupported EU status code")

        query = {
            "bool": {
                "must": [
                    {"terms": {"type": selected_types}},
                    {"terms": {"status": selected_statuses}},
                    {
                        "term": {
                            "programmePeriod": (
                                programme_period or self.programme_period
                            )
                        }
                    },
                ]
            }
        }
        files = {
            "query": (None, json.dumps(query), "application/json"),
            "languages": (
                None,
                json.dumps([language or self.language]),
                "application/json",
            ),
            "sort": (
                None,
                json.dumps(
                    {"field": sort_field, "order": normalized_direction}
                ),
                "application/json",
            ),
            "displayFields": (
                None,
                json.dumps(self.display_fields),
                "application/json",
            ),
        }
        return await post_json(
            self.search_url,
            params={
                "apiKey": self.api_key,
                "text": keyword or "",
                "pageSize": page_size,
                "pageNumber": page,
            },
            files=files,
            headers={"Accept": "application/json"},
        )

    async def collect(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        type_codes: list[str] | None = None,
        status_codes: list[str] | None = None,
        programme_period: str | None = None,
        language: str | None = None,
        sort_field: str = "startDate",
        sort_direction: str = "DESC",
    ) -> list[NormalizedExternalOpportunity]:
        response = await self.search_raw(
            keyword=keyword,
            page=page,
            page_size=page_size,
            type_codes=type_codes,
            status_codes=status_codes,
            programme_period=programme_period,
            language=language,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        normalized: list[NormalizedExternalOpportunity] = []
        for record in _records_from_response(response):
            if not isinstance(record, dict):
                continue
            try:
                normalized.append(self._normalize(record))
            except (ValidationError, TypeError, ValueError):
                continue
        return normalized

    async def collect_for_import(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        type_codes: list[str] | None = None,
        status_codes: list[str] | None = None,
        programme_period: str | None = None,
        language: str | None = None,
        sort_field: str = "startDate",
        sort_direction: str = "DESC",
    ) -> list[NormalizedExternalOpportunity | dict[str, Any]]:
        """Retain malformed records so the import pipeline can audit failures."""
        response = await self.search_raw(
            keyword=keyword,
            page=page,
            page_size=page_size,
            type_codes=type_codes,
            status_codes=status_codes,
            programme_period=programme_period,
            language=language,
            sort_field=sort_field,
            sort_direction=sort_direction,
        )
        candidates: list[NormalizedExternalOpportunity | dict[str, Any]] = []
        for record in _records_from_response(response):
            if not isinstance(record, dict):
                continue
            try:
                candidates.append(self._normalize(record))
            except (ValidationError, TypeError, ValueError):
                metadata = _metadata_dict(record.get("metadata")) or record
                candidates.append(
                    {
                        "source_code": self.source_code,
                        "external_id": _text(
                            nested_value(metadata, "identifier", "callccm2Id"),
                            fallback=record.get("id"),
                        ),
                        "title": "",
                        "raw_payload": record,
                    }
                )
        return candidates

    def _normalize(
        self,
        record: dict[str, Any],
    ) -> NormalizedExternalOpportunity:
        metadata = _metadata_dict(record.get("metadata")) or record

        def field(name: str, *fallbacks: str) -> Any:
            return nested_value(metadata, name, *fallbacks)

        external_id = _text(
            field("identifier", "callccm2Id"),
            fallback=record.get("id"),
        )
        reference = _text(field("reference")) or None
        type_code = _text(field("type"))
        status_code = _text(field("status"))
        floor, ceiling = _budget_range(field("budgetOverview"))
        provided_url = safe_https_url(
            _text(nested_value(
                record,
                "url",
                "resultUrl",
                "metadata.url",
                "metadata.resultUrl",
            ))
        )
        topic_key = reference or external_id
        fallback_url = (
            "https://ec.europa.eu/info/funding-tenders/opportunities/"
            "portal/screen/opportunities/topic-details/"
            + quote(topic_key, safe="")
            if topic_key
            else None
        )
        mapped_type = self.type_codes.get(
            type_code,
            "funding_opportunity",
        )
        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            external_reference=reference,
            title=_text(field("title")) or "Untitled opportunity",
            opportunity_type=mapped_type,
            provider_name=_text(field("caName")) or "European Commission",
            country="European Union",
            description=sanitize_html(_text(field("description"))),
            opening_date=parse_date(_text(field("startDate"))),
            deadline=earliest_date(field("deadlineDate")),
            opportunity_status=self.status_codes.get(
                status_code,
                status_code.lower() or "unknown",
            ),
            funding_type="grant" if mapped_type == "grant" else None,
            award_floor=floor,
            award_ceiling=ceiling,
            currency="EUR",
            official_source_url=provided_url or fallback_url,
            official_application_url=provided_url or fallback_url,
            raw_payload=record,
        )


def _budget_range(value: Any) -> tuple[float | None, float | None]:
    numbers: list[float] = []
    for item in as_list(value):
        if isinstance(item, dict):
            for key in (
                "amount",
                "value",
                "budget",
                "totalBudget",
                "min",
                "max",
            ):
                number = safe_float(item.get(key))
                if number is not None:
                    numbers.append(number)
        else:
            number = safe_float(item)
            if number is not None:
                numbers.append(number)
    return (min(numbers), max(numbers)) if numbers else (None, None)


def _metadata_dict(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    result: dict[str, Any] = {}
    for item in as_list(value):
        if not isinstance(item, dict):
            continue
        key = item.get("name") or item.get("field") or item.get("key")
        if key:
            result[str(key)] = item.get("value", item.get("values"))
    return result


def _text(value: Any, *, fallback: Any = None) -> str:
    candidate = first_value(value)
    if candidate in (None, ""):
        candidate = fallback
    if isinstance(candidate, dict):
        for key in ("value", "label", "name", "text"):
            if key in candidate:
                return _text(candidate[key])
        return ""
    return html.unescape(str(candidate or "")).strip()


def _records_from_response(response: dict[str, Any]) -> list[Any]:
    value = nested_value(
        response,
        "results",
        "data.results",
        "data.items",
        "items",
        default=[],
    )
    if isinstance(value, list):
        return value
    if isinstance(value, dict):
        for key in ("results", "items", "content"):
            nested = value.get(key)
            if isinstance(nested, list):
                return nested
    return []


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
