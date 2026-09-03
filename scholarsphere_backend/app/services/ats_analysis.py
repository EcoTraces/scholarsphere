"""Deterministic, rule-based ATS (Applicant Tracking System) analysis of a

CV's structured content. Never AI-dependent - this runs identically
whether or not an AI provider is configured, and its scoring rules are
fully enumerated here (nothing hidden in a model). The disclaimer in
``ATS_DISCLAIMER`` is returned with every analysis and must never be
dropped by a caller: an ATS score is a structural/keyword signal, not a
prediction of acceptance.

Expected CV ``content`` shape (the same shape
app/services/document_generation.py produces and
app/services/document_export.py renders):

    {
        "full_name": str,
        "contact": {"email": str, "phone": str, "location": str},
        "summary": str,
        "education": [{"institution", "degree", "field", "start_date",
                        "end_date", "description"}, ...],
        "experience": [{"organization", "role", "start_date", "end_date",
                         "description"}, ...],
        "skills": [str, ...],
        "projects": [...], "publications": [...], "awards": [...],
        "leadership": [...],
    }
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

ATS_DISCLAIMER = (
    "This ATS score reflects structure, formatting, and keyword coverage "
    "only. It does not guarantee that any application will be accepted or "
    "even seen favorably by a real reviewer - use it as a checklist, not "
    "a prediction."
)

_REQUIRED_SECTIONS = ("full_name", "contact", "summary", "education", "experience", "skills")
_STOPWORDS = frozenset(
    "the a an and or of to for in on with at by from as is are was were be "
    "been being this that these those i we you he she it they".split()
)
_WORD_RE = re.compile(r"[a-zA-Z][a-zA-Z\-]{2,}")
_MAX_DESCRIPTION_CHARS = 700


@dataclass(frozen=True)
class AtsAnalysis:
    score: float
    structure_score: float
    formatting_score: float
    readability_score: float
    keyword_score: float | None
    missing_sections: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    strengths: list[str] = field(default_factory=list)
    disclaimer: str = ATS_DISCLAIMER


def _flatten_text(content: dict) -> str:
    parts: list[str] = [str(content.get("full_name", "")), str(content.get("summary", ""))]
    for entry in content.get("education", []) or []:
        parts.append(" ".join(str(entry.get(key, "")) for key in ("institution", "degree", "field", "description")))
    for entry in content.get("experience", []) or []:
        parts.append(" ".join(str(entry.get(key, "")) for key in ("organization", "role", "description")))
    parts.extend(str(skill) for skill in content.get("skills", []) or [])
    for key in ("projects", "publications", "awards", "leadership"):
        for entry in content.get(key, []) or []:
            if isinstance(entry, dict):
                parts.append(" ".join(str(value) for value in entry.values()))
            else:
                parts.append(str(entry))
    return " ".join(parts)


def _structure(content: dict) -> tuple[float, list[str]]:
    missing = [section for section in _REQUIRED_SECTIONS if not content.get(section)]
    score = 100 * (len(_REQUIRED_SECTIONS) - len(missing)) / len(_REQUIRED_SECTIONS)
    return round(score, 1), missing


def _formatting(content: dict) -> tuple[float, list[str]]:
    issues: list[str] = []
    entries = list(content.get("education", []) or []) + list(content.get("experience", []) or [])
    undated = sum(1 for entry in entries if not entry.get("start_date"))
    if entries and undated:
        issues.append(f"{undated} of {len(entries)} entries are missing a start date.")
    score = 100.0
    if entries:
        score = round(100 * (len(entries) - undated) / len(entries), 1)
    return score, issues


def _readability(content: dict) -> tuple[float, list[str]]:
    issues: list[str] = []
    score = 100.0
    for entry in list(content.get("education", []) or []) + list(content.get("experience", []) or []):
        description = str(entry.get("description", ""))
        if len(description) > _MAX_DESCRIPTION_CHARS:
            issues.append(
                f"An entry's description is {len(description)} characters - consider "
                "shortening it into concise bullet points."
            )
            score -= 10
    text = _flatten_text(content)
    words = [w.lower() for w in _WORD_RE.findall(text) if w.lower() not in _STOPWORDS]
    if words:
        counts = Counter(words)
        top_word, top_count = counts.most_common(1)[0]
        ratio = top_count / len(words)
        if ratio > 0.08 and top_count >= 6:
            issues.append(
                f'The word "{top_word}" appears unusually often ({top_count} times) - '
                "this can read as keyword stuffing."
            )
            score -= 15
    return max(0.0, round(score, 1)), issues


def _keyword_coverage(content: dict, target_keywords: list[str]) -> tuple[float, list[str]]:
    text = _flatten_text(content).lower()
    missing = [kw for kw in target_keywords if kw.lower() not in text]
    matched = len(target_keywords) - len(missing)
    score = round(100 * matched / len(target_keywords), 1) if target_keywords else 100.0
    issues = (
        [f"Missing keywords from the target opportunity: {', '.join(missing[:10])}"]
        if missing
        else []
    )
    return score, issues


def analyze_ats(content: dict, *, target_keywords: list[str] | None = None) -> AtsAnalysis:
    structure_score, missing_sections = _structure(content)
    formatting_score, formatting_issues = _formatting(content)
    readability_score, readability_issues = _readability(content)

    issues = list(formatting_issues) + list(readability_issues)
    strengths: list[str] = []
    if not missing_sections:
        strengths.append("All standard CV sections are present.")
    if formatting_score == 100.0:
        strengths.append("Every entry has a start date - dates parse cleanly for ATS software.")
    strengths.append("This CV is generated as clean, single-column text with no images, "
                      "tables, or graphics that commonly break ATS parsing.")

    keyword_score: float | None = None
    components = [structure_score, formatting_score, readability_score]
    if target_keywords:
        keyword_score, keyword_issues = _keyword_coverage(content, target_keywords)
        issues.extend(keyword_issues)
        components.append(keyword_score)

    overall = round(sum(components) / len(components), 1)

    return AtsAnalysis(
        score=overall,
        structure_score=structure_score,
        formatting_score=formatting_score,
        readability_score=readability_score,
        keyword_score=keyword_score,
        missing_sections=missing_sections,
        issues=issues,
        strengths=strengths,
    )


def extract_target_keywords(*texts: str | None, limit: int = 15) -> list[str]:
    """Derives a small set of significant real words from the applicant's

    own target strings (a workspace's target university/program, the
    linked opportunity's real title) - never invented, never fetched from
    a generic "common CV keywords" list. Used to give ``keyword_score`` an
    actual target to check the CV against, rather than always skipping
    that component of the score. Ranked by frequency across the supplied
    texts so a word repeated in both the opportunity title and the target
    program (e.g. "Data Science") is prioritized.
    """
    counts: Counter[str] = Counter()
    for text in texts:
        if not text:
            continue
        for match in _WORD_RE.finditer(text):
            word = match.group(0)
            if word.lower() in _STOPWORDS:
                continue
            counts[word] += 1
    return [word for word, _ in counts.most_common(limit)]
