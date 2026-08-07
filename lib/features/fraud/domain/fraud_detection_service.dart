import '../../opportunities/domain/opportunity.dart';
import 'fraud_assessment.dart';

class FraudDetectionService {
  FraudDetectionService({
    DateTime Function()? clock,
    Map<String, String>? officialInstitutionDomains,
  }) : _clock = clock ?? DateTime.now,
       _officialInstitutionDomains =
           officialInstitutionDomains ?? _defaultOfficialDomains;

  final DateTime Function() _clock;
  final Map<String, String> _officialInstitutionDomains;

  static const Map<String, String> _defaultOfficialDomains = {
    'harvard university': 'harvard.edu',
    'university of oxford': 'ox.ac.uk',
    'university of cambridge': 'cam.ac.uk',
    'unicef': 'unicef.org',
    'united nations': 'un.org',
  };

  FraudAssessment assess(
    Opportunity opportunity, {
    Iterable<Opportunity> knownOpportunities = const [],
  }) {
    final signals = <FraudSignal>[
      ..._contentSignals(opportunity),
      ..._linkSignals(opportunity),
      ..._recordSignals(opportunity),
      ..._impersonationSignals(opportunity),
      ..._duplicateSignals(opportunity, knownOpportunities),
    ];
    final score = signals
        .fold<int>(0, (sum, signal) => sum + _weight(signal.severity))
        .clamp(0, 100)
        .toInt();
    final level = switch (score) {
      >= 70 => OverallRiskLevel.critical,
      >= 40 => OverallRiskLevel.high,
      >= 15 => OverallRiskLevel.moderate,
      _ => OverallRiskLevel.low,
    };
    return FraudAssessment(
      opportunityId: opportunity.id,
      assessedAt: _clock(),
      score: score,
      level: level,
      signals: signals,
    );
  }

  List<FraudSignal> _contentSignals(Opportunity opportunity) {
    final content = [
      opportunity.summary,
      opportunity.contactInformation,
      ...opportunity.benefits,
      ...opportunity.eligibilityRequirements,
      ...opportunity.applicationProcedure,
    ].join(' ').toLowerCase();
    final signals = <FraudSignal>[];
    if (_containsAny(content, const [
      'personal account',
      'personal bank account',
      'mobile money number',
      'western union',
      'moneygram',
      'send payment directly',
    ])) {
      signals.add(
        _signal(
          FraudSignalType.personalAccountPayment,
          RiskSeverity.high,
          'The instructions may request payment through a personal channel.',
          'Confirm all fees and payment accounts directly with the official '
              'institution.',
        ),
      );
    }
    if (_containsAny(content, const [
      'guaranteed selection',
      'guaranteed admission',
      '100% acceptance',
      'guaranteed scholarship',
      'you will be selected',
    ])) {
      signals.add(
        _signal(
          FraudSignalType.guaranteedSelection,
          RiskSeverity.high,
          'The wording appears to promise selection or acceptance.',
          'Legitimate competitive programs generally do not guarantee '
              'selection.',
        ),
      );
    }
    if (_containsAny(content, const [
      'send your password',
      'provide your password',
      'banking password',
      'online banking credentials',
      'card pin',
      'security code',
    ])) {
      signals.add(
        _signal(
          FraudSignalType.credentialRequest,
          RiskSeverity.critical,
          'The instructions may request passwords or banking credentials.',
          'Do not provide passwords, PINs, or banking login details.',
        ),
      );
    }
    if (_containsAny(content, const [
      'unlimited stipend',
      'instant cash award',
      'guaranteed visa',
      'no review required',
      'everyone receives funding',
    ])) {
      signals.add(
        _signal(
          FraudSignalType.unrealisticBenefits,
          RiskSeverity.medium,
          'Some advertised benefits appear unusually broad or unconditional.',
          'Compare every benefit with the official sponsor publication.',
        ),
      );
    }
    return signals;
  }

  List<FraudSignal> _linkSignals(Opportunity opportunity) {
    final source = Uri.tryParse(opportunity.officialSourceUrl);
    final application = Uri.tryParse(opportunity.applicationUrl);
    final signals = <FraudSignal>[];
    final hosts = [
      source?.host,
      application?.host,
    ].whereType<String>().where((host) => host.isNotEmpty).toList();
    if (hosts.length < 2 ||
        source?.scheme != 'https' ||
        application?.scheme != 'https') {
      signals.add(
        _signal(
          FraudSignalType.unofficialDomain,
          RiskSeverity.medium,
          'One or more official links cannot be securely validated.',
          'Confirm the HTTPS source and application links from the '
              'institution website.',
        ),
      );
    } else if (hosts.any(_isUnofficialHost) ||
        _baseDomain(hosts[0]) != _baseDomain(hosts[1])) {
      signals.add(
        _signal(
          FraudSignalType.unofficialDomain,
          RiskSeverity.medium,
          'The application link uses a different domain from the stated '
              'official source.',
          'Different domains can be legitimate, but the institution should '
              'link to the application domain directly.',
        ),
      );
    }
    if (hosts.any(_isShortener)) {
      signals.add(
        _signal(
          FraudSignalType.shortenedLink,
          RiskSeverity.high,
          'A shortened link hides the final destination.',
          'Open applications only from a link published on the official '
              'institution or sponsor website.',
        ),
      );
    }
    return signals;
  }

  List<FraudSignal> _recordSignals(Opportunity opportunity) {
    final signals = <FraudSignal>[];
    if (opportunity.applicationOpenDate.isAfter(opportunity.deadline)) {
      signals.add(
        _signal(
          FraudSignalType.inconsistentDeadline,
          RiskSeverity.high,
          'The application opening date is after the stated deadline.',
          'Verify both dates against the official program page.',
        ),
      );
    }
    final provider = opportunity.provider.trim().toLowerCase();
    final institution = opportunity.hostInstitution.trim().toLowerCase();
    if (provider.isEmpty ||
        institution.isEmpty ||
        provider.contains('unconfirmed') ||
        institution.contains('unconfirmed') ||
        provider == 'unknown' ||
        institution == 'unknown') {
      signals.add(
        _signal(
          FraudSignalType.missingSponsor,
          RiskSeverity.high,
          'The sponsor or host institution is not clearly identified.',
          'Require an identifiable legal institution and authoritative source.',
        ),
      );
    }
    return signals;
  }

  List<FraudSignal> _impersonationSignals(Opportunity opportunity) {
    final identity = [
      opportunity.title,
      opportunity.provider,
      opportunity.hostInstitution,
    ].join(' ').toLowerCase();
    final hosts = [
      Uri.tryParse(opportunity.officialSourceUrl)?.host ?? '',
      Uri.tryParse(opportunity.applicationUrl)?.host ?? '',
    ];
    for (final entry in _officialInstitutionDomains.entries) {
      if (identity.contains(entry.key) &&
          !hosts.any((host) => _hostMatches(host, entry.value))) {
        return [
          _signal(
            FraudSignalType.institutionImpersonation,
            RiskSeverity.critical,
            'The listing names ${_titleCase(entry.key)}, but its links do not '
                'use the expected official domain.',
            'Locate the opportunity independently from ${entry.value}.',
          ),
        ];
      }
    }
    return const [];
  }

  List<FraudSignal> _duplicateSignals(
    Opportunity opportunity,
    Iterable<Opportunity> known,
  ) {
    final normalizedTitle = _normalize(opportunity.title);
    for (final other in known) {
      if (other.id == opportunity.id) continue;
      final sameIdentity =
          _normalize(other.title) == normalizedTitle &&
          _normalize(other.provider) == _normalize(opportunity.provider);
      if (sameIdentity &&
          _baseDomain(Uri.tryParse(other.applicationUrl)?.host ?? '') !=
              _baseDomain(
                Uri.tryParse(opportunity.applicationUrl)?.host ?? '',
              )) {
        return [
          _signal(
            FraudSignalType.alteredLinkDuplicate,
            RiskSeverity.high,
            'A similar listing exists with a different application domain.',
            'Compare both records with the official sponsor source and retain '
                'only the authoritative link.',
          ),
        ];
      }
    }
    return const [];
  }

  FraudSignal _signal(
    FraudSignalType type,
    RiskSeverity severity,
    String userMessage,
    String reviewGuidance,
  ) => FraudSignal(
    type: type,
    severity: severity,
    userMessage: userMessage,
    reviewGuidance: reviewGuidance,
  );

  bool _containsAny(String content, List<String> values) =>
      values.any(content.contains);

  bool _isShortener(String host) => const {
    'bit.ly',
    'tinyurl.com',
    't.co',
    'goo.gl',
    'ow.ly',
    'shorturl.at',
    'cutt.ly',
  }.contains(host.toLowerCase());

  bool _isUnofficialHost(String host) => const {
    'gmail.com',
    'yahoo.com',
    'outlook.com',
    'hotmail.com',
    'forms.gle',
    'docs.google.com',
  }.contains(host.toLowerCase());

  String _baseDomain(String host) {
    final parts = host
        .toLowerCase()
        .split('.')
        .where((part) => part.isNotEmpty);
    final list = parts.toList();
    if (list.length <= 2) return list.join('.');
    final suffix = list.sublist(list.length - 2).join('.');
    if (const {'ac.uk', 'co.uk', 'org.uk'}.contains(suffix) &&
        list.length >= 3) {
      return list.sublist(list.length - 3).join('.');
    }
    return suffix;
  }

  bool _hostMatches(String host, String officialDomain) =>
      host == officialDomain || host.endsWith('.$officialDomain');

  String _normalize(String value) =>
      value.toLowerCase().replaceAll(RegExp(r'[^a-z0-9]+'), ' ').trim();

  String _titleCase(String value) => value
      .split(' ')
      .map((part) => '${part[0].toUpperCase()}${part.substring(1)}')
      .join(' ');

  int _weight(RiskSeverity severity) => switch (severity) {
    RiskSeverity.low => 5,
    RiskSeverity.medium => 15,
    RiskSeverity.high => 30,
    RiskSeverity.critical => 50,
  };
}
