import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';
import '../widgets/countdown.dart';

class RequestsScreen extends StatelessWidget {
  const RequestsScreen({super.key});

  @override
  Widget build(BuildContext context) {
    return DefaultTabController(
      length: 2,
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 20, 20, 0),
            child: Align(
              alignment: Alignment.centerLeft,
              child: Text('Requests', style: Theme.of(context).textTheme.headlineSmall),
            ),
          ),
          const TabBar(tabs: [Tab(text: 'Sent by me'), Tab(text: 'Received')]),
          const Expanded(child: TabBarView(children: [_SentTab(), _ReceivedTab()])),
        ],
      ),
    );
  }
}

class _SentTab extends StatefulWidget {
  const _SentTab();

  @override
  State<_SentTab> createState() => _SentTabState();
}

class _SentTabState extends State<_SentTab> {
  List<dynamic> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await api.get('/requests/sent') as List;
      if (mounted) {
        setState(() {
          _items = res;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _act(String path, {String? confirmTitle, String? confirmMessage, String? yes}) async {
    if (confirmTitle != null) {
      final ok = await confirmDialog(context, title: confirmTitle, message: confirmMessage ?? '', yes: yes ?? 'Yes');
      if (!ok) return;
    }
    try {
      await api.post(path);
    } on ApiException catch (e) {
      if (mounted) snack(context, e.message);
    }
    _load();
  }

  Future<void> _travel(Map<String, dynamic> r, bool travelled) async {
    try {
      await api.post('/requests/${r['request_id']}/confirm-travel', {'travelled': travelled});
      await auth.refreshUser();
      if (mounted) snack(context, travelled ? 'Thanks, trip counted' : 'Thanks, noted');
    } on ApiException catch (e) {
      if (mounted) snack(context, e.message);
    }
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) errorText(context, _error!),
          if (!_loading && _error == null && _items.isEmpty)
            const Text('No requests yet. Find a trip on Home and send a request.'),
          for (final r in _items) _card(r as Map<String, dynamic>),
        ],
      ),
    );
  }

  Widget _card(Map<String, dynamic> r) {
    final trip = r['trip'] as Map;
    final status = r['status'] as String;
    final manager = trip['manager'] as Map;
    return Card(
      child: InkWell(
        onTap: () async {
          await context.push('/trip/${r['trip_id']}');
          if (mounted) _load();
        },
        child: Padding(
          padding: const EdgeInsets.all(14),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            children: [
              Row(
                mainAxisAlignment: MainAxisAlignment.spaceBetween,
                children: [
                  Expanded(
                    child: Text('${trip['origin_area']} to ${trip['destination_area']}',
                        style: Theme.of(context).textTheme.titleMedium),
                  ),
                  Chip(label: Text(capitalize(status))),
                ],
              ),
              Text('${formatTime(trip['departure_time'] as String)} · ${manager['full_name']}'),
              if (status == 'pending') ...[
                const SizedBox(height: 6),
                Countdown(expiresAt: r['expires_at'] as String, prefix: 'Expires in ', onDone: _load),
                const SizedBox(height: 6),
                OutlinedButton(
                  onPressed: () => _act('/requests/${r['request_id']}/cancel'),
                  child: const Text('Cancel request'),
                ),
              ],
              if (status == 'accepted' && r['needs_confirmation'] == true) ...[
                const SizedBox(height: 6),
                const Text('The manager marked this trip as completed. Did you travel?'),
                const SizedBox(height: 6),
                Row(children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: () => _travel(r, false),
                      child: const Text('No'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: FilledButton(
                      onPressed: () => _travel(r, true),
                      child: const Text('Yes, I travelled'),
                    ),
                  ),
                ]),
              ] else if (status == 'accepted' && trip['status'] == 'completed') ...[
                const SizedBox(height: 6),
                const Text('Trip completed.'),
              ] else if (status == 'accepted') ...[
                const SizedBox(height: 6),
                if (trip['pickup_point'] != null) Text('Pickup point: ${trip['pickup_point']}'),
                Text('Manager phone: ${r['manager_phone'] ?? 'not shared'}'),
                const SizedBox(height: 6),
                if (trip['status'] != 'confirmed')
                OutlinedButton(
                  onPressed: () => _act(
                    '/requests/${r['request_id']}/leave',
                    confirmTitle: 'Leave this trip?',
                    confirmMessage: 'Your seat is released and the manager is notified.',
                    yes: 'Leave trip',
                  ),
                  child: const Text('Leave trip'),
                ),
              ],
              if (status == 'expired')
                const Padding(
                  padding: EdgeInsets.only(top: 6),
                  child: Text('The manager did not respond in time. You can request a trip again.'),
                ),
            ],
          ),
        ),
      ),
    );
  }
}

class _ReceivedTab extends StatefulWidget {
  const _ReceivedTab();

  @override
  State<_ReceivedTab> createState() => _ReceivedTabState();
}

class _ReceivedTabState extends State<_ReceivedTab> {
  List<dynamic> _items = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await api.get('/requests/received', query: {'status': 'pending'}) as List;
      if (mounted) {
        setState(() {
          _items = res;
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _answer(Map<String, dynamic> r, String action) async {
    try {
      await api.post('/requests/${r['request_id']}/$action');
      if (mounted) snack(context, action == 'accept' ? 'Request accepted' : 'Request declined');
    } on ApiException catch (e) {
      if (mounted) snack(context, e.message);
    }
    _load();
  }

  @override
  Widget build(BuildContext context) {
    return RefreshIndicator(
      onRefresh: _load,
      child: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) errorText(context, _error!),
          if (!_loading && _error == null && _items.isEmpty)
            const Text('No requests waiting for you. Requests for your trips show up here.'),
          for (final r in _items) _card(r as Map<String, dynamic>),
        ],
      ),
    );
  }

  Widget _card(Map<String, dynamic> r) {
    final rider = r['rider'] as Map;
    final trip = r['trip'] as Map;
    final message = r['message'] as String?;
    return Card(
      child: Padding(
        padding: const EdgeInsets.all(14),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text('${trip['origin_area']} to ${trip['destination_area']} · ${formatTime(trip['departure_time'] as String)}',
                style: Theme.of(context).textTheme.bodySmall),
            const SizedBox(height: 6),
            Text('${rider['full_name']}', style: Theme.of(context).textTheme.titleMedium),
            Text('${capitalize(rider['gender'] as String)} · ${rider['completed_trips_count']} trips completed'),
            if (message != null && message.isNotEmpty) ...[
              const SizedBox(height: 6),
              Text('"$message"'),
            ],
            const SizedBox(height: 6),
            Countdown(expiresAt: r['expires_at'] as String, prefix: 'Respond within ', onDone: _load),
            const SizedBox(height: 8),
            Row(children: [
              Expanded(child: OutlinedButton(onPressed: () => _answer(r, 'decline'), child: const Text('Decline'))),
              const SizedBox(width: 10),
              Expanded(child: FilledButton(onPressed: () => _answer(r, 'accept'), child: const Text('Accept'))),
            ]),
          ],
        ),
      ),
    );
  }
}
