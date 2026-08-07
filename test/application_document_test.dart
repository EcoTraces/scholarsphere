import 'package:flutter_test/flutter_test.dart';
import 'package:scholarsphere/features/applications/data/demo_application_repository.dart';
import 'package:scholarsphere/features/applications/domain/application_record.dart';
import 'package:scholarsphere/features/documents/data/demo_document_repository.dart';
import 'package:scholarsphere/features/documents/domain/document_readiness.dart';
import 'package:scholarsphere/features/documents/domain/document_readiness_service.dart';
import 'package:scholarsphere/features/opportunities/data/demo_opportunity_repository.dart';

void main() {
  test(
    'saved opportunity progresses through the application tracker',
    () async {
      final clock = DateTime(2026, 7, 28);
      final repository = DemoApplicationRepository(clock: () => clock);
      final opportunity =
          (await DemoOpportunityRepository().getPublished()).first;

      final saved = await repository.saveOpportunity('applicant', opportunity);
      await repository.update(
        saved.copyWith(
          stage: ApplicationStage.applicationSubmitted,
          applicationDate: DateTime(2026, 8, 1),
          applicationReferenceNumber: 'APP-2026-100',
          personalNotes: 'Submitted through the official portal.',
        ),
      );
      final records = await repository.getForUser('applicant');

      expect(records.single.stage, ApplicationStage.applicationSubmitted);
      expect(records.single.applicationReferenceNumber, 'APP-2026-100');
    },
  );

  test('readiness counts encrypted owner documents', () async {
    final repository = DemoDocumentRepository();
    final opportunity =
        (await DemoOpportunityRepository().getPublished()).first;
    for (final type in const [
      DocumentType.curriculumVitae,
      DocumentType.academicTranscript,
      DocumentType.personalStatement,
    ]) {
      await repository.add(
        UserDocument(
          id: type.name,
          ownerUserId: 'applicant',
          type: type,
          fileName: '${type.name}.encrypted',
          uploadedAt: DateTime(2026, 7, 28),
          encryptedAtRest: true,
        ),
      );
    }

    final documents = await repository.getForUser('applicant');
    final readiness = const DocumentReadinessService().evaluate(
      opportunity,
      documents,
    );

    expect(readiness.requiredCount, 4);
    expect(readiness.readyCount, 3);
    expect(readiness.missing, {DocumentType.recommendationLetters});
    expect(documents.first.sharedWithProviderIds, isEmpty);
  });

  test('unencrypted documents are rejected', () async {
    final repository = DemoDocumentRepository();

    await expectLater(
      repository.add(
        UserDocument(
          id: 'unsafe',
          ownerUserId: 'applicant',
          type: DocumentType.passport,
          fileName: 'passport.pdf',
          uploadedAt: DateTime(2026, 7, 28),
          encryptedAtRest: false,
        ),
      ),
      throwsArgumentError,
    );
  });
}
