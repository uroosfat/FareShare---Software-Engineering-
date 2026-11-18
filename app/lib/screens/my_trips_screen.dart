import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../utils.dart';
import '../app_state.dart';
import '../widgets/trip_card.dart';

class MyTripsScreen extends StatefulWidget {
  const MyTripsScreen({super.key});

  @override
  State<MyTripsScreen> createState() => _MyTripsScreenState();
}

class _MyTripsScreenState extends State<MyTripsScreen> {
  List<dynamic> _managing = [];
  List<dynamic> _joined = [];
  bool _loading = true;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await api.get('/trips/mine') as Map;
      if (!mounted) return;
      setState(() {
        _managing = res['managing'] as List;
        _joined = res['joined'] as List;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  @override
  Widget build(BuildContext context) {
    final empty = _managing.isEmpty && _joined.isEmpty;
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final changed = await context.push<bool>('/post-trip');
          if (changed == true) _load();
        },
        icon: const Icon(Icons.add),
        label: const Text('Post trip'),
      ),
      body: RefreshIndicator(
        onRefresh: _load,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 90),
          children: [
            Text('My trips', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 12),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null) errorText(context, _error!),
            if (!_loading && _error == null && empty)
              const Text('No trips yet. Post a trip, or find one on Home.'),
            for (final t in _managing)
              TripCard(
                trip: t as Map<String, dynamic>,
                tags: ['Manager', capitalize(t['status'] as String)],
                onTap: () async {
                  await context.push('/trip/${t['trip_id']}');
                  if (mounted) _load();
                },
                actions: [
                  Text('${t['pending_requests']} pending · ${t['accepted_riders']} accepted'),
                  if (t['status'] == 'open')
                    OutlinedButton(
                      onPressed: () async {
                        final changed = await context.push<bool>('/post-trip', extra: t);
                        if (changed == true) _load();
                      },
                      child: const Text('Edit'),
                    ),
                  if ((t['pending_requests'] as int) > 0)
                    FilledButton(onPressed: () => context.go('/requests'), child: const Text('View requests')),
                ],
              ),
            for (final t in _joined)
              TripCard(
                trip: t as Map<String, dynamic>,
                tags: ['Rider', capitalize(((t['my_request'] as Map?)?['status'] ?? 'pending') as String)],
                onTap: () async {
                  await context.push('/trip/${t['trip_id']}');
                  if (mounted) _load();
                },
              ),
          ],
        ),
      ),
    );
  }
}
