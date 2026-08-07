from collections.abc import Iterator

import pytest

from app.core.config import get_settings


@pytest.fixture(autouse=True)
def clear_settings_cache() -> Iterator[None]:
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def grants_hit() -> dict[str, object]:
    return {
        "id": "123",
        "number": "ABC-2026-001",
        "title": "Education Innovation Grant",
        "agencyCode": "ED",
        "agencyName": "Department of Education",
        "openDate": "07/01/2026",
        "closeDate": "2026-08-31",
        "oppStatus": "posted",
    }
