import 'testimonial.dart';

/// Filters for both the public Success Stories listing and the admin
/// moderation queue - a single shape covers both since the underlying
/// query shape is the same, only the allowed values (and who may set
/// `status`) differ.
class SuccessStoryFilters {
  const SuccessStoryFilters({
    this.keyword,
    this.opportunityType,
    this.country,
    this.fieldOfStudy,
    this.degreeLevel,
    this.successYear,
    this.verifiedOnly = false,
    this.featuredOnly = false,
    this.sort = 'recent',
  });

  final String? keyword;
  final String? opportunityType;
  final String? country;
  final String? fieldOfStudy;
  final String? degreeLevel;
  final int? successYear;
  final bool verifiedOnly;
  final bool featuredOnly;
  final String sort;

  Map<String, String> toQuery() => {
    if (keyword != null && keyword!.isNotEmpty) 'keyword': keyword!,
    if (opportunityType != null) 'opportunity_type': opportunityType!,
    if (country != null) 'country': country!,
    if (fieldOfStudy != null) 'field_of_study': fieldOfStudy!,
    if (degreeLevel != null) 'degree_level': degreeLevel!,
    if (successYear != null) 'success_year': successYear.toString(),
    if (verifiedOnly) 'verified_only': 'true',
    if (featuredOnly) 'featured_only': 'true',
    'sort': sort,
  };
}

class AdminTestimonialFilters {
  const AdminTestimonialFilters({
    this.status,
    this.opportunityType,
    this.country,
    this.verificationStatus,
  });

  final TestimonialStatus? status;
  final String? opportunityType;
  final String? country;
  final TestimonialVerificationStatus? verificationStatus;
}

abstract interface class TestimonialRepository {
  // --- Public / any signed-in applicant --------------------------------
  Future<SuccessStoryPage> listSuccessStories(
    SuccessStoryFilters filters, {
    int page = 1,
    int pageSize = 25,
  });
  Future<TestimonialStats> getStats();
  Future<SuccessStoryDetail> getStory(String slug);
  Future<List<SuccessStorySummary>> getRelatedStories(
    String slug, {
    int limit = 4,
  });
  Future<SuccessStoryDetail> react(String slug, TestimonialReactionType type);
  Future<SuccessStoryDetail> removeReaction(String slug);

  // --- The caller's own submissions -------------------------------------
  Future<List<MyTestimonial>> listMine();
  Future<MyTestimonial> getMine(String testimonialId);
  Future<MyTestimonial> saveDraft(TestimonialDraftInput input, {String? id});
  Future<MyTestimonial> submit(String testimonialId);
  Future<MyTestimonial> withdraw(String testimonialId);
  Future<String> getMyEvidenceUrl(String testimonialId, String path);

  // --- Admin moderation --------------------------------------------------
  Future<AdminTestimonialPage> listForModeration(
    AdminTestimonialFilters filters, {
    int page = 1,
    int pageSize = 25,
  });
  Future<AdminTestimonial> getForModeration(String testimonialId);
  Future<List<TestimonialModerationHistoryItem>> getModerationHistory(
    String testimonialId,
  );
  Future<AdminTestimonial> markUnderReview(String testimonialId);
  Future<AdminTestimonial> approve(String testimonialId, String notes);
  Future<AdminTestimonial> reject(String testimonialId, String reason);
  Future<AdminTestimonial> requestChanges(String testimonialId, String reason);
  Future<AdminTestimonial> verify(
    String testimonialId,
    String verificationMethod,
    String? notes,
  );
  Future<AdminTestimonial> feature(String testimonialId);
  Future<AdminTestimonial> unfeature(String testimonialId);
  Future<AdminTestimonial> archive(String testimonialId, String reason);
  Future<AdminTestimonial> setInternalNotes(String testimonialId, String notes);
  Future<String> getAdminEvidenceUrl(String testimonialId, String path);
}
