from dataclasses import dataclass, field

from app.models.fraud_investigation import InvestigationRiskLevel


@dataclass
class RiskScoringInput:
    provider_risk: int = 0
    source_risk: int = 0
    user_behaviour_risk: int = 0
    suspicious_domain: bool = False
    duplicate_account: bool = False
    risky_link: bool = False
    payment_request: bool = False
    impersonation: bool = False


@dataclass
class RiskScore:
    overall: int
    level: InvestigationRiskLevel
    provider_risk: int
    source_risk: int
    user_behaviour_risk: int
    domain_risk: int
    link_risk: int
    payment_risk: int
    impersonation_risk: int
    reasons: list[str] = field(default_factory=list)


def _clamp(value: int) -> int:
    return max(0, min(100, value))


def evaluate(data: RiskScoringInput) -> RiskScore:
    domain = 100 if data.suspicious_domain else 0
    link = 90 if data.risky_link else 0
    payment = 95 if data.payment_request else 0
    impersonation = 100 if data.impersonation else 0
    duplicate_penalty = 70 if data.duplicate_account else 0
    score = round(
        (data.provider_risk * 0.15)
        + (data.source_risk * 0.15)
        + (data.user_behaviour_risk * 0.1)
        + (domain * 0.15)
        + (link * 0.1)
        + (payment * 0.15)
        + (impersonation * 0.15)
        + (duplicate_penalty * 0.05)
    )
    score = _clamp(int(score))
    if score >= 75:
        level = InvestigationRiskLevel.critical
    elif score >= 50:
        level = InvestigationRiskLevel.high
    elif score >= 25:
        level = InvestigationRiskLevel.medium
    else:
        level = InvestigationRiskLevel.low
    reasons = []
    if data.suspicious_domain:
        reasons.append("Suspicious domain detected.")
    if data.duplicate_account:
        reasons.append("Possible duplicate account detected.")
    if data.risky_link:
        reasons.append("Link-risk indicators detected.")
    if data.payment_request:
        reasons.append("Unofficial payment request detected.")
    if data.impersonation:
        reasons.append("Institution impersonation indicators detected.")
    return RiskScore(
        overall=score,
        level=level,
        provider_risk=_clamp(data.provider_risk),
        source_risk=_clamp(data.source_risk),
        user_behaviour_risk=_clamp(data.user_behaviour_risk),
        domain_risk=domain,
        link_risk=link,
        payment_risk=payment,
        impersonation_risk=impersonation,
        reasons=reasons,
    )
