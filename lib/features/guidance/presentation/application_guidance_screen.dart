import 'package:flutter/material.dart';

import '../../documents/domain/document_readiness.dart';
import '../../opportunities/domain/opportunity.dart';
import '../../profiles/domain/applicant_profile.dart';
import '../domain/application_guidance.dart';
import '../domain/application_guidance_repository.dart';

class ApplicationGuidanceScreen extends StatefulWidget {
  const ApplicationGuidanceScreen({
    super.key,
    required this.userId,
    required this.opportunity,
    required this.profile,
    required this.documents,
    required this.repository,
  });
  final String userId;
  final Opportunity opportunity;
  final ApplicantProfile profile;
  final List<UserDocument> documents;
  final ApplicationGuidanceRepository repository;

  @override
  State<ApplicationGuidanceScreen> createState() =>
      _ApplicationGuidanceScreenState();
}

class _ApplicationGuidanceScreenState extends State<ApplicationGuidanceScreen> {
  late Future<ApplicationGuidancePlan> _plan;

  @override
  void initState() {
    super.initState();
    _plan = _load();
  }

  Future<ApplicationGuidancePlan> _load() async =>
      await widget.repository.getPlan(widget.userId, widget.opportunity.id) ??
      widget.repository.createPlan(
        userId: widget.userId,
        opportunity: widget.opportunity,
        profile: widget.profile,
        documents: widget.documents,
      );

  @override
  Widget build(BuildContext context) => FutureBuilder<ApplicationGuidancePlan>(
    future: _plan,
    builder: (context, snapshot) {
      if (!snapshot.hasData) {
        return const Scaffold(body: Center(child: CircularProgressIndicator()));
      }
      final plan = snapshot.data!;
      return Scaffold(
        appBar: AppBar(title: const Text('Application guidance')),
        body: ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              widget.opportunity.title,
              style: Theme.of(context).textTheme.headlineLarge,
            ),
            const SizedBox(height: 16),
            Text('Application readiness: ${plan.applicationReadinessScore}%'),
            LinearProgressIndicator(
              value: plan.applicationReadinessScore / 100,
            ),
            const SizedBox(height: 12),
            Text('Document readiness: ${plan.documentReadinessScore}%'),
            LinearProgressIndicator(value: plan.documentReadinessScore / 100),
            const SizedBox(height: 24),
            for (final item in ([
              ...plan.items,
            ]..sort((a, b) => a.order.compareTo(b.order))))
              CheckboxListTile(
                value: {
                  GuidanceItemStatus.ready,
                  GuidanceItemStatus.confirmed,
                }.contains(item.status),
                title: Text(item.title),
                subtitle: Text(item.guidance),
                onChanged: (checked) async {
                  final updated = await widget.repository.updateItem(
                    plan.id,
                    item.id,
                    checked == true
                        ? GuidanceItemStatus.ready
                        : GuidanceItemStatus.inProgress,
                  );
                  if (mounted) {
                    setState(() => _plan = Future.value(updated));
                  }
                },
              ),
            const SizedBox(height: 16),
            Text(plan.disclaimer),
          ],
        ),
      );
    },
  );
}
