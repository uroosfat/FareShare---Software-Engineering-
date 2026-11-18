import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';
import '../widgets/countdown.dart';

class TripDetailsScreen extends StatefulWidget {
  const TripDetailsScreen({super.key, required this.tripId});

  final int tripId;

  @override
  State<TripDetailsScreen> createState() => _TripDetailsScreenState();
}

class _TripDetailsScreenState extends State<TripDetailsScreen> {
  Map<String, dynamic>? _trip;
  String? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      if (auth.user == null) await auth.refreshUser();
      final res = await api.get('/trips/${widget.tripId}');
      if (mounted) {
        setState(() {
          _trip = Map<String, dynamic>.from(res as Map);
          _error = null;
        });
      }
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _requestToJoin() async {
    final controller = TextEditingController();
    final send = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Request to join'),
        content: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            TextField(
              controller: controller,
              maxLength: 300,
              maxLines: 3,
              decoration: const InputDecoration(
                labelText: 'Message to the manager (optional)',
                hintText: 'e.g. I can be ready at the Clifton Bridge stop.',
              ),
            ),
            const SizedBox(height: 8),
            const Text('One request at a time. The manager has 10 minutes to accept or decline. '
                'If they do not respond, the request expires.'),
          ],
        ),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Cancel')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Send request')),
        ],
      ),
    );
    final message = controller.text;
    if (send != true) return;
    setState(() => _busy = true);
    try {
      await api.post('/trips/${widget.tripId}/requests', {'message': message});
      await _load();
      if (mounted) snack(context, 'Request sent');
    } on ApiException catch (e) {
      if (mounted) snack(context, e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  Future<void> _cancelRequest(int requestId) async {
    setState(() => _busy = true);
    try {
      await api.post('/requests/$requestId/cancel');
      await _load();
    } on ApiException catch (e) {
      if (mounted) snack(context, e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final t = _trip;
    return Scaffold(
      appBar: AppBar(title: const Text('Trip details')),
      body: t == null
          ? Center(child: _error == null ? const CircularProgressIndicator() : errorText(context, _error!))
          : _body(t),
    );
  }

  Widget _body(Map<String, dynamic> t) {
    final manager = t['manager'] as Map;
    final vehicle = t['vehicle'] as Map?;
    final mine = manager['user_id'] == auth.user?['user_id'];
    final req = t['my_request'] as Map?;
    final status = req?['status'] as String?;
    final gender = t['gender_filter'] as String;

    Widget action;
    if (mine) {
      action = OutlinedButton(
        onPressed: () => context.go('/my-trips'),
        child: const Padding(
          padding: EdgeInsets.symmetric(vertical: 12),
          child: Text('You manage this trip. Edit it from My trips'),
        ),
      );
    } else if (status == 'pending' && req != null) {
      final r = req;
      action = Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          const FilledButton(
            onPressed: null,
            child: Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Text('Request pending')),
          ),
          const SizedBox(height: 8),
          Center(
            child: Countdown(
              expiresAt: r['expires_at'] as String,
              prefix: 'Time left for the manager to respond: ',
              onDone: _load,
            ),
          ),
          TextButton(
            onPressed: _busy ? null : () => _cancelRequest(r['request_id'] as int),
            child: const Text('Cancel request'),
          ),
        ],
      );
    } else if (status == 'accepted') {
      action = const FilledButton(
        onPressed: null,
        child: Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Text('You joined this trip')),
      );
    } else {
      action = FilledButton(
        onPressed: _busy || t['status'] != 'open' ? null : _requestToJoin,
        child: Padding(
          padding: const EdgeInsets.symmetric(vertical: 12),
          child: Text(status == null ? 'Request to join' : 'Request again (was $status)'),
        ),
      );
    }

    return ListView(
      padding: const EdgeInsets.all(20),
      children: [
        Text('${t['origin_area']} to ${t['destination_area']}', style: Theme.of(context).textTheme.headlineSmall),
        const SizedBox(height: 8),
        Wrap(spacing: 6, children: [
          Chip(label: Text(capitalize(t['status'] as String))),
          Chip(label: Text(gender == 'any' ? 'Anyone' : '${capitalize(gender)} only')),
          Chip(label: Text(t['ride_type'] == 'own_car' ? 'Own car' : 'InDrive group')),
        ]),
        const SizedBox(height: 12),
        Card(
          child: Column(children: [
            _row('Departure', formatTime(t['departure_time'] as String)),
            _row('Seats left', '${t['available_seats']}'),
            _row('Cost per person', 'Rs ${(t['cost_per_person'] as num).toStringAsFixed(0)}'),
            _row('Vehicle',
                vehicle == null ? 'InDrive group (booked together)' : '${vehicle['make']} ${vehicle['model']}, ${vehicle['color']}'),
          ]),
        ),
        const SizedBox(height: 12),
        Card(
          child: ListTile(
            leading: const CircleAvatar(child: Icon(Icons.person)),
            title: Text('${manager['full_name']}'),
            subtitle: Text('Trip manager · ${manager['completed_trips_count']} trips completed'),
          ),
        ),
        const SizedBox(height: 8),
        Text(
          'The fare is split between riders and paid outside the app. The manager\'s phone number is '
          'shown only after your request is accepted.',
          style: Theme.of(context).textTheme.bodySmall,
        ),
        const SizedBox(height: 20),
        action,
      ],
    );
  }

  Widget _row(String k, String v) => ListTile(
        dense: true,
        title: Text(k),
        trailing: Text(v, style: const TextStyle(fontWeight: FontWeight.w600)),
      );
}
