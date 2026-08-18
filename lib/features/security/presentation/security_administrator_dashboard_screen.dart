import 'package:flutter/material.dart';

import '../../audit/domain/audit_repository.dart';
import '../../audit/presentation/audit_log_screen.dart';
import '../../authentication/domain/user_account.dart';
import '../domain/security_models.dart';
import '../domain/security_repository.dart';

class SecurityAdministratorDashboardScreen extends StatefulWidget {
  const SecurityAdministratorDashboardScreen({
    super.key,
    required this.user,
    required this.securityRepository,
    required this.auditRepository,
    required this.onOpenSecurityCenter,
    required this.onSignOut,
  });
  final UserAccount user;
  final SecurityRepository securityRepository;
  final AuditRepository auditRepository;
  final VoidCallback onOpenSecurityCenter;
  final VoidCallback onSignOut;

  @override
  State<SecurityAdministratorDashboardScreen> createState() =>
      _SecurityAdministratorDashboardScreenState();
}

class _SecurityAdministratorDashboardScreenState
    extends State<SecurityAdministratorDashboardScreen> {
  late Future<_SecurityData> _data;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _data = _load();
  }

  Future<_SecurityData> _load() async => _SecurityData(
    history: await widget.securityRepository.getLoginHistory(widget.user.email),
    sessions: await widget.securityRepository.getSessions(widget.user.id),
    alerts: await widget.securityRepository.getAlerts(widget.user.id),
    auditIntegrity: await widget.auditRepository.verifyIntegrity(),
  );

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final desktop = constraints.maxWidth >= 1050;
      return Scaffold(
        drawer: desktop ? null : Drawer(child: _navigation()),
        body: Row(
          children: [
            if (desktop) SizedBox(width: 250, child: _navigation()),
            Expanded(
              child: Column(
                children: [
                  _SecurityHeader(
                    showMenu: !desktop,
                    user: widget.user,
                    onRefresh: () => setState(_reload),
                    onSignOut: widget.onSignOut,
                  ),
                  Expanded(
                    child: FutureBuilder<_SecurityData>(
                      future: _data,
                      builder: (context, snapshot) {
                        if (snapshot.hasError) {
                          return Center(
                            child: Padding(
                              padding: const EdgeInsets.all(24),
                              child: Column(
                                mainAxisSize: MainAxisSize.min,
                                children: [
                                  Icon(
                                    Icons.error_outline,
                                    size: 40,
                                    color: Theme.of(context).colorScheme.error,
                                  ),
                                  const SizedBox(height: 12),
                                  const Text(
                                    "We couldn't load the security dashboard.",
                                  ),
                                  const SizedBox(height: 16),
                                  FilledButton.icon(
                                    onPressed: () => setState(_reload),
                                    icon: const Icon(Icons.refresh),
                                    label: const Text('Retry'),
                                  ),
                                ],
                              ),
                            ),
                          );
                        }
                        if (!snapshot.hasData) {
                          return const Center(
                            child: CircularProgressIndicator(),
                          );
                        }
                        return _SecurityDashboard(data: snapshot.data!);
                      },
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      );
    },
  );

  Widget _navigation() => _SecurityNavigation(
    user: widget.user,
    onDashboard: () {},
    onSecurityCenter: widget.onOpenSecurityCenter,
    onAudit: () => Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => AuditLogScreen(
          user: widget.user,
          repository: widget.auditRepository,
        ),
      ),
    ),
  );
}

class _SecurityData {
  const _SecurityData({
    required this.history,
    required this.sessions,
    required this.alerts,
    required this.auditIntegrity,
  });
  final List<LoginHistoryEntry> history;
  final List<SecuritySession> sessions;
  final List<SecurityAlert> alerts;
  final bool auditIntegrity;

  int get failed =>
      history.where((entry) => entry.outcome != LoginOutcome.success).length;
  int get blocked => history
      .where(
        (entry) =>
            entry.outcome == LoginOutcome.blockedIp ||
            entry.outcome == LoginOutcome.locked,
      )
      .length;
  int get suspicious =>
      history.where((entry) => entry.suspicious).length +
      alerts
          .where((alert) => alert.type == SecurityAlertType.suspiciousLogin)
          .length;
  int get activeSessions =>
      sessions.where((session) => session.isActiveAt(DateTime.now())).length;
  int get securityScore {
    var score = auditIntegrity ? 75 : 45;
    if (suspicious == 0) score += 10;
    if (blocked == 0) score += 5;
    if (sessions.every((session) => session.strongAuthentication)) score += 10;
    return score.clamp(0, 100);
  }
}

class _SecurityHeader extends StatelessWidget {
  const _SecurityHeader({
    required this.showMenu,
    required this.user,
    required this.onRefresh,
    required this.onSignOut,
  });
  final bool showMenu;
  final UserAccount user;
  final VoidCallback onRefresh;
  final VoidCallback onSignOut;

  @override
  Widget build(BuildContext context) => Container(
    height: 84,
    padding: const EdgeInsets.symmetric(horizontal: 20),
    decoration: const BoxDecoration(
      color: Colors.white,
      border: Border(bottom: BorderSide(color: Color(0xFFE7EBF1))),
    ),
    child: Row(
      children: [
        if (showMenu)
          Builder(
            builder: (context) => IconButton(
              tooltip: 'Open navigation',
              onPressed: () => Scaffold.of(context).openDrawer(),
              icon: const Icon(Icons.menu),
            ),
          ),
        Expanded(
          child: Column(
            mainAxisAlignment: MainAxisAlignment.center,
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Text(
                'Security Dashboard',
                style: Theme.of(context).textTheme.headlineSmall,
              ),
              const Text('Monitor, detect, and respond to security events.'),
            ],
          ),
        ),
        if (MediaQuery.sizeOf(context).width >= 720)
          const SizedBox(
            width: 330,
            child: TextField(
              readOnly: true,
              decoration: InputDecoration(
                isDense: true,
                prefixIcon: Icon(Icons.search),
                hintText: 'Search users, IPs, events...',
              ),
            ),
          ),
        IconButton(
          tooltip: 'Refresh dashboard',
          onPressed: onRefresh,
          icon: const Icon(Icons.refresh),
        ),
        IconButton(
          tooltip: 'Security alerts',
          onPressed: () {},
          icon: const Icon(Icons.notifications_none),
        ),
        PopupMenuButton<String>(
          tooltip: 'Security administrator account',
          onSelected: (value) {
            if (value == 'sign-out') onSignOut();
          },
          itemBuilder: (_) => const [
            PopupMenuItem(value: 'sign-out', child: Text('Sign out')),
          ],
          child: Padding(
            padding: const EdgeInsets.only(left: 10),
            child: CircleAvatar(child: Text(user.fullName.substring(0, 1))),
          ),
        ),
      ],
    ),
  );
}

class _SecurityNavigation extends StatelessWidget {
  const _SecurityNavigation({
    required this.user,
    required this.onDashboard,
    required this.onSecurityCenter,
    required this.onAudit,
  });
  final UserAccount user;
  final VoidCallback onDashboard;
  final VoidCallback onSecurityCenter;
  final VoidCallback onAudit;

  @override
  Widget build(BuildContext context) => Material(
    color: const Color(0xFF14213D), // brand ink
    child: SafeArea(
      child: Column(
        children: [
          const Padding(
            padding: EdgeInsets.fromLTRB(20, 18, 14, 20),
            child: Row(
              children: [
                Icon(
                  Icons.shield_outlined,
                  color: Color(0xFFE09F3E), // brand amber
                  size: 36,
                ),
                SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        'ScholarSphere',
                        style: TextStyle(
                          color: Colors.white,
                          fontSize: 18,
                          fontWeight: FontWeight.w700,
                        ),
                      ),
                      Text(
                        'Secure. Trusted. Global Opportunities.',
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(color: Color(0xFFB8C7DC), fontSize: 9),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: ListView(
              padding: const EdgeInsets.symmetric(horizontal: 12),
              children: [
                _item(Icons.dashboard_outlined, 'Dashboard', onDashboard, true),
                _label('MONITOR'),
                _item(
                  Icons.security_outlined,
                  'Security Overview',
                  onSecurityCenter,
                ),
                _item(
                  Icons.radar_outlined,
                  'Real-time Monitoring',
                  onSecurityCenter,
                ),
                _item(
                  Icons.warning_amber_outlined,
                  'Threat Detection',
                  onSecurityCenter,
                ),
                _item(
                  Icons.health_and_safety_outlined,
                  'System Health',
                  onSecurityCenter,
                ),
                _label('ACCESS & IDENTITY'),
                _item(
                  Icons.person_search_outlined,
                  'User Activity',
                  onSecurityCenter,
                ),
                _item(Icons.login_outlined, 'Login Attempts', onSecurityCenter),
                _item(
                  Icons.admin_panel_settings_outlined,
                  'Roles & Permissions',
                  onSecurityCenter,
                ),
                _item(Icons.api_outlined, 'API Access', onSecurityCenter),
                _label('INCIDENT MANAGEMENT'),
                _item(
                  Icons.crisis_alert_outlined,
                  'Security Incidents',
                  onSecurityCenter,
                ),
                _item(
                  Icons.notifications_active_outlined,
                  'Alerts',
                  onSecurityCenter,
                ),
                _item(Icons.manage_search, 'Audit Logs', onAudit),
                _label('CONFIGURATION'),
                _item(
                  Icons.policy_outlined,
                  'Security Policies',
                  onSecurityCenter,
                ),
                _item(
                  Icons.block_outlined,
                  'IP Allowlist / Blocklist',
                  onSecurityCenter,
                ),
                _item(
                  Icons.phonelink_lock_outlined,
                  'MFA Settings',
                  onSecurityCenter,
                ),
                _item(
                  Icons.privacy_tip_outlined,
                  'Data Protection',
                  onSecurityCenter,
                ),
                _label('REPORTS'),
                _item(Icons.analytics_outlined, 'Security Reports', onAudit),
                _item(Icons.fact_check_outlined, 'Compliance', onAudit),
              ],
            ),
          ),
          Container(
            margin: const EdgeInsets.all(14),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              // Frosted panel on the ink sidebar, same technique as the
              // login screen's decorative side panel.
              color: Colors.white.withValues(alpha: 0.08),
              borderRadius: BorderRadius.circular(8),
            ),
            child: Row(
              children: [
                CircleAvatar(child: Text(user.fullName.substring(0, 1))),
                const SizedBox(width: 10),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(
                        user.fullName,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: const TextStyle(color: Colors.white),
                      ),
                      const Text(
                        'Security Administrator • Online',
                        style: TextStyle(
                          color: Color(0xFFB8C7DC),
                          fontSize: 10,
                        ),
                      ),
                    ],
                  ),
                ),
              ],
            ),
          ),
        ],
      ),
    ),
  );

  Widget _label(String value) => Padding(
    padding: const EdgeInsets.fromLTRB(12, 17, 12, 6),
    child: Text(
      value,
      style: const TextStyle(color: Color(0xFF8FA6C3), fontSize: 10),
    ),
  );

  Widget _item(
    IconData icon,
    String label,
    VoidCallback onTap, [
    bool selected = false,
  ]) => Padding(
    padding: const EdgeInsets.only(bottom: 2),
    child: ListTile(
      dense: true,
      selected: selected,
      selectedTileColor: const Color(0xFF007C72), // brand teal
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(7)),
      leading: Icon(icon, color: Colors.white, size: 19),
      title: Text(
        label,
        style: const TextStyle(color: Colors.white, fontSize: 13),
      ),
      onTap: onTap,
    ),
  );
}

class _SecurityDashboard extends StatelessWidget {
  const _SecurityDashboard({required this.data});
  final _SecurityData data;

  @override
  Widget build(BuildContext context) => ListView(
    padding: const EdgeInsets.all(20),
    children: [
      Center(
        child: ConstrainedBox(
          constraints: const BoxConstraints(maxWidth: 1300),
          child: Column(
            children: [
              _SecurityMetrics(data: data),
              const SizedBox(height: 16),
              LayoutBuilder(
                builder: (context, constraints) {
                  final width = constraints.maxWidth >= 840
                      ? (constraints.maxWidth - 16) / 2
                      : constraints.maxWidth;
                  return Wrap(
                    spacing: 16,
                    runSpacing: 16,
                    children: [
                      SizedBox(
                        width: width,
                        child: _LoginOverview(history: data.history),
                      ),
                      SizedBox(
                        width: width,
                        child: _ThreatOverview(data: data),
                      ),
                      SizedBox(
                        width: width,
                        child: _SecurityEvents(alerts: data.alerts),
                      ),
                      SizedBox(
                        width: width,
                        child: _LoginHistory(history: data.history),
                      ),
                    ],
                  );
                },
              ),
              const SizedBox(height: 16),
              LayoutBuilder(
                builder: (context, constraints) {
                  final width = constraints.maxWidth >= 760
                      ? (constraints.maxWidth - 32) / 3
                      : constraints.maxWidth;
                  return Wrap(
                    spacing: 16,
                    runSpacing: 16,
                    children: [
                      SizedBox(
                        width: width,
                        child: _MfaAdoption(sessions: data.sessions),
                      ),
                      SizedBox(
                        width: width,
                        child: _AuditHealth(valid: data.auditIntegrity),
                      ),
                      SizedBox(
                        width: width,
                        child: _AlertSummary(alerts: data.alerts),
                      ),
                    ],
                  );
                },
              ),
            ],
          ),
        ),
      ),
    ],
  );
}

class _SecurityMetrics extends StatelessWidget {
  const _SecurityMetrics({required this.data});
  final _SecurityData data;

  @override
  Widget build(BuildContext context) => LayoutBuilder(
    builder: (context, constraints) {
      final columns = constraints.maxWidth >= 1000
          ? 5
          : constraints.maxWidth >= 620
          ? 3
          : 2;
      final width = (constraints.maxWidth - (columns - 1) * 12) / columns;
      return Wrap(
        spacing: 12,
        runSpacing: 12,
        children: [
          _SecurityMetric(
            width: width,
            label: 'Login Attempts',
            value: data.history.length,
            icon: Icons.login,
            color: const Color(0xFF14213D), // brand ink (neutral count)
          ),
          _SecurityMetric(
            width: width,
            label: 'Failed Attempts',
            value: data.failed,
            icon: Icons.person_off_outlined,
            color: const Color(0xFFE09F3E), // brand amber (attention)
          ),
          _SecurityMetric(
            width: width,
            label: 'Blocked Attempts',
            value: data.blocked,
            icon: Icons.gpp_bad_outlined,
            color: const Color(0xFFE83B55), // danger, matches the rest of file
          ),
          _SecurityMetric(
            width: width,
            label: 'Active Threats',
            value: data.suspicious,
            icon: Icons.warning_amber,
            color: const Color(0xFFE83B55),
          ),
          _SecurityMetric(
            width: width,
            label: 'Security Score',
            value: data.securityScore,
            suffix: '/100',
            icon: Icons.shield_outlined,
            color: const Color(0xFF007C72), // brand teal (positive gauge)
          ),
        ],
      );
    },
  );
}

class _SecurityMetric extends StatelessWidget {
  const _SecurityMetric({
    required this.width,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.suffix = '',
  });
  final double width;
  final String label;
  final int value;
  final IconData icon;
  final Color color;
  final String suffix;

  @override
  Widget build(BuildContext context) => SizedBox(
    width: width,
    height: 132,
    child: Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Row(
          children: [
            CircleAvatar(
              backgroundColor: color.withValues(alpha: 0.12),
              child: Icon(icon, color: color),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                mainAxisAlignment: MainAxisAlignment.center,
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(label, maxLines: 2, overflow: TextOverflow.ellipsis),
                  Text(
                    '$value$suffix',
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    ),
  );
}

class _LoginOverview extends StatelessWidget {
  const _LoginOverview({required this.history});
  final List<LoginHistoryEntry> history;

  @override
  Widget build(BuildContext context) => _SecurityPanel(
    title: 'Login Attempts Overview',
    child: SizedBox(
      height: 180,
      child: history.isEmpty
          ? const Center(child: Text('No login activity recorded.'))
          : Row(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: history.take(12).map((entry) {
                final success = entry.outcome == LoginOutcome.success;
                return Expanded(
                  child: Padding(
                    padding: const EdgeInsets.symmetric(horizontal: 3),
                    child: Container(
                      height: success ? 120 : 65,
                      color: success
                          ? const Color(0xFF007C72)
                          : const Color(0xFFE83B55),
                    ),
                  ),
                );
              }).toList(),
            ),
    ),
  );
}

class _ThreatOverview extends StatelessWidget {
  const _ThreatOverview({required this.data});
  final _SecurityData data;

  @override
  Widget build(BuildContext context) => _SecurityPanel(
    title: 'Top Threats by Type',
    child: Column(
      children: [
        _row('Failed credentials', data.failed),
        _row('Blocked access', data.blocked),
        _row('Suspicious login', data.suspicious),
        _row('Session alerts', data.alerts.length),
      ],
    ),
  );
}

class _SecurityEvents extends StatelessWidget {
  const _SecurityEvents({required this.alerts});
  final List<SecurityAlert> alerts;

  @override
  Widget build(BuildContext context) => _SecurityPanel(
    title: 'Real-time Security Events',
    child: alerts.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Text('No active security alerts.'),
          )
        : Column(
            children: alerts
                .take(6)
                .map(
                  (alert) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: const CircleAvatar(
                      backgroundColor: Color(0xFFFFE8EC),
                      child: Icon(
                        Icons.warning_amber,
                        color: Color(0xFFE83B55),
                      ),
                    ),
                    title: Text(alert.message),
                    subtitle: Text(alert.type.name),
                  ),
                )
                .toList(),
          ),
  );
}

class _LoginHistory extends StatelessWidget {
  const _LoginHistory({required this.history});
  final List<LoginHistoryEntry> history;

  @override
  Widget build(BuildContext context) => _SecurityPanel(
    title: 'Recent Security Incidents',
    child: history.isEmpty
        ? const Padding(
            padding: EdgeInsets.symmetric(vertical: 24),
            child: Text('No recent incidents.'),
          )
        : Column(
            children: history
                .take(6)
                .map(
                  (entry) => ListTile(
                    contentPadding: EdgeInsets.zero,
                    leading: Icon(
                      entry.outcome == LoginOutcome.success
                          ? Icons.check_circle_outline
                          : Icons.error_outline,
                      color: entry.outcome == LoginOutcome.success
                          ? const Color(0xFF007C72)
                          : const Color(0xFFE83B55),
                    ),
                    title: Text(entry.outcome.name),
                    subtitle: Text(
                      '${entry.device.ipAddress} • ${entry.device.browser}',
                    ),
                    trailing: Text(_time(entry.occurredAt)),
                  ),
                )
                .toList(),
          ),
  );
}

class _MfaAdoption extends StatelessWidget {
  const _MfaAdoption({required this.sessions});
  final List<SecuritySession> sessions;

  @override
  Widget build(BuildContext context) {
    final strong = sessions
        .where((session) => session.strongAuthentication)
        .length;
    final ratio = sessions.isEmpty ? 1.0 : strong / sessions.length;
    return _SecurityPanel(
      title: 'MFA Adoption',
      child: Center(
        child: SizedBox(
          width: 120,
          height: 120,
          child: Stack(
            alignment: Alignment.center,
            children: [
              CircularProgressIndicator(
                value: ratio,
                strokeWidth: 13,
                backgroundColor: const Color(0xFFE7EBF1),
                color: const Color(0xFF007C72),
              ),
              Text(
                '${(ratio * 100).round()}%\nEnabled',
                textAlign: TextAlign.center,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class _AuditHealth extends StatelessWidget {
  const _AuditHealth({required this.valid});
  final bool valid;

  @override
  Widget build(BuildContext context) => _SecurityPanel(
    title: 'System Health',
    child: Column(
      children: [
        _health('Audit integrity', valid),
        _health('Authentication service', true),
        _health('Session controls', true),
        _health('Rate limiting', true),
      ],
    ),
  );
}

class _AlertSummary extends StatelessWidget {
  const _AlertSummary({required this.alerts});
  final List<SecurityAlert> alerts;

  @override
  Widget build(BuildContext context) => _SecurityPanel(
    title: 'Security Alerts Summary',
    child: Column(
      children: [
        _row(
          'Unacknowledged',
          alerts.where((item) => item.acknowledgedAt == null).length,
        ),
        _row(
          'Suspicious logins',
          alerts
              .where((item) => item.type == SecurityAlertType.suspiciousLogin)
              .length,
        ),
        _row(
          'Account locks',
          alerts
              .where((item) => item.type == SecurityAlertType.accountLocked)
              .length,
        ),
        _row(
          'Session events',
          alerts
              .where((item) => item.type == SecurityAlertType.sessionRevoked)
              .length,
        ),
      ],
    ),
  );
}

class _SecurityPanel extends StatelessWidget {
  const _SecurityPanel({required this.title, required this.child});
  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) => Card(
    child: Padding(
      padding: const EdgeInsets.all(16),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          // No "View all" action: no caller has a real destination for it,
          // and a button that looks tappable but does nothing is worse than
          // no button at all.
          Text(title, style: Theme.of(context).textTheme.titleLarge),
          const SizedBox(height: 10),
          child,
        ],
      ),
    ),
  );
}

Widget _row(String label, int value) => Padding(
  padding: const EdgeInsets.symmetric(vertical: 8),
  child: Row(
    children: [
      Expanded(child: Text(label)),
      Text('$value'),
    ],
  ),
);

Widget _health(String label, bool healthy) => ListTile(
  dense: true,
  contentPadding: EdgeInsets.zero,
  leading: Icon(
    healthy ? Icons.check_circle_outline : Icons.error_outline,
    color: healthy ? const Color(0xFF007C72) : const Color(0xFFE83B55),
  ),
  title: Text(label),
  trailing: Text(healthy ? 'Healthy' : 'Attention'),
);

String _time(DateTime value) =>
    '${value.hour.toString().padLeft(2, '0')}:'
    '${value.minute.toString().padLeft(2, '0')}';
