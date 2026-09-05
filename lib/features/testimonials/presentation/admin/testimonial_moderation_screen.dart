import 'package:flutter/material.dart';

import '../../domain/testimonial.dart';
import '../../domain/testimonial_repository.dart';
import 'testimonial_review_screen.dart';

/// Phase 11 of the feature spec: the moderation queue. Reachable from the
/// Moderator Dashboard (the role that actually holds the
/// `moderateContent` permission this whole admin surface is gated on -
/// see `require_permissions("moderateContent")` in
/// `app/api/routes/testimonials.py`).
class TestimonialModerationScreen extends StatefulWidget {
  const TestimonialModerationScreen({super.key, required this.repository});

  final TestimonialRepository repository;

  @override
  State<TestimonialModerationScreen> createState() =>
      _TestimonialModerationScreenState();
}

class _TestimonialModerationScreenState
    extends State<TestimonialModerationScreen> {
  TestimonialStatus? _statusFilter = TestimonialStatus.submitted;
  late Future<AdminTestimonialPage> _page;

  static const _tabs = <(String, TestimonialStatus?)>[
    ('Pending', TestimonialStatus.submitted),
    ('Under review', TestimonialStatus.underReview),
    ('Changes requested', TestimonialStatus.changesRequested),
    ('Approved', TestimonialStatus.approved),
    ('Rejected', TestimonialStatus.rejected),
    ('Withdrawn', TestimonialStatus.withdrawn),
    ('All', null),
  ];

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    setState(() {
      _page = widget.repository.listForModeration(
        AdminTestimonialFilters(status: _statusFilter),
        page: 1,
        pageSize: 50,
      );
    });
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Testimonial Moderation')),
      body: Column(
        children: [
          Padding(
            padding: const EdgeInsets.all(12),
            child: SingleChildScrollView(
              scrollDirection: Axis.horizontal,
              child: Row(
                children: [
                  for (final tab in _tabs)
                    Padding(
                      padding: const EdgeInsets.only(right: 8),
                      child: ChoiceChip(
                        label: Text(tab.$1),
                        selected: _statusFilter == tab.$2,
                        onSelected: (_) {
                          _statusFilter = tab.$2;
                          _reload();
                        },
                      ),
                    ),
                ],
              ),
            ),
          ),
          Expanded(
            child: RefreshIndicator(
              onRefresh: () async => _reload(),
              child: FutureBuilder<AdminTestimonialPage>(
                future: _page,
                builder: (context, snapshot) {
                  if (snapshot.connectionState == ConnectionState.waiting) {
                    return const Center(child: CircularProgressIndicator());
                  }
                  if (snapshot.hasError) {
                    return ListView(
                      children: const [
                        Padding(
                          padding: EdgeInsets.all(32),
                          child: Center(
                            child: Text(
                              'Something went wrong while loading the '
                              'moderation queue.',
                            ),
                          ),
                        ),
                      ],
                    );
                  }
                  final items = snapshot.data!.items;
                  if (items.isEmpty) {
                    return ListView(
                      children: const [
                        Padding(
                          padding: EdgeInsets.all(32),
                          child: Center(
                            child: Text('Nothing in this queue right now.'),
                          ),
                        ),
                      ],
                    );
                  }
                  return ListView.builder(
                    itemCount: items.length,
                    itemBuilder: (context, index) {
                      final item = items[index];
                      return ListTile(
                        title: Text(item.opportunityName),
                        subtitle: Text(
                          '${item.fullName} · ${item.status.label}'
                          '${item.country != null ? ' · ${item.country}' : ''}',
                        ),
                        trailing:
                            item.verificationStatus ==
                                TestimonialVerificationStatus.verified
                            ? const Icon(
                                Icons.verified,
                                color: Color(0xFF007C72),
                              )
                            : null,
                        onTap: () async {
                          await Navigator.of(context).push<void>(
                            MaterialPageRoute(
                              builder: (_) => TestimonialReviewScreen(
                                repository: widget.repository,
                                testimonialId: item.id,
                              ),
                            ),
                          );
                          _reload();
                        },
                      );
                    },
                  );
                },
              ),
            ),
          ),
        ],
      ),
    );
  }
}
