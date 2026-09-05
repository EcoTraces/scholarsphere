import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:firebase_storage/firebase_storage.dart' as storage;

/// Uploads success-story supporting evidence directly to Firebase
/// Storage - the backend never handles the file bytes, matching
/// [ApplicantDocumentUpload]'s established pattern. `storage.rules`
/// keeps `testimonial-evidence/` readable only by the uploading
/// applicant and the staff roles that moderate testimonials
/// (moderator/administrator/superAdministrator) - never public, and
/// never automatically shown alongside the published story (Phase 7 of
/// the feature spec: "Do NOT require users to publicly expose sensitive
/// documents").
class TestimonialEvidenceUploadFailure implements Exception {
  const TestimonialEvidenceUploadFailure(this.message);
  final String message;

  @override
  String toString() => message;
}

class TestimonialEvidenceUpload {
  TestimonialEvidenceUpload({
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
  /// file to the caller's own evidence folder, and returns the resulting
  /// Storage path to attach to the draft. Returns null if the user
  /// cancels.
  Future<String?> pickAndUpload() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const TestimonialEvidenceUploadFailure(
        'Sign in to upload evidence.',
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
      throw const TestimonialEvidenceUploadFailure(
        'Could not read the selected file.',
      );
    }
    if (bytes.lengthInBytes > _maxBytes) {
      throw const TestimonialEvidenceUploadFailure(
        'Files must be 10 MB or smaller.',
      );
    }
    final dot = file.name.lastIndexOf('.');
    final extension = dot == -1
        ? ''
        : file.name.substring(dot + 1).toLowerCase();
    final contentType = _contentTypes[extension];
    if (contentType == null) {
      throw const TestimonialEvidenceUploadFailure(
        'Only PDF, JPEG, and PNG files are accepted.',
      );
    }
    final path = 'testimonial-evidence/${user.uid}/${file.name}';
    try {
      await _storage
          .ref(path)
          .putData(bytes, storage.SettableMetadata(contentType: contentType));
    } on Exception catch (error) {
      throw TestimonialEvidenceUploadFailure('Upload failed: $error');
    }
    return path;
  }
}
