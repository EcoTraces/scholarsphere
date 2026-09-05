import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:firebase_storage/firebase_storage.dart' as storage;

/// Uploads a personal applicant document directly to Firebase Storage.
///
/// The backend never handles the file bytes - `storage.rules` enforces the
/// strictly owner-only (no staff access, unlike provider-documents) read/
/// write path, the 10 MB size cap, and the PDF/JPEG/PNG content-type
/// allowlist. This class only returns the resulting Storage path
/// (`applicant-documents/{uid}/{fileName}`), which is what the backend
/// expects when adding a document.
class ApplicantDocumentUploadFailure implements Exception {
  const ApplicantDocumentUploadFailure(this.message);
  final String message;

  @override
  String toString() => message;
}

class ApplicantDocumentUpload {
  ApplicantDocumentUpload({
    firebase.FirebaseAuth? auth,
    storage.FirebaseStorage? storageInstance,
  }) : _authOverride = auth,
       _storageOverride = storageInstance;

  final firebase.FirebaseAuth? _authOverride;
  final storage.FirebaseStorage? _storageOverride;

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;
  storage.FirebaseStorage get _storage =>
      _storageOverride ?? storage.FirebaseStorage.instance;

  static const _allowedExtensions = ['pdf', 'jpg', 'jpeg', 'png'];
  static const _maxBytes = 10 * 1024 * 1024;
  static const _contentTypes = {
    'pdf': 'application/pdf',
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
  };

  /// Opens a file picker restricted to PDF/JPEG/PNG, uploads the chosen
  /// file to the caller's own Storage folder, and returns the resulting
  /// (storagePath, fileName) pair. Returns null if the user cancels.
  Future<({String storagePath, String fileName})?> pickAndUpload() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const ApplicantDocumentUploadFailure(
        'Sign in to upload a document.',
      );
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
      throw const ApplicantDocumentUploadFailure(
        'Could not read the selected file.',
      );
    }
    if (bytes.lengthInBytes > _maxBytes) {
      throw const ApplicantDocumentUploadFailure(
        'Files must be 10 MB or smaller.',
      );
    }
    final dot = file.name.lastIndexOf('.');
    final extension = dot == -1
        ? ''
        : file.name.substring(dot + 1).toLowerCase();
    final contentType = _contentTypes[extension];
    if (contentType == null) {
      throw const ApplicantDocumentUploadFailure(
        'Only PDF, JPEG, and PNG files are accepted.',
      );
    }
    final path = 'applicant-documents/${user.uid}/${file.name}';
    try {
      await _storage
          .ref(path)
          .putData(bytes, storage.SettableMetadata(contentType: contentType));
    } on Exception catch (error) {
      throw ApplicantDocumentUploadFailure('Upload failed: $error');
    }
    return (storagePath: path, fileName: file.name);
  }

  /// Deletes the underlying Storage object for a previously uploaded
  /// document. Safe to call even if the object no longer exists.
  Future<void> delete(String storagePath) async {
    try {
      await _storage.ref(storagePath).delete();
    } on Exception {
      // Best-effort: the backend row is the source of truth for whether a
      // document "exists"; a Storage object already gone (or never
      // uploaded, e.g. a demo record) shouldn't block removing the record.
    }
  }
}
