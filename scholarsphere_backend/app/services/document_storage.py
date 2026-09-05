"""Signed download URLs for Firebase-Storage-backed applicant documents.

``storage.rules`` keeps ``applicant-documents/`` strictly owner-only - no
Storage security rule grants a provider read access to a document shared
with them via ``ApplicantDocument.shared_with_provider_ids``, and it
deliberately stays that way (see the rules file's own comment). This
backend is the auditable choke point for that third-party access instead:
callers who pass the Postgres-level authorization check
(``app/api/routes/applicant_documents.py``) get a short-lived signed URL
minted here with the Admin SDK's private key, rather than a widened
client-side Storage rule.
"""

from __future__ import annotations

import logging
from datetime import timedelta

import firebase_admin
from firebase_admin import storage as firebase_storage

from app.core.auth import initialize_firebase

logger = logging.getLogger(__name__)

DEFAULT_EXPIRES_IN_MINUTES = 15


class DocumentDownloadUrlError(Exception):
    """Raised when a signed download URL could not be minted at all.

    Signing requires either a real service-account private key
    (``FIREBASE_CREDENTIALS_PATH``) or IAM ``signBlob`` permission on the
    runtime's Application Default Credentials - neither is guaranteed to
    be configured in every environment. Callers must surface this as a
    real failure, never fabricate a URL.
    """


def generate_download_url(
    storage_path: str, *, expires_in_minutes: int = DEFAULT_EXPIRES_IN_MINUTES
) -> str:
    try:
        initialize_firebase()
        bucket = firebase_storage.bucket(app=firebase_admin.get_app())
        blob = bucket.blob(storage_path)
        return blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=expires_in_minutes),
            method="GET",
        )
    except Exception as exc:
        logger.warning(
            "document_download_url_generation_failed error_type=%s",
            type(exc).__name__,
        )
        raise DocumentDownloadUrlError(
            "Could not generate a document download URL."
        ) from exc
