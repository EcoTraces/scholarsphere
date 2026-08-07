from abc import ABC, abstractmethod

from app.schemas.external_opportunity import NormalizedExternalOpportunity


class OpportunitySource(ABC):
    """Contract implemented by external opportunity collectors."""

    source_code: str

    @abstractmethod
    async def collect(
        self,
        *,
        keyword: str | None = None,
        page: int = 1,
        page_size: int = 25,
    ) -> list[NormalizedExternalOpportunity]:
        raise NotImplementedError
