import 'package:flutter/material.dart';

import '../domain/fraud_assessment.dart';

class FraudWarningPanel extends StatelessWidget {
  const FraudWarningPanel({
    super.key,
    required this.assessment,
    this.compact = false,
  });

  final FraudAssessment assessment;
  final bool compact;

  @override
  Widget build(BuildContext context) {
    if (!assessment.hasWarnings) {
      return Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          border: Border.all(
            color: Theme.of(context).colorScheme.outlineVariant,
          ),
          borderRadius: BorderRadius.circular(8),
        ),
        child: const Row(
          children: [
            Icon(Icons.shield_outlined, color: Color(0xFF007C72)),
            SizedBox(width: 10),
            Expanded(
              child: Text(
                'No automated safety warnings detected. Always apply through '
                'the verified official source.',
              ),
            ),
          ],
        ),
      );
    }
    final color = switch (assessment.level) {
      OverallRiskLevel.low => const Color(0xFF596579),
      OverallRiskLevel.moderate => const Color(0xFF8A5A00),
      OverallRiskLevel.high => const Color(0xFFB54708),
      OverallRiskLevel.critical => Theme.of(context).colorScheme.error,
    };
    return Container(
      padding: const EdgeInsets.all(16),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.08),
        border: Border.all(color: color),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.warning_amber_outlined, color: color),
              const SizedBox(width: 10),
              Expanded(
                child: Text(
                  assessment.levelLabel,
                  style: Theme.of(context).textTheme.titleLarge,
                ),
              ),
              Text('${assessment.score}/100'),
            ],
          ),
          const SizedBox(height: 8),
          const Text(
            'These automated indicators are cautions for further review, not '
            'proof that the opportunity or provider is fraudulent.',
          ),
          if (!compact) ...[
            const SizedBox(height: 12),
            for (final signal in assessment.signals)
              ListTile(
                contentPadding: EdgeInsets.zero,
                dense: true,
                leading: Icon(Icons.report_outlined, color: color),
                title: Text(signal.userMessage),
                subtitle: Text(signal.reviewGuidance),
              ),
          ],
        ],
      ),
    );
  }
}
