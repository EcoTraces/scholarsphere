import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/backup_repository.dart';
import '../domain/backup_recovery.dart';
import '../domain/observability_repository.dart';
import '../domain/release_repository.dart';
import '../domain/system_configuration.dart';
import '../domain/system_configuration_repository.dart';

class OperationsConsoleScreen extends StatefulWidget {
  const OperationsConsoleScreen({
    super.key,
    required this.user,
    required this.configurationRepository,
    required this.observabilityRepository,
    required this.backupRepository,
    required this.releaseRepository,
  });
  final UserAccount user;
  final SystemConfigurationRepository configurationRepository;
  final ObservabilityRepository observabilityRepository;
  final BackupRepository backupRepository;
  final ReleaseRepository releaseRepository;

  @override
  State<OperationsConsoleScreen> createState() =>
      _OperationsConsoleScreenState();
}

class _OperationsConsoleScreenState extends State<OperationsConsoleScreen> {
  late Future<PlatformConfiguration> _configuration;

  @override
  void initState() {
    super.initState();
    _configuration = widget.configurationRepository.current();
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('System operations')),
    body: FutureBuilder<PlatformConfiguration>(
      future: _configuration,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final value = snapshot.data!;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text(
              'Platform configuration',
              style: Theme.of(context).textTheme.headlineSmall,
            ),
            const SizedBox(height: 12),
            TextFormField(
              initialValue: value.platformName,
              decoration: const InputDecoration(labelText: 'Platform name'),
              onFieldSubmitted: (name) =>
                  _save(value.copyWith(platformName: name)),
            ),
            const SizedBox(height: 12),
            SwitchListTile(
              value: value.maintenanceMode,
              title: const Text('Maintenance mode'),
              onChanged: (enabled) =>
                  _save(value.copyWith(maintenanceMode: enabled)),
            ),
            for (final flag in FeatureFlag.values)
              SwitchListTile(
                value: value.enabled(flag),
                title: Text(_label(flag.name)),
                onChanged: (enabled) {
                  final flags = {...value.featureFlags, flag: enabled};
                  _save(value.copyWith(featureFlags: flags));
                },
              ),
            const Divider(height: 32),
            Wrap(
              spacing: 10,
              runSpacing: 10,
              children: [
                OutlinedButton.icon(
                  onPressed: _showHistory,
                  icon: const Icon(Icons.history),
                  label: Text('Configuration v${value.version}'),
                ),
                OutlinedButton.icon(
                  onPressed: _showHealth,
                  icon: const Icon(Icons.monitor_heart_outlined),
                  label: const Text('Service health'),
                ),
                if ({
                  UserRole.securityAdministrator,
                  UserRole.superAdministrator,
                }.contains(widget.user.role))
                  OutlinedButton.icon(
                    onPressed: _createBackup,
                    icon: const Icon(Icons.backup_outlined),
                    label: const Text('Create encrypted backup'),
                  ),
                OutlinedButton.icon(
                  onPressed: _showDeployments,
                  icon: const Icon(Icons.rocket_launch_outlined),
                  label: const Text('Deployment history'),
                ),
              ],
            ),
          ],
        );
      },
    ),
  );

  Future<void> _save(PlatformConfiguration value) async {
    final updated = await widget.configurationRepository.update(
      widget.user,
      value,
      'Updated through operations console',
    );
    if (mounted) setState(() => _configuration = Future.value(updated));
  }

  Future<void> _showHistory() async {
    final history = await widget.configurationRepository.history(widget.user);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Configuration history'),
        content: SizedBox(
          width: 500,
          child: ListView(
            shrinkWrap: true,
            children: history
                .map(
                  (item) => ListTile(
                    title: Text('Version ${item.version}'),
                    subtitle: Text('${item.updatedBy} | ${item.changeReason}'),
                    trailing: item.version == history.first.version
                        ? null
                        : IconButton(
                            tooltip: 'Roll back to this version',
                            icon: const Icon(Icons.restore),
                            onPressed: () async {
                              final restored = await widget
                                  .configurationRepository
                                  .rollback(
                                    widget.user,
                                    item.version,
                                    'Administrator rollback',
                                  );
                              if (!context.mounted) return;
                              Navigator.pop(context);
                              setState(
                                () => _configuration = Future.value(restored),
                              );
                            },
                          ),
                  ),
                )
                .toList(),
          ),
        ),
      ),
    );
  }

  Future<void> _showHealth() async {
    final health = await widget.observabilityRepository.health();
    final report = await widget.observabilityRepository.performanceReport();
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('System health'),
        content: Text(
          '${health.length} services checked\n'
          '${report.requestVolume} monitored requests\n'
          '${(report.errorRate * 100).toStringAsFixed(1)}% error rate',
        ),
      ),
    );
  }

  Future<void> _createBackup() async {
    final backup = await widget.backupRepository.createBackup(
      widget.user,
      BackupType.fullDatabase,
      region: 'separate-recovery-region',
    );
    await widget.backupRepository.verifyIntegrity(widget.user, backup.id);
    if (!mounted) return;
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Backup ${backup.id} created and verified.')),
    );
  }

  Future<void> _showDeployments() async {
    final deployments = await widget.releaseRepository.history(widget.user);
    if (!mounted) return;
    await showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Deployment history'),
        content: Text(
          deployments.isEmpty
              ? 'No deployment records.'
              : deployments
                    .map(
                      (item) => '${item.artifact.version}: ${item.status.name}',
                    )
                    .join('\n'),
        ),
      ),
    );
  }

  static String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}
