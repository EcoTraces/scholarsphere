import 'package:flutter/material.dart';

import '../../domain/testimonial.dart';
import '../../domain/testimonial_repository.dart';
import '../success_story_detail_screen.dart';
import '../widgets/success_story_card.dart';

/// The dashboard-integrated Success Stories section from Phase 18 of the
/// feature spec (adapted from a separate marketing homepage - this app
/// has no such page distinct from the applicant dashboard, which is
/// already every signed-in applicant's "home"). Shows 3-6 real approved
/// stories, self-contained (own loading/empty/error handling) so it can
/// be dropped into the dashboard body without touching its existing
/// `_DashboardData` loading pipeline.
class SuccessStoriesDashboardPanel extends StatefulWidget {
  const SuccessStoriesDashboardPanel({
    super.key,
    required this.repository,
    required this.onViewAll,
    required this.onShareStory,
  });

  final TestimonialRepository repository;
  final VoidCallback onViewAll;
  final VoidCallback onShareStory;

  @override
  State<SuccessStoriesDashboardPanel> createState() =>
      _SuccessStoriesDashboardPanelState();
}

class _SuccessStoriesDashboardPanelState
    extends State<SuccessStoriesDashboardPanel> {
  late Future<SuccessStoryPage> _page;

  @override
  void initState() {
    super.initState();
    _page = widget.repository.listSuccessStories(
      const SuccessStoryFilters(sort: 'featured'),
      page: 1,
      pageSize: 6,
    );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<SuccessStoryPage>(
      future: _page,
      builder: (context, snapshot) {
        if (snapshot.connectionState == ConnectionState.waiting) {
          return const SizedBox.shrink();
        }
        if (snapshot.hasError || (snapshot.data?.items.isEmpty ?? true)) {
          // Quietly absent rather than an error banner on the dashboard -
          // Phase 20's empty state ("Success stories are coming soon")
          // belongs on the dedicated Success Stories screen, not as
          // dashboard clutter when there is nothing to show yet.
          return const SizedBox.shrink();
        }
        final items = snapshot.data!.items;
        return Card(
          child: Padding(
            padding: const EdgeInsets.all(20),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Expanded(
                      child: Text(
                        'ScholarSphere Success Stories',
                        style: Theme.of(context).textTheme.titleLarge?.copyWith(
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                    ),
                    TextButton(
                      onPressed: widget.onViewAll,
                      child: const Text('View All'),
                    ),
                  ],
                ),
                const SizedBox(height: 4),
                const Text(
                  'See how applicants used ScholarSphere to navigate real '
                  'scholarship and opportunity applications.',
                ),
                const SizedBox(height: 12),
                SizedBox(
                  height: 260,
                  child: ListView.separated(
                    scrollDirection: Axis.horizontal,
                    itemCount: items.length,
                    separatorBuilder: (_, _) => const SizedBox(width: 12),
                    itemBuilder: (context, index) {
                      final story = items[index];
                      return SizedBox(
                        width: 300,
                        child: SuccessStoryCard(
                          story: story,
                          featuredStyle: story.featured,
                          onTap: () => Navigator.of(context).push<void>(
                            MaterialPageRoute(
                              builder: (_) => SuccessStoryDetailScreen(
                                slug: story.slug,
                                repository: widget.repository,
                              ),
                            ),
                          ),
                        ),
                      );
                    },
                  ),
                ),
                const SizedBox(height: 12),
                OutlinedButton.icon(
                  onPressed: widget.onShareStory,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Share Your Story'),
                ),
              ],
            ),
          ),
        );
      },
    );
  }
}
