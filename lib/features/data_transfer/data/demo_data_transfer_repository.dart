import '../domain/data_transfer.dart';

class DemoDataTransferRepository implements DataTransferRepository {
  final Map<String, ImportBatch> _batches = {};
  final List<String> _audit = [];
  final Set<String> _knownOfficialUrls = {};

  @override
  Future<ImportBatch> upload({
    required ImportFormat format,
    required List<Map<String, Object?>> records,
    required String actorId,
  }) async {
    final rows = records.map((record) {
      final errors = <String>[];
      for (final field in const ['title', 'officialSourceUrl']) {
        if ((record[field]?.toString().trim() ?? '').isEmpty)
          errors.add('$field is required');
      }
      final url = record['officialSourceUrl']?.toString();
      return ImportRow(
        values: Map.unmodifiable(record),
        errors: errors,
        duplicate: url != null && _knownOfficialUrls.contains(url),
      );
    }).toList();
    final batch = ImportBatch(
      id: 'import-${_batches.length + 1}',
      format: format,
      rows: rows,
      status: ImportStatus.validated,
      createdBy: actorId,
      createdAt: DateTime.now(),
    );
    _batches[batch.id] = batch;
    _audit.add('$actorId uploaded ${batch.id}');
    return batch;
  }

  ImportBatch _replace(ImportBatch batch, ImportStatus status) {
    final next = ImportBatch(
      id: batch.id,
      format: batch.format,
      rows: batch.rows,
      status: status,
      createdBy: batch.createdBy,
      createdAt: batch.createdAt,
    );
    _batches[batch.id] = next;
    return next;
  }

  @override
  Future<ImportBatch> preview(String batchId) async =>
      _replace(_required(batchId), ImportStatus.previewed);

  @override
  Future<ImportBatch> approve(String batchId, String administratorId) async {
    final batch = _required(batchId);
    if (batch.status != ImportStatus.previewed)
      throw StateError('Preview required');
    if (batch.rows.any((row) => !row.valid))
      throw StateError('Resolve invalid rows');
    _audit.add('$administratorId approved $batchId');
    return _replace(batch, ImportStatus.approved);
  }

  @override
  Future<ImportBatch> importToVerificationQueue(String batchId) async {
    final batch = _required(batchId);
    if (batch.status != ImportStatus.approved)
      throw StateError('Approval required');
    for (final row in batch.rows) {
      _knownOfficialUrls.add(row.values['officialSourceUrl']! as String);
    }
    _audit.add('${batch.createdBy} imported $batchId to verification queue');
    return _replace(batch, ImportStatus.imported);
  }

  @override
  Future<void> rollback(String batchId, String administratorId) async {
    final batch = _required(batchId);
    if (batch.status != ImportStatus.imported)
      throw StateError('Import not completed');
    for (final row in batch.rows) {
      _knownOfficialUrls.remove(row.values['officialSourceUrl']);
    }
    _replace(batch, ImportStatus.rolledBack);
    _audit.add('$administratorId rolled back $batchId');
  }

  ImportBatch _required(String id) {
    final batch = _batches[id];
    if (batch == null) throw StateError('Import batch not found');
    return batch;
  }

  @override
  Future<String> exportCsv(List<Map<String, Object?>> records) async {
    if (records.isEmpty) return '';
    final headers = records.first.keys.toList();
    String escape(Object? value) =>
        '"${value.toString().replaceAll('"', '""')}"';
    return '${headers.join(',')}\n${records.map((row) => headers.map((key) => escape(row[key])).join(',')).join('\n')}';
  }

  @override
  Future<List<String>> auditLog() async => List.unmodifiable(_audit);
}
