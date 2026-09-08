import 'package:flutter/material.dart';

import '../../opportunities/domain/opportunity.dart';
import '../../recommendations/domain/recommendation.dart';
import '../domain/opportunity_filter.dart';

/// What [OpportunityFilterScreen] hands back: the structured filter fields
/// plus the selected recommendation lens (`null` = "All opportunities") -
/// both live behind the single "Filters" entry point now, rather than the
/// category chips also sitting permanently on the Discover screen itself.
typedef OpportunityFilterResult = ({
  OpportunityFilter filter,
  RecommendationCategory? category,
});

class OpportunityFilterScreen extends StatefulWidget {
  const OpportunityFilterScreen({
    super.key,
    required this.initial,
    required this.initialCategory,
    required this.personalizationEnabled,
  });

  final OpportunityFilter initial;
  final RecommendationCategory? initialCategory;
  final bool personalizationEnabled;

  @override
  State<OpportunityFilterScreen> createState() =>
      _OpportunityFilterScreenState();
}

class _OpportunityFilterScreenState extends State<OpportunityFilterScreen> {
  late final Map<String, TextEditingController> _controllers;
  OpportunityType? _type;
  GeographicRegion? _region;
  FundingType? _funding;
  DeadlineWindow _deadline = DeadlineWindow.any;
  DeliveryFormat? _delivery;
  OpportunityAvailability _availability = OpportunityAvailability.open;
  bool _noFee = false;
  bool _verified = true;
  late RecommendationCategory? _category;

  @override
  void initState() {
    super.initState();
    _category = widget.initialCategory;
    final initial = widget.initial;
    _controllers = {
      'country': TextEditingController(text: initial.country),
      'provider': TextEditingController(text: initial.provider),
      'field': TextEditingController(text: initial.field),
      'level': TextEditingController(text: initial.studyLevel),
      'nationality': TextEditingController(text: initial.eligibleNationality),
      'age': TextEditingController(text: initial.applicantAge?.toString()),
      'experience': TextEditingController(
        text: initial.availableWorkExperienceYears?.toString(),
      ),
      'language': TextEditingController(text: initial.language),
    };
    _type = initial.type;
    _region = initial.region;
    _funding = initial.funding;
    _deadline = initial.deadlineWindow;
    _delivery = initial.deliveryFormat;
    _availability = initial.availability;
    _noFee = initial.noApplicationFee;
    _verified = initial.verifiedOnly;
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Search filters'),
        actions: [
          TextButton(
            onPressed: () => Navigator.of(
              context,
            ).pop((filter: const OpportunityFilter(), category: null)),
            child: const Text('Clear'),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.all(24),
        children: [
          Center(
            child: ConstrainedBox(
              constraints: const BoxConstraints(maxWidth: 720),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Recommendation lens',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  if (!widget.personalizationEnabled)
                    const Padding(
                      padding: EdgeInsets.only(bottom: 8),
                      child: Text(
                        'Personalized recommendations are disabled, so only '
                        '"All opportunities" is available.',
                      ),
                    ),
                  Wrap(
                    spacing: 8,
                    runSpacing: 8,
                    children: [
                      ChoiceChip(
                        label: const Text('All opportunities'),
                        selected: _category == null,
                        onSelected: (_) => setState(() => _category = null),
                      ),
                      ...RecommendationCategory.values.map(
                        (category) => ChoiceChip(
                          label: Text(_categoryLabel(category)),
                          selected: _category == category,
                          onSelected: widget.personalizationEnabled
                              ? (_) => setState(() => _category = category)
                              : null,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 20),
                  Text(
                    'Structured filters',
                    style: Theme.of(context).textTheme.titleMedium,
                  ),
                  const SizedBox(height: 4),
                  _enumField(
                    'Opportunity type',
                    _type,
                    OpportunityType.values,
                    (value) => setState(() => _type = value),
                  ),
                  _textField('country', 'Country'),
                  _enumField(
                    'Continent or region',
                    _region,
                    GeographicRegion.values,
                    (value) => setState(() => _region = value),
                  ),
                  _textField('provider', 'University or organization'),
                  _textField('field', 'Field of study'),
                  _textField('level', 'Degree level'),
                  _enumField(
                    'Funding type',
                    _funding,
                    FundingType.values,
                    (value) => setState(() => _funding = value),
                  ),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('No application fee'),
                    value: _noFee,
                    onChanged: (value) => setState(() => _noFee = value),
                  ),
                  _textField('nationality', 'Eligible nationality'),
                  _enumField(
                    'Deadline',
                    _deadline,
                    DeadlineWindow.values,
                    (value) =>
                        setState(() => _deadline = value ?? DeadlineWindow.any),
                    allowAny: false,
                  ),
                  _enumField(
                    'Delivery format',
                    _delivery,
                    DeliveryFormat.values,
                    (value) => setState(() => _delivery = value),
                  ),
                  _textField(
                    'age',
                    'Applicant age',
                    keyboardType: TextInputType.number,
                  ),
                  _textField(
                    'experience',
                    'Available work experience in years',
                    keyboardType: TextInputType.number,
                  ),
                  _textField('language', 'Language requirement'),
                  SwitchListTile(
                    contentPadding: EdgeInsets.zero,
                    title: const Text('Verified only'),
                    value: _verified,
                    onChanged: (value) => setState(() => _verified = value),
                  ),
                  _enumField(
                    'Application status',
                    _availability,
                    OpportunityAvailability.values,
                    (value) => setState(
                      () =>
                          _availability = value ?? OpportunityAvailability.any,
                    ),
                    allowAny: false,
                  ),
                  const SizedBox(height: 24),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      key: const Key('apply-filters'),
                      onPressed: _apply,
                      icon: const Icon(Icons.filter_alt_outlined),
                      label: const Text('Apply filters'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ],
      ),
    );
  }

  Widget _textField(String key, String label, {TextInputType? keyboardType}) =>
      Padding(
        padding: const EdgeInsets.only(bottom: 12),
        child: TextField(
          controller: _controllers[key],
          keyboardType: keyboardType,
          decoration: InputDecoration(labelText: label),
        ),
      );

  Widget _enumField<T extends Enum>(
    String label,
    T? value,
    List<T> values,
    ValueChanged<T?> onChanged, {
    bool allowAny = true,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<T>(
      initialValue: value,
      decoration: InputDecoration(labelText: label),
      hint: allowAny ? const Text('Any') : null,
      items: values
          .map(
            (item) =>
                DropdownMenuItem(value: item, child: Text(_label(item.name))),
          )
          .toList(),
      onChanged: onChanged,
    ),
  );

  void _apply() {
    Navigator.of(context).pop((
      filter: OpportunityFilter(
        query: widget.initial.query,
        type: _type,
        country: _value('country'),
        region: _region,
        provider: _value('provider'),
        field: _value('field'),
        studyLevel: _value('level'),
        funding: _funding,
        noApplicationFee: _noFee,
        eligibleNationality: _value('nationality'),
        deadlineWindow: _deadline,
        deliveryFormat: _delivery,
        applicantAge: int.tryParse(_value('age') ?? ''),
        availableWorkExperienceYears: double.tryParse(
          _value('experience') ?? '',
        ),
        language: _value('language'),
        verifiedOnly: _verified,
        availability: _availability,
      ),
      category: widget.personalizationEnabled ? _category : null,
    ));
  }

  static String _categoryLabel(RecommendationCategory category) =>
      switch (category) {
        RecommendationCategory.bestMatches => 'Best matches',
        RecommendationCategory.newlyPublished => 'Newly published',
        RecommendationCategory.fullyFunded => 'Fully funded',
        RecommendationCategory.noApplicationFee => 'No application fee',
        RecommendationCategory.closingSoon => 'Closing soon',
        RecommendationCategory.suitableForCountry => 'For your country',
        RecommendationCategory.suitableForDegree => 'For your degree',
        RecommendationCategory.online => 'Online',
        RecommendationCategory.noIelts => 'No IELTS',
        RecommendationCategory.undergraduate => 'Undergraduate',
        RecommendationCategory.masters => 'Master\'s',
        RecommendationCategory.phd => 'PhD',
        RecommendationCategory.professional => 'Professional',
      };

  String? _value(String key) {
    final value = _controllers[key]!.text.trim();
    return value.isEmpty ? null : value;
  }

  static String _label(String value) {
    final spaced = value.replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    );
    return '${spaced[0].toUpperCase()}${spaced.substring(1)}';
  }
}
