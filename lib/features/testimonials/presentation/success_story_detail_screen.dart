import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../domain/testimonial.dart';
import '../domain/testimonial_repository.dart';
import 'widgets/story_avatar.dart';
import 'widgets/success_story_card.dart';
import 'widgets/verification_badge.dart';

/// The long-form success-story page from Phase 6 of the feature spec -
/// applicant header, the seven-question case study broken into clearly
/// labeled sections, an honest (never-collapsed-to-"success") outcome,
/// an application timeline built only from timestamps this story
/// actually has, related stories, and lightweight reactions.
class SuccessStoryDetailScreen extends StatefulWidget {
  const SuccessStoryDetailScreen({
    super.key,
    required this.slug,
    required this.repository,
  });

  final String slug;
  final TestimonialRepository repository;

  @override
  State<SuccessStoryDetailScreen> createState() =>
      _SuccessStoryDetailScreenState();
}

class _SuccessStoryDetailScreenState extends State<SuccessStoryDetailScreen> {
  late Future<SuccessStoryDetail> _story;
  Future<List<SuccessStorySummary>>? _related;
  TestimonialReactionType? _myReaction;

  @override
  void initState() {
    super.initState();
    _story = widget.repository.getStory(widget.slug);
    _story.then((_) {
      if (!mounted) return;
      setState(() {
        _related = widget.repository.getRelatedStories(widget.slug);
      });
    });
  }

  Future<void> _toggleReaction(TestimonialReactionType type) async {
    final previous = _myReaction;
    setState(() => _myReaction = previous == type ? null : type);
    try {
      final updated = previous == type
          ? await widget.repository.removeReaction(widget.slug)
          : await widget.repository.react(widget.slug, type);
      if (!mounted) return;
      setState(() => _story = Future.value(updated));
    } catch (_) {
      if (!mounted) return;
      setState(() => _myReaction = previous);
      ScaffoldMessenger.of(context).showSnackBar(
        const SnackBar(content: Text('Could not save your reaction.')),
      );
    }
  }

  void _copyLink(String slug) {
    Clipboard.setData(
      ClipboardData(text: 'https://scholarsphere.app/success-stories/$slug'),
    );
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Link copied.')));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Success Story')),
      body: FutureBuilder<SuccessStoryDetail>(
        future: _story,
        builder: (context, snapshot) {
          if (snapshot.connectionState == ConnectionState.waiting) {
            return const Center(child: CircularProgressIndicator());
          }
          if (snapshot.hasError) {
            return _ErrorState(
              onRetry: () => setState(() {
                _story = widget.repository.getStory(widget.slug);
              }),
            );
          }
          final story = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(16),
            children: [
              _Header(story: story, onCopyLink: () => _copyLink(story.slug)),
              const SizedBox(height: 20),
              _Section(title: 'The Challenge', body: story.challenge),
              _Section(
                title: 'Finding the Opportunity',
                body: story.discoveryStory,
              ),
              _Section(
                title: 'Preparing the Application',
                body: story.preparationStory,
              ),
              _Section(
                title: 'How ScholarSphere Helped',
                body: story.scholarsphereHelp,
              ),
              if (story.featuresUsed.isNotEmpty)
                Padding(
                  padding: const EdgeInsets.only(bottom: 16),
                  child: Wrap(
                    spacing: 6,
                    runSpacing: 6,
                    children: [
                      for (final feature in story.featuresUsed)
                        Chip(
                          avatar: const Icon(Icons.check, size: 14),
                          label: Text(featureLabel(feature)),
                          visualDensity: VisualDensity.compact,
                        ),
                    ],
                  ),
                ),
              _OutcomeSection(story: story),
              _Section(title: 'The Outcome', body: story.outcomeNarrative),
              _Section(title: 'The Impact', body: story.impact),
              _Section(
                title: 'Advice to Future Applicants',
                body: story.advice,
              ),
              const SizedBox(height: 20),
              _Reactions(
                story: story,
                selected: _myReaction,
                onSelect: _toggleReaction,
              ),
              const SizedBox(height: 24),
              if (_related != null)
                _RelatedStories(
                  future: _related!,
                  repository: widget.repository,
                ),
            ],
          );
        },
      ),
    );
  }
}

class _Header extends StatelessWidget {
  const _Header({required this.story, required this.onCopyLink});

  final SuccessStoryDetail story;
  final VoidCallback onCopyLink;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final subtitleParts = [
      if (story.program != null) story.program,
      if (story.university != null) story.university,
      if (story.country != null) story.country,
    ].whereType<String>().join(' · ');
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(20),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                StoryAvatar(
                  displayName: story.displayName,
                  photoStoragePath: story.photoStoragePath,
                  radius: 30,
                ),
                const SizedBox(width: 16),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        story.displayName,
                        style: theme.textTheme.headlineSmall?.copyWith(
                          fontWeight: FontWeight.w800,
                        ),
                      ),
                      if (subtitleParts.isNotEmpty)
                        Text(subtitleParts, style: theme.textTheme.bodyMedium),
                    ],
                  ),
                ),
                IconButton(
                  tooltip: 'Copy link',
                  icon: const Icon(Icons.link),
                  onPressed: onCopyLink,
                ),
              ],
            ),
            const SizedBox(height: 12),
            VerificationBadges(badges: story.badges),
            const SizedBox(height: 12),
            Wrap(
              spacing: 8,
              runSpacing: 6,
              children: [
                Chip(label: Text(story.opportunityName)),
                Chip(label: Text(story.opportunityProvider)),
                if (story.successYear != null)
                  Chip(label: Text('${story.successYear}')),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _Section extends StatelessWidget {
  const _Section({required this.title, required this.body});

  final String title;
  final String? body;

  @override
  Widget build(BuildContext context) {
    if (body == null || body!.trim().isEmpty) return const SizedBox.shrink();
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            title,
            style: theme.textTheme.titleLarge?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
          const SizedBox(height: 8),
          Text(body!, style: theme.textTheme.bodyLarge),
        ],
      ),
    );
  }
}

/// Phase 6: "Clearly distinguish: Applied / Shortlisted / Interviewed /
/// Selected / Awarded / Admitted / Funded / Other. Do NOT collapse all
/// outcomes into 'success'." - this is the one place that distinction is
/// shown prominently, deliberately separate from the free-text "Outcome"
/// narrative section below it.
class _OutcomeSection extends StatelessWidget {
  const _OutcomeSection({required this.story});

  final SuccessStoryDetail story;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Padding(
      padding: const EdgeInsets.only(bottom: 20),
      child: Row(
        children: [
          Icon(Icons.emoji_events_outlined, color: theme.colorScheme.primary),
          const SizedBox(width: 8),
          Text(
            'Outcome: ${story.outcome.label}',
            style: theme.textTheme.titleMedium?.copyWith(
              fontWeight: FontWeight.w700,
            ),
          ),
        ],
      ),
    );
  }
}

class _Reactions extends StatelessWidget {
  const _Reactions({
    required this.story,
    required this.selected,
    required this.onSelect,
  });

  final SuccessStoryDetail story;
  final TestimonialReactionType? selected;
  final ValueChanged<TestimonialReactionType> onSelect;

  @override
  Widget build(BuildContext context) {
    final counts = {
      TestimonialReactionType.helpful: story.helpfulCount,
      TestimonialReactionType.inspiring: story.inspiringCount,
      TestimonialReactionType.useful: story.usefulCount,
    };
    return Wrap(
      spacing: 8,
      children: [
        for (final type in TestimonialReactionType.values)
          FilterChip(
            label: Text('${type.label} (${counts[type]})'),
            selected: selected == type,
            onSelected: (_) => onSelect(type),
          ),
      ],
    );
  }
}

class _RelatedStories extends StatelessWidget {
  const _RelatedStories({required this.future, required this.repository});

  final Future<List<SuccessStorySummary>> future;
  final TestimonialRepository repository;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<SuccessStorySummary>>(
      future: future,
      builder: (context, snapshot) {
        final items = snapshot.data ?? const [];
        if (items.isEmpty) return const SizedBox.shrink();
        return Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Related Success Stories',
              style: Theme.of(
                context,
              ).textTheme.titleLarge?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 12),
            for (final item in items)
              Padding(
                padding: const EdgeInsets.only(bottom: 12),
                child: SuccessStoryCard(
                  story: item,
                  onTap: () => Navigator.of(context).pushReplacement(
                    MaterialPageRoute<void>(
                      builder: (_) => SuccessStoryDetailScreen(
                        slug: item.slug,
                        repository: repository,
                      ),
                    ),
                  ),
                ),
              ),
          ],
        );
      },
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Center(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          const Icon(Icons.error_outline, size: 42),
          const SizedBox(height: 12),
          const Text('This success story could not be loaded.'),
          const SizedBox(height: 12),
          OutlinedButton(onPressed: onRetry, child: const Text('Try again')),
        ],
      ),
    );
  }
}
