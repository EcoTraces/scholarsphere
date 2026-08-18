import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:firebase_storage/firebase_storage.dart' as storage;

/// Uploads a provider registration document directly to Firebase Storage.
///
/// The backend never handles the file bytes - `storage.rules` enforces the
/// owner-only write path, the 10 MB size cap, and the PDF/JPEG/PNG
/// content-type allowlist. This class only stores/returns the resulting
/// Storage path (`provider-documents/{uid}/{fileName}`), which is what the
/// backend expects in `ProviderProfile.supportingDocuments`.
class ProviderDocumentUploadFailure implements Exception {
  const ProviderDocumentUploadFailure(this.message);
  final String message;

  @override
  String toString() => message;
}

class ProviderDocumentUpload {
  ProviderDocumentUpload({firebase.FirebaseAuth? auth, storage.FirebaseStorage? storageInstance})
    : _authOverride = auth,
      _storageOverride = storageInstance;

  final firebase.FirebaseAuth? _authOverride;
  final storage.FirebaseStorage? _storageOverride;

  firebase.FirebaseAuth get _auth => _authOverride ?? firebase.FirebaseAuth.instance;
  storage.FirebaseStorage get _storage => _storageOverride ?? storage.FirebaseStorage.instance;

  static const _allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png'];
  static const _maxBytes = 10 * 1024 * 1024;
  static const _contentTypes = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
  };

  /// Opens a file picker restricted to PDF/JPEG/PNG, uploads the chosen file
  /// to the caller's own Storage folder, and returns the resulting Storage
  /// path. Returns null if the user cancels the picker.
  Future<String?> pickAndUpload() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const ProviderDocumentUploadFailure('Sign in to upload a document.');
    }
    final file = await FilePicker.pickFile(
      type: FileType.custom,
      allowedExtensions: _allowedExtensions,
    );
    if (file == null) return null;
    final Uint8List bytes;
    try {
      bytes = await file.readAsBytes();
    } on Exception {
      throw const ProviderDocumentUploadFailure('Could not read the selected file.');
    }
    if (bytes.lengthInBytes > _maxBytes) {
      throw const ProviderDocumentUploadFailure('Files must be 10 MB or smaller.');
    }
    final dot = file.name.lastIndexOf('.');
    final extension = dot == -1 ? '' : file.name.substring(dot + 1).toLowerCase();
    final contentType = _contentTypes[extension];
    if (contentType == null) {
      throw const ProviderDocumentUploadFailure(
        'Only PDF, JPEG, and PNG files are accepted.',
      );
    }
    final path = 'provider-documents/${user.uid}/${file.name}';
    try {
      await _storage
          .ref(path)
          .putData(bytes, storage.SettableMetadata(contentType: contentType));
    } on Exception catch (error) {
      throw ProviderDocumentUploadFailure('Upload failed: $error');
    }
    return path;
  }
}
