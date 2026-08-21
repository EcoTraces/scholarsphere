import re

from app.models.taxonomy import TaxonomyTerm

_NON_ALPHANUMERIC = re.compile(r"[^a-z0-9]+")


def normalize(value: str) -> str:
    return _NON_ALPHANUMERIC.sub(" ", value.lower()).strip()


def duplicate_candidate_groups(terms: list[TaxonomyTerm]) -> list[list[TaxonomyTerm]]:
    groups: list[list[TaxonomyTerm]] = []
    used: set[str] = set()

    def tokens_for(term: TaxonomyTerm) -> set[str]:
        return {normalize(term.canonical_name), *(normalize(item) for item in term.synonyms)}

    for term in terms:
        if term.id in used:
            continue
        term_tokens = tokens_for(term)
        matches = [
            other
            for other in terms
            if other.id == term.id or bool(term_tokens & tokens_for(other))
        ]
        if len(matches) > 1:
            groups.append(matches)
            used.update(match.id for match in matches)
    return groups
