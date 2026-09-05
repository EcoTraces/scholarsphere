import 'package:flutter/material.dart';

import '../data/testimonial_evidence_upload.dart';
import '../data/testimonial_photo_upload.dart';
import '../domain/testimonial.dart';
import '../domain/testimonial_repository.dart';
import 'widgets/story_avatar.dart';
import 'widgets/success_story_card.dart';

/// The multi-step submission wizard from Phase 9 of the feature spec.
/// Uses Flutter's built-in [Stepper] (progress indicator + back/next
/// controls for free, no new dependency) across the wizard's first six
/// steps, with a distinct seventh "Consent" step gating the final
/// submit action.
class ShareSuccessStoryScreen extends StatefulWidget {
  const ShareSuccessStoryScreen({
    super.key,
    required this.repository,
    this.existing,
  });

  final TestimonialRepository repository;

  /// When editing a draft or a story sent back with `changes_requested`
  /// - null starts a brand-new draft.
  final MyTestimonial? existing;

  @override
  State<ShareSuccessStoryScreen> createState() =>
      _ShareSuccessStoryScreenState();
}

class _ShareSuccessStoryScreenState extends State<ShareSuccessStoryScreen> {
  int _step = 0;
  String? _testimonialId;
  late TestimonialDraftInput _draft;
  bool _saving = false;
  String? _error;
  bool _consentTruthful = false;
  bool _consentPermission = false;
  bool _consentPublic = false;
  bool _consentWithdrawal = false;

  final _opportunityNameController = TextEditingController();
  final _opportunityProviderController = TextEditingController();
  final _countryController = TextEditingController();
  final _fieldController = TextEditingController();
  final _yearController = TextEditingController();
  final _challengeController = TextEditingController();
  final _discoveryController = TextEditingController();
  final _preparationController = TextEditingController();
  final _helpController = TextEditingController();
  final _outcomeController = TextEditingController();
  final _impactController = TextEditingController();
  final _adviceController = TextEditingController();
  final _fullNameController = TextEditingController();
  final _universityController = TextEditingController();
  final _programController = TextEditingController();

  @override
  void initState() {
    super.initState();
    final existing = widget.existing;
    _testimonialId = existing?.id;
    _draft = existing == null
        ? TestimonialDraftInput.empty
        : TestimonialDraftInput(
            opportunityId: existing.opportunityId,
            opportunityName: existing.opportunityName,
            opportunityProvider: existing.opportunityProvider,
            opportunityType: existing.opportunityType,
            country: existing.country,
            degreeLevel: existing.degreeLevel,
            fieldOfStudy: existing.fieldOfStudy,
            successYear: existing.successYear,
            outcome: existing.outcome,
            challenge: existing.challenge,
            discoveryStory: existing.discoveryStory,
            preparationStory: existing.preparationStory,
            scholarsphereHelp: existing.scholarsphereHelp,
            outcomeNarrative: existing.outcomeNarrative,
            impact: existing.impact,
            advice: existing.advice,
            featuresUsed: existing.featuresUsed,
            fullName: existing.fullName,
            university: existing.university,
            program: existing.program,
            photoStoragePath: existing.photoStoragePath,
            displayMode: existing.displayMode,
            showUniversity: existing.showUniversity,
            showCountry: existing.showCountry,
            showProgram: existing.showProgram,
            showPhoto: existing.showPhoto,
            evidenceStoragePaths: existing.evidenceStoragePaths,
          );
    _opportunityNameController.text = _draft.opportunityName;
    _opportunityProviderController.text = _draft.opportunityProvider;
    _countryController.text = _draft.country ?? '';
    _fieldController.text = _draft.fieldOfStudy ?? '';
    _yearController.text = _draft.successYear?.toString() ?? '';
    _challengeController.text = _draft.challenge ?? '';
    _discoveryController.text = _draft.discoveryStory ?? '';
    _preparationController.text = _draft.preparationStory ?? '';
    _helpController.text = _draft.scholarsphereHelp ?? '';
    _outcomeController.text = _draft.outcomeNarrative ?? '';
    _impactController.text = _draft.impact ?? '';
    _adviceController.text = _draft.advice ?? '';
    _fullNameController.text = _draft.fullName;
    _universityController.text = _draft.university ?? '';
    _programController.text = _draft.program ?? '';
  }

  @override
  void dispose() {
    for (final controller in [
      _opportunityNameController,
      _opportunityProviderController,
      _countryController,
      _fieldController,
      _yearController,
      _challengeController,
      _discoveryController,
      _preparationController,
      _helpController,
      _outcomeController,
      _impactController,
      _adviceController,
      _fullNameController,
      _universityController,
      _programController,
    ]) {
      controller.dispose();
    }
    super.dispose();
  }

  void _syncControllersIntoDraft() {
    _draft = _draft.copyWith(
      opportunityName: _opportunityNameController.text.trim(),
      opportunityProvider: _opportunityProviderController.text.trim(),
      country: _countryController.text.trim().isEmpty
          ? null
          : _countryController.text.trim(),
      fieldOfStudy: _fieldController.text.trim().isEmpty
          ? null
          : _fieldController.text.trim(),
      successYear: int.tryParse(_yearController.text.trim()),
      challenge: _challengeController.text.trim().isEmpty
          ? null
          : _challengeController.text.trim(),
      discoveryStory: _discoveryController.text.trim().isEmpty
          ? null
          : _discoveryController.text.trim(),
      preparationStory: _preparationController.text.trim().isEmpty
          ? null
          : _preparationController.text.trim(),
      scholarsphereHelp: _helpController.text.trim().isEmpty
          ? null
          : _helpController.text.trim(),
      outcomeNarrative: _outcomeController.text.trim().isEmpty
          ? null
          : _outcomeController.text.trim(),
      impact: _impactController.text.trim().isEmpty
          ? null
          : _impactController.text.trim(),
      advice: _adviceController.text.trim().isEmpty
          ? null
          : _adviceController.text.trim(),
      fullName: _fullNameController.text.trim(),
      university: _universityController.text.trim().isEmpty
          ? null
          : _universityController.text.trim(),
      program: _programController.text.trim().isEmpty
          ? null
          : _programController.text.trim(),
    );
  }

  Future<bool> _saveDraft({bool silent = false}) async {
    _syncControllersIntoDraft();
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final result = await widget.repository.saveDraft(
        _draft,
        id: _testimonialId,
      );
      if (!mounted) return true;
      setState(() {
        _testimonialId = result.id;
        _saving = false;
      });
      if (!silent && mounted) {
        ScaffoldMessenger.of(
          context,
        ).showSnackBar(const SnackBar(content: Text('Draft saved.')));
      }
      return true;
    } catch (error) {
      if (!mounted) return false;
      setState(() {
        _saving = false;
        _error =
            'Your story could not be saved. Your draft has been preserved locally.';
      });
      return false;
    }
  }

  bool get _consentComplete =>
      _consentTruthful &&
      _consentPermission &&
      _consentPublic &&
      _consentWithdrawal;

  Future<void> _submit() async {
    if (!_consentComplete) return;
    final saved = await _saveDraft(silent: true);
    if (!saved || _testimonialId == null) return;
    setState(() => _saving = true);
    try {
      await widget.repository.submit(_testimonialId!);
      if (!mounted) return;
      Navigator.of(context).pop(true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error =
            'Your story could not be submitted. Your draft has been preserved.';
      });
    }
  }

  static const _steps = [
    'Your Opportunity',
    'Your Experience',
    'Profile',
    'Privacy',
    'Evidence',
    'Review',
    'Consent',
  ];

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Share Your Success Story'),
        actions: [
          TextButton(
            onPressed: _saving ? null : () => _saveDraft(),
            child: const Text('Save Draft'),
          ),
        ],
      ),
      body: Column(
        children: [
          if (_error != null)
            MaterialBanner(
              content: Text(_error!),
              actions: [
                TextButton(
                  onPressed: () => setState(() => _error = null),
                  child: const Text('Dismiss'),
                ),
              ],
            ),
          Expanded(
            child: Stepper(
              currentStep: _step,
              onStepContinue: _step < _steps.length - 1
                  ? () async {
                      _syncControllersIntoDraft();
                      final ok = await _saveDraft(silent: true);
                      if (ok && mounted) setState(() => _step += 1);
                    }
                  : null,
              onStepCancel: _step > 0 ? () => setState(() => _step -= 1) : null,
              controlsBuilder: (context, details) => Padding(
                padding: const EdgeInsets.only(top: 16),
                child: Row(
                  children: [
                    if (details.stepIndex > 0)
                      OutlinedButton(
                        onPressed: _saving ? null : details.onStepCancel,
                        child: const Text('Back'),
                      ),
                    const SizedBox(width: 12),
                    if (details.stepIndex < _steps.length - 1)
                      FilledButton(
                        onPressed: _saving ? null : details.onStepContinue,
                        child: _saving
                            ? const SizedBox(
                                width: 18,
                                height: 18,
                                child: CircularProgressIndicator(
                                  strokeWidth: 2,
                                ),
                              )
                            : const Text('Next'),
                      ),
                  ],
                ),
              ),
              steps: [
                for (var index = 0; index < _steps.length; index++)
                  Step(
                    title: Text(_steps[index]),
                    isActive: _step >= index,
                    state: _step > index
                        ? StepState.complete
                        : StepState.indexed,
                    content: _stepContent(index),
                  ),
              ],
            ),
          ),
        ],
      ),
    );
  }

  Widget _stepContent(int index) {
    switch (index) {
      case 0:
        return _OpportunityStep(
          nameController: _opportunityNameController,
          providerController: _opportunityProviderController,
          countryController: _countryController,
          fieldController: _fieldController,
          yearController: _yearController,
          type: _draft.opportunityType,
          degreeLevel: _draft.degreeLevel,
          outcome: _draft.outcome,
          onTypeChanged: (value) =>
              setState(() => _draft = _draft.copyWith(opportunityType: value)),
          onDegreeChanged: (value) =>
              setState(() => _draft = _draft.copyWith(degreeLevel: value)),
          onOutcomeChanged: (value) =>
              setState(() => _draft = _draft.copyWith(outcome: value)),
        );
      case 1:
        return _ExperienceStep(
          challengeController: _challengeController,
          discoveryController: _discoveryController,
          preparationController: _preparationController,
          helpController: _helpController,
          outcomeController: _outcomeController,
          impactController: _impactController,
          adviceController: _adviceController,
          featuresUsed: _draft.featuresUsed,
          onFeaturesChanged: (features) =>
              setState(() => _draft = _draft.copyWith(featuresUsed: features)),
        );
      case 2:
        return _ProfileStep(
          fullNameController: _fullNameController,
          universityController: _universityController,
          programController: _programController,
          photoStoragePath: _draft.photoStoragePath,
          onPhotoChanged: (path) =>
              setState(() => _draft = _draft.copyWith(photoStoragePath: path)),
        );
      case 3:
        return _PrivacyStep(
          displayMode: _draft.displayMode,
          showUniversity: _draft.showUniversity,
          showCountry: _draft.showCountry,
          showProgram: _draft.showProgram,
          showPhoto: _draft.showPhoto,
          onChanged: (draft) => setState(() => _draft = draft),
          draft: _draft,
        );
      case 4:
        return _EvidenceStep(
          paths: _draft.evidenceStoragePaths,
          onChanged: (paths) => setState(
            () => _draft = _draft.copyWith(evidenceStoragePaths: paths),
          ),
        );
      case 5:
        return _ReviewStep(draft: _draft);
      case 6:
        return _ConsentStep(
          truthful: _consentTruthful,
          permission: _consentPermission,
          public: _consentPublic,
          withdrawal: _consentWithdrawal,
          onTruthfulChanged: (v) => setState(() => _consentTruthful = v),
          onPermissionChanged: (v) => setState(() => _consentPermission = v),
          onPublicChanged: (v) => setState(() => _consentPublic = v),
          onWithdrawalChanged: (v) => setState(() => _consentWithdrawal = v),
          canSubmit: _consentComplete && !_saving,
          onSubmit: _submit,
        );
      default:
        return const SizedBox.shrink();
    }
  }
}

class _OpportunityStep extends StatelessWidget {
  const _OpportunityStep({
    required this.nameController,
    required this.providerController,
    required this.countryController,
    required this.fieldController,
    required this.yearController,
    required this.type,
    required this.degreeLevel,
    required this.outcome,
    required this.onTypeChanged,
    required this.onDegreeChanged,
    required this.onOutcomeChanged,
  });

  final TextEditingController nameController;
  final TextEditingController providerController;
  final TextEditingController countryController;
  final TextEditingController fieldController;
  final TextEditingController yearController;
  final String type;
  final String? degreeLevel;
  final TestimonialOutcome outcome;
  final ValueChanged<String> onTypeChanged;
  final ValueChanged<String?> onDegreeChanged;
  final ValueChanged<TestimonialOutcome> onOutcomeChanged;

  static const _types = [
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
          controller: nameController,
          decoration: const InputDecoration(
            labelText: 'Opportunity name',
            helperText: 'e.g. Commonwealth Shared Scholarship',
          ),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: providerController,
          decoration: const InputDecoration(labelText: 'Opportunity provider'),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String>(
          initialValue: _types.contains(type) ? type : null,
          decoration: const InputDecoration(labelText: 'Opportunity type'),
          items: [
            for (final item in _types)
              DropdownMenuItem(value: item, child: Text(item)),
          ],
          onChanged: (value) {
            if (value != null) onTypeChanged(value);
          },
        ),
        const SizedBox(height: 12),
        TextField(
          controller: countryController,
          decoration: const InputDecoration(labelText: 'Country'),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<String?>(
          initialValue: degreeLevel,
          decoration: const InputDecoration(labelText: 'Degree level'),
          items: [
            const DropdownMenuItem(value: null, child: Text('Not applicable')),
            for (final level in _degreeLevels)
              DropdownMenuItem(value: level, child: Text(level)),
          ],
          onChanged: onDegreeChanged,
        ),
        const SizedBox(height: 12),
        TextField(
          controller: fieldController,
          decoration: const InputDecoration(labelText: 'Field of study'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: yearController,
          keyboardType: TextInputType.number,
          decoration: const InputDecoration(labelText: 'Year'),
        ),
        const SizedBox(height: 12),
        DropdownButtonFormField<TestimonialOutcome>(
          initialValue: outcome,
          decoration: const InputDecoration(labelText: 'Outcome'),
          items: [
            for (final value in TestimonialOutcome.values)
              DropdownMenuItem(value: value, child: Text(value.label)),
          ],
          onChanged: (value) {
            if (value != null) onOutcomeChanged(value);
          },
        ),
      ],
    );
  }
}

class _ExperienceStep extends StatelessWidget {
  const _ExperienceStep({
    required this.challengeController,
    required this.discoveryController,
    required this.preparationController,
    required this.helpController,
    required this.outcomeController,
    required this.impactController,
    required this.adviceController,
    required this.featuresUsed,
    required this.onFeaturesChanged,
  });

  final TextEditingController challengeController;
  final TextEditingController discoveryController;
  final TextEditingController preparationController;
  final TextEditingController helpController;
  final TextEditingController outcomeController;
  final TextEditingController impactController;
  final TextEditingController adviceController;
  final List<String> featuresUsed;
  final ValueChanged<List<String>> onFeaturesChanged;

  static const _maxLength = 4000;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        _question(
          'What challenge were you facing before using ScholarSphere?',
          challengeController,
        ),
        _question('How did you discover the opportunity?', discoveryController),
        _question(
          'Which ScholarSphere features helped you?',
          null,
          child: Wrap(
            spacing: 8,
            runSpacing: 8,
            children: [
              for (final feature in knownTestimonialFeatures)
                FilterChip(
                  label: Text(featureLabel(feature)),
                  selected: featuresUsed.contains(feature),
                  onSelected: (selected) {
                    final updated = [...featuresUsed];
                    if (selected) {
                      updated.add(feature);
                    } else {
                      updated.remove(feature);
                    }
                    onFeaturesChanged(updated);
                  },
                ),
            ],
          ),
        ),
        _question(
          'How did ScholarSphere help you prepare your application?',
          preparationController,
        ),
        _question(
          'Anything else about how ScholarSphere helped?',
          helpController,
        ),
        _question(
          'What was the outcome of your application?',
          outcomeController,
        ),
        _question(
          'What difference did the opportunity make to you?',
          impactController,
        ),
        _question(
          'What advice would you give to future applicants?',
          adviceController,
        ),
      ],
    );
  }

  Widget _question(
    String label,
    TextEditingController? controller, {
    Widget? child,
  }) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(label, style: const TextStyle(fontWeight: FontWeight.w600)),
          const SizedBox(height: 8),
          if (child != null)
            child
          else
            TextField(
              controller: controller,
              maxLines: 4,
              maxLength: _maxLength,
              decoration: const InputDecoration(border: OutlineInputBorder()),
            ),
        ],
      ),
    );
  }
}

class _ProfileStep extends StatefulWidget {
  const _ProfileStep({
    required this.fullNameController,
    required this.universityController,
    required this.programController,
    required this.photoStoragePath,
    required this.onPhotoChanged,
  });

  final TextEditingController fullNameController;
  final TextEditingController universityController;
  final TextEditingController programController;
  final String? photoStoragePath;
  final ValueChanged<String?> onPhotoChanged;

  @override
  State<_ProfileStep> createState() => _ProfileStepState();
}

class _ProfileStepState extends State<_ProfileStep> {
  final _upload = TestimonialPhotoUpload();
  bool _uploading = false;
  String? _error;

  Future<void> _pickPhoto() async {
    setState(() {
      _uploading = true;
      _error = null;
    });
    try {
      final path = await _upload.pickAndUpload();
      if (path != null) widget.onPhotoChanged(path);
    } on TestimonialPhotoUploadFailure catch (error) {
      _error = error.message;
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          children: [
            StoryAvatar(
              displayName: widget.fullNameController.text,
              photoStoragePath: widget.photoStoragePath,
              radius: 32,
            ),
            const SizedBox(width: 16),
            OutlinedButton.icon(
              onPressed: _uploading ? null : _pickPhoto,
              icon: const Icon(Icons.photo_camera_outlined),
              label: Text(
                widget.photoStoragePath == null
                    ? 'Add a photo (optional)'
                    : 'Change photo',
              ),
            ),
          ],
        ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(top: 8),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        const SizedBox(height: 20),
        TextField(
          controller: widget.fullNameController,
          decoration: const InputDecoration(labelText: 'Your name'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: widget.universityController,
          decoration: const InputDecoration(labelText: 'University (optional)'),
        ),
        const SizedBox(height: 12),
        TextField(
          controller: widget.programController,
          decoration: const InputDecoration(labelText: 'Program (optional)'),
        ),
      ],
    );
  }
}

class _PrivacyStep extends StatelessWidget {
  const _PrivacyStep({
    required this.displayMode,
    required this.showUniversity,
    required this.showCountry,
    required this.showProgram,
    required this.showPhoto,
    required this.draft,
    required this.onChanged,
  });

  final TestimonialDisplayMode displayMode;
  final bool showUniversity;
  final bool showCountry;
  final bool showProgram;
  final bool showPhoto;
  final TestimonialDraftInput draft;
  final ValueChanged<TestimonialDraftInput> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          'How should your name appear?',
          style: Theme.of(context).textTheme.titleSmall,
        ),
        RadioGroup<TestimonialDisplayMode>(
          groupValue: displayMode,
          onChanged: (value) {
            if (value != null) {
              onChanged(draft.copyWith(displayMode: value));
            }
          },
          child: Column(
            children: [
              for (final mode in TestimonialDisplayMode.values)
                RadioListTile<TestimonialDisplayMode>(
                  value: mode,
                  title: Text(mode.label),
                ),
            ],
          ),
        ),
        const Divider(),
        SwitchListTile(
          title: const Text('Display university'),
          value: showUniversity,
          onChanged: (value) =>
              onChanged(draft.copyWith(showUniversity: value)),
        ),
        SwitchListTile(
          title: const Text('Display country'),
          value: showCountry,
          onChanged: (value) => onChanged(draft.copyWith(showCountry: value)),
        ),
        SwitchListTile(
          title: const Text('Display program'),
          value: showProgram,
          onChanged: (value) => onChanged(draft.copyWith(showProgram: value)),
        ),
        SwitchListTile(
          title: const Text('Display photo'),
          value: showPhoto,
          onChanged: (value) => onChanged(draft.copyWith(showPhoto: value)),
        ),
      ],
    );
  }
}

class _EvidenceStep extends StatefulWidget {
  const _EvidenceStep({required this.paths, required this.onChanged});

  final List<String> paths;
  final ValueChanged<List<String>> onChanged;

  @override
  State<_EvidenceStep> createState() => _EvidenceStepState();
}

class _EvidenceStepState extends State<_EvidenceStep> {
  final _upload = TestimonialEvidenceUpload();
  bool _uploading = false;
  String? _error;

  Future<void> _pick() async {
    if (widget.paths.length >= 5) return;
    setState(() {
      _uploading = true;
      _error = null;
    });
    try {
      final path = await _upload.pickAndUpload();
      if (path != null) widget.onChanged([...widget.paths, path]);
    } on TestimonialEvidenceUploadFailure catch (error) {
      _error = error.message;
    } finally {
      if (mounted) setState(() => _uploading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Supporting evidence is reviewed privately and is not '
          'automatically published. This is optional, but it is required '
          'before a story can display a "Verified" badge.',
        ),
        const SizedBox(height: 12),
        for (final path in widget.paths)
          ListTile(
            leading: const Icon(Icons.description_outlined),
            title: Text(path.split('/').last),
            trailing: IconButton(
              icon: const Icon(Icons.close),
              onPressed: () => widget.onChanged(
                widget.paths.where((item) => item != path).toList(),
              ),
            ),
          ),
        if (_error != null)
          Padding(
            padding: const EdgeInsets.only(bottom: 8),
            child: Text(_error!, style: const TextStyle(color: Colors.red)),
          ),
        OutlinedButton.icon(
          onPressed: widget.paths.length >= 5 || _uploading ? null : _pick,
          icon: const Icon(Icons.upload_file),
          label: Text(
            _uploading ? 'Uploading...' : 'Upload evidence (PDF/JPEG/PNG)',
          ),
        ),
      ],
    );
  }
}

class _ReviewStep extends StatelessWidget {
  const _ReviewStep({required this.draft});

  final TestimonialDraftInput draft;

  @override
  Widget build(BuildContext context) {
    final displayName = _previewName(draft);
    final preview = SuccessStorySummary(
      id: 'preview',
      slug: 'preview',
      displayName: displayName,
      photoStoragePath: draft.showPhoto ? draft.photoStoragePath : null,
      country: draft.showCountry ? draft.country : null,
      university: draft.showUniversity ? draft.university : null,
      program: draft.showProgram ? draft.program : null,
      degreeLevel: draft.degreeLevel,
      fieldOfStudy: draft.fieldOfStudy,
      opportunityName: draft.opportunityName.isEmpty
          ? '(Opportunity name)'
          : draft.opportunityName,
      opportunityProvider: draft.opportunityProvider,
      opportunityType: draft.opportunityType,
      outcome: draft.outcome,
      successYear: draft.successYear,
      verificationStatus: TestimonialVerificationStatus.unverified,
      featured: false,
      badges: const ['under_review'],
      excerpt: draft.outcomeNarrative ?? draft.impact ?? '',
      featuresUsed: draft.featuresUsed,
      helpfulCount: 0,
      inspiringCount: 0,
      usefulCount: 0,
      createdAt: DateTime.now(),
    );
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'This is exactly how your story will appear publicly once '
          'approved (with the privacy choices you made on the previous '
          'step already applied).',
        ),
        const SizedBox(height: 16),
        SuccessStoryCard(story: preview, onTap: () {}),
      ],
    );
  }

  static String _previewName(TestimonialDraftInput draft) {
    final name = draft.fullName.trim();
    if (draft.displayMode == TestimonialDisplayMode.anonymous || name.isEmpty) {
      return 'Anonymous Applicant';
    }
    if (draft.displayMode == TestimonialDisplayMode.fullName) return name;
    final parts = name.split(' ');
    if (parts.length == 1) return parts.first;
    return '${parts.first} ${parts.last[0]}.';
  }
}

class _ConsentStep extends StatelessWidget {
  const _ConsentStep({
    required this.truthful,
    required this.permission,
    required this.public,
    required this.withdrawal,
    required this.onTruthfulChanged,
    required this.onPermissionChanged,
    required this.onPublicChanged,
    required this.onWithdrawalChanged,
    required this.canSubmit,
    required this.onSubmit,
  });

  final bool truthful;
  final bool permission;
  final bool public;
  final bool withdrawal;
  final ValueChanged<bool> onTruthfulChanged;
  final ValueChanged<bool> onPermissionChanged;
  final ValueChanged<bool> onPublicChanged;
  final ValueChanged<bool> onWithdrawalChanged;
  final bool canSubmit;
  final VoidCallback onSubmit;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        CheckboxListTile(
          value: truthful,
          onChanged: (value) => onTruthfulChanged(value ?? false),
          title: const Text('This story is truthful.'),
        ),
        CheckboxListTile(
          value: permission,
          onChanged: (value) => onPermissionChanged(value ?? false),
          title: const Text('I have permission to submit this content.'),
        ),
        CheckboxListTile(
          value: public,
          onChanged: (value) => onPublicChanged(value ?? false),
          title: const Text(
            'I understand this story may be publicly displayed, subject '
            'to the privacy choices I made.',
          ),
        ),
        CheckboxListTile(
          value: withdrawal,
          onChanged: (value) => onWithdrawalChanged(value ?? false),
          title: const Text(
            'I understand I can request withdrawal or editing according '
            'to ScholarSphere\'s policy.',
          ),
        ),
        const SizedBox(height: 16),
        FilledButton(
          onPressed: canSubmit ? onSubmit : null,
          child: const Text('Submit for Review'),
        ),
      ],
    );
  }
}
