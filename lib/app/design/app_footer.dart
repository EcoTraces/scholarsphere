import 'package:flutter/material.dart';

import '../../features/governance/domain/legal_compliance.dart';
import '../../features/governance/domain/legal_compliance_repository.dart';
import '../../features/governance/presentation/legal_policy_screen.dart';
import '../launch_link.dart';

/// Standard site footer shown on the public entry point (the sign-in /
/// registration screen): real contact details, real legal-policy links
/// (backed by [LegalComplianceRepository], not static placeholder text),
/// and a copyright line. Deliberately has no social-media icons or app
/// links - this project doesn't have real accounts to point them at, and
/// a row of dead icon buttons would be exactly the kind of fake polish
/// this app has otherwise been cleaned of.
class AppFooter extends StatelessWidget {
  const AppFooter({super.key, required this.legalRepository});

  final LegalComplianceRepository legalRepository;

  static const _supportEmail = 'ecotrace2026@gmail.com';
  static const _supportPhone = '+232395457';
  static const _borderColor = Color(0xFFE7EAF0);
  static const _headingColor = Color(0xFF14213D);
  static const _mutedColor = Color(0xFF667085);

  @override
  Widget build(BuildContext context) {
    final wide = MediaQuery.sizeOf(context).width >= 720;
    return Container(
      decoration: const BoxDecoration(
        color: Color(0xFFF9FAFB),
        border: Border(top: BorderSide(color: _borderColor)),
      ),
      padding: EdgeInsets.symmetric(
        horizontal: wide ? 56 : 24,
        vertical: wide ? 48 : 32,
      ),
      child: Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1120),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              wide
                  ? IntrinsicHeight(
                      child: Row(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Expanded(flex: 4, child: _buildBrandColumn()),
                          Expanded(child: _buildLegalColumn(context)),
                          Expanded(child: _buildContactColumn(context)),
                        ],
                      ),
                    )
                  : Column(
                      crossAxisAlignment: CrossAxisAlignment.start,
                      children: [
                        _buildBrandColumn(),
                        const SizedBox(height: 28),
                        _buildLegalColumn(context),
                        const SizedBox(height: 28),
                        _buildContactColumn(context),
                      ],
                    ),
              const SizedBox(height: 32),
              const Divider(color: _borderColor, height: 1),
              const SizedBox(height: 16),
              Wrap(
                alignment: WrapAlignment.spaceBetween,
                crossAxisAlignment: WrapCrossAlignment.center,
                runSpacing: 8,
                children: [
                  Text(
                    '© ${DateTime.now().year} ScholarSphere. All rights reserved.',
                    style: const TextStyle(fontSize: 12.5, color: _mutedColor),
                  ),
                  const Text(
                    'Verified opportunities. No fabricated data, ever.',
                    style: TextStyle(fontSize: 12.5, color: _mutedColor),
                  ),
                ],
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _buildBrandColumn() {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Row(
          children: [
            Icon(Icons.public, color: _headingColor),
            SizedBox(width: 8),
            Text(
              'ScholarSphere',
              style: TextStyle(fontWeight: FontWeight.w700, fontSize: 16),
            ),
          ],
        ),
        const SizedBox(height: 10),
        const SizedBox(
          width: 280,
          child: Text(
            'Helping students find and apply to verified scholarships, '
            'grants, fellowships, and internships worldwide.',
            style: TextStyle(fontSize: 13, color: _mutedColor, height: 1.5),
          ),
        ),
      ],
    );
  }

  Widget _buildLegalColumn(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Legal',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        ),
        const SizedBox(height: 12),
        _FooterLink(
          label: 'Terms & Conditions',
          onTap: () => _openPolicy(
            context,
            LegalPolicyType.termsAndConditions,
            'Terms & Conditions',
          ),
        ),
        _FooterLink(
          label: 'Privacy Policy',
          onTap: () => _openPolicy(
            context,
            LegalPolicyType.privacyPolicy,
            'Privacy Policy',
          ),
        ),
        _FooterLink(
          label: 'Cookie Policy',
          onTap: () => _openPolicy(
            context,
            LegalPolicyType.cookiePolicy,
            'Cookie Policy',
          ),
        ),
      ],
    );
  }

  Widget _buildContactColumn(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        const Text(
          'Contact',
          style: TextStyle(fontWeight: FontWeight.w700, fontSize: 13),
        ),
        const SizedBox(height: 12),
        _FooterContactRow(
          icon: Icons.email_outlined,
          label: _supportEmail,
          onTap: () => openEmail(context, _supportEmail),
        ),
        const SizedBox(height: 8),
        _FooterContactRow(
          icon: Icons.call_outlined,
          label: _supportPhone,
          onTap: () => openPhone(context, _supportPhone),
        ),
        const SizedBox(height: 8),
        _FooterContactRow(
          icon: Icons.chat_outlined,
          label: 'WhatsApp $_supportPhone',
          onTap: () => openExternalLink(
            context,
            'https://wa.me/${_supportPhone.replaceAll('+', '')}',
          ),
        ),
      ],
    );
  }

  void _openPolicy(BuildContext context, LegalPolicyType type, String title) {
    Navigator.of(context).push(
      MaterialPageRoute(
        builder: (context) => LegalPolicyScreen(
          repository: legalRepository,
          policyType: type,
          title: title,
        ),
      ),
    );
  }
}

class _FooterLink extends StatelessWidget {
  const _FooterLink({required this.label, required this.onTap});

  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.only(bottom: 10),
      child: InkWell(
        onTap: onTap,
        child: Text(
          label,
          style: const TextStyle(fontSize: 13.5, color: AppFooter._mutedColor),
        ),
      ),
    );
  }
}

class _FooterContactRow extends StatelessWidget {
  const _FooterContactRow({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return InkWell(
      onTap: onTap,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          Icon(icon, size: 16, color: AppFooter._mutedColor),
          const SizedBox(width: 8),
          Flexible(
            child: Text(
              label,
              style: const TextStyle(
                fontSize: 13.5,
                color: AppFooter._mutedColor,
              ),
            ),
          ),
        ],
      ),
    );
  }
}
