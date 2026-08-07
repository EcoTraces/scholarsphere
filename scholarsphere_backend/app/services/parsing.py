import hashlib
import html
import json
import re
import unicodedata
from datetime import UTC, date, datetime
from typing import Any
from urllib.parse import urlparse

import bleach
from dateutil import parser as date_parser

SAFE_HTML_TAGS = ["p", "br", "strong", "em", "ul", "ol", "li", "a"]
SAFE_HTML_ATTRIBUTES = {"a": ["href", "title", "rel"]}
UNSAFE_BLOCK_PATTERN = re.compile(
    r"<(script|style|iframe|object|form)\b[^>]*>.*?</\1\s*>",
    flags=re.IGNORECASE | re.DOTALL,
)


def utc_now() -> datetime:
    return datetime.now(UTC)


def parse_date(value: Any) -> date | None:
    value = first_value(value)
    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    try:
        return date_parser.parse(str(value)).date()
    except (TypeError, ValueError, OverflowError):
        return None


def first_value(value: Any) -> Any:
    if isinstance(value, (list, tuple)):
        return value[0] if value else None
    return value


def as_list(value: Any) -> list[Any]:
    if value is None:
        return []
    return list(value) if isinstance(value, (list, tuple, set)) else [value]


def safe_float(value: Any) -> float | None:
    value = first_value(value)
    if isinstance(value, dict):
        value = next(
            (value[key] for key in ("value", "amount", "total") if key in value),
            None,
        )
    if value in (None, "") or isinstance(value, bool):
        return None
    try:
        return float(
            str(value)
            .replace(",", "")
            .replace("\N{EURO SIGN}", "")
            .replace("$", "")
            .strip()
        )
    except (TypeError, ValueError):
        return None


def nested_value(data: Any, *paths: str, default: Any = None) -> Any:
    if not isinstance(data, dict):
        return default
    for path in paths:
        current: Any = data
        for part in path.split("."):
            if not isinstance(current, dict) or part not in current:
                current = None
                break
            current = current[part]
        if current is not None:
            return current
    return default


def sanitize_html(value: Any) -> str | None:
    if value in (None, ""):
        return None
    decoded = html.unescape(str(first_value(value)))
    decoded = UNSAFE_BLOCK_PATTERN.sub("", decoded)
    cleaned = bleach.clean(
        decoded,
        tags=SAFE_HTML_TAGS,
        attributes=SAFE_HTML_ATTRIBUTES,
        protocols=["https"],
        strip=True,
    )
    return bleach.linkify(
        cleaned,
        callbacks=[bleach.callbacks.nofollow, _require_https_link],
        skip_tags=["pre", "code"],
    ).strip() or None


def _require_https_link(attrs: dict[tuple[str | None, str], str], new: bool = False):
    href_key = (None, "href")
    if href_key in attrs and not attrs[href_key].lower().startswith("https://"):
        return None
    attrs[(None, "rel")] = "nofollow noopener noreferrer"
    return attrs


def safe_https_url(value: Any) -> str | None:
    value = first_value(value)
    if not isinstance(value, str):
        return None
    candidate = html.unescape(value).strip()
    try:
        parsed = urlparse(candidate)
    except ValueError:
        return None
    return candidate if parsed.scheme.lower() == "https" and parsed.netloc else None


def normalize_fingerprint_text(value: Any) -> str:
    text = unicodedata.normalize("NFKC", str(value or "")).lower().strip()
    text = re.sub(r"[^\w\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def duplicate_fingerprint(title: Any, provider: Any, deadline: Any) -> str:
    canonical = "|".join(
        (
            normalize_fingerprint_text(title),
            normalize_fingerprint_text(provider),
            parse_date(deadline).isoformat() if parse_date(deadline) else "",
        )
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def payload_hash(payload: dict[str, Any]) -> str:
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def earliest_date(value: Any) -> date | None:
    candidates: list[Any] = []
    for item in as_list(value):
        if isinstance(item, dict):
            candidates.extend(
                item[key]
                for key in ("date", "deadline", "deadlineDate", "value")
                if key in item
            )
        else:
            candidates.append(item)
    dates = [parsed for item in candidates if (parsed := parse_date(item))]
    return min(dates) if dates else None
