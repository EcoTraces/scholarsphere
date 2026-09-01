"""Per-``ApplicantCategory`` workflow configuration - a single registry,

not category-specific branching scattered through routes/services. Adding
a new category or changing what an existing one includes is a registry
edit here, never a new ``if category == ...`` somewhere else in the
codebase (this is what the platform spec's "Make category workflows
configurable rather than hard-coded" requirement means in practice).

Each entry lists the document kinds a workspace of that category gets
(drives which ``PremiumDocument`` creation options
app/api/routes/premium_documents.py offers) and the checklist items
auto-generated for a new workspace of that category
(app/services/application_preparation.py::generate_checklist).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.models.application_preparation import ApplicantCategory
from app.models.premium_documents import DocumentKind


@dataclass(frozen=True)
class ChecklistItemSpec:
    item_key: str
    label: str
    category: str


@dataclass(frozen=True)
class CategoryWorkflow:
    category: ApplicantCategory
    document_kinds: tuple[DocumentKind, ...]
    checklist_items: tuple[ChecklistItemSpec, ...]


def _common_checklist(*extra: ChecklistItemSpec) -> tuple[ChecklistItemSpec, ...]:
    base = (
        ChecklistItemSpec("profile_complete", "Complete your applicant profile", "profile"),
        ChecklistItemSpec(
            "background_complete", "Add your education and experience history", "profile"
        ),
        ChecklistItemSpec(
            "requirements_reviewed", "Review the requirement match analysis", "strategy"
        ),
    )
    return base + extra


CATEGORY_WORKFLOWS: dict[ApplicantCategory, CategoryWorkflow] = {
    ApplicantCategory.undergraduate: CategoryWorkflow(
        category=ApplicantCategory.undergraduate,
        document_kinds=(
            DocumentKind.cv_scholarship,
            DocumentKind.personal_statement,
            DocumentKind.motivation_letter,
            DocumentKind.study_plan,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your CV", "documents"),
            ChecklistItemSpec(
                "personal_statement_ready", "Write your personal statement", "documents"
            ),
            ChecklistItemSpec("motivation_letter_ready", "Write your motivation letter", "documents"),
            ChecklistItemSpec("study_plan_ready", "Prepare your study plan", "documents"),
        ),
    ),
    ApplicantCategory.postgraduate: CategoryWorkflow(
        category=ApplicantCategory.postgraduate,
        document_kinds=(
            DocumentKind.cv_professional,
            DocumentKind.sop,
            DocumentKind.personal_statement,
            DocumentKind.motivation_letter,
            DocumentKind.study_plan,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your academic/professional CV", "documents"),
            ChecklistItemSpec("sop_ready", "Write your statement of purpose", "documents"),
            ChecklistItemSpec("motivation_letter_ready", "Write your motivation letter", "documents"),
            ChecklistItemSpec("study_plan_ready", "Prepare your study plan", "documents"),
            ChecklistItemSpec(
                "program_fit_reviewed", "Review your program-fit analysis", "strategy"
            ),
        ),
    ),
    ApplicantCategory.phd: CategoryWorkflow(
        category=ApplicantCategory.phd,
        document_kinds=(
            DocumentKind.cv_academic,
            DocumentKind.sop,
            DocumentKind.research_proposal,
            DocumentKind.study_plan,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("academic_cv_ready", "Prepare your academic CV", "documents"),
            ChecklistItemSpec("sop_ready", "Write your statement of purpose", "documents"),
            ChecklistItemSpec(
                "research_proposal_ready", "Prepare your research proposal", "documents"
            ),
            ChecklistItemSpec(
                "supervisor_fit_reviewed", "Identify potential supervisors/program fit", "strategy"
            ),
            ChecklistItemSpec(
                "publications_listed", "List any publications or research projects", "profile"
            ),
        ),
    ),
    ApplicantCategory.fellowship: CategoryWorkflow(
        category=ApplicantCategory.fellowship,
        document_kinds=(
            DocumentKind.cv_professional,
            DocumentKind.fellowship_leadership_statement,
            DocumentKind.fellowship_personal_statement,
            DocumentKind.fellowship_impact_statement,
            DocumentKind.fellowship_essay,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your CV", "documents"),
            ChecklistItemSpec(
                "leadership_statement_ready", "Write your leadership statement", "documents"
            ),
            ChecklistItemSpec(
                "personal_statement_ready", "Write your personal statement", "documents"
            ),
            ChecklistItemSpec("impact_statement_ready", "Write your impact statement", "documents"),
            ChecklistItemSpec(
                "fellowship_alignment_reviewed", "Review fellowship-alignment analysis", "strategy"
            ),
            ChecklistItemSpec("essays_ready", "Complete required fellowship essays", "documents"),
        ),
    ),
    ApplicantCategory.research_scholarship: CategoryWorkflow(
        category=ApplicantCategory.research_scholarship,
        document_kinds=(
            DocumentKind.cv_academic,
            DocumentKind.sop,
            DocumentKind.research_proposal,
            DocumentKind.study_plan,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("academic_cv_ready", "Prepare your academic CV", "documents"),
            ChecklistItemSpec("sop_ready", "Write your statement of purpose", "documents"),
            ChecklistItemSpec(
                "research_proposal_ready", "Prepare your research proposal", "documents"
            ),
        ),
    ),
    ApplicantCategory.professional_scholarship: CategoryWorkflow(
        category=ApplicantCategory.professional_scholarship,
        document_kinds=(
            DocumentKind.cv_professional,
            DocumentKind.sop,
            DocumentKind.motivation_letter,
            DocumentKind.study_plan,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your professional resume", "documents"),
            ChecklistItemSpec("sop_ready", "Write your statement of purpose", "documents"),
            ChecklistItemSpec("motivation_letter_ready", "Write your motivation letter", "documents"),
            ChecklistItemSpec(
                "work_experience_listed", "List your relevant work experience", "profile"
            ),
        ),
    ),
    ApplicantCategory.exchange_mobility: CategoryWorkflow(
        category=ApplicantCategory.exchange_mobility,
        document_kinds=(
            DocumentKind.cv_professional,
            DocumentKind.motivation_letter,
            DocumentKind.study_plan,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your CV", "documents"),
            ChecklistItemSpec("motivation_letter_ready", "Write your motivation letter", "documents"),
            ChecklistItemSpec(
                "study_plan_ready", "Prepare your mobility/exchange study plan", "documents"
            ),
        ),
    ),
    ApplicantCategory.short_course_training: CategoryWorkflow(
        category=ApplicantCategory.short_course_training,
        document_kinds=(
            DocumentKind.cv_professional,
            DocumentKind.motivation_letter,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your CV", "documents"),
            ChecklistItemSpec("motivation_letter_ready", "Write your motivation letter", "documents"),
        ),
    ),
    ApplicantCategory.internship_graduate_opportunity: CategoryWorkflow(
        category=ApplicantCategory.internship_graduate_opportunity,
        document_kinds=(
            DocumentKind.cv_professional,
            DocumentKind.motivation_letter,
        ),
        checklist_items=_common_checklist(
            ChecklistItemSpec("cv_ready", "Prepare your CV", "documents"),
            ChecklistItemSpec("motivation_letter_ready", "Write your motivation/cover letter", "documents"),
            ChecklistItemSpec(
                "work_experience_listed", "List your relevant work experience/projects", "profile"
            ),
        ),
    ),
}


def workflow_for(category: ApplicantCategory) -> CategoryWorkflow:
    return CATEGORY_WORKFLOWS[category]
