import 'package:flutter/material.dart';
import 'package:url_launcher/url_launcher.dart';

/// Opens [url] in the platform browser, showing a SnackBar if the link
/// can't be opened (no matching handler, malformed URL) rather than
/// failing silently.
Future<void> openExternalLink(BuildContext context, String url) async {
  final uri = Uri.tryParse(url);
  final opened =
      uri != null && await launchUrl(uri, mode: LaunchMode.externalApplication);
  if (!opened && context.mounted) {
    ScaffoldMessenger.of(
      context,
    ).showSnackBar(SnackBar(content: Text('Could not open $url')));
  }
}

/// Opens the platform's mail client addressed to [email].
Future<void> openEmail(BuildContext context, String email) async {
  final uri = Uri(scheme: 'mailto', path: email);
  final opened = await launchUrl(uri);
  if (!opened && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Could not open mail app for $email')),
    );
  }
}

/// Opens the platform's dialer addressed to [phoneNumber].
Future<void> openPhone(BuildContext context, String phoneNumber) async {
  final uri = Uri(scheme: 'tel', path: phoneNumber);
  final opened = await launchUrl(uri);
  if (!opened && context.mounted) {
    ScaffoldMessenger.of(context).showSnackBar(
      SnackBar(content: Text('Could not open dialer for $phoneNumber')),
    );
  }
}
