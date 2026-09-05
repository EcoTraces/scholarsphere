import 'package:flutter/material.dart';

import '../../domain/testimonial.dart';
import '../../domain/testimonial_repository.dart';
import '../share_success_story_screen.dart';
import '../success_stories_screen.dart';

/// The dashboard card from Phase 19 of the feature spec. Self-contained
/// (own loading), so it drops into the dashboard body without touching
/// the existing `_DashboardData` pipeline. Shows the single most recent
/// testimonial's state if the applicant has one; the empty state
/// otherwise.
class MyTestimonialStatusCard extends StatefulWidget {
  const MyTestimonialStatusCard({super.key, required this.repository});

  final TestimonialRepository repository;

  @override
  State<MyTestimonialStatusCard> createState() =>
      _MyTestimonialStatusCardState();
}

class _MyTestimonialStatusCardState extends State<MyTestimonialStatusCard> {
  late Future<List<MyTestimonial>> _mine;

  @override
  void initState() {
    super.initState();
    _mine = widget.repository.listMine();
  }

  void _reload() => setState(() => _mine = widget.repository.listMine());

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<List<MyTestimonial>>(
      future: _mine,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const _StatusCard(
            title: 'Your Success Story',
            body: SizedBox(
              height: 24,
              width: 24,
              child: CircularProgressIndicator(strokeWidth: 2),
            ),
          );
        }
        final mine = snapshot.data;
        final testimonial = (mine == null || mine.isEmpty) ? null : mine.first;
        return _content(context, testimonial);
      },
    );
  }

  Widget _content(BuildContext context, MyTestimonial? testimonial) {
    void openWizard([MyTestimonial? existing]) async {
      final submitted = await Navigator.of(context).push<bool>(
        MaterialPageRoute(
          builder: (_) => ShareSuccessStoryScreen(
            repository: widget.repository,
            existing: existing,
          ),
        ),
      );
      if (submitted == true) _reload();
    }

    if (testimonial == null) {
      return _StatusCard(
        title: 'Your Success Story',
        body: const Text(
          'Successfully received an opportunity through ScholarSphere? '
          'Share your experience.',
        ),
        action: FilledButton(
          onPressed: () => openWizard(),
          child: const Text('Share Your Story'),
        ),
      );
    }
    switch (testimonial.status) {
      case TestimonialStatus.draft:
        return _StatusCard(
          title: 'Your Success Story',
          body: const Text('You have a draft waiting to be finished.'),
          action: OutlinedButton(
            onPressed: () => openWizard(testimonial),
            child: const Text('Continue your story'),
          ),
        );
      case TestimonialStatus.submitted:
      case TestimonialStatus.underReview:
        return const _StatusCard(
          title: 'Your Success Story',
          body: Text('Your story is being reviewed.'),
        );
      case TestimonialStatus.approved:
        return _StatusCard(
          title: 'Your Success Story',
          body: const Text('Your success story is live.'),
          action: OutlinedButton(
            onPressed: () => Navigator.of(context).push<void>(
              MaterialPageRoute(
                builder: (_) => SuccessStoriesScreen(
                  repository: widget.repository,
                  onShareStory: () => openWizard(),
                ),
              ),
            ),
            child: const Text('View Success Stories'),
          ),
        );
      case TestimonialStatus.rejected:
      case TestimonialStatus.changesRequested:
        return _StatusCard(
          title: 'Your Success Story',
          body: Text(
            testimonial.rejectionReason?.isNotEmpty == true
                ? testimonial.rejectionReason!
                : 'Your story needs an update before it can be published.',
          ),
          action: OutlinedButton(
            onPressed: () => openWizard(testimonial),
            child: const Text('Update your story'),
          ),
        );
      case TestimonialStatus.withdrawn:
        return _StatusCard(
          title: 'Your Success Story',
          body: const Text('Your success story is currently unpublished.'),
        );
    }
  }
}

class _StatusCard extends StatelessWidget {
  const _StatusCard({required this.title, required this.body, this.action});

  final String title;
  final Widget body;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(16),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              title,
              style: Theme.of(
                context,
              ).textTheme.titleMedium?.copyWith(fontWeight: FontWeight.w700),
            ),
            const SizedBox(height: 8),
            body,
            if (action != null) ...[
              const SizedBox(height: 12),
              Align(alignment: Alignment.centerLeft, child: action),
            ],
          ],
        ),
      ),
    );
  }
}
