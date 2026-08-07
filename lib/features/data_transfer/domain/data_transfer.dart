enum ImportFormat { csv, excel, json, api }

enum ImportStatus {
  uploaded,
  validated,
  previewed,
  approved,
  imported,
  rolledBack,
}

class ImportRow {
  const ImportRow({
    required this.values,
    this.errors = const [],
    this.duplicate = false,
  });
  final Map<String, Object?> values;
  final List<String> errors;
  final bool duplicate;
  bool get valid => errors.isEmpty && !duplicate;
}

class ImportBatch {
  const ImportBatch({
    required this.id,
    required this.format,
    required this.rows,
    required this.status,
    required this.createdBy,
    required this.createdAt,
  });
  final String id;
  final ImportFormat format;
  final List<ImportRow> rows;
  final ImportStatus status;
  final String createdBy;
  final DateTime createdAt;
}

abstract interface class DataTransferRepository {
  Future<ImportBatch> upload({
    required ImportFormat format,
    required List<Map<String, Object?>> records,
    required String actorId,
  });
  Future<ImportBatch> preview(String batchId);
  Future<ImportBatch> approve(String batchId, String administratorId);
  Future<ImportBatch> importToVerificationQueue(String batchId);
  Future<void> rollback(String batchId, String administratorId);
  Future<String> exportCsv(List<Map<String, Object?>> records);
  Future<List<String>> auditLog();
}
