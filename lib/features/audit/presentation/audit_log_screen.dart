import 'package:flutter/material.dart';

import '../../authentication/domain/user_account.dart';
import '../domain/audit_record.dart';
import '../domain/audit_repository.dart';

class AuditLogScreen extends StatefulWidget {
  const AuditLogScreen({
    super.key,
    required this.user,
    required this.repository,
  });
  final UserAccount user;
  final AuditRepository repository;

  @override
  State<AuditLogScreen> createState() => _AuditLogScreenState();
}

class _AuditLogScreenState extends State<AuditLogScreen> {
  AuditAction? _action;
  String _query = '';
  late Future<List<AuditRecord>> _records;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _records = widget.repository.search(
      widget.user.role,
      AuditQuery(action: _action),
    );
  }

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(
      title: const Text('Audit log'),
      actions: [
        IconButton(
          onPressed: _export,
          tooltip: 'Export audit log',
          icon: const Icon(Icons.download_outlined),
        ),
      ],
    ),
    body: FutureBuilder<List<AuditRecord>>(
      future: _records,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final records = snapshot.data!
            .where(
              (record) =>
                  _query.isEmpty ||
                  record.actorId.toLowerCase().contains(_query) ||
                  record.entityId.toLowerCase().contains(_query),
            )
            .toList()
            .reversed;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            TextField(
              decoration: const InputDecoration(
                prefixIcon: Icon(Icons.search),
                labelText: 'Search actor or entity',
              ),
              onChanged: (value) =>
                  setState(() => _query = value.toLowerCase().trim()),
            ),
            const SizedBox(height: 12),
            DropdownButtonFormField<AuditAction?>(
              initialValue: _action,
              decoration: const InputDecoration(labelText: 'Action'),
              items: [
                const DropdownMenuItem(value: null, child: Text('All actions')),
                ...AuditAction.values.map(
                  (action) => DropdownMenuItem(
                    value: action,
                    child: Text(_label(action.name)),
                  ),
                ),
              ],
              onChanged: (value) {
                _action = value;
                setState(_reload);
              },
            ),
            const SizedBox(height: 20),
            for (final record in records)
              Card(
                child: ListTile(
                  title: Text(_label(record.action.name)),
                  subtitle: Text(
                    '${record.actorId} | ${record.entityType}: '
                    '${record.entityId}\n${record.timestamp.toLocal()}',
                  ),
                  isThreeLine: true,
                  trailing: Chip(label: Text(record.result.name)),
                ),
              ),
          ],
        );
      },
    ),
  );

  Future<void> _export() async {
    final csv = await widget.repository.exportCsv(
      widget.user.role,
      AuditQuery(action: _action),
    );
    if (!mounted) return;
    showDialog<void>(
      context: context,
      builder: (context) => AlertDialog(
        title: const Text('Audit export prepared'),
        content: Text('${csv.split('\n').length - 1} records exported.'),
        actions: [
          FilledButton(
            onPressed: () => Navigator.pop(context),
            child: const Text('Done'),
          ),
        ],
      ),
    );
  }

  static String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}
