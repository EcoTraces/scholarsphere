import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/applicant_profile.dart';
import '../domain/applicant_profile_repository.dart';

class ApplicantProfileScreen extends StatefulWidget {
  const ApplicantProfileScreen({
    super.key,
    required this.user,
    required this.repository,
  });

  final UserAccount user;
  final ApplicantProfileRepository repository;

  @override
  State<ApplicantProfileScreen> createState() => _ApplicantProfileScreenState();
}

class _ApplicantProfileScreenState extends State<ApplicantProfileScreen> {
  late Future<ApplicantProfile> _profile;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _profile = widget.repository
        .getForUser(widget.user.id)
        .then((value) => value ?? ApplicantProfile.empty(widget.user));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Applicant profile')),
      body: FutureBuilder<ApplicantProfile>(
        future: _profile,
        builder: (context, snapshot) {
          if (snapshot.hasError) {
            return Center(
              child: Padding(
                padding: const EdgeInsets.all(24),
                child: Column(
                  mainAxisSize: MainAxisSize.min,
                  children: [
                    Icon(
                      Icons.error_outline,
                      size: 40,
                      color: Theme.of(context).colorScheme.error,
                    ),
                    const SizedBox(height: 12),
                    const Text("We couldn't load your profile."),
                    const SizedBox(height: 16),
                    FilledButton.icon(
                      onPressed: () => setState(_load),
                      icon: const Icon(Icons.refresh),
                      label: const Text('Retry'),
                    ),
                  ],
                ),
              ),
            );
          }
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return _ProfileForm(
            profile: snapshot.data!,
            repository: widget.repository,
          );
        },
      ),
    );
  }
}

class _ProfileForm extends StatefulWidget {
  const _ProfileForm({required this.profile, required this.repository});

  final ApplicantProfile profile;
  final ApplicantProfileRepository repository;

  @override
  State<_ProfileForm> createState() => _ProfileFormState();
}

class _ProfileFormState extends State<_ProfileForm> {
  // Every field below is required except 'gender' and 'special', which are
  // labeled "(optional)" in the UI.
  static const _requiredKeys = {
    'name',
    'nationality',
    'residence',
    'birth',
    'qualification',
    'field',
    'classification',
    'graduation',
    'experience',
    'levels',
    'countries',
    'interests',
    'funding',
  };

  late final Map<String, TextEditingController> _controllers;
  late final Map<String, FocusNode> _focusNodes;
  final _touched = <String>{};
  late EnglishTestStatus _englishTest;
  late PassportStatus _passport;
  late EmploymentStatus _employment;
  late List<ProfileDocument> _documents;
  bool _saving = false;
  bool _dirty = false;

  bool get _requiredFieldsFilled => _requiredKeys.every(
    (key) => _controllers[key]!.text.trim().isNotEmpty,
  );

  @override
  void initState() {
    super.initState();
    final profile = widget.profile;
    _controllers = {
      'name': TextEditingController(text: profile.fullName),
      'nationality': TextEditingController(text: profile.nationality),
      'residence': TextEditingController(text: profile.countryOfResidence),
      'birth': TextEditingController(
        text: profile.dateOfBirth == null
            ? ''
            : _dateText(profile.dateOfBirth!),
      ),
      'gender': TextEditingController(text: profile.gender),
      'qualification': TextEditingController(
        text: profile.highestQualification,
      ),
      'field': TextEditingController(text: profile.degreeField),
      'classification': TextEditingController(
        text: profile.academicClassification,
      ),
      'graduation': TextEditingController(
        text: profile.graduationYear?.toString() ?? '',
      ),
      'experience': TextEditingController(
        text: profile.workExperienceYears.toString(),
      ),
      'levels': TextEditingController(
        text: profile.preferredStudyLevels.join(', '),
      ),
      'countries': TextEditingController(
        text: profile.preferredCountries.join(', '),
      ),
      'interests': TextEditingController(
        text: profile.areasOfInterest.join(', '),
      ),
      'funding': TextEditingController(
        text: profile.fundingPreferences.join(', '),
      ),
      'special': TextEditingController(
        text: profile.specialEligibilityCategories.join(', '),
      ),
    };
    for (final controller in _controllers.values) {
      controller.addListener(() => setState(() => _dirty = true));
    }
    _focusNodes = {for (final key in _controllers.keys) key: FocusNode()};
    for (final entry in _focusNodes.entries) {
      entry.value.addListener(() {
        if (!entry.value.hasFocus) setState(() => _touched.add(entry.key));
      });
    }
    _englishTest = profile.englishTestStatus;
    _passport = profile.passportStatus;
    _employment = profile.employmentStatus;
    _documents = [...profile.documents];
  }

  @override
  void dispose() {
    for (final controller in _controllers.values) {
      controller.dispose();
    }
    for (final node in _focusNodes.values) {
      node.dispose();
    }
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return PopScope(
      canPop: !_dirty,
      onPopInvokedWithResult: (didPop, result) async {
        if (didPop) return;
        final discard = await showDialog<bool>(
          context: context,
          builder: (context) => AlertDialog(
            title: const Text('Discard changes?'),
            content: const Text(
              'You have unsaved profile changes. Discard them?',
            ),
            actions: [
              TextButton(
                onPressed: () => Navigator.of(context).pop(false),
                child: const Text('Keep editing'),
              ),
              FilledButton(
                onPressed: () => Navigator.of(context).pop(true),
                child: const Text('Discard'),
              ),
            ],
          ),
        );
        if (discard == true && context.mounted) {
          Navigator.of(context).pop();
        }
      },
      child: ListView(
      padding: const EdgeInsets.fromLTRB(20, 20, 20, 48),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 820),
            child: Form(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Container(
                    padding: const EdgeInsets.all(16),
                    decoration: BoxDecoration(
                      color: Theme.of(context).colorScheme.primaryContainer,
                      borderRadius: BorderRadius.circular(8),
                    ),
                    child: const Row(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        Icon(Icons.lock_outline),
                        SizedBox(width: 12),
                        Expanded(
                          child: Text(
                            'Your profile is private. Sensitive information '
                            'is used only for matching and is never shown on '
                            'a public profile.',
                          ),
                        ),
                      ],
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Fields marked * are required.',
                    style: Theme.of(
                      context,
                    ).textTheme.bodySmall?.copyWith(color: Colors.grey.shade600),
                  ),
                  const SizedBox(height: 24),
                  _heading(context, 'Personal information'),
                  _field('name', 'Full name'),
                  _field('nationality', 'Nationality'),
                  _field('residence', 'Country of residence'),
                  _dateField(context),
                  _field('gender', 'Gender (optional)', required: false),
                  const SizedBox(height: 24),
                  _heading(context, 'Education and experience'),
                  _field('qualification', 'Highest qualification'),
                  _field('field', 'Degree field'),
                  _field('classification', 'GPA or academic classification'),
                  _field(
                    'graduation',
                    'Graduation year',
                    keyboardType: TextInputType.number,
                  ),
                  _field(
                    'experience',
                    'Work experience in years',
                    keyboardType: TextInputType.number,
                  ),
                  const SizedBox(height: 24),
                  _heading(context, 'Preferences'),
                  _field('levels', 'Preferred study levels'),
                  _field('countries', 'Preferred countries'),
                  _field('interests', 'Areas of interest'),
                  _field('funding', 'Funding preferences'),
                  _field(
                    'special',
                    'Disability or special eligibility categories (optional)',
                    required: false,
                  ),
                  const SizedBox(height: 24),
                  _heading(context, 'Readiness'),
                  _enumField<EnglishTestStatus>(
                    label: 'English-language test status',
                    value: _englishTest,
                    values: EnglishTestStatus.values,
                    onChanged: (value) => setState(() {
                      _englishTest = value;
                      _dirty = true;
                    }),
                  ),
                  _enumField<PassportStatus>(
                    label: 'Passport status',
                    value: _passport,
                    values: PassportStatus.values,
                    onChanged: (value) => setState(() {
                      _passport = value;
                      _dirty = true;
                    }),
                  ),
                  _enumField<EmploymentStatus>(
                    label: 'Employment status',
                    value: _employment,
                    values: EmploymentStatus.values,
                    onChanged: (value) => setState(() {
                      _employment = value;
                      _dirty = true;
                    }),
                  ),
                  const SizedBox(height: 24),
                  _heading(context, 'Uploaded documents'),
                  if (_documents.isEmpty)
                    const Text('No documents have been added.')
                  else
                    ..._documents.map(
                      (document) => ListTile(
                        contentPadding: EdgeInsets.zero,
                        leading: const Icon(Icons.description_outlined),
                        title: Text(document.name),
                        subtitle: Text(document.type),
                        trailing: IconButton(
                          tooltip: 'Remove document',
                          onPressed: () => setState(() {
                            _documents.remove(document);
                            _dirty = true;
                          }),
                          icon: const Icon(Icons.delete_outline),
                        ),
                      ),
                    ),
                  OutlinedButton.icon(
                    onPressed: _addDemoDocument,
                    icon: const Icon(Icons.upload_file),
                    label: const Text('Add document record'),
                  ),
                  const SizedBox(height: 32),
                  SizedBox(
                    width: double.infinity,
                    child: FilledButton.icon(
                      key: const Key('save-profile'),
                      onPressed: _saving || !_requiredFieldsFilled
                          ? null
                          : _save,
                      icon: const Icon(Icons.save_outlined),
                      label: Text(_saving ? 'Saving...' : 'Save profile'),
                    ),
                  ),
                ],
              ),
            ),
          ),
        ),
      ],
      ),
    );
  }

  Widget _heading(BuildContext context, String text) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: Text(text, style: Theme.of(context).textTheme.headlineSmall),
  );

  Widget _field(
    String key,
    String label, {
    TextInputType? keyboardType,
    bool required = true,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextFormField(
      controller: _controllers[key],
      focusNode: _focusNodes[key],
      keyboardType: keyboardType,
      decoration: InputDecoration(
        labelText: required ? '$label *' : label,
        errorText:
            required &&
                _touched.contains(key) &&
                _controllers[key]!.text.trim().isEmpty
            ? 'Required'
            : null,
        helperText:
            const {
              'levels',
              'countries',
              'interests',
              'funding',
              'special',
            }.contains(key)
            ? 'Separate multiple values with commas'
            : null,
      ),
    ),
  );

  Widget _dateField(BuildContext context) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: TextFormField(
      controller: _controllers['birth'],
      focusNode: _focusNodes['birth'],
      readOnly: true,
      decoration: InputDecoration(
        labelText: 'Date of birth *',
        errorText:
            _touched.contains('birth') &&
                _controllers['birth']!.text.trim().isEmpty
            ? 'Required'
            : null,
        suffixIcon: const Icon(Icons.calendar_today_outlined),
      ),
      onTap: () async {
        setState(() => _touched.add('birth'));
        final date = await showDatePicker(
          context: context,
          firstDate: DateTime(1940),
          lastDate: DateTime.now(),
          initialDate: DateTime(2000),
        );
        if (date != null) {
          _controllers['birth']!.text = _dateText(date);
        }
      },
    ),
  );

  Widget _enumField<T extends Enum>({
    required String label,
    required T value,
    required List<T> values,
    required ValueChanged<T> onChanged,
  }) => Padding(
    padding: const EdgeInsets.only(bottom: 12),
    child: DropdownButtonFormField<T>(
      initialValue: value,
      decoration: InputDecoration(labelText: label),
      items: values
          .map(
            (item) => DropdownMenuItem(
              value: item,
              child: Text(_enumLabel(item.name)),
            ),
          )
          .toList(),
      onChanged: (item) {
        if (item != null) onChanged(item);
      },
    ),
  );

  void _addDemoDocument() {
    final number = _documents.length + 1;
    setState(() {
      _documents.add(
        ProfileDocument(
          id: 'document-$number',
          name: 'Document $number',
          type: 'Supporting document',
          uploadedAt: DateTime.now(),
        ),
      );
      _dirty = true;
    });
  }

  Future<void> _save() async {
    setState(() => _saving = true);
    final birthText = _controllers['birth']!.text;
    await widget.repository.save(
      ApplicantProfile(
        userId: widget.profile.userId,
        fullName: _controllers['name']!.text.trim(),
        nationality: _controllers['nationality']!.text.trim(),
        countryOfResidence: _controllers['residence']!.text.trim(),
        dateOfBirth: birthText.isEmpty ? null : DateTime.parse(birthText),
        gender: _controllers['gender']!.text.trim(),
        highestQualification: _controllers['qualification']!.text.trim(),
        degreeField: _controllers['field']!.text.trim(),
        academicClassification: _controllers['classification']!.text.trim(),
        graduationYear: int.tryParse(_controllers['graduation']!.text),
        workExperienceYears:
            double.tryParse(_controllers['experience']!.text) ?? 0,
        preferredStudyLevels: _list('levels'),
        preferredCountries: _list('countries'),
        areasOfInterest: _list('interests'),
        englishTestStatus: _englishTest,
        passportStatus: _passport,
        employmentStatus: _employment,
        fundingPreferences: _list('funding'),
        specialEligibilityCategories: _list('special'),
        documents: _documents,
      ),
    );
    if (!mounted) return;
    setState(() {
      _saving = false;
      _dirty = false;
    });
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(const SnackBar(content: Text('Profile saved privately.')));
  }

  List<String> _list(String key) => _controllers[key]!.text
      .split(',')
      .map((value) => value.trim())
      .where((value) => value.isNotEmpty)
      .toList();

  static String _dateText(DateTime date) =>
      '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}-'
      '${date.day.toString().padLeft(2, '0')}';

  static String _enumLabel(String value) {
    final withSpaces = value.replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    );
    return '${withSpaces[0].toUpperCase()}${withSpaces.substring(1)}';
  }
}
