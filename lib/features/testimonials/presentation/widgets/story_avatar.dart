import 'package:firebase_storage/firebase_storage.dart' as storage;
import 'package:flutter/material.dart';

/// Resolves a `testimonial-photos/{uid}/{file}` Storage *path* (never a
/// ready-to-use URL - see [SuccessStorySummary.photoStoragePath]) to its
/// public download URL and renders it as a circular avatar, falling back
/// to the applicant's display-name initial while loading or if no photo
/// was provided/opted into (`show_photo` is false server-side, so
/// `photoStoragePath` is simply null in that case - this widget never
/// needs its own privacy check).
class StoryAvatar extends StatelessWidget {
  const StoryAvatar({
    super.key,
    required this.displayName,
    required this.photoStoragePath,
    this.radius = 22,
  });

  final String displayName;
  final String? photoStoragePath;
  final double radius;

  @override
  Widget build(BuildContext context) {
    final path = photoStoragePath;
    if (path == null || path.isEmpty) {
      return CircleAvatar(radius: radius, child: Text(_initial(displayName)));
    }
    return FutureBuilder<String>(
      future: storage.FirebaseStorage.instance.ref(path).getDownloadURL(),
      builder: (context, snapshot) {
        if (snapshot.hasData) {
          return CircleAvatar(
            radius: radius,
            backgroundImage: NetworkImage(snapshot.data!),
          );
        }
        return CircleAvatar(
          radius: radius,
          child: snapshot.connectionState == ConnectionState.waiting
              ? const SizedBox(
                  width: 16,
                  height: 16,
                  child: CircularProgressIndicator(strokeWidth: 2),
                )
              : Text(_initial(displayName)),
        );
      },
    );
  }

  static String _initial(String name) =>
      name.isEmpty ? '?' : name[0].toUpperCase();
}
