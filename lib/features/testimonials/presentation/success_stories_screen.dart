import 'package:flutter/material.dart';

import '../domain/testimonial.dart';
import '../domain/testimonial_repository.dart';
import 'success_story_detail_screen.dart';
import 'widgets/success_story_card.dart';
import 'widgets/verification_badge.dart';

/// Public Success Stories landing page (Phase 2 of the feature spec):
/// hero, real (never-fabricated) trust statistics, search/filter, and a
/// paginated list of approved stories. Reachable from the applicant
/// dashboard's "Success Stories" panel and side navigation.
class SuccessStoriesScreen extends StatefulWidget {
  const SuccessStoriesScreen({
    super.key,
    required this.repository,
    required this.onShareStory,
  });

  final TestimonialRepository repository;
  final VoidCallback onShareStory;

  @override
  State<SuccessStoriesScreen> createState() => _SuccessStoriesScreenState();
}

class _SuccessStoriesScreenState extends State<SuccessStoriesScreen> {
  final _searchController = TextEditingController();
  final _filtersKey = GlobalKey();
  String? _opportunityType;
  String? _country;
  String? _degreeLevel;
  bool _verifiedOnly = false;
  String _sort = 'recent';

  late Future<TestimonialStats> _stats;
  final List<SuccessStorySummary> _items = [];
  int _page = 1;
  bool _hasMore = true;
  bool _loadingMore = false;
  bool _initialLoading = true;
  Object? _error;

  @override
  void initState() {
    super.initState();
    _stats = widget.repository.getStats();
    // Deferred rather than called directly: _loadFirstPage's first
    // statement is a setState() call, and initState() itself still runs
    // inside the framework's build phase - calling setState()
    // synchronously in that same call stack throws "setState() or
    // markNeedsBuild() called during build." Scheduling it as a
    // microtask lets this frame finish first.
    Future.microtask(_loadFirstPage);
  }

  @override
  void dispose() {
    _searchController.dispose();
    super.dispose();
  }

  SuccessStoryFilters get _filters => SuccessStoryFilters(
    keyword: _searchController.text.trim().isEmpty
        ? null
        : _searchController.text.trim(),
    opportunityType: _opportunityType,
    country: _country,
    degreeLevel: _degreeLevel,
    verifiedOnly: _verifiedOnly,
    sort: _sort,
  );

  Future<void> _loadFirstPage() async {
    setState(() {
      _initialLoading = true;
      _error = null;
      _items.clear();
      _page = 1;
      _hasMore = true;
    });
    try {
      final result = await widget.repository.listSuccessStories(
        _filters,
        page: 1,
      );
      if (!mounted) return;
      setState(() {
        _items.addAll(result.items);
        _hasMore = result.hasMore;
        _initialLoading = false;
      });
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _error = error;
        _initialLoading = false;
      });
    }
  }

  Future<void> _loadMore() async {
    if (_loadingMore || !_hasMore) return;
    setState(() => _loadingMore = true);
    try {
      final result = await widget.repository.listSuccessStories(
        _filters,
        page: _page + 1,
      );
      if (!mounted) return;
      setState(() {
        _items.addAll(result.items);
        _page += 1;
        _hasMore = result.hasMore;
        _loadingMore = false;
      });
    } catch (_) {
      if (!mounted) return;
      setState(() => _loadingMore = false);
    }
  }

  void _openStory(String slug) {
    Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) =>
            SuccessStoryDetailScreen(slug: slug, repository: widget.repository),
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Success Stories')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: widget.onShareStory,
        icon: const Icon(Icons.edit_outlined),
        label: const Text('Share Your Story'),
      ),
      body: RefreshIndicator(
        onRefresh: () async {
          setState(() => _stats = widget.repository.getStats());
          await _loadFirstPage();
        },
        child: ListView(
          padding: const EdgeInsets.all(16),
          children: [
            _Hero(
              onShareStory: widget.onShareStory,
              onExplore: () {
                final context = _filtersKey.currentContext;
                if (context != null) {
                  Scrollable.ensureVisible(
                    context,
                    duration: const Duration(milliseconds: 300),
                  );
                }
              },
            ),
            const SizedBox(height: 20),
            _TrustStats(statsFuture: _stats),
            const SizedBox(height: 20),
            _Filters(
              key: _filtersKey,
              searchController: _searchController,
              opportunityType: _opportunityType,
              country: _country,
              degreeLevel: _degreeLevel,
              verifiedOnly: _verifiedOnly,
              sort: _sort,
              onTypeChanged: (value) {
                setState(() => _opportunityType = value);
                _loadFirstPage();
              },
              onCountryChanged: (value) {
                setState(() => _country = value);
                _loadFirstPage();
              },
              onDegreeChanged: (value) {
                setState(() => _degreeLevel = value);
                _loadFirstPage();
              },
              onVerifiedChanged: (value) {
                setState(() => _verifiedOnly = value);
                _loadFirstPage();
              },
              onSortChanged: (value) {
                setState(() => _sort = value);
                _loadFirstPage();
              },
              onSearchSubmitted: _loadFirstPage,
            ),
            const SizedBox(height: 12),
            if (_initialLoading)
              const _ListSkeleton()
            else if (_error != null)
              _ErrorState(onRetry: _loadFirstPage)
            else if (_items.isEmpty)
              const _EmptyStories()
            else ...[
              for (final item in _items)
                Padding(
                  padding: const EdgeInsets.only(bottom: 12),
                  child: SuccessStoryCard(
                    story: item,
                    onTap: () => _openStory(item.slug),
                  ),
                ),
              if (_hasMore)
                Padding(
                  padding: const EdgeInsets.symmetric(vertical: 16),
                  child: Center(
                    child: _loadingMore
                        ? const CircularProgressIndicator()
                        : OutlinedButton(
                            onPressed: _loadMore,
                            child: const Text('Load more stories'),
                          ),
                  ),
                ),
            ],
          ],
        ),
      ),
    );
  }
}

class _Hero extends StatelessWidget {
  const _Hero({required this.onShareStory, required this.onExplore});

  final VoidCallback onShareStory;
  final VoidCallback onExplore;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(24),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Real Applicants. Real Opportunities. Real Success.',
              style: theme.textTheme.headlineSmall?.copyWith(
                fontWeight: FontWeight.w800,
              ),
            ),
            const SizedBox(height: 12),
            Text(
              'Learn how successful applicants used ScholarSphere to '
              'discover, prepare for, and apply to scholarships, '
              'fellowships, grants, internships, and other opportunities. '
              'Success depends on eligibility, application quality, '
              'competition, and each opportunity provider\'s own selection '
              'process - these stories show how applicants navigated that '
              'process, not a guarantee of the same outcome.',
              style: theme.textTheme.bodyMedium,
            ),
            const SizedBox(height: 16),
            Wrap(
              spacing: 12,
              runSpacing: 8,
              children: [
                FilledButton.icon(
                  onPressed: onShareStory,
                  icon: const Icon(Icons.edit_outlined),
                  label: const Text('Share Your Success Story'),
                ),
                OutlinedButton.icon(
                  onPressed: onExplore,
                  icon: const Icon(Icons.explore_outlined),
                  label: const Text('Explore Success Stories'),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

class _TrustStats extends StatelessWidget {
  const _TrustStats({required this.statsFuture});

  final Future<TestimonialStats> statsFuture;

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<TestimonialStats>(
      future: statsFuture,
      builder: (context, snapshot) {
        final stats = snapshot.data;
        // Every statistic here is a real, live-computed aggregate from
        // the backend (app/services/testimonial_service.py::public_stats)
        // - a metric with nothing real behind it comes back as `null` and
        // is skipped entirely, rather than ever showing a fabricated "0"
        // or placeholder number (Phase 3 of the feature spec).
        if (stats == null || !stats.hasAnyStat) return const SizedBox.shrink();
        final tiles = <(String, int?)>[
          ('Success stories', stats.totalStories),
          ('Verified stories', stats.verifiedStories),
          ('Countries represented', stats.countriesRepresented),
          ('Opportunity types', stats.opportunityTypesRepresented),
          ('Fields of study', stats.fieldsOfStudyRepresented),
        ].where((tile) => tile.$2 != null).toList();
        if (tiles.isEmpty) return const SizedBox.shrink();
        return Wrap(
          spacing: 12,
          runSpacing: 12,
          children: [
            for (final tile in tiles)
              SizedBox(
                width: 150,
                child: Card(
                  child: Padding(
                    padding: const EdgeInsets.all(16),
                    child: Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Text(
                          '${tile.$2}',
                          style: Theme.of(context).textTheme.headlineMedium
                              ?.copyWith(fontWeight: FontWeight.w800),
                        ),
                        const SizedBox(height: 4),
                        Text(
                          tile.$1,
                          style: Theme.of(context).textTheme.bodySmall,
                        ),
                      ],
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

class _Filters extends StatefulWidget {
  const _Filters({
    super.key,
    required this.searchController,
    required this.opportunityType,
    required this.country,
    required this.degreeLevel,
    required this.verifiedOnly,
    required this.sort,
    required this.onTypeChanged,
    required this.onCountryChanged,
    required this.onDegreeChanged,
    required this.onVerifiedChanged,
    required this.onSortChanged,
    required this.onSearchSubmitted,
  });

  final TextEditingController searchController;
  final String? opportunityType;
  final String? country;
  final String? degreeLevel;
  final bool verifiedOnly;
  final String sort;
  final ValueChanged<String?> onTypeChanged;
  final ValueChanged<String?> onCountryChanged;
  final ValueChanged<String?> onDegreeChanged;
  final ValueChanged<bool> onVerifiedChanged;
  final ValueChanged<String> onSortChanged;
  final VoidCallback onSearchSubmitted;

  @override
  State<_Filters> createState() => _FiltersState();
}

class _FiltersState extends State<_Filters> {
  late final _countryController = TextEditingController(
    text: widget.country ?? '',
  );

  @override
  void dispose() {
    _countryController.dispose();
    super.dispose();
  }

  static const _opportunityTypes = [
    'scholarship',
    'fellowship',
    'grant',
    'internship',
    'job',
    'training',
  ];
  static const _degreeLevels = ['Undergraduate', 'Masters', 'PhD', 'Other'];

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        TextField(
          controller: widget.searchController,
          textInputAction: TextInputAction.search,
          onSubmitted: (_) => widget.onSearchSubmitted(),
          decoration: InputDecoration(
            hintText: 'Search stories, opportunities, or universities',
            prefixIcon: const Icon(Icons.search),
            border: const OutlineInputBorder(),
            suffixIcon: IconButton(
              icon: const Icon(Icons.arrow_forward),
              onPressed: widget.onSearchSubmitted,
            ),
          ),
        ),
        const SizedBox(height: 12),
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          child: Row(
            children: [
              DropdownButton<String?>(
                value: widget.opportunityType,
                hint: const Text('Opportunity type'),
                items: [
                  const DropdownMenuItem(value: null, child: Text('Any type')),
                  for (final type in _opportunityTypes)
                    DropdownMenuItem(value: type, child: Text(type)),
                ],
                onChanged: widget.onTypeChanged,
              ),
              const SizedBox(width: 12),
              DropdownButton<String?>(
                value: widget.degreeLevel,
                hint: const Text('Degree level'),
                items: [
                  const DropdownMenuItem(value: null, child: Text('Any level')),
                  for (final level in _degreeLevels)
                    DropdownMenuItem(value: level, child: Text(level)),
                ],
                onChanged: widget.onDegreeChanged,
              ),
              const SizedBox(width: 12),
              SizedBox(
                width: 160,
                child: TextField(
                  controller: _countryController,
                  textInputAction: TextInputAction.done,
                  decoration: const InputDecoration(
                    hintText: 'Country',
                    isDense: true,
                    border: OutlineInputBorder(),
                  ),
                  onSubmitted: (value) => widget.onCountryChanged(
                    value.trim().isEmpty ? null : value.trim(),
                  ),
                ),
              ),
              const SizedBox(width: 12),
              DropdownButton<String>(
                value: widget.sort,
                items: const [
                  DropdownMenuItem(value: 'recent', child: Text('Most recent')),
                  DropdownMenuItem(
                    value: 'featured',
                    child: Text('Featured first'),
                  ),
                  DropdownMenuItem(
                    value: 'most_viewed',
                    child: Text('Most viewed'),
                  ),
                  DropdownMenuItem(
                    value: 'verified_first',
                    child: Text('Verified first'),
                  ),
                ],
                onChanged: (value) {
                  if (value != null) widget.onSortChanged(value);
                },
              ),
              const SizedBox(width: 12),
              FilterChip(
                label: const Text('Verified only'),
                selected: widget.verifiedOnly,
                onSelected: widget.onVerifiedChanged,
                avatar: const VerificationBadgeIcon(),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _ListSkeleton extends StatelessWidget {
  const _ListSkeleton();

  @override
  Widget build(BuildContext context) {
    return Column(
      children: List.generate(
        3,
        (index) => Padding(
          padding: const EdgeInsets.only(bottom: 12),
          child: Card(
            child: Container(
              height: 140,
              padding: const EdgeInsets.all(16),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Container(
                    height: 16,
                    width: 180,
                    color: Theme.of(
                      context,
                    ).colorScheme.surfaceContainerHighest,
                  ),
                  Container(
                    height: 12,
                    width: double.infinity,
                    color: Theme.of(
                      context,
                    ).colorScheme.surfaceContainerHighest,
                  ),
                  Container(
                    height: 12,
                    width: 220,
                    color: Theme.of(
                      context,
                    ).colorScheme.surfaceContainerHighest,
                  ),
                ],
              ),
            ),
          ),
        ),
      ),
    );
  }
}

class _EmptyStories extends StatelessWidget {
  const _EmptyStories();

  @override
  Widget build(BuildContext context) {
    return const Padding(
      padding: EdgeInsets.symmetric(vertical: 56),
      child: Center(
        child: Column(
          children: [
            Icon(Icons.auto_stories_outlined, size: 42),
            SizedBox(height: 12),
            Text(
              'Success stories are coming soon.',
              style: TextStyle(fontWeight: FontWeight.w700),
            ),
            SizedBox(height: 4),
            Text(
              'Be among the first ScholarSphere users to share your '
              'journey.',
              textAlign: TextAlign.center,
            ),
          ],
        ),
      ),
    );
  }
}

class _ErrorState extends StatelessWidget {
  const _ErrorState({required this.onRetry});

  final VoidCallback onRetry;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 56),
      child: Center(
        child: Column(
          children: [
            const Icon(Icons.error_outline, size: 42),
            const SizedBox(height: 12),
            const Text('Something went wrong while loading success stories.'),
            const SizedBox(height: 12),
            OutlinedButton(onPressed: onRetry, child: const Text('Try again')),
          ],
        ),
      ),
    );
  }
}
