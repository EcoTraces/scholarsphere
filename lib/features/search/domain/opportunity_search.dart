import '../../opportunities/domain/opportunity.dart';
import 'opportunity_filter.dart';

class OpportunitySearch {
  const OpportunitySearch();

  List<Opportunity> apply(
    Iterable<Opportunity> opportunities,
    OpportunityFilter filter, {
    DateTime? now,
  }) {
    final today = now ?? DateTime.now();
    return opportunities
        .where((item) => _matches(item, filter, today))
        .toList();
  }

  bool _matches(Opportunity item, OpportunityFilter filter, DateTime now) {
    final query = filter.query.trim().toLowerCase();
    if (query.isNotEmpty &&
        !_contains(item.title, query) &&
        !_contains(item.provider, query) &&
        !_contains(item.hostInstitution, query) &&
        !_contains(item.hostCountry, query) &&
        !item.fieldsOfStudy.any((value) => _contains(value, query))) {
      return false;
    }
    if (filter.type != null && item.type != filter.type) return false;
    if (!_optionalText(item.hostCountry, filter.country)) return false;
    if (filter.region != null &&
        !Geography.matches(item.hostCountry, filter.region!)) {
      return false;
    }
    if (!_optionalText(item.provider, filter.provider) &&
        !_optionalText(item.hostInstitution, filter.provider)) {
      return false;
    }
    if (!_optionalList(item.fieldsOfStudy, filter.field)) return false;
    if (!_optionalList(item.studyLevels, filter.studyLevel)) return false;
    if (filter.funding != null && item.funding != filter.funding) return false;
    if (filter.noApplicationFee && item.applicationFee != 0) return false;
    if (filter.eligibleNationality != null &&
        !_containsAny(
          item.eligibleNationalities,
          filter.eligibleNationality!,
          allowAll: true,
        )) {
      return false;
    }
    if (!_deadlineMatches(item.deadline, filter.deadlineWindow, now)) {
      return false;
    }
    if (filter.deliveryFormat != null &&
        item.deliveryFormat != filter.deliveryFormat) {
      return false;
    }
    final age = filter.applicantAge;
    if (age != null &&
        ((item.minimumAge != null && age < item.minimumAge!) ||
            (item.maximumAge != null && age > item.maximumAge!))) {
      return false;
    }
    final experience = filter.availableWorkExperienceYears;
    if (experience != null &&
        item.workExperienceYearsRequired != null &&
        experience < item.workExperienceYearsRequired!) {
      return false;
    }
    if (!_optionalList(item.languageRequirements, filter.language)) {
      return false;
    }
    if (filter.verifiedOnly && !item.isVerified) return false;
    if (filter.availability == OpportunityAvailability.open &&
        !item.deadline.isAfter(now)) {
      return false;
    }
    if (filter.availability == OpportunityAvailability.closed &&
        item.deadline.isAfter(now)) {
      return false;
    }
    return true;
  }

  bool _deadlineMatches(
    DateTime deadline,
    DeadlineWindow window,
    DateTime now,
  ) {
    final days = switch (window) {
      DeadlineWindow.any => null,
      DeadlineWindow.sevenDays => 7,
      DeadlineWindow.thirtyDays => 30,
      DeadlineWindow.ninetyDays => 90,
    };
    return days == null ||
        (deadline.isAfter(now) &&
            !deadline.isAfter(now.add(Duration(days: days))));
  }

  bool _optionalText(String source, String? expected) =>
      expected == null ||
      expected.trim().isEmpty ||
      _contains(source, expected.trim());

  bool _optionalList(List<String> source, String? expected) =>
      expected == null ||
      expected.trim().isEmpty ||
      _containsAny(source, expected);

  bool _containsAny(
    List<String> source,
    String expected, {
    bool allowAll = false,
  }) => source.any(
    (value) =>
        (allowAll && _contains(value, 'all nationalities')) ||
        _contains(value, expected),
  );

  bool _contains(String source, String expected) =>
      source.toLowerCase().contains(expected.toLowerCase());
}

abstract final class Geography {
  static const Map<String, GeographicRegion> _countries = {
    'united kingdom': GeographicRegion.europe,
    'germany': GeographicRegion.europe,
    'france': GeographicRegion.europe,
    'italy': GeographicRegion.europe,
    'canada': GeographicRegion.northAmerica,
    'united states': GeographicRegion.northAmerica,
    'mexico': GeographicRegion.northAmerica,
    'brazil': GeographicRegion.latinAmerica,
    'argentina': GeographicRegion.latinAmerica,
    'ghana': GeographicRegion.africa,
    'nigeria': GeographicRegion.africa,
    'kenya': GeographicRegion.africa,
    'south africa': GeographicRegion.africa,
    'china': GeographicRegion.asia,
    'japan': GeographicRegion.asia,
    'india': GeographicRegion.asia,
    'united arab emirates': GeographicRegion.middleEast,
    'qatar': GeographicRegion.middleEast,
    'saudi arabia': GeographicRegion.middleEast,
    'australia': GeographicRegion.australiaOceania,
    'new zealand': GeographicRegion.australiaOceania,
    'remote': GeographicRegion.globalOnline,
    'global': GeographicRegion.globalOnline,
    'online': GeographicRegion.globalOnline,
  };

  static GeographicRegion? regionFor(String country) =>
      _countries[country.trim().toLowerCase()];

  static bool matches(String country, GeographicRegion requested) {
    final normalized = country.trim().toLowerCase();
    if (requested == GeographicRegion.canada) return normalized == 'canada';
    return regionFor(country) == requested;
  }
}
