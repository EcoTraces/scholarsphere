"""USAJOBS (U.S. Office of Personnel Management) collector.

USAJOBS is the official employment site for the U.S. federal government,
with a free, self-service, key-based public API - see
https://developer.usajobs.gov/. Authentication requires three headers:
``Host: data.usajobs.gov``, ``User-Agent: <the email you registered with>``,
and ``Authorization-Key: <your key>``. The request shape (``Keyword``,
``ResultsPerPage``, ``Page``, ``HiringPath`` query parameters against
``https://data.usajobs.gov/api/search``) is confirmed from official
documentation and third-party integration guides consulted directly.

CAVEAT: the exact response JSON field names below
(``SearchResult.SearchResultItems[].MatchedObjectDescriptor.*``) reflect
USAJOBS' long-stable, widely-documented schema, but this adapter has not
been exercised against a live authenticated response in this environment
(no outbound internet + no registered API key). Parsing is written
defensively - unrecognized/missing fields degrade to ``None`` rather than
raising - but this source should be smoke-tested with a real
``USAJOBS_API_KEY`` before it is enabled for scheduled sync.
"""

from typing import Any

from pydantic import ValidationError

from app.core.config import get_settings
from app.core.http_client import ExternalAPIError, get_json
from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.base_source import OpportunitySource
from app.services.parsing import first_value, nested_value, parse_date, sanitize_html

STUDENT_HIRING_PATH_HINTS = ("student", "recent grad", "intern")


class UsaJobsSource(OpportunitySource):
    source_code = "usajobs"

    def __init__(self) -> None:
        settings = get_settings()
        self.search_url = settings.usajobs_base_url
        self.api_key = settings.usajobs_api_key.get_secret_value()
        self.user_agent = settings.usajobs_user_agent

    def _headers(self) -> dict[str, str]:
        if not self.api_key or not self.user_agent:
            raise ExternalAPIError(
                "USAJOBS_API_KEY / USAJOBS_USER_AGENT is not configured."
            )
        return {
            "Host": "data.usajobs.gov",
            "User-Agent": self.user_agent,
            "Authorization-Key": self.api_key,
            "Accept": "application/json",
        }

    async def search_raw(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        hiring_paths: list[str] | None = None,
    ) -> dict[str, Any]:
        _validate_pagination(page, page_size)
        params: dict[str, str] = {
            "ResultsPerPage": str(page_size),
            "Page": str(page),
        }
        if keyword:
            params["Keyword"] = keyword
        if hiring_paths:
            params["HiringPath"] = ";".join(hiring_paths)
        return await get_json(
            self.search_url,
            params=params,
            headers=self._headers(),
            override_user_agent=False,
        )

    async def collect(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        hiring_paths: list[str] | None = None,
    ) -> list[NormalizedExternalOpportunity]:
        response = await self.search_raw(
            keyword=keyword, page=page, page_size=page_size, hiring_paths=hiring_paths
        )
        items = nested_value(response, "SearchResult.SearchResultItems", default=[])
        normalized: list[NormalizedExternalOpportunity] = []
        if not isinstance(items, list):
            return normalized
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                normalized.append(self._normalize(item))
            except ValidationError:
                continue
        return normalized

    async def collect_for_import(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
        hiring_paths: list[str] | None = None,
    ) -> list[NormalizedExternalOpportunity | dict[str, Any]]:
        """Retain malformed records so the import pipeline can audit failures."""
        response = await self.search_raw(
            keyword=keyword, page=page, page_size=page_size, hiring_paths=hiring_paths
        )
        items = nested_value(response, "SearchResult.SearchResultItems", default=[])
        candidates: list[NormalizedExternalOpportunity | dict[str, Any]] = []
        if not isinstance(items, list):
            return candidates
        for item in items:
            if not isinstance(item, dict):
                continue
            try:
                candidates.append(self._normalize(item))
            except ValidationError:
                descriptor = item.get("MatchedObjectDescriptor")
                external_id = str(
                    item.get("MatchedObjectId")
                    or (descriptor.get("PositionID") if isinstance(descriptor, dict) else "")
                    or ""
                )
                candidates.append(
                    {
                        "source_code": self.source_code,
                        "external_id": external_id,
                        "title": "",
                        "raw_payload": item,
                    }
                )
        return candidates

    def _normalize(self, item: dict[str, Any]) -> NormalizedExternalOpportunity:
        descriptor = item.get("MatchedObjectDescriptor")
        descriptor = descriptor if isinstance(descriptor, dict) else {}
        external_id = str(
            item.get("MatchedObjectId") or descriptor.get("PositionID") or ""
        ).strip()
        title = str(descriptor.get("PositionTitle") or "Untitled opportunity").strip()
        provider_name = str(
            descriptor.get("OrganizationName") or descriptor.get("DepartmentName") or "U.S. federal government"
        ).strip()

        apply_url = first_value(descriptor.get("ApplyURI"))
        source_url = descriptor.get("PositionURI") or apply_url

        hiring_path = nested_value(
            descriptor, "UserArea.Details.HiringPath", "HiringPath", default=[]
        )
        hiring_path_text = " ".join(str(value) for value in hiring_path) if isinstance(
            hiring_path, list
        ) else str(hiring_path or "")
        opportunity_type = (
            "internship"
            if any(hint in hiring_path_text.lower() for hint in STUDENT_HIRING_PATH_HINTS)
            else "job"
        )

        deadline = parse_date(descriptor.get("ApplicationCloseDate"))
        opening = parse_date(
            descriptor.get("PositionStartDate") or descriptor.get("PublicationStartDate")
        )
        description = sanitize_html(
            nested_value(descriptor, "UserArea.Details.JobSummary", "QualificationSummary")
        )

        return NormalizedExternalOpportunity(
            source_code=self.source_code,
            external_id=external_id,
            title=title,
            opportunity_type=opportunity_type,
            provider_name=provider_name,
            country="United States",
            description=description,
            opening_date=opening,
            deadline=deadline,
            opportunity_status="posted",
            official_source_url=source_url,
            official_application_url=apply_url or source_url,
            raw_payload=item,
        )


def _validate_pagination(page: int, page_size: int) -> None:
    if page < 1:
        raise ValueError("page must be at least 1")
    if not 1 <= page_size <= 100:
        raise ValueError("page_size must be between 1 and 100")
