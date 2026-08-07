import 'package:flutter/material.dart';

import '../domain/eligibility_match.dart';

class EligibilityMatchPanel extends StatelessWidget {
  const EligibilityMatchPanel({super.key, required this.match});

  final EligibilityMatch match;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        border: Border.all(color: Theme.of(context).colorScheme.outlineVariant),
        borderRadius: BorderRadius.circular(8),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Expanded(
                child: Text(
                  'Eligibility score: ${match.score}% - ${match.strength}',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
              ),
              CircularProgressIndicator(value: match.score / 100),
            ],
          ),
          const SizedBox(height: 18),
          if (match.matched.isNotEmpty)
            _ConditionGroup(
              title: 'Matched requirements',
              conditions: match.matched,
              icon: Icons.check_circle_outline,
              color: const Color(0xFF007C72),
            ),
          if (match.missing.isNotEmpty)
            _ConditionGroup(
              title: 'Missing requirements',
              conditions: match.missing,
              icon: Icons.cancel_outlined,
              color: Theme.of(context).colorScheme.error,
            ),
          if (match.uncertain.isNotEmpty)
            _ConditionGroup(
              title: 'Uncertain requirements',
              conditions: match.uncertain,
              icon: Icons.help_outline,
              color: const Color(0xFF8A5A00),
            ),
        ],
      ),
    );
  }
}

class _ConditionGroup extends StatelessWidget {
  const _ConditionGroup({
    required this.title,
    required this.conditions,
    required this.icon,
    required this.color,
  });

  final String title;
  final List<MatchCondition> conditions;
  final IconData icon;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 12),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          for (final condition in conditions)
            ListTile(
              contentPadding: EdgeInsets.zero,
              dense: true,
              leading: Icon(icon, color: color),
              title: Text(condition.label),
              subtitle: Text(condition.explanation),
            ),
        ],
      ),
    );
  }
}
