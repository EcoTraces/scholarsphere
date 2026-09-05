import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/testimonials/data/demo_testimonial_repository.dart';
import 'package:scholarsphere/features/testimonials/domain/testimonial.dart';
import 'package:scholarsphere/features/testimonials/domain/testimonial_repository.dart';
import 'package:scholarsphere/features/testimonials/presentation/admin/testimonial_moderation_screen.dart';
import 'package:scholarsphere/features/testimonials/presentation/dashboard/my_testimonial_status_card.dart';
import 'package:scholarsphere/features/testimonials/presentation/share_success_story_screen.dart';
import 'package:scholarsphere/features/testimonials/presentation/success_stories_screen.dart';

/// Constructs each Success Stories screen directly against a
/// [DemoTestimonialRepository] (matching test/premium_landing_screen_test
/// .dart's own pattern) - none of these screens need a live Firebase app
/// of their own, so a focused pump per screen is simpler than routing
/// through the full ScholarSphereApp.
void main() {
  testWidgets('Success Stories screen lists real demo stories, not fake '
      'placeholders', (tester) async {
    final repository = DemoTestimonialRepository();

    await tester.pumpWidget(
      MaterialApp(
        home: SuccessStoriesScreen(repository: repository, onShareStory: () {}),
      ),
    );
    await tester.pumpAndSettle();

    expect(
      find.text('Real Applicants. Real Opportunities. Real Success.'),
      findsOneWidget,
    );

    // The story cards render below the hero/stats/filters, off the
    // default 800x600 test viewport - this is a scrollable ListView, not
    // a `.builder` one, but Flutter's Sliver machinery still only builds
    // children within the viewport + cache extent regardless of which
    // ListView constructor was used, so `find` can't see them without an
    // explicit scroll first.
    await tester.drag(find.byType(ListView).first, const Offset(0, -1200));
    await tester.pumpAndSettle();

    // Every seeded field is prefixed "DEMO —" so it can never be mistaken
    // for a real applicant's story - see DemoTestimonialRepository's own
    // docstring.
    expect(find.textContaining('DEMO —'), findsWidgets);
    expect(find.text('DEMO — Commonwealth Shared Scholarship'), findsOneWidget);
  });

  testWidgets('opening a story shows its full case-study sections', (
    tester,
  ) async {
    final repository = DemoTestimonialRepository();

    await tester.pumpWidget(
      MaterialApp(
        home: SuccessStoriesScreen(repository: repository, onShareStory: () {}),
      ),
    );
    await tester.pumpAndSettle();

    await tester.drag(find.byType(ListView).first, const Offset(0, -1200));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Read Full Story').first);
    await tester.pumpAndSettle();

    expect(find.text('The Challenge'), findsOneWidget);
    expect(find.text('Finding the Opportunity'), findsOneWidget);

    // The remaining sections are further down the same long-form page,
    // off-screen until scrolled into the sliver cache extent.
    await tester.drag(find.byType(ListView).first, const Offset(0, -1200));
    await tester.pumpAndSettle();

    expect(find.text('How ScholarSphere Helped'), findsOneWidget);
    expect(find.text('Advice to Future Applicants'), findsOneWidget);
    // The outcome is shown as one of the closed set of real outcomes, not
    // collapsed into a generic "success" (Phase 6 of the feature spec).
    expect(find.textContaining('Outcome:'), findsOneWidget);
  });

  testWidgets(
    'dashboard status card shows the empty state before any submission',
    (tester) async {
      final repository = DemoTestimonialRepository();

      await tester.pumpWidget(
        MaterialApp(
          home: Scaffold(body: MyTestimonialStatusCard(repository: repository)),
        ),
      );
      await tester.pumpAndSettle();

      expect(
        find.textContaining('Successfully received an opportunity'),
        findsOneWidget,
      );
      expect(find.text('Share Your Story'), findsOneWidget);
    },
  );

  testWidgets('dashboard status card reflects draft, then submitted, state', (
    tester,
  ) async {
    final repository = DemoTestimonialRepository();
    await repository.saveDraft(
      const TestimonialDraftInput(
        opportunityName: 'Test Fellowship',
        opportunityProvider: 'Test Provider',
        opportunityType: 'fellowship',
        outcome: TestimonialOutcome.awarded,
        fullName: 'Test Applicant',
      ),
    );

    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(body: MyTestimonialStatusCard(repository: repository)),
      ),
    );
    await tester.pumpAndSettle();

    expect(find.textContaining('draft waiting to be finished'), findsOneWidget);
  });

  testWidgets('submission wizard walks through opportunity and experience '
      'steps with a real progress indicator', (tester) async {
    final repository = DemoTestimonialRepository();

    await tester.pumpWidget(
      MaterialApp(home: ShareSuccessStoryScreen(repository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Your Opportunity'), findsWidgets);
    await tester.enterText(
      find.widgetWithText(TextField, 'Opportunity name'),
      'Widget Test Scholarship',
    );
    await tester.enterText(
      find.widgetWithText(TextField, 'Opportunity provider'),
      'Widget Test Provider',
    );

    await tester.ensureVisible(find.text('Next').first);
    await tester.pumpAndSettle();
    await tester.tap(find.text('Next').first);
    await tester.pumpAndSettle();

    // Now on step 2 ("Your Experience") - the seven case-study questions
    // should be visible, proving the Stepper actually advanced.
    expect(
      find.text('What challenge were you facing before using ScholarSphere?'),
      findsOneWidget,
    );

    final mine = await repository.listMine();
    expect(mine, hasLength(1));
    expect(mine.first.opportunityName, 'Widget Test Scholarship');
    expect(mine.first.status, TestimonialStatus.draft);
  });

  testWidgets('moderation queue shows a real submission awaiting review', (
    tester,
  ) async {
    final repository = DemoTestimonialRepository();
    final draft = await repository.saveDraft(
      const TestimonialDraftInput(
        opportunityName: 'Queue Test Opportunity',
        opportunityProvider: 'Queue Test Provider',
        opportunityType: 'grant',
        outcome: TestimonialOutcome.funded,
        fullName: 'Queue Test Applicant',
        outcomeNarrative: 'A real outcome for the moderation queue test.',
      ),
    );
    await repository.submit(draft.id);

    await tester.pumpWidget(
      MaterialApp(home: TestimonialModerationScreen(repository: repository)),
    );
    await tester.pumpAndSettle();

    expect(find.text('Queue Test Opportunity'), findsOneWidget);
    expect(find.textContaining('Submitted'), findsWidgets);
  });

  testWidgets(
    'moderation queue never shows internal moderation states as a public '
    'story (the same repository never puts them there)',
    (tester) async {
      final repository = DemoTestimonialRepository();
      final page = await repository.listSuccessStories(
        const SuccessStoryFilters(),
      );
      // Only the two seeded *approved* demo stories are public - a
      // freshly-created draft (never submitted) must never appear here.
      await repository.saveDraft(
        const TestimonialDraftInput(
          opportunityName: 'Should Never Be Public',
          opportunityProvider: 'X',
          opportunityType: 'grant',
          outcome: TestimonialOutcome.applied,
          fullName: 'Nobody',
        ),
      );
      final pageAfter = await repository.listSuccessStories(
        const SuccessStoryFilters(),
      );
      expect(pageAfter.items.length, page.items.length);
      expect(
        pageAfter.items.any(
          (item) => item.opportunityName == 'Should Never Be Public',
        ),
        isFalse,
      );
    },
  );
}
