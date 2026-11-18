import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../config.dart';
import '../widgets/trip_card.dart';

class HomeScreen extends StatefulWidget {
  const HomeScreen({super.key});

  @override
  State<HomeScreen> createState() => _HomeScreenState();
}

class _HomeScreenState extends State<HomeScreen> {
  final _origin = TextEditingController();
  String _campus = campuses.first;
  List<dynamic> _trips = [];
  bool _loading = false;
  String? _error;
  String? _serverCheck;

  @override
  void initState() {
    super.initState();
    _search();
  }

  @override
  void dispose() {
    _origin.dispose();
    super.dispose();
  }

  Future<void> _search() async {
    setState(() {
      _loading = true;
      _error = null;
    });
    try {
      final res = await api.get('/trips', query: {'origin': _origin.text, 'campus': _campus});
      if (mounted) setState(() => _trips = res as List<dynamic>);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _checkServer() async {
    setState(() => _serverCheck = 'Checking...');
    try {
      final res = await api.get('/health/db') as Map;
      if (!mounted) return;
      setState(() => _serverCheck =
          'Server: OK. Database ${res['database']}. ${res['users']} users, ${res['trips']} trips.');
    } on ApiException catch (e) {
      if (!mounted) return;
      setState(() => _serverCheck = 'Failed: ${e.message}');
    }
  }

  @override
  Widget build(BuildContext context) {
    final locked = _trips.any((t) => (t as Map)['locked'] == true);
    return Scaffold(
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () async {
          final changed = await context.push<bool>('/post-trip');
          if (changed == true) _search();
        },
        icon: const Icon(Icons.add),
        label: const Text('Post trip'),
      ),
      body: RefreshIndicator(
        onRefresh: _search,
        child: ListView(
          padding: const EdgeInsets.fromLTRB(20, 20, 20, 90),
          children: [
            Text('Find a trip', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 14),
            TextField(
              controller: _origin,
              textInputAction: TextInputAction.search,
              onSubmitted: (_) => _search(),
              decoration: const InputDecoration(
                labelText: 'Pickup place',
                hintText: 'e.g. Clifton',
                prefixIcon: Icon(Icons.place_outlined),
              ),
            ),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: _campus,
              decoration: const InputDecoration(labelText: 'Campus', prefixIcon: Icon(Icons.school_outlined)),
              items: [for (final c in campuses) DropdownMenuItem(value: c, child: Text(c))],
              onChanged: (v) {
                if (v == null) return;
                setState(() => _campus = v);
                _search();
              },
            ),
            const SizedBox(height: 10),
            FilledButton.icon(
              onPressed: _loading ? null : _search,
              icon: const Icon(Icons.search),
              label: const Text('Search trips'),
            ),
            const SizedBox(height: 16),
            if (_loading) const LinearProgressIndicator(),
            if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            if (locked)
              const Card(
                child: Padding(
                  padding: EdgeInsets.all(12),
                  child: Text('You have a pending or accepted request. You can request one trip at a time, '
                      'so the other trips are locked until it is answered or cancelled.'),
                ),
              ),
            if (!_loading && _error == null && _trips.isEmpty)
              const Text('No trips found. Try a different pickup place or campus, or post your own trip.'),
            for (final t in _trips)
              TripCard(
                trip: t as Map<String, dynamic>,
                tags: [
                  if ((t['my_request'] as Map?) != null) _requestTag((t['my_request'] as Map)['status'] as String),
                ],
                onTap: () async {
                  await context.push('/trip/${t['trip_id']}');
                  if (mounted) _search();
                },
              ),
            const SizedBox(height: 24),
            const Divider(),
            TextButton(onPressed: _checkServer, child: const Text('Check server connection')),
            if (_serverCheck != null) Text(_serverCheck!, style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
  }
}

String _requestTag(String status) {
  switch (status) {
    case 'pending':
      return 'Requested';
    case 'accepted':
      return 'Joined';
    case 'declined':
      return 'Declined';
    case 'expired':
      return 'Expired';
    default:
      return 'Cancelled';
  }
}
