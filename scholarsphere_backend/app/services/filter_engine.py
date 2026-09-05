"""Applies a configurable set of scholarship-portal filters (country,
nationality, degree level, field, funding type, deadline, university,
category, ...) to an already-rendered page, via
`app.services.browser_interaction.BrowserInteractionEngine`.

Configuration is a plain mapping, not a hardcoded per-site integration -
the engine supports whatever filters a caller describes rather than
assuming every scholarship portal uses the same UI:

    {
        "country": FilterSpec(selector="#country-select", value="International"),
        "degree": FilterSpec(selector="#degree-select", value="Master"),
    }

Each filter's `selector` is checked for presence on the page before use -
a filter a given site doesn't have is simply skipped (recorded in
`FilterApplicationResult.skipped`), never an error. Two control shapes
are supported, picked automatically from the element's own tag: a
`<select>` (set via `select_option`) and anything else clickable (a
checkbox/radio/button, applied via a click).

`apply_filters` applies exactly the one combination it's given - it never
tests every possible combination itself (the spec's own "avoid
combinatorial explosion" rule). A caller wanting several targeted
combinations calls `iter_filter_combinations` to generate a bounded,
caller-controlled set of them (via `max_combinations`) and then calls
`apply_filters` once per combination - this module never invents which
combinations are "worth" trying; that judgment stays with the caller
(e.g. a source adapter that knows which axes matter for its own portal).
"""

from dataclasses import dataclass, field
from itertools import product
from typing import Iterator, Mapping
from urllib.parse import urlsplit

from app.services.source_capability_profile import get_capability_registry


@dataclass(frozen=True)
class FilterSpec:
    selector: str
    value: str


@dataclass
class FilterApplicationResult:
    applied: dict[str, str] = field(default_factory=dict)
    skipped: list[str] = field(default_factory=list)
    results_changed: bool = False


async def apply_filters(
    engine: object,
    filters: Mapping[str, FilterSpec],
    *,
    timeout_ms: int | None = None,
) -> FilterApplicationResult:
    """`engine` is a `BrowserInteractionEngine` already positioned on the
    listing page. Applies every filter in `filters` that has a matching
    control on the page, then waits once (via
    `engine.wait_for_navigation_or_change`) to see whether the combined
    change actually altered the page - a single check against the state
    captured before any filter was touched, not one check per filter.
    """
    page = engine.page  # type: ignore[attr-defined]
    timeout = timeout_ms or engine.default_timeout_ms  # type: ignore[attr-defined]
    result = FilterApplicationResult()

    await engine.mark_baseline()  # type: ignore[attr-defined]

    for name, spec in filters.items():
        locator = page.locator(spec.selector)
        try:
            count = await locator.count()
        except Exception:  # noqa: BLE001
            count = 0
        if count == 0:
            result.skipped.append(name)
            continue

        try:
            tag_name = await locator.first.evaluate("(el) => el.tagName.toLowerCase()")
            if tag_name == "select":
                await locator.first.select_option(label=spec.value, timeout=timeout)
            else:
                await locator.first.click(timeout=timeout)
            result.applied[name] = spec.value
        except Exception:  # noqa: BLE001 - a filter this site doesn't actually
            # support the way we assumed is a skip, not a fatal error for
            # every other requested filter.
            result.skipped.append(name)

    if result.applied:
        outcome = await engine.wait_for_navigation_or_change(  # type: ignore[attr-defined]
            timeout_ms=timeout
        )
        result.results_changed = outcome.kind != "no_change"
        host = urlsplit(page.url).hostname
        if host:
            get_capability_registry().record(host, supports_filters=True)

    return result


def iter_filter_combinations(
    options: Mapping[str, list[FilterSpec]], *, max_combinations: int = 10
) -> Iterator[dict[str, FilterSpec]]:
    """Yields up to `max_combinations` filter combinations from the
    cartesian product of `options` (e.g. `{"degree": [Master, PhD],
    "country": [International]}` yields at most 2 combinations here).
    Bounded and deterministic - never an unbounded/implicit "try
    everything" sweep.
    """
    if not options:
        return
    names = list(options)
    value_lists = [options[name] for name in names]
    count = 0
    for combo in product(*value_lists):
        if count >= max_combinations:
            return
        yield dict(zip(names, combo))
        count += 1
