import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:firebase_storage/firebase_storage.dart' as storage;

/// Uploads a success-story profile photo. Unlike
/// [TestimonialEvidenceUpload], `testimonial-photos/` is publicly
/// readable in `storage.rules` - a photo only ever ends up here because
/// the applicant chose to upload one for a story whose `showPhoto`
/// privacy toggle they also control, functionally a public avatar, not
/// a sensitive document.
class TestimonialPhotoUploadFailure implements Exception {
  const TestimonialPhotoUploadFailure(this.message);
  final String message;

  @override
  String toString() => message;
}

class TestimonialPhotoUpload {
  TestimonialPhotoUpload({
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

  static const _allowedExtensions = ['jpg', 'jpeg', 'png'];
  static const _maxBytes = 5 * 1024 * 1024;
  static const _contentTypes = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
  };

  Future<String?> pickAndUpload() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const TestimonialPhotoUploadFailure('Sign in to upload a photo.');
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
      throw const TestimonialPhotoUploadFailure(
        'Could not read the selected photo.',
      );
    }
    if (bytes.lengthInBytes > _maxBytes) {
      throw const TestimonialPhotoUploadFailure(
        'Photos must be 5 MB or smaller.',
      );
    }
    final dot = file.name.lastIndexOf('.');
    final extension = dot == -1
        ? ''
        : file.name.substring(dot + 1).toLowerCase();
    final contentType = _contentTypes[extension];
    if (contentType == null) {
      throw const TestimonialPhotoUploadFailure(
        'Only JPEG and PNG photos are accepted.',
      );
    }
    final path = 'testimonial-photos/${user.uid}/${file.name}';
    try {
      await _storage
          .ref(path)
          .putData(bytes, storage.SettableMetadata(contentType: contentType));
    } on Exception catch (error) {
      throw TestimonialPhotoUploadFailure('Upload failed: $error');
    }
    return path;
  }

  /// Public download URL for a photo stored under `testimonial-photos/`
  /// - safe to call without authentication since that path is publicly
  /// readable (see this file's own docstring and storage.rules).
  Future<String> publicUrl(String storagePath) =>
      _storage.ref(storagePath).getDownloadURL();
}
