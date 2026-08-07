import 'package:flutter/material.dart';

import '../../opportunities/domain/opportunity.dart';
import '../domain/notification.dart';
import '../domain/notification_repository.dart';

class NotificationCenterScreen extends StatefulWidget {
  const NotificationCenterScreen({
    super.key,
    required this.userId,
    required this.opportunities,
    required this.repository,
  });

  final String userId;
  final List<Opportunity> opportunities;
  final NotificationRepository repository;

  @override
  State<NotificationCenterScreen> createState() =>
      _NotificationCenterScreenState();
}

class _NotificationCenterScreenState extends State<NotificationCenterScreen> {
  late Future<List<ScholarSphereNotification>> _notifications;

  @override
  void initState() {
    super.initState();
    _load();
  }

  void _load() {
    _notifications = widget.repository
        .scheduleDeadlineReminders(
          userId: widget.userId,
          opportunities: widget.opportunities,
        )
        .then((_) => widget.repository.processDueNotifications())
        .then((_) => widget.repository.getForUser(widget.userId));
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Notifications'),
        actions: [
          IconButton(
            tooltip: 'Notification settings',
            onPressed: _openSettings,
            icon: const Icon(Icons.tune),
          ),
          const SizedBox(width: 8),
        ],
      ),
      body: FutureBuilder<List<ScholarSphereNotification>>(
        future: _notifications,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final records = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(20),
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'Updates and reminders',
                        style: Theme.of(context).textTheme.headlineLarge,
                      ),
                      const SizedBox(height: 16),
                      for (final item in records)
                        Card(
                          margin: const EdgeInsets.only(bottom: 10),
                          child: ListTile(
                            contentPadding: const EdgeInsets.all(14),
                            leading: Icon(
                              item.type ==
                                      NotificationEventType.deadlineReminder
                                  ? Icons.event_outlined
                                  : Icons.notifications_outlined,
                            ),
                            title: Text(item.title),
                            subtitle: Text(
                              '${item.message}\n'
                              '${_label(item.status.name)}: '
                              '${_date(item.scheduledFor)}',
                            ),
                            isThreeLine: true,
                            trailing: item.isRead
                                ? null
                                : const Icon(Icons.circle, size: 10),
                            onTap: () async {
                              await widget.repository.markRead(
                                widget.userId,
                                item.id,
                              );
                              setState(_load);
                            },
                          ),
                        ),
                    ],
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }

  Future<void> _openSettings() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => NotificationSettingsScreen(
          userId: widget.userId,
          repository: widget.repository,
        ),
      ),
    );
    setState(_load);
  }

  static String _date(DateTime date) =>
      '${date.day}/${date.month}/${date.year}';

  static String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}

class NotificationSettingsScreen extends StatefulWidget {
  const NotificationSettingsScreen({
    super.key,
    required this.userId,
    required this.repository,
  });

  final String userId;
  final NotificationRepository repository;

  @override
  State<NotificationSettingsScreen> createState() =>
      _NotificationSettingsScreenState();
}

class _NotificationSettingsScreenState
    extends State<NotificationSettingsScreen> {
  late Future<NotificationPreferences> _preferences;

  @override
  void initState() {
    super.initState();
    _preferences = widget.repository.getPreferences(widget.userId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Notification settings')),
      body: FutureBuilder<NotificationPreferences>(
        future: _preferences,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          return _SettingsForm(
            userId: widget.userId,
            repository: widget.repository,
            initial: snapshot.data!,
          );
        },
      ),
    );
  }
}

class _SettingsForm extends StatefulWidget {
  const _SettingsForm({
    required this.userId,
    required this.repository,
    required this.initial,
  });

  final String userId;
  final NotificationRepository repository;
  final NotificationPreferences initial;

  @override
  State<_SettingsForm> createState() => _SettingsFormState();
}

class _SettingsFormState extends State<_SettingsForm> {
  late NotificationPreferences _value;

  @override
  void initState() {
    super.initState();
    _value = widget.initial;
  }

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.all(24),
      children: [
        Center(
          child: ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 720),
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  'Delivery channels',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                for (final channel in NotificationChannel.values)
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _value.channels.contains(channel),
                    title: Text(_label(channel.name)),
                    subtitle:
                        channel == NotificationChannel.sms ||
                            channel == NotificationChannel.whatsapp
                        ? const Text('Requires a configured delivery provider')
                        : null,
                    onChanged: (enabled) {
                      final channels = {..._value.channels};
                      enabled == true
                          ? channels.add(channel)
                          : channels.remove(channel);
                      setState(
                        () => _value = _value.copyWith(channels: channels),
                      );
                    },
                  ),
                const SizedBox(height: 16),
                DropdownButtonFormField<NotificationFrequency>(
                  initialValue: _value.frequency,
                  decoration: const InputDecoration(labelText: 'Frequency'),
                  items: NotificationFrequency.values
                      .map(
                        (item) => DropdownMenuItem(
                          value: item,
                          child: Text(_label(item.name)),
                        ),
                      )
                      .toList(),
                  onChanged: (frequency) => setState(
                    () => _value = _value.copyWith(frequency: frequency),
                  ),
                ),
                const SizedBox(height: 24),
                Text(
                  'Deadline reminders',
                  style: Theme.of(context).textTheme.headlineSmall,
                ),
                for (final days in const [30, 14, 7, 3, 1])
                  CheckboxListTile(
                    contentPadding: EdgeInsets.zero,
                    value: _value.reminderDays.contains(days),
                    title: Text(
                      days == 1 ? '24 hours before' : '$days days before',
                    ),
                    onChanged: (enabled) {
                      final reminders = {..._value.reminderDays};
                      enabled == true
                          ? reminders.add(days)
                          : reminders.remove(days);
                      setState(
                        () => _value = _value.copyWith(reminderDays: reminders),
                      );
                    },
                  ),
                const SizedBox(height: 16),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Matching opportunities'),
                  value: _value.matchingOpportunities,
                  onChanged: (enabled) => setState(
                    () => _value = _value.copyWith(
                      matchingOpportunities: enabled,
                    ),
                  ),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Requirement and deadline changes'),
                  value: _value.opportunityChanges,
                  onChanged: (enabled) => setState(
                    () => _value = _value.copyWith(opportunityChanges: enabled),
                  ),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Verification updates'),
                  value: _value.verificationUpdates,
                  onChanged: (enabled) => setState(
                    () =>
                        _value = _value.copyWith(verificationUpdates: enabled),
                  ),
                ),
                SwitchListTile(
                  contentPadding: EdgeInsets.zero,
                  title: const Text('Saved opportunity expiry'),
                  value: _value.savedOpportunityExpiry,
                  onChanged: (enabled) => setState(
                    () => _value = _value.copyWith(
                      savedOpportunityExpiry: enabled,
                    ),
                  ),
                ),
                const SizedBox(height: 24),
                SizedBox(
                  width: double.infinity,
                  child: FilledButton.icon(
                    onPressed: _save,
                    icon: const Icon(Icons.save_outlined),
                    label: const Text('Save notification settings'),
                  ),
                ),
              ],
            ),
          ),
        ),
      ],
    );
  }

  Future<void> _save() async {
    await widget.repository.savePreferences(widget.userId, _value);
    if (!mounted) return;
    Navigator.of(context).pop();
  }

  static String _label(String value) {
    final spaced = value.replaceAllMapped(
      RegExp(r'([A-Z])'),
      (match) => ' ${match.group(1)!.toLowerCase()}',
    );
    return '${spaced[0].toUpperCase()}${spaced.substring(1)}';
  }
}
