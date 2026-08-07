import 'package:flutter/material.dart';

import '../../applications/domain/application_record.dart';
import '../../opportunities/domain/opportunity.dart';
import '../domain/calendar_event.dart';
import '../domain/calendar_repository.dart';

class CalendarScreen extends StatefulWidget {
  const CalendarScreen({
    super.key,
    required this.userId,
    required this.opportunities,
    required this.applications,
    required this.repository,
  });
  final String userId;
  final List<Opportunity> opportunities;
  final List<ApplicationRecord> applications;
  final CalendarRepository repository;

  @override
  State<CalendarScreen> createState() => _CalendarScreenState();
}

class _CalendarScreenState extends State<CalendarScreen> {
  late Future<List<CalendarEvent>> _events;

  @override
  void initState() {
    super.initState();
    _events = _load();
  }

  Future<List<CalendarEvent>> _load() async {
    final now = DateTime.now();
    for (final opportunity in widget.opportunities) {
      await widget.repository.save(
        CalendarEvent(
          id: '${widget.userId}-deadline-${opportunity.id}',
          userId: widget.userId,
          title: opportunity.title,
          description: 'Official opportunity deadline',
          type: CalendarEventType.opportunityDeadline,
          startsAt: opportunity.deadline,
          endsAt: opportunity.deadline.add(const Duration(hours: 1)),
          timezone: 'UTC',
          reminderMinutes: const {10080, 1440, 60},
          deadlineState: DeadlineState.upcoming,
          relatedEntityId: opportunity.id,
          createdAt: now,
        ),
      );
    }
    for (final application in widget.applications) {
      final interview = application.interviewDate;
      if (interview == null) continue;
      await widget.repository.save(
        CalendarEvent(
          id: '${widget.userId}-interview-${application.id}',
          userId: widget.userId,
          title: 'Interview: ${application.opportunityTitle}',
          description: 'Application interview',
          type: CalendarEventType.interview,
          startsAt: interview,
          endsAt: interview.add(const Duration(hours: 1)),
          timezone: 'UTC',
          reminderMinutes: const {1440, 60},
          deadlineState: DeadlineState.upcoming,
          relatedEntityId: application.id,
          createdAt: now,
        ),
      );
    }
    return widget.repository.events(widget.userId);
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Application calendar'),
      actions: [
        IconButton(
          tooltip: 'Export calendar',
          icon: const Icon(Icons.calendar_month_outlined),
          onPressed: _export,
        ),
      ],
    ),
    body: FutureBuilder<List<CalendarEvent>>(
      future: _events,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        return ListView(
          padding: const EdgeInsets.all(24),
          children: snapshot.data!
              .map(
                (event) => Card(
                  child: ListTile(
                    leading: const Icon(Icons.event_outlined),
                    title: Text(event.title),
                    subtitle: Text(
                      '${event.startsAt.toLocal()} | '
                      '${_label(event.deadlineState.name)}',
                    ),
                  ),
                ),
              )
              .toList(),
        );
      },
    ),
  );

  Future<void> _export() async {
    final ics = await widget.repository.exportIcs(widget.userId);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Calendar export ready'),
        content: Text(
          '${ics.split('BEGIN:VEVENT').length - 1} events exported.',
        ),
      ),
    );
  }

  static String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}
