"""Adapter base classes for scraper sources whose extraction can be
driven by declarative CSS-selector configuration alone, rather than
bespoke imperative parsing code per site.

Prefer generic behavior first - matching this project's own standing
convention (see docs/AUTHORITATIVE_SOURCES.md): every one of this
project's 43 existing `app.services.national_scholarship_programs`
scraper sources keeps its own bespoke `collect()` implementation
unchanged; nothing here requires migrating any of them, and none has
been migrated. This is purely additive infrastructure a *future* source
can opt into when its own live-testing (documented the same way as every
other design decision in this project) shows generic selector-driven
extraction is enough for that site - reached for only when it materially
reduces bespoke code, never applied to force every site into one shape.

Class hierarchy (matching the spec's own naming):
  `GenericHTMLAdapter` - a static-HTML listing page, driven entirely by
                         CSS selectors (no browser rendering).
  `GenericJSAdapter`   - the same, but for a JS-rendered listing (opts
                         into `allow_browser_rendering`).
  `GovernmentPortalAdapter` / `UniversityPortalAdapter` - semantic
                         aliases of `GenericHTMLAdapter`, for sources
                         whose only real difference is which sector they
                         belong to. They add no behavioral difference
                         over their parent today - a concrete government/
                         university source can still override anything it
                         needs to; the separate names exist because the
                         spec calls for them and because a distinct name
                         is still useful documentation of intent even
                         before any behavioral divergence exists.
  `SPAAdapter`         - the named extension point for a single-page app
                         whose listing and detail views are both reached
                         via client-side navigation rather than distinct
                         URLs. Deliberately left as an interface, not a
                         generic implementation: an SPA's own click/
                         detail-open flow is inherently site-specific, so
                         a concrete subclass drives
                         `app.services.browser_rendering.interactive_session`
                         and `app.services.browser_interaction.
                         BrowserInteractionEngine` directly in its own
                         `collect()`.
"""

from dataclasses import dataclass

from app.schemas.external_opportunity import NormalizedExternalOpportunity
from app.services.web_scraper_base import (
    WebScraperSource,
    absolute_https_url,
    clean_text,
)


@dataclass(frozen=True)
class AdapterSelectors:
    """CSS selectors a `GenericHTMLAdapter` subclass uses to extract one
    listing's worth of scholarship cards. `listing_selector` selects each
    individual card/row; the rest are resolved relative to each card
    (via BeautifulSoup's `select_one`) and are optional - a selector that
    doesn't match on a given card simply leaves that field `None`, never
    guessed (matching `app.services.web_scraper_base`'s own
    never-invent-a-field rule).
    """

    listing_selector: str
    title_selector: str | None = None
    provider_selector: str | None = None
    description_selector: str | None = None
    deadline_selector: str | None = None
    eligibility_selector: str | None = None
    application_selector: str | None = None


class GenericHTMLAdapter(WebScraperSource):
    """A concrete subclass sets `selectors` (an `AdapterSelectors`),
    `list_url`, and `provider_name_default` (used when
    `selectors.provider_selector` isn't set or doesn't match); `collect()`
    is provided here and needs no per-site override for a site whose
    listing page is simple enough to describe this way.
    """

    selectors: AdapterSelectors
    list_url: str
    provider_name_default: str = ""

    async def collect(
        self, **_: object
    ) -> list[NormalizedExternalOpportunity | dict[str, object]]:
        soup = await self.fetch_soup(self.list_url)
        cards = soup.select(self.selectors.listing_selector)

        results: list[dict[str, object]] = []
        for card in cards:
            title = self._select_text(card, self.selectors.title_selector) or clean_text(
                card
            )
            provider_name = (
                self._select_text(card, self.selectors.provider_selector)
                or self.provider_name_default
            )
            application_url = self._select_href(card, self.selectors.application_selector)
            results.append(
                {
                    "title": title,
                    "provider_name": provider_name,
                    "description": self._select_text(
                        card, self.selectors.description_selector
                    ),
                    "deadline_text": self._select_text(
                        card, self.selectors.deadline_selector
                    ),
                    "eligibility_text": self._select_text(
                        card, self.selectors.eligibility_selector
                    ),
                    "official_application_url": application_url,
                }
            )
        return results

    def _select_text(self, card: object, selector: str | None) -> str | None:
        if not selector:
            return None
        node = card.select_one(selector)  # type: ignore[attr-defined]
        return clean_text(node) if node is not None else None

    def _select_href(self, card: object, selector: str | None) -> str | None:
        if not selector:
            return None
        node = card.select_one(selector)  # type: ignore[attr-defined]
        if node is None:
            return None
        return absolute_https_url(self.list_url, node.get("href"))


class GenericJSAdapter(GenericHTMLAdapter):
    """Same declarative extraction as `GenericHTMLAdapter`, for a listing
    page that needs the browser-rendering fallback - see
    `app.services.web_scraper_base.WebScraperSource.allow_browser_rendering`.
    A concrete subclass should still only set this after live-testing
    confirms the plain-HTTP response really is an unrendered JS shell.
    """

    allow_browser_rendering = True


class GovernmentPortalAdapter(GenericHTMLAdapter):
    """Semantic alias of `GenericHTMLAdapter` - see this module's
    docstring for why it exists as a separate name today.
    """


class UniversityPortalAdapter(GenericHTMLAdapter):
    """Semantic alias of `GenericHTMLAdapter` - see this module's
    docstring for why it exists as a separate name today.
    """


class SPAAdapter(WebScraperSource):
    """Named extension point for a single-page-app source. Deliberately
    not a generic implementation (see this module's docstring) - a
    concrete subclass implements `collect()` using
    `app.services.browser_rendering.interactive_session(self.list_url)`
    and `app.services.browser_interaction.BrowserInteractionEngine`
    directly, optionally combined with `app.services.pagination_engine`,
    `app.services.infinite_scroll_engine`, `app.services.filter_engine`,
    and `app.services.application_link_discovery` as needed.
    """

    allow_browser_rendering = True
    list_url: str
