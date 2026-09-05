import 'package:flutter/material.dart';

import '../../opportunities/domain/opportunity.dart';
import '../data/applicant_document_upload.dart';
import '../domain/document_readiness.dart';
import '../domain/document_readiness_service.dart';
import '../domain/document_repository.dart';

class DocumentReadinessPanel extends StatefulWidget {
  const DocumentReadinessPanel({
    super.key,
    required this.userId,
    required this.opportunity,
    required this.repository,
  });

  final String userId;
  final Opportunity opportunity;
  final DocumentRepository repository;

  @override
  State<DocumentReadinessPanel> createState() => _DocumentReadinessPanelState();
}

class _DocumentReadinessPanelState extends State<DocumentReadinessPanel> {
  late Future<DocumentReadiness> _readiness;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _readiness = widget.repository
        .getForUser(widget.userId)
        .then(
          (documents) => const DocumentReadinessService().evaluate(
            widget.opportunity,
            documents,
          ),
        );
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<DocumentReadiness>(
      future: _readiness,
      builder: (context, snapshot) {
        if (!snapshot.hasData) {
          return const Center(child: CircularProgressIndicator());
        }
        final readiness = snapshot.data!;
        return Container(
          padding: const EdgeInsets.all(18),
          decoration: BoxDecoration(
            border: Border.all(
              color: Theme.of(context).colorScheme.outlineVariant,
            ),
            borderRadius: BorderRadius.circular(8),
          ),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Document readiness',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const SizedBox(height: 8),
              Text(
                'You currently have ${readiness.readyCount} of the '
                '${readiness.requiredCount} documents required for this '
                'opportunity.',
              ),
              if (readiness.missing.isNotEmpty) ...[
                const SizedBox(height: 12),
                Text(
                  'Missing: ${readiness.missing.map(DocumentTypes.label).join(', ')}',
                ),
              ],
              const SizedBox(height: 14),
              OutlinedButton.icon(
                onPressed: _manage,
                icon: const Icon(Icons.folder_outlined),
                label: const Text('Manage documents'),
              ),
            ],
          ),
        );
      },
    );
  }

  Future<void> _manage() async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (context) => DocumentVaultScreen(
          userId: widget.userId,
          repository: widget.repository,
        ),
      ),
    );
    if (mounted) setState(_reload);
  }
}

class DocumentVaultScreen extends StatefulWidget {
  const DocumentVaultScreen({
    super.key,
    required this.userId,
    required this.repository,
  });

  final String userId;
  final DocumentRepository repository;

  @override
  State<DocumentVaultScreen> createState() => _DocumentVaultScreenState();
}

class _DocumentVaultScreenState extends State<DocumentVaultScreen> {
  final _upload = ApplicantDocumentUpload();
  late Future<List<UserDocument>> _documents;
  DocumentType? _busyType;
  String? _error;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _documents = widget.repository.getForUser(widget.userId);
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Private document vault')),
      body: FutureBuilder<List<UserDocument>>(
        future: _documents,
        builder: (context, snapshot) {
          if (!snapshot.hasData) {
            return const Center(child: CircularProgressIndicator());
          }
          final documents = snapshot.data!;
          return ListView(
            padding: const EdgeInsets.all(24),
            children: [
              Center(
                child: ConstrainedBox(
                  constraints: const BoxConstraints(maxWidth: 760),
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
                            Icon(Icons.enhanced_encryption_outlined),
                            SizedBox(width: 12),
                            Expanded(
                              child: Text(
                                'Document records are private, encrypted, and '
                                'owner-controlled. Providers receive no access '
                                'without your explicit consent.',
                              ),
                            ),
                          ],
                        ),
                      ),
                      Text(
                        'PDF, JPEG, or PNG, up to 10 MB.',
                        style: Theme.of(context).textTheme.bodySmall,
                      ),
                      if (_error != null) ...[
                        const SizedBox(height: 8),
                        Text(
                          _error!,
                          style: TextStyle(
                            color: Theme.of(context).colorScheme.error,
                          ),
                        ),
                      ],
                      const SizedBox(height: 20),
                      for (final type in DocumentType.values)
                        CheckboxListTile(
                          contentPadding: EdgeInsets.zero,
                          value: documents.any((item) => item.type == type),
                          title: Text(DocumentTypes.label(type)),
                          subtitle: _subtitle(type, documents),
                          secondary: _busyType == type
                              ? const SizedBox.square(
                                  dimension: 20,
                                  child: CircularProgressIndicator(
                                    strokeWidth: 2,
                                  ),
                                )
                              : null,
                          onChanged: _busyType != null
                              ? null
                              : (available) => _toggle(
                                  type,
                                  available ?? false,
                                  documents,
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

  Widget? _subtitle(DocumentType type, List<UserDocument> documents) {
    UserDocument? existing;
    for (final document in documents) {
      if (document.type == type) {
        existing = document;
        break;
      }
    }
    if (existing == null) return null;
    return Text('Encrypted and private • ${existing.fileName}');
  }

  Future<void> _toggle(
    DocumentType type,
    bool available,
    List<UserDocument> documents,
  ) async {
    UserDocument? existing;
    for (final document in documents) {
      if (document.type == type) {
        existing = document;
        break;
      }
    }
    setState(() {
      _busyType = type;
      _error = null;
    });
    try {
      if (available && existing == null) {
        final picked = await _upload.pickAndUpload();
        if (picked == null) return;
        await widget.repository.add(
          UserDocument(
            id: '${widget.userId}-${type.name}',
            ownerUserId: widget.userId,
            type: type,
            fileName: picked.fileName,
            uploadedAt: DateTime.now(),
            encryptedAtRest: true,
            storagePath: picked.storagePath,
          ),
        );
      } else if (!available && existing != null) {
        await widget.repository.remove(widget.userId, existing.id);
        final storagePath = existing.storagePath;
        if (storagePath != null) await _upload.delete(storagePath);
      }
    } on ApplicantDocumentUploadFailure catch (error) {
      _error = error.message;
    } on Exception catch (error) {
      _error = 'Could not update this document: $error';
    } finally {
      if (mounted) {
        setState(() {
          _busyType = null;
          _reload();
        });
      }
    }
  }
}
