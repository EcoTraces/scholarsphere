import math
from urllib.parse import urlparse

from app.models.source_registry import ReliabilityLevel, SourceRegistryEntry

_BASE_SCORE: dict[ReliabilityLevel, int] = {
    ReliabilityLevel.a: 95,
    ReliabilityLevel.b: 85,
    ReliabilityLevel.c: 75,
    ReliabilityLevel.d: 62,
    ReliabilityLevel.e: 42,
    ReliabilityLevel.f: 10,
}


def normalize_domain(value: str) -> str:
    parsed = urlparse(value if "://" in value else f"https://{value}")
    host = (parsed.hostname or "").lower()
    return host[4:] if host.startswith("www.") else host


def _dart_round(value: float) -> int:
    """Round half away from zero, matching Dart's `num.round()`."""
    return math.floor(value + 0.5) if value >= 0 else math.ceil(value - 0.5)


def compute_trust_score(
    *,
    trust_level: ReliabilityLevel,
    correction_count: int,
    rejection_count: int,
    accuracy_rate: float,
) -> int:
    base = _BASE_SCORE[trust_level]
    value = (
        base
        - correction_count * 3
        - rejection_count * 5
        + _dart_round((accuracy_rate - 0.8) * 20)
    )
    return max(0, min(100, value))


def score_for_entry(entry: SourceRegistryEntry, *, trust_level: ReliabilityLevel | None = None) -> int:
    return compute_trust_score(
        trust_level=trust_level or entry.trust_level,
        correction_count=entry.correction_count,
        rejection_count=entry.rejection_count,
        accuracy_rate=entry.accuracy_rate,
    )
