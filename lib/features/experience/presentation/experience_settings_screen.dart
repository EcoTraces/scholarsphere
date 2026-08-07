import 'package:flutter/material.dart';

import '../domain/experience_preferences.dart';
import '../domain/experience_repository.dart';

class ExperienceSettingsScreen extends StatefulWidget {
  const ExperienceSettingsScreen({
    super.key,
    required this.userId,
    required this.repository,
    required this.onChanged,
  });
  final String userId;
  final ExperienceRepository repository;
  final ValueChanged<ExperiencePreferences> onChanged;

  @override
  State<ExperienceSettingsScreen> createState() =>
      _ExperienceSettingsScreenState();
}

class _ExperienceSettingsScreenState extends State<ExperienceSettingsScreen> {
  late Future<ExperiencePreferences> _preferences;

  @override
  void initState() {
    super.initState();
    _preferences = widget.repository.getPreferences(widget.userId);
  }

  @override
  Widget build(BuildContext context) => FutureBuilder<ExperiencePreferences>(
    future: _preferences,
    builder: (context, snapshot) {
      if (!snapshot.hasData) {
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      }
      final value = snapshot.data!;
      return Scaffold(
        appBar: AppBar(title: const Text('Language and accessibility')),
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            DropdownButtonFormField<SupportedLanguage>(
              initialValue: value.language,
              decoration: const InputDecoration(labelText: 'Language'),
              items: SupportedLanguage.values
                  .map(
                    (language) => DropdownMenuItem(
                      value: language,
                      child: Text(_languageLabel(language)),
                    ),
                  )
                  .toList(),
              onChanged: (language) =>
                  _save(value.copyWith(language: language)),
            ),
            const SizedBox(height: 16),
            Semantics(
              label: 'Text size',
              value: '${(value.textScale * 100).round()} percent',
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text('Text size: ${(value.textScale * 100).round()}%'),
                  Slider(
                    value: value.textScale,
                    min: 1,
                    max: 2,
                    divisions: 4,
                    onChanged: (scale) =>
                        _save(value.copyWith(textScale: scale)),
                  ),
                ],
              ),
            ),
            SwitchListTile(
              value: value.highContrast,
              title: const Text('High contrast'),
              onChanged: (enabled) =>
                  _save(value.copyWith(highContrast: enabled)),
            ),
            SwitchListTile(
              value: value.screenReaderOptimized,
              title: const Text('Screen-reader optimized layout'),
              onChanged: (enabled) =>
                  _save(value.copyWith(screenReaderOptimized: enabled)),
            ),
            SwitchListTile(
              value: value.keyboardNavigation,
              title: const Text('Keyboard navigation'),
              onChanged: (enabled) =>
                  _save(value.copyWith(keyboardNavigation: enabled)),
            ),
            const Divider(height: 32),
            SwitchListTile(
              value: value.lowBandwidthMode,
              title: const Text('Low-bandwidth mode'),
              subtitle: const Text(
                'Prefer compact content and progressive loading',
              ),
              onChanged: (enabled) =>
                  _save(value.copyWith(lowBandwidthMode: enabled)),
            ),
            SwitchListTile(
              value: value.dataSaving,
              title: const Text('Data saving'),
              onChanged: (enabled) =>
                  _save(value.copyWith(dataSaving: enabled)),
            ),
            SwitchListTile(
              value: value.compressImages,
              title: const Text('Compress images'),
              onChanged: (enabled) =>
                  _save(value.copyWith(compressImages: enabled)),
            ),
            SwitchListTile(
              value: value.cacheSavedOpportunities,
              title: const Text('Cache saved opportunities'),
              onChanged: (enabled) =>
                  _save(value.copyWith(cacheSavedOpportunities: enabled)),
            ),
            const Divider(height: 32),
            TextFormField(
              initialValue: value.timezone,
              decoration: const InputDecoration(
                labelText: 'Timezone',
                hintText: 'UTC+0',
              ),
              onFieldSubmitted: (timezone) =>
                  _save(value.copyWith(timezone: timezone.trim())),
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: value.currencyCode,
              decoration: const InputDecoration(
                labelText: 'Currency code',
                hintText: 'USD',
              ),
              onFieldSubmitted: (currency) => _save(
                value.copyWith(currencyCode: currency.trim().toUpperCase()),
              ),
            ),
          ],
        ),
      );
    },
  );

  Future<void> _save(ExperiencePreferences value) async {
    await widget.repository.savePreferences(widget.userId, value);
    widget.onChanged(value);
    if (mounted) setState(() => _preferences = Future.value(value));
  }

  String _languageLabel(SupportedLanguage language) => switch (language) {
    SupportedLanguage.english => 'English',
    SupportedLanguage.french => 'Francais',
    SupportedLanguage.spanish => 'Espanol',
    SupportedLanguage.arabic => 'Arabic',
  };
}
