import 'package:flutter/material.dart';

/// Phase 8 of the feature spec: badges must never be used loosely - each
/// one has one specific, tooltip-explained meaning, and "Verified" is
/// used only when the backend's `verification_status` is actually
/// `verified` (never merely because a story exists or was submitted).
/// Icon + color + text together (never color alone), so the distinction
/// still reads for a colorblind viewer or a screen reader.
class VerificationBadges extends StatelessWidget {
  const VerificationBadges({super.key, required this.badges});

  final List<String> badges;

  @override
  Widget build(BuildContext context) {
    return Wrap(
      spacing: 6,
      runSpacing: 6,
      children: [for (final badge in badges) _badgeFor(context, badge)],
    );
  }

  Widget _badgeFor(BuildContext context, String badge) {
    switch (badge) {
      case 'verified':
        return const Tooltip(
          message:
              'Verified means ScholarSphere reviewed supporting '
              'information associated with this success story.',
          child: Chip(
            avatar: Icon(Icons.verified, size: 16, color: Color(0xFF007C72)),
            label: Text('Verified Success'),
            visualDensity: VisualDensity.compact,
          ),
        );
      case 'featured':
        return const Tooltip(
          message:
              'Featured Story: highlighted by ScholarSphere staff as an '
              'outstanding example.',
          child: Chip(
            avatar: Icon(Icons.star, size: 16, color: Color(0xFFB8860B)),
            label: Text('Featured Story'),
            visualDensity: VisualDensity.compact,
          ),
        );
      case 'under_review':
        return const Tooltip(
          message: 'This story has been submitted and is awaiting review.',
          child: Chip(
            avatar: Icon(Icons.hourglass_empty, size: 16),
            label: Text('Under Review'),
            visualDensity: VisualDensity.compact,
          ),
        );
      case 'community':
      default:
        return const Tooltip(
          message:
              'Community Story: shared by an applicant and passed basic '
              'content review, not independently verified by '
              'ScholarSphere.',
          child: Chip(
            avatar: Icon(Icons.groups_outlined, size: 16),
            label: Text('Community Story'),
            visualDensity: VisualDensity.compact,
          ),
        );
    }
  }
}

/// A compact standalone verified icon, for contexts (e.g. a filter chip
/// avatar) too tight for the full [VerificationBadges] chip.
class VerificationBadgeIcon extends StatelessWidget {
  const VerificationBadgeIcon({super.key});

  @override
  Widget build(BuildContext context) =>
      const Icon(Icons.verified, size: 16, color: Color(0xFF007C72));
}
