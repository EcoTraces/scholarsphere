"""AI-assisted document generation - grounded strictly in real, user-

provided data. Two distinct, deliberately different paths:

1. **CV content** (``build_cv_content``) is assembled *deterministically*
   from the applicant's own ``ApplicantBackgroundEntry`` rows and
   ``ApplicantProfile`` - no AI involved by default, so a CV always
   reflects exactly the facts the applicant entered, in the exact
   structure app/services/ats_analysis.py and
   app/services/document_export.py both expect. AI's only role here is an
   explicitly opt-in, per-field *wording polish*
   (``ai_polish_text``) that is instructed to add no new fact, number,
   date, or claim - "AI may improve wording but must remain faithful to
   user-provided facts," per the platform spec, taken literally.

2. **Narrative documents** (SOP, personal statement, motivation letter,
   study plan, research proposal, fellowship essays -
   ``generate_narrative_document``) genuinely need generated prose, so
   they go through the AI provider - but the prompt sent is built
   entirely from a real "facts block" (``build_facts_block``, a verbatim
   dump of the applicant's own background/profile data) plus the
   applicant's own free-text answers to a structured questionnaire
   (never invented by this module). The system prompt explicitly forbids
   inventing any fact, and if no AI provider is configured, this raises
   ``AIProviderNotConfiguredError`` (via app/services/ai_provider.py)
   rather than returning placeholder or fabricated text.
"""

from __future__ import annotations

from app.models.applicant_background import ApplicantBackgroundEntry, BackgroundEntryCategory
from app.models.applicant_profile import ApplicantProfile
from app.models.application_preparation import PremiumWorkspace
from app.models.external_opportunity import ExternalOpportunity
from app.models.premium_billing import PremiumFeature
from app.models.premium_documents import DocumentKind
from app.services.ai_provider import AIProvider

# Which PremiumFeature gates building/generating each document kind - used
# by app/api/routes/premium_documents.py so the mapping lives in one
# place rather than a route-level if/elif chain.
KIND_FEATURE_MAP: dict[DocumentKind, PremiumFeature] = {
    DocumentKind.cv_academic: PremiumFeature.cv_builder,
    DocumentKind.cv_professional: PremiumFeature.cv_builder,
    DocumentKind.cv_scholarship: PremiumFeature.cv_builder,
    DocumentKind.sop: PremiumFeature.sop_builder,
    DocumentKind.personal_statement: PremiumFeature.sop_builder,
    DocumentKind.motivation_letter: PremiumFeature.sop_builder,
    DocumentKind.study_plan: PremiumFeature.study_plan_builder,
    DocumentKind.research_proposal: PremiumFeature.research_proposal_builder,
    DocumentKind.fellowship_leadership_statement: PremiumFeature.fellowship_preparation,
    DocumentKind.fellowship_personal_statement: PremiumFeature.fellowship_preparation,
    DocumentKind.fellowship_impact_statement: PremiumFeature.fellowship_preparation,
    DocumentKind.fellowship_essay: PremiumFeature.fellowship_preparation,
}
CV_KINDS = frozenset(
    {DocumentKind.cv_academic, DocumentKind.cv_professional, DocumentKind.cv_scholarship}
)

_POLISH_SYSTEM_PROMPT = (
    "You are a professional CV editor. Rewrite the given text to be more "
    "concise, professional, and impact-focused. You MUST NOT add any new "
    "fact, achievement, number, date, employer, degree, skill, or claim "
    "that is not already present in the original text. Do not invent "
    "metrics or outcomes. If the original text is vague, keep it vague "
    "rather than inventing specificity. Return only the rewritten text, "
    "with no preamble or explanation."
)

_NARRATIVE_SYSTEM_PROMPT_BASE = (
    "You are a professional academic and scholarship application writing "
    "assistant. You MUST use only the facts provided in the APPLICANT "
    "FACTS section below. Do not invent, assume, exaggerate, or add any "
    "award, degree, publication, job, project, skill, research finding, "
    "citation, statistic, or experience that is not explicitly present in "
    "those facts or in the applicant's own answers. If a section would "
    "otherwise be thin because the applicant provided little relevant "
    "information, write it honestly and concisely rather than inventing "
    "content to fill space - you may note in a bracketed comment like "
    "'[Consider adding more detail about X]' where the applicant should "
    "expand it themselves, but never fabricate the missing content."
)

_NARRATIVE_KIND_INSTRUCTIONS: dict[DocumentKind, str] = {
    DocumentKind.sop: (
        "Write a Statement of Purpose. Cover: academic background, why this "
        "field, why this program, why this university, relevant experience "
        "and projects, research interests if applicable, career goals, "
        "scholarship motivation, and intended future contribution."
    ),
    DocumentKind.personal_statement: (
        "Write a Personal Statement. Cover the applicant's personal journey, "
        "motivation, relevant background, and future goals, in a genuine, "
        "individual voice grounded only in the given facts."
    ),
    DocumentKind.motivation_letter: (
        "Write a Motivation Letter explaining why the applicant is "
        "motivated to pursue this specific opportunity, program, or "
        "scholarship, grounded only in the given facts."
    ),
    DocumentKind.study_plan: (
        "Write a Study Plan covering academic objectives, learning "
        "objectives, program rationale, research interests if applicable, "
        "skills development, academic milestones, career objectives, "
        "contribution to the applicant's home country/community, "
        "post-study plans, and a timeline."
    ),
    DocumentKind.research_proposal: (
        "Write a Research Proposal with sections: Title, Background, "
        "Problem Statement, Research Gap, Objectives, Research Questions, "
        "Methodology, Expected Contribution, and Timeline. Never fabricate "
        "citations, prior research findings, or data - if a claim would "
        "need a citation the applicant hasn't provided, phrase it as the "
        "applicant's own proposed reasoning instead."
    ),
    DocumentKind.fellowship_leadership_statement: (
        "Write a Leadership Statement for a fellowship application, "
        "grounded only in the applicant's real leadership and community "
        "experience provided in the facts."
    ),
    DocumentKind.fellowship_personal_statement: (
        "Write a Personal Statement for a fellowship application, grounded "
        "only in the given facts."
    ),
    DocumentKind.fellowship_impact_statement: (
        "Write an Impact Statement describing the applicant's real "
        "community impact and professional experience, grounded only in "
        "the given facts, and their fellowship alignment and career "
        "trajectory."
    ),
    DocumentKind.fellowship_essay: (
        "Write a fellowship application essay responding to the applicant's "
        "own prompt/answers provided below, grounded only in the given "
        "facts."
    ),
}


def _entry_line(entry: ApplicantBackgroundEntry) -> str:
    span = ""
    if entry.start_date:
        end = "Present" if entry.is_current else (entry.end_date.isoformat() if entry.end_date else "")
        span = f" ({entry.start_date.isoformat()} - {end})"
    organization = f" at {entry.organization}" if entry.organization else ""
    description = f": {entry.description}" if entry.description else ""
    return f"- {entry.title}{organization}{span}{description}"


def build_facts_block(
    entries: list[ApplicantBackgroundEntry], profile: ApplicantProfile | None
) -> str:
    """A verbatim, plain-text dump of only real applicant data - the

    prompt's entire factual grounding. Nothing here is inferred or
    embellished; formatting only.
    """
    lines: list[str] = ["APPLICANT FACTS:"]
    if profile is not None:
        lines.append(
            f"Nationality: {profile.nationality or 'not provided'}; "
            f"Highest qualification: {profile.highest_qualification or 'not provided'} "
            f"in {profile.degree_field or 'not provided'}; "
            f"Work experience: {profile.work_experience_years:g} years."
        )
    by_category: dict[BackgroundEntryCategory, list[ApplicantBackgroundEntry]] = {}
    for entry in entries:
        by_category.setdefault(entry.category, []).append(entry)
    for category, category_entries in by_category.items():
        lines.append(f"\n{category.value.replace('_', ' ').title()}:")
        lines.extend(_entry_line(entry) for entry in category_entries)
    if len(lines) == 1:
        lines.append("(No background entries recorded yet.)")
    return "\n".join(lines)


def build_cv_content(
    entries: list[ApplicantBackgroundEntry],
    profile: ApplicantProfile | None,
    *,
    summary: str = "",
) -> dict:
    """Deterministic CV assembly - no AI required or involved. Every field

    traces directly to a real ``ApplicantProfile``/``ApplicantBackgroundEntry``
    value.
    """

    def _entries(category: BackgroundEntryCategory) -> list[dict]:
        return [
            {
                "institution": entry.organization,
                "organization": entry.organization,
                "degree": entry.title,
                "role": entry.title,
                "field": entry.details.get("field", ""),
                "start_date": entry.start_date.isoformat() if entry.start_date else "",
                "end_date": "Present" if entry.is_current else (
                    entry.end_date.isoformat() if entry.end_date else ""
                ),
                "description": entry.description,
            }
            for entry in entries
            if entry.category == category
        ]

    return {
        "full_name": profile.full_name if profile else "",
        "contact": {
            "email": "",
            "phone": "",
            "location": profile.country_of_residence if profile else "",
        },
        "summary": summary,
        "education": _entries(BackgroundEntryCategory.education),
        "experience": _entries(BackgroundEntryCategory.work_experience),
        "skills": [
            entry.title
            for entry in entries
            if entry.category == BackgroundEntryCategory.skill
        ],
        "projects": _entries(BackgroundEntryCategory.project),
        "publications": _entries(BackgroundEntryCategory.publication),
        "awards": _entries(BackgroundEntryCategory.award),
        "leadership": _entries(BackgroundEntryCategory.leadership_community),
    }


async def ai_polish_text(
    text: str, *, section_label: str, ai_provider: AIProvider, max_tokens: int = 400
) -> str:
    if not text.strip():
        return text
    result = await ai_provider.generate_text(
        system_prompt=_POLISH_SYSTEM_PROMPT,
        user_prompt=f"Section: {section_label}\n\nOriginal text:\n{text}",
        max_tokens=max_tokens,
    )
    return result.text.strip()


def _target_block(
    workspace: PremiumWorkspace | None, opportunity: ExternalOpportunity | None
) -> str:
    lines = ["TARGET OPPORTUNITY:"]
    if workspace is not None:
        lines.append(f"Applicant category: {workspace.category.value}")
        if workspace.target_university:
            lines.append(f"Target university: {workspace.target_university}")
        if workspace.target_program:
            lines.append(f"Target program: {workspace.target_program}")
    if opportunity is not None:
        lines.append(f"Scholarship/opportunity: {opportunity.title} ({opportunity.provider_name})")
        if opportunity.country:
            lines.append(f"Country: {opportunity.country}")
    if len(lines) == 1:
        lines.append("(No specific target selected.)")
    return "\n".join(lines)


async def generate_narrative_document(
    kind: DocumentKind,
    *,
    entries: list[ApplicantBackgroundEntry],
    profile: ApplicantProfile | None,
    workspace: PremiumWorkspace | None,
    opportunity: ExternalOpportunity | None,
    user_answers: dict[str, str],
    ai_provider: AIProvider,
    max_tokens: int = 1600,
) -> str:
    kind_instructions = _NARRATIVE_KIND_INSTRUCTIONS.get(
        kind, "Write a well-structured application document."
    )
    system_prompt = f"{_NARRATIVE_SYSTEM_PROMPT_BASE}\n\n{kind_instructions}"

    answers_block = "APPLICANT'S OWN ANSWERS/NOTES:\n" + (
        "\n".join(f"- {question}: {answer}" for question, answer in user_answers.items())
        if user_answers
        else "(none provided)"
    )

    user_prompt = "\n\n".join(
        [
            build_facts_block(entries, profile),
            _target_block(workspace, opportunity),
            answers_block,
        ]
    )

    result = await ai_provider.generate_text(
        system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens
    )
    return result.text.strip()
