import 'fraud_case.dart';

class RiskScoringInput {
  const RiskScoringInput({
    this.providerRisk = 0,
    this.sourceRisk = 0,
    this.userBehaviourRisk = 0,
    this.suspiciousDomain = false,
    this.duplicateAccount = false,
    this.riskyLink = false,
    this.paymentRequest = false,
    this.impersonation = false,
  });
  final int providerRisk;
  final int sourceRisk;
  final int userBehaviourRisk;
  final bool suspiciousDomain;
  final bool duplicateAccount;
  final bool riskyLink;
  final bool paymentRequest;
  final bool impersonation;
}

class RiskScoringService {
  const RiskScoringService();

  RiskScore evaluate(RiskScoringInput input) {
    final domain = input.suspiciousDomain ? 100 : 0;
    final link = input.riskyLink ? 90 : 0;
    final payment = input.paymentRequest ? 95 : 0;
    final impersonation = input.impersonation ? 100 : 0;
    final duplicatePenalty = input.duplicateAccount ? 70 : 0;
    final score =
        ((input.providerRisk * .15) +
                (input.sourceRisk * .15) +
                (input.userBehaviourRisk * .1) +
                (domain * .15) +
                (link * .1) +
                (payment * .15) +
                (impersonation * .15) +
                (duplicatePenalty * .05))
            .round()
            .clamp(0, 100)
            .toInt();
    return RiskScore(
      overall: score,
      level: switch (score) {
        >= 75 => InvestigationRiskLevel.critical,
        >= 50 => InvestigationRiskLevel.high,
        >= 25 => InvestigationRiskLevel.medium,
        _ => InvestigationRiskLevel.low,
      },
      providerRisk: input.providerRisk.clamp(0, 100).toInt(),
      sourceRisk: input.sourceRisk.clamp(0, 100).toInt(),
      userBehaviourRisk: input.userBehaviourRisk.clamp(0, 100).toInt(),
      domainRisk: domain,
      linkRisk: link,
      paymentRisk: payment,
      impersonationRisk: impersonation,
      reasons: [
        if (input.suspiciousDomain) 'Suspicious domain detected.',
        if (input.duplicateAccount) 'Possible duplicate account detected.',
        if (input.riskyLink) 'Link-risk indicators detected.',
        if (input.paymentRequest) 'Unofficial payment request detected.',
        if (input.impersonation)
          'Institution impersonation indicators detected.',
      ],
    );
  }
}
