import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart' as firebase;
import 'package:flutter/foundation.dart' show kReleaseMode;
import 'package:http/http.dart' as http;

import '../../opportunities/data/api_opportunity_repository.dart'
    show LiveBackendException;
import '../../security/domain/security_backend_contracts.dart';
import '../domain/support_models.dart';
import '../domain/support_repository.dart';

/// Reads and writes real support ticketing/knowledge-base data from the
/// ScholarSphere Python backend (scholarsphere_backend/).
///
/// This is the live replacement for [DemoSupportRepository]. Whether a
/// message is from an agent is always derived server-side from the
/// caller's verified role, never from the client-supplied [isAgent]
/// parameter on [addMessage] - this repository still accepts it for
/// interface compatibility but the backend ignores it.
class ApiSupportRepository implements SupportRepository {
  ApiSupportRepository({
    String? baseUrl,
    http.Client? client,
    firebase.FirebaseAuth? auth,
  }) : baseUrl = baseUrl ?? _defaultBaseUrl,
       _client = client ?? http.Client(),
       _authOverride = auth {
    if (kReleaseMode) {
      TransportSecurityPolicy.requireHttps(Uri.parse(this.baseUrl));
    }
  }

  static const _defaultBaseUrl = String.fromEnvironment(
    'SCHOLARSPHERE_API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );

  final String baseUrl;
  final http.Client _client;
  final firebase.FirebaseAuth? _authOverride;

  firebase.FirebaseAuth get _auth =>
      _authOverride ?? firebase.FirebaseAuth.instance;

  @override
  Future<SupportTicket> submitTicket({
    required String requesterId,
    required String subject,
    required SupportTicketCategory category,
    required SupportTicketPriority priority,
    required String message,
    List<SupportAttachment> attachments = const [],
  }) async {
    try {
      final body = await _post('/support/tickets', {
        'subject': subject,
        'category': _categoryToWire(category),
        'priority': _priorityToWire(priority),
        'message': message,
        'attachments': attachments.map(_attachmentToWire).toList(),
      });
      return _toTicket(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 422) {
        throw const SupportFailure('A subject and message are required.');
      }
      rethrow;
    }
  }

  @override
  Future<List<SupportTicket>> getForUser(String userId) async {
    final body = await _get('/support/tickets/mine');
    return (body as List<dynamic>)
        .map((item) => _toTicket(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<List<SupportTicket>> getAgentQueue() async {
    final body = await _get('/support/tickets/queue');
    return (body as List<dynamic>)
        .map((item) => _toTicket(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<SupportTicket?> getById(String ticketId) async {
    try {
      final body = await _get('/support/tickets/$ticketId');
      return _toTicket(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) return null;
      rethrow;
    }
  }

  @override
  Future<SupportTicket> assign(String ticketId, String agentId) async {
    final body = await _post('/support/tickets/$ticketId/assign', const {});
    return _toTicket(body as Map<String, dynamic>);
  }

  @override
  Future<SupportTicket> addMessage({
    required String ticketId,
    required String senderId,
    required String message,
    required bool isAgent,
    List<SupportAttachment> attachments = const [],
  }) async {
    try {
      final body = await _post('/support/tickets/$ticketId/messages', {
        'message': message,
        'attachments': attachments.map(_attachmentToWire).toList(),
      });
      return _toTicket(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 404) {
        throw const SupportFailure('Support ticket not found.');
      }
      if (error.statusCode == 409) {
        throw const SupportFailure('Closed tickets must be reopened first.');
      }
      rethrow;
    }
  }

  @override
  Future<SupportTicket> addInternalNote(
    String ticketId,
    String agentId,
    String note,
  ) async {
    final body = await _post('/support/tickets/$ticketId/notes', {
      'note': note,
    });
    return _toTicket(body as Map<String, dynamic>);
  }

  @override
  Future<SupportTicket> updateStatus(
    String ticketId,
    String actorId,
    SupportTicketStatus status, {
    String notes = '',
  }) async {
    try {
      final body = await _post('/support/tickets/$ticketId/status', {
        'status': _statusToWire(status),
        'notes': notes,
      });
      return _toTicket(body as Map<String, dynamic>);
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const SupportFailure(
          'Only resolved or closed tickets can reopen.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<SupportTicket> escalate(
    String ticketId,
    String actorId,
    String reason,
  ) async {
    final body = await _post('/support/tickets/$ticketId/escalate', {
      'reason': reason,
    });
    return _toTicket(body as Map<String, dynamic>);
  }

  @override
  Future<List<KnowledgeArticle>> searchKnowledge(
    String query, {
    SupportTicketCategory? category,
  }) async {
    final params = <String, String>{'query': query};
    if (category != null) params['category'] = _categoryToWire(category);
    final body = await _get('/support/knowledge', params);
    return (body as List<dynamic>)
        .map((item) => _toArticle(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> saveArticle(KnowledgeArticle article) async {
    await _put('/support/knowledge/${article.id}', {
      'title': article.title,
      'summary': article.summary,
      'content': article.content,
      'type': _contentTypeToWire(article.type),
      'category': _categoryToWire(article.category),
      'language_code': article.languageCode,
      'published': article.published,
      'keywords': article.keywords,
    });
  }

  @override
  Future<List<SupportResponseTemplate>> templates(
    SupportTicketCategory category,
  ) async {
    final body = await _get('/support/templates', {
      'category': _categoryToWire(category),
    });
    return (body as List<dynamic>)
        .map((item) => _toTemplate(item as Map<String, dynamic>))
        .toList();
  }

  @override
  Future<void> saveTemplate(SupportResponseTemplate template) async {
    await _put('/support/templates/${template.id}', {
      'name': template.name,
      'category': _categoryToWire(template.category),
      'subject': template.subject,
      'body': template.body,
    });
  }

  @override
  Future<void> submitSurvey(SatisfactionSurvey survey) async {
    try {
      await _post('/support/tickets/${survey.ticketId}/survey', {
        'rating': survey.rating,
        'comment': survey.comment,
      });
    } on LiveBackendException catch (error) {
      if (error.statusCode == 409) {
        throw const SupportFailure(
          'Surveys are available to the requester after resolution.',
        );
      }
      rethrow;
    }
  }

  @override
  Future<SupportPerformanceReport> performanceReport() async {
    final body =
        await _get('/support/performance-report') as Map<String, dynamic>;
    final byCategory = <SupportTicketCategory, int>{};
    (body['by_category'] as Map<String, dynamic>).forEach((key, value) {
      byCategory[_categoryFromWire(key)] = value as int;
    });
    return SupportPerformanceReport(
      totalTickets: body['total_tickets'] as int,
      openTickets: body['open_tickets'] as int,
      slaBreaches: body['sla_breaches'] as int,
      averageFirstResponseMinutes:
          (body['average_first_response_minutes'] as num).toDouble(),
      averageResolutionMinutes: (body['average_resolution_minutes'] as num)
          .toDouble(),
      satisfactionScore: (body['satisfaction_score'] as num).toDouble(),
      byCategory: byCategory,
    );
  }

  Map<String, dynamic> _attachmentToWire(SupportAttachment attachment) => {
    'id': attachment.id,
    'name': attachment.name,
    'storage_location': attachment.storageLocation,
    'content_type': attachment.contentType,
    'size_bytes': attachment.sizeBytes,
  };

  SupportAttachment _attachmentFromWire(Map<String, dynamic> json) =>
      SupportAttachment(
        id: json['id'] as String,
        name: json['name'] as String,
        storageLocation: json['storage_location'] as String,
        contentType: json['content_type'] as String,
        sizeBytes: json['size_bytes'] as int,
      );

  SupportTicket _toTicket(Map<String, dynamic> json) => SupportTicket(
    id: json['id'] as String,
    requesterId: json['requester_id'] as String,
    subject: json['subject'] as String,
    category: _categoryFromWire(json['category'] as String),
    priority: _priorityFromWire(json['priority'] as String),
    status: _statusFromWire(json['status'] as String),
    messages: (json['messages'] as List<dynamic>)
        .map((item) => _toMessage(item as Map<String, dynamic>))
        .toList(),
    internalNotes: (json['internal_notes'] as List<dynamic>)
        .map((item) => _toNote(item as Map<String, dynamic>))
        .toList(),
    history: (json['history'] as List<dynamic>)
        .map((item) => _toEvent(item as Map<String, dynamic>))
        .toList(),
    createdAt: DateTime.parse(json['created_at'] as String),
    updatedAt: DateTime.parse(json['updated_at'] as String),
    firstResponseDueAt: DateTime.parse(json['first_response_due_at'] as String),
    resolutionDueAt: DateTime.parse(json['resolution_due_at'] as String),
    assignedAgentId: json['assigned_agent_id'] as String?,
    escalationReason: json['escalation_reason'] as String?,
    resolvedAt: _dateTime(json['resolved_at']),
    closedAt: _dateTime(json['closed_at']),
  );

  SupportMessage _toMessage(Map<String, dynamic> json) => SupportMessage(
    id: json['id'] as String,
    senderId: json['sender_id'] as String,
    message: json['message'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
    attachments: (json['attachments'] as List<dynamic>)
        .map((item) => _attachmentFromWire(item as Map<String, dynamic>))
        .toList(),
    isAgent: json['is_agent'] as bool,
  );

  InternalSupportNote _toNote(Map<String, dynamic> json) => InternalSupportNote(
    id: json['id'] as String,
    agentId: json['agent_id'] as String,
    note: json['note'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
  );

  SupportTicketEvent _toEvent(Map<String, dynamic> json) => SupportTicketEvent(
    status: _statusFromWire(json['status'] as String),
    actorId: json['actor_id'] as String,
    createdAt: DateTime.parse(json['created_at'] as String),
    notes: json['notes'] as String,
  );

  KnowledgeArticle _toArticle(Map<String, dynamic> json) => KnowledgeArticle(
    id: json['id'] as String,
    title: json['title'] as String,
    summary: json['summary'] as String,
    content: json['content'] as String,
    type: _contentTypeFromWire(json['type'] as String),
    category: _categoryFromWire(json['category'] as String),
    languageCode: json['language_code'] as String,
    published: json['published'] as bool,
    updatedAt: DateTime.parse(json['updated_at'] as String),
    keywords: (json['keywords'] as List<dynamic>).cast<String>(),
  );

  SupportResponseTemplate _toTemplate(Map<String, dynamic> json) =>
      SupportResponseTemplate(
        id: json['id'] as String,
        name: json['name'] as String,
        category: _categoryFromWire(json['category'] as String),
        subject: json['subject'] as String,
        body: json['body'] as String,
      );

  static DateTime? _dateTime(dynamic value) =>
      value == null ? null : DateTime.tryParse(value as String);

  // Keep these four maps in sync with app/schemas/support.py's wire maps.
  static String _categoryToWire(SupportTicketCategory category) =>
      switch (category) {
        SupportTicketCategory.accountAccess => 'accountAccess',
        SupportTicketCategory.profileProblem => 'profileProblem',
        SupportTicketCategory.opportunityInformation =>
          'opportunityInformation',
        SupportTicketCategory.eligibilityResult => 'eligibilityResult',
        SupportTicketCategory.applicationTracking => 'applicationTracking',
        SupportTicketCategory.documentUpload => 'documentUpload',
        SupportTicketCategory.notificationProblem => 'notificationProblem',
        SupportTicketCategory.providerVerification => 'providerVerification',
        SupportTicketCategory.fraudReport => 'fraudReport',
        SupportTicketCategory.privacyRequest => 'privacyRequest',
        SupportTicketCategory.technicalIssue => 'technicalIssue',
        SupportTicketCategory.billingIssue => 'billingIssue',
        SupportTicketCategory.generalInquiry => 'generalInquiry',
      };

  static SupportTicketCategory _categoryFromWire(
    String value,
  ) => switch (value) {
    'accountAccess' => SupportTicketCategory.accountAccess,
    'profileProblem' => SupportTicketCategory.profileProblem,
    'opportunityInformation' => SupportTicketCategory.opportunityInformation,
    'eligibilityResult' => SupportTicketCategory.eligibilityResult,
    'applicationTracking' => SupportTicketCategory.applicationTracking,
    'documentUpload' => SupportTicketCategory.documentUpload,
    'notificationProblem' => SupportTicketCategory.notificationProblem,
    'providerVerification' => SupportTicketCategory.providerVerification,
    'fraudReport' => SupportTicketCategory.fraudReport,
    'privacyRequest' => SupportTicketCategory.privacyRequest,
    'technicalIssue' => SupportTicketCategory.technicalIssue,
    'billingIssue' => SupportTicketCategory.billingIssue,
    'generalInquiry' => SupportTicketCategory.generalInquiry,
    _ => throw LiveBackendException('Unknown support ticket category: $value'),
  };

  static String _priorityToWire(SupportTicketPriority priority) =>
      switch (priority) {
        SupportTicketPriority.low => 'low',
        SupportTicketPriority.normal => 'normal',
        SupportTicketPriority.high => 'high',
        SupportTicketPriority.urgent => 'urgent',
      };

  static SupportTicketPriority _priorityFromWire(String value) =>
      switch (value) {
        'low' => SupportTicketPriority.low,
        'normal' => SupportTicketPriority.normal,
        'high' => SupportTicketPriority.high,
        'urgent' => SupportTicketPriority.urgent,
        _ => throw LiveBackendException(
          'Unknown support ticket priority: $value',
        ),
      };

  static String _statusToWire(SupportTicketStatus status) => switch (status) {
    SupportTicketStatus.open => 'open',
    SupportTicketStatus.assigned => 'assigned',
    SupportTicketStatus.inProgress => 'inProgress',
    SupportTicketStatus.waitingForUser => 'waitingForUser',
    SupportTicketStatus.escalated => 'escalated',
    SupportTicketStatus.resolved => 'resolved',
    SupportTicketStatus.closed => 'closed',
    SupportTicketStatus.reopened => 'reopened',
  };

  static SupportTicketStatus _statusFromWire(String value) => switch (value) {
    'open' => SupportTicketStatus.open,
    'assigned' => SupportTicketStatus.assigned,
    'inProgress' => SupportTicketStatus.inProgress,
    'waitingForUser' => SupportTicketStatus.waitingForUser,
    'escalated' => SupportTicketStatus.escalated,
    'resolved' => SupportTicketStatus.resolved,
    'closed' => SupportTicketStatus.closed,
    'reopened' => SupportTicketStatus.reopened,
    _ => throw LiveBackendException('Unknown support ticket status: $value'),
  };

  static String _contentTypeToWire(KnowledgeContentType type) => switch (type) {
    KnowledgeContentType.frequentlyAskedQuestion => 'frequentlyAskedQuestion',
    KnowledgeContentType.article => 'article',
    KnowledgeContentType.tutorial => 'tutorial',
    KnowledgeContentType.applicationHelp => 'applicationHelp',
  };

  static KnowledgeContentType _contentTypeFromWire(
    String value,
  ) => switch (value) {
    'frequentlyAskedQuestion' => KnowledgeContentType.frequentlyAskedQuestion,
    'article' => KnowledgeContentType.article,
    'tutorial' => KnowledgeContentType.tutorial,
    'applicationHelp' => KnowledgeContentType.applicationHelp,
    _ => throw LiveBackendException('Unknown knowledge content type: $value'),
  };

  Future<dynamic> _get(
    String path, [
    Map<String, String> query = const {},
  ]) async {
    final headers = await _headers();
    final uri = Uri.parse(
      '$baseUrl$path',
    ).replace(queryParameters: query.isEmpty ? null : query);
    return _handle(() => _client.get(uri, headers: headers));
  }

  Future<dynamic> _post(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.post(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _put(String path, Map<String, dynamic> body) async {
    final headers = await _headers();
    final uri = Uri.parse('$baseUrl$path');
    return _handle(
      () => _client.put(uri, headers: headers, body: jsonEncode(body)),
    );
  }

  Future<dynamic> _handle(Future<http.Response> Function() request) async {
    late final http.Response response;
    try {
      response = await request();
    } on Exception catch (error) {
      throw LiveBackendException(
        'Could not reach the ScholarSphere backend: $error',
      );
    }
    if (response.statusCode == 401) {
      throw const LiveBackendException(
        'Sign-in expired. Sign in again.',
        statusCode: 401,
      );
    }
    if (response.statusCode >= 400) {
      throw LiveBackendException(
        'The ScholarSphere backend returned an error.',
        statusCode: response.statusCode,
      );
    }
    if (response.body.isEmpty) return null;
    return jsonDecode(response.body);
  }

  Future<Map<String, String>> _headers() async {
    final user = _auth.currentUser;
    if (user == null) {
      throw const LiveBackendException('Sign in first.', statusCode: 401);
    }
    final token = await user.getIdToken();
    return {
      'Authorization': 'Bearer $token',
      'Accept': 'application/json',
      'Content-Type': 'application/json',
    };
  }

  void dispose() => _client.close();
}
