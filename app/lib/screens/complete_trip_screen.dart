import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';

/// Manager marks the trip completed and ticks who actually travelled.
class CompleteTripScreen extends StatefulWidget {
  const CompleteTripScreen({super.key, required this.tripId});

  final int tripId;

  @override
  State<CompleteTripScreen> createState() => _CompleteTripScreenState();
}

class _CompleteTripScreenState extends State<CompleteTripScreen> {
  List<dynamic> _riders = [];
  final Set<int> _ticked = {};
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      final res = await api.get('/trips/${widget.tripId}/riders') as List;
      if (!mounted) return;
      setState(() {
        _riders = res;
        for (final r in res) {
          _ticked.add((r as Map)['rider']['user_id'] as int); // everyone ticked by default
        }
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _complete() async {
    setState(() => _busy = true);
    try {
      await api.post('/trips/${widget.tripId}/complete', {'rider_ids': _ticked.toList()});
      await auth.refreshUser();
      if (!mounted) return;
      snack(context, 'Trip marked as completed');
      context.pop(true);
    } on ApiException catch (e) {
      if (mounted) snack(context, e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('Mark trip completed')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('Who travelled?', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 4),
          const Text('Untick anyone who did not show up. Each rider you tick is asked to confirm, '
              'and their completed-trips count goes up once they do.'),
          const SizedBox(height: 8),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) errorText(context, _error!),
          for (final r in _riders)
            CheckboxListTile(
              value: _ticked.contains((r as Map)['rider']['user_id']),
              title: Text('${r['rider']['full_name']}'),
              subtitle: Text('${r['rider']['phone'] ?? ''}'),
              onChanged: (v) => setState(() {
                final id = r['rider']['user_id'] as int;
                v == true ? _ticked.add(id) : _ticked.remove(id);
              }),
            ),
          const SizedBox(height: 12),
          FilledButton(
            onPressed: _busy || _loading ? null : _complete,
            child: const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Text('Mark as completed')),
          ),
        ],
      ),
    );
  }
}
