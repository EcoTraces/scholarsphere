import 'package:flutter/material.dart';

import '../../domain/testimonial.dart';
import 'story_avatar.dart';
import 'verification_badge.dart';

/// The professional testimonial card from Phase 4 of the feature spec:
/// avatar, display name (already privacy-resolved server-side), verified
/// indicator, degree/program, university, country, opportunity, year, a
/// short excerpt, features used, and a "Read full story" CTA. A
/// [SuccessStorySummary] never carries a field the applicant chose to
/// withhold, so this card never needs its own privacy logic - it only
/// renders what it was given.
class SuccessStoryCard extends StatelessWidget {
  const SuccessStoryCard({
    super.key,
    required this.story,
    required this.onTap,
    this.featuredStyle = false,
  });

  final SuccessStorySummary story;
  final VoidCallback onTap;
  final bool featuredStyle;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final subtitleParts = [
      if (story.program != null) story.program,
      if (story.university != null) story.university,
      if (story.country != null) story.country,
    ].whereType<String>().join(' · ');

    return Card(
      elevation: featuredStyle ? 3 : 1,
      shape: featuredStyle
          ? RoundedRectangleBorder(
              borderRadius: BorderRadius.circular(12),
              side: BorderSide(color: theme.colorScheme.primary, width: 1.5),
            )
          : null,
      child: InkWell(
        borderRadius: BorderRadius.circular(12),
        onTap: onTap,
        child: Padding(
          padding: const EdgeInsets.all(16),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  StoryAvatar(
                    displayName: story.displayName,
                    photoStoragePath: story.photoStoragePath,
                  ),
                  const SizedBox(width: 12),
                  Expanded(
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          story.displayName,
                          style: theme.textTheme.titleMedium?.copyWith(
                            fontWeight: FontWeight.w700,
                          ),
                        ),
                        if (subtitleParts.isNotEmpty)
                          Text(
                            subtitleParts,
                            style: theme.textTheme.bodySmall,
                            maxLines: 1,
                            overflow: TextOverflow.ellipsis,
                          ),
                      ],
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 10),
              VerificationBadges(badges: story.badges),
              const SizedBox(height: 10),
              Wrap(
                spacing: 8,
                runSpacing: 4,
                children: [
                  Chip(
                    label: Text(story.opportunityName),
                    visualDensity: VisualDensity.compact,
                  ),
                  if (story.successYear != null)
                    Chip(
                      label: Text('${story.successYear}'),
                      visualDensity: VisualDensity.compact,
                    ),
                ],
              ),
              if (story.excerpt.isNotEmpty) ...[
                const SizedBox(height: 10),
                Text(
                  '"${story.excerpt}"',
                  style: theme.textTheme.bodyMedium?.copyWith(
                    fontStyle: FontStyle.italic,
                  ),
                  maxLines: 3,
                  overflow: TextOverflow.ellipsis,
                ),
              ],
              if (story.featuresUsed.isNotEmpty) ...[
                const SizedBox(height: 10),
                Wrap(
                  spacing: 6,
                  runSpacing: 4,
                  children: [
                    for (final feature in story.featuresUsed)
                      Chip(
                        avatar: const Icon(Icons.check, size: 14),
                        label: Text(featureLabel(feature)),
                        visualDensity: VisualDensity.compact,
                        materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                      ),
                  ],
                ),
              ],
              const SizedBox(height: 12),
              Align(
                alignment: Alignment.centerRight,
                child: TextButton(
                  onPressed: onTap,
                  child: const Text('Read Full Story'),
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
