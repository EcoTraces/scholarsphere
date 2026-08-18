from urllib.parse import urlparse

FREE_EMAIL_DOMAINS = frozenset({"gmail.com", "yahoo.com", "outlook.com"})


def compute_risk_score(
    *,
    official_email_domain: str,
    official_website: str,
    registration_number: str,
    supporting_documents: list[str],
) -> int:
    """Port of DemoProviderRepository._riskScore() - server-authoritative.

    Never trust a client-supplied risk score; this is the only place it is
    computed.
    """
    score = 0
    domain = official_email_domain.lower().strip()
    if domain in FREE_EMAIL_DOMAINS:
        score += 55
    website_host = (urlparse(official_website).hostname or "").lower()
    if not website_host or not website_host.endswith(domain):
        score += 25
    if not registration_number.strip():
        score += 15
    if not supporting_documents:
        score += 15
    return max(0, min(100, score))
