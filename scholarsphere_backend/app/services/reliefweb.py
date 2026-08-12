"""ReliefWeb (UN OCHA) job and training collectors.

ReliefWeb is the UN Office for the Coordination of Humanitarian Affairs'
official humanitarian information portal. Its API is public, free, and
documented at https://apidoc.reliefweb.int/ - field names here
(``title``, ``country.name``, ``source.name``, ``date.closing``,
``date.registration``, ``date.start``, ``date.end``, ``url``) were
confirmed directly against that documentation, not guessed.

Since 1 November 2025 ReliefWeb requires a pre-approved ``appname`` on every
request (see ``RELIEFWEB_APPNAME``); it is an application identifier, not a
secret credential.
"""

from datetime import date as date_type
from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError, post_json
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource
from app.services.parsing import (
    as_list,
    first_value,
    nested_value,
    parse_date,
    sanitize_html,
)


class _ReliefWebSource(OpportunitySource):
    """Shared request/normalization logic for the jobs and training endpoints."""

    endpoint: str
    opportunity_type: str

    def __init__(self) -> None:
        settings = get_settings()
        self.base_url = f"{settings.reliefweb_base_url.rstrip('/')}/{self.endpoint}"
        self.appname = settings.reliefweb_appname

    def _require_appname(self) -> str:
        if not self.appname:
            raise ExternalAPIError("RELIEFWEB_APPNAME is not configured.")
        return self.appname

    async def search_raw(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> dict[str, Any]:
        _validate_pagination(page, page_size)
        body: dict[str, Any] = {
            "fields": {"include": list(self.include_fields)},
            "sort": ["date.created:desc"],
            "limit": page_size,
            "offset": (page - 1) * page_size,
        }
        if keyword:
            body["query"] = {"value": keyword, "operator": "AND"}
        return await post_json(
            self.base_url,
            json=body,
            params={"appname": self._require_appname()},
            headers={"Content-Type": "application/json", "Accept": "application/json"},
        )

    async def collect(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity]:
        response = await self.search_raw(keyword=keyword, page=page, page_size=page_size)
        items = response.get("data") if isinstance(response, dict) else None
        normalized: list[NormalizedExternalOpportunity] = []
        for item in as_list(items):
            if not isinstance(item, dict):
                continue
            try:
                normalized.append(self._normalize(item))
            except ValidationError:
                continue
        return normalized

    async def collect_for_import(
        self, *, keyword: str | None = None, page: int = 1, page_size: int = 25
    ) -> list[NormalizedExternalOpportunity | dict[str, Any]]:
        """Retain malformed records so the import pipeline can audit failures."""
        response = await self.search_raw(keyword=keyword, page=page, page_size=page_size)
        items = response.get("data") if isinstance(response, dict) else None
        candidates: list[NormalizedExternalOpportunity | dict[str, Any]] = []
        for item in as_list(items):
            if not isinstance(item, dict):
                continue
            try:
                candidates.append(self._normalize(item))
            except ValidationError:
                candidates.append(
                    {
                        "source_code": self.source_code,
                        "external_id": str(item.get("id") or ""),
                        "title": "",
                        "raw_payload": item,
                    }
                )
        return candidates

    include_fields: tuple[str, ...] = (
        "title",
        "url",
        "url_alias",
        "body",
        "source",
        "country",
        "city",
        "date",
        "type",
    )

    def _deadline_field(self, fields: dict[str, Any]) -> Any:
        raise NotImplementedError

    def _normalize(self, item: dict[str, Any]) -> NormalizedExternalOpportunity:
        fields = item.get("fields") if isinstance(item.get("fields"), dict) else {}
        external_id = str(item.get("id") or "").strip()
        title = str(fields.get("title") or "Untitled opportunity").strip()

        source_entries = as_list(fields.get("source"))
        provider_name = (
            str(source_entries[0].get("name")).strip()
            if source_entries and isinstance(source_entries[0], dict) and source_entries[0].get("name")
            else "ReliefWeb partner organization"
        )

        country_entries = as_list(fields.get("country"))
        country = (
            str(country_entries[0].get("name")).strip()
            if country_entries and isinstance(country_entries[0], dict) and country_entries[0].get("name")
            else None
        )

        url = first_value(fields.get("url")) or first_value(fields.get("url_alias"))
        deadline = parse_date(self._deadline_field(fields))
        opening = parse_date(nested_value(fields, "date.created"))
        opportunity_status = (
            "closed" if deadline is not None and deadline < date_type.today() else "posted"
        )
        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            title=title,
            opportunity_type=self.opportunity_type,
            provider_name=provider_name,
            country=country,
            description=sanitize_html(fields.get("body")),
            opening_date=opening,
            deadline=deadline,
            opportunity_status=opportunity_status,
            official_source_url=url,
            official_application_url=url,
            raw_payload=item,
        )


class ReliefWebJobsSource(_ReliefWebSource):
    source_code = "reliefweb_jobs"
    endpoint = "jobs"
    opportunity_type = "internship"

    def _deadline_field(self, fields: dict[str, Any]) -> Any:
        return nested_value(fields, "date.closing")


class ReliefWebTrainingSource(_ReliefWebSource):
    source_code = "reliefweb_training"
    endpoint = "training"
    opportunity_type = "training"

    def _deadline_field(self, fields: dict[str, Any]) -> Any:
        return nested_value(fields, "date.registration")


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
