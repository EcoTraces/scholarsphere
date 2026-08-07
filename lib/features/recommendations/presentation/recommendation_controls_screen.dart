import 'package:flutter/material.dart';

import '../domain/recommendation.dart';
import '../domain/recommendation_governance.dart';
import '../domain/recommendation_governance_repository.dart';

class RecommendationControlsScreen extends StatefulWidget {
  const RecommendationControlsScreen({
    super.key,
    required this.userId,
    required this.repository,
  });

  final String userId;
  final RecommendationGovernanceRepository repository;

  @override
  State<RecommendationControlsScreen> createState() =>
      _RecommendationControlsScreenState();
}

class _RecommendationControlsScreenState
    extends State<RecommendationControlsScreen> {
  late Future<PersonalizationControls> _controls;
  final _countries = TextEditingController();

  @override
  void initState() {
    super.initState();
    _controls = widget.repository.getControls(widget.userId);
  }

  @override
  void dispose() {
    _countries.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<PersonalizationControls>(
    future: _controls,
    builder: (context, snapshot) {
      if (!snapshot.hasData) {
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      }
      final controls = snapshot.data!;
      if (_countries.text.isEmpty) {
        _countries.text = controls.preferredCountries.join(', ');
      }
      return Scaffold(
        appBar: AppBar(title: const Text('Recommendation controls')),
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            SwitchListTile(
              value: controls.behaviouralRecommendationsEnabled,
              title: const Text('Behaviour-based recommendations'),
              subtitle: const Text(
                'Use searches and interaction history for ranking',
              ),
              onChanged: (value) => _save(
                controls.copyWith(behaviouralRecommendationsEnabled: value),
              ),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _countries,
              decoration: const InputDecoration(
                labelText: 'Preferred countries',
                hintText: 'Canada, Germany, Japan',
              ),
              onSubmitted: (_) => _save(
                controls.copyWith(
                  preferredCountries: _countries.text
                      .split(',')
                      .map((value) => value.trim())
                      .where((value) => value.isNotEmpty)
                      .toList(),
                ),
              ),
            ),
            const SizedBox(height: 24),
            Text(
              'Opportunity categories',
              style: Theme.of(context).textTheme.titleLarge,
            ),
            const SizedBox(height: 8),
            Wrap(
              spacing: 8,
              runSpacing: 8,
              children: RecommendationCategory.values
                  .map(
                    (category) => FilterChip(
                      label: Text(_label(category)),
                      selected: controls.opportunityCategories.contains(
                        category,
                      ),
                      onSelected: (selected) {
                        final categories = {...controls.opportunityCategories};
                        selected
                            ? categories.add(category)
                            : categories.remove(category);
                        _save(
                          controls.copyWith(opportunityCategories: categories),
                        );
                      },
                    ),
                  )
                  .toList(),
            ),
            const SizedBox(height: 28),
            OutlinedButton.icon(
              onPressed: () async {
                await widget.repository.resetHistory(widget.userId);
                if (mounted) {
                  ScaffoldMessenger.of(context).showSnackBar(
                    const SnackBar(
                      content: Text('Recommendation history reset.'),
                    ),
                  );
                }
              },
              icon: const Icon(Icons.history_toggle_off),
              label: const Text('Reset recommendation history'),
            ),
          ],
        ),
      );
    },
  );

  Future<void> _save(PersonalizationControls controls) async {
    await widget.repository.saveControls(widget.userId, controls);
    if (mounted) {
      setState(() => _controls = Future.value(controls));
    }
  }

  String _label(RecommendationCategory category) =>
      category.name.replaceAllMapped(
        RegExp(r'([A-Z])'),
        (match) => ' ${match.group(1)!.toLowerCase()}',
      );
}
