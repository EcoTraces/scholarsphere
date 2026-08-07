import 'package:flutter/material.dart';

import '../domain/support_models.dart';
import '../domain/support_repository.dart';

class HelpCentreScreen extends StatefulWidget {
  const HelpCentreScreen({
    super.key,
    required this.userId,
    required this.repository,
  });
  final String userId;
  final SupportRepository repository;

  @override
  State<HelpCentreScreen> createState() => _HelpCentreScreenState();
}

class _HelpCentreScreenState extends State<HelpCentreScreen> {
  late Future<List<KnowledgeArticle>> _articles;
  late Future<List<SupportTicket>> _tickets;

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() {
    _articles = widget.repository.searchKnowledge('');
    _tickets = widget.repository.getForUser(widget.userId);
  }

  @override
  Widget build(BuildContext context) => DefaultTabController(
    length: 2,
    child: Scaffold(
      appBar: AppBar(
        title: const Text('Help centre'),
        bottom: const TabBar(
          tabs: [
            Tab(icon: Icon(Icons.menu_book_outlined), text: 'Help'),
            Tab(icon: Icon(Icons.support_agent), text: 'My tickets'),
          ],
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: _submitTicket,
        icon: const Icon(Icons.add),
        label: const Text('New ticket'),
      ),
      body: TabBarView(
        children: [
          FutureBuilder<List<KnowledgeArticle>>(
            future: _articles,
            builder: (context, snapshot) {
              if (!snapshot.hasData) {
                return const Center(child: CircularProgressIndicator());
              }
              return ListView(
                padding: const EdgeInsets.all(24),
                children: [
                  TextField(
                    decoration: const InputDecoration(
                      prefixIcon: Icon(Icons.search),
                      hintText: 'Search help articles',
                    ),
                    onSubmitted: (query) => setState(
                      () =>
                          _articles = widget.repository.searchKnowledge(query),
                    ),
                  ),
                  const SizedBox(height: 20),
                  for (final article in snapshot.data!)
                    Card(
                      child: ExpansionTile(
                        leading: Icon(_articleIcon(article.type)),
                        title: Text(article.title),
                        subtitle: Text(article.summary),
                        children: [
                          Padding(
                            padding: const EdgeInsets.all(16),
                            child: Align(
                              alignment: Alignment.centerLeft,
                              child: SelectableText(article.content),
                            ),
                          ),
                        ],
                      ),
                    ),
                ],
              );
            },
          ),
          FutureBuilder<List<SupportTicket>>(
            future: _tickets,
            builder: (context, snapshot) {
              if (!snapshot.hasData) {
                return const Center(child: CircularProgressIndicator());
              }
              return ListView(
                padding: const EdgeInsets.all(24),
                children: snapshot.data!
                    .map(
                      (ticket) => Card(
                        child: ListTile(
                          title: Text(ticket.subject),
                          subtitle: Text(
                            '${_label(ticket.category.name)} | '
                            '${_label(ticket.status.name)}',
                          ),
                          trailing: const Icon(Icons.chevron_right),
                          onTap: () => _openTicket(ticket),
                        ),
                      ),
                    )
                    .toList(),
              );
            },
          ),
        ],
      ),
    ),
  );

  Future<void> _submitTicket() async {
    final subject = TextEditingController();
    final message = TextEditingController();
    var category = SupportTicketCategory.generalInquiry;
    var priority = SupportTicketPriority.normal;
    final submit = await showDialog<bool>(
      context: context,
      builder: (context) => StatefulBuilder(
        builder: (context, setDialogState) => AlertDialog(
          title: const Text('New support ticket'),
          content: SingleChildScrollView(
            child: Column(
              mainAxisSize: MainAxisSize.min,
              children: [
                TextField(
                  controller: subject,
                  decoration: const InputDecoration(labelText: 'Subject'),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<SupportTicketCategory>(
                  initialValue: category,
                  decoration: const InputDecoration(labelText: 'Category'),
                  items: SupportTicketCategory.values
                      .map(
                        (value) => DropdownMenuItem(
                          value: value,
                          child: Text(_label(value.name)),
                        ),
                      )
                      .toList(),
                  onChanged: (value) =>
                      setDialogState(() => category = value ?? category),
                ),
                const SizedBox(height: 12),
                DropdownButtonFormField<SupportTicketPriority>(
                  initialValue: priority,
                  decoration: const InputDecoration(labelText: 'Priority'),
                  items: SupportTicketPriority.values
                      .map(
                        (value) => DropdownMenuItem(
                          value: value,
                          child: Text(_label(value.name)),
                        ),
                      )
                      .toList(),
                  onChanged: (value) =>
                      setDialogState(() => priority = value ?? priority),
                ),
                const SizedBox(height: 12),
                TextField(
                  controller: message,
                  maxLines: 4,
                  decoration: const InputDecoration(labelText: 'Message'),
                ),
              ],
            ),
          ),
          actions: [
            TextButton(
              onPressed: () => Navigator.pop(context),
              child: const Text('Cancel'),
            ),
            FilledButton(
              onPressed: () => Navigator.pop(context, true),
              child: const Text('Submit'),
            ),
          ],
        ),
      ),
    );
    if (submit != true) return;
    await widget.repository.submitTicket(
      requesterId: widget.userId,
      subject: subject.text,
      category: category,
      priority: priority,
      message: message.text,
    );
    if (mounted) setState(_reload);
  }

  Future<void> _openTicket(SupportTicket ticket) async {
    await Navigator.of(context).push<void>(
      MaterialPageRoute(
        builder: (_) => SupportConversationScreen(
          ticketId: ticket.id,
          userId: widget.userId,
          repository: widget.repository,
          isAgent: false,
        ),
      ),
    );
    if (mounted) setState(_reload);
  }

  static IconData _articleIcon(KnowledgeContentType type) => switch (type) {
    KnowledgeContentType.frequentlyAskedQuestion => Icons.help_outline,
    KnowledgeContentType.article => Icons.article_outlined,
    KnowledgeContentType.tutorial => Icons.school_outlined,
    KnowledgeContentType.applicationHelp => Icons.fact_check_outlined,
  };

  static String _label(String value) => value.replaceAllMapped(
    RegExp(r'([A-Z])'),
    (match) => ' ${match.group(1)!.toLowerCase()}',
  );
}

class SupportConversationScreen extends StatefulWidget {
  const SupportConversationScreen({
    super.key,
    required this.ticketId,
    required this.userId,
    required this.repository,
    required this.isAgent,
  });
  final String ticketId;
  final String userId;
  final SupportRepository repository;
  final bool isAgent;

  @override
  State<SupportConversationScreen> createState() =>
      _SupportConversationScreenState();
}

class _SupportConversationScreenState extends State<SupportConversationScreen> {
  late Future<SupportTicket?> _ticket;
  final _message = TextEditingController();

  @override
  void initState() {
    super.initState();
    _reload();
  }

  void _reload() => _ticket = widget.repository.getById(widget.ticketId);

  @override
  Widget build(BuildContext context) => Scaffold(
    appBar: AppBar(title: const Text('Support conversation')),
    body: FutureBuilder<SupportTicket?>(
      future: _ticket,
      builder: (context, snapshot) {
        final ticket = snapshot.data;
        if (ticket == null) {
          return const Center(child: CircularProgressIndicator());
        }
        return Column(
          children: [
            Expanded(
              child: ListView(
                padding: const EdgeInsets.all(20),
                children: [
                  Text(
                    ticket.subject,
                    style: Theme.of(context).textTheme.headlineSmall,
                  ),
                  const SizedBox(height: 8),
                  Chip(
                    label: Text(
                      _HelpCentreScreenState._label(ticket.status.name),
                    ),
                  ),
                  const SizedBox(height: 16),
                  for (final message in ticket.messages)
                    ListTile(
                      leading: Icon(
                        message.isAgent
                            ? Icons.support_agent
                            : Icons.person_outline,
                      ),
                      title: Text(message.message),
                      subtitle: Text(message.createdAt.toLocal().toString()),
                    ),
                ],
              ),
            ),
            Padding(
              padding: const EdgeInsets.all(16),
              child: Row(
                children: [
                  Expanded(
                    child: TextField(
                      controller: _message,
                      decoration: const InputDecoration(
                        hintText: 'Write a reply',
                      ),
                    ),
                  ),
                  IconButton(
                    tooltip: 'Send reply',
                    icon: const Icon(Icons.send),
                    onPressed: _send,
                  ),
                ],
              ),
            ),
          ],
        );
      },
    ),
  );

  Future<void> _send() async {
    if (_message.text.trim().isEmpty) return;
    await widget.repository.addMessage(
      ticketId: widget.ticketId,
      senderId: widget.userId,
      message: _message.text,
      isAgent: widget.isAgent,
    );
    _message.clear();
    if (mounted) setState(_reload);
  }
}
