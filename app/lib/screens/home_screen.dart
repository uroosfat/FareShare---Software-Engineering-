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
  String _day = 'any'; // any | today | tomorrow | week
  String _slot = 'any'; // any | morning | afternoon | evening
  String _gender = 'any'; // any | female | male
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
      final now = DateTime.now();
      final today = DateTime(now.year, now.month, now.day);
      final query = <String, String>{'origin': _origin.text, 'campus': _campus};
      if (_day == 'today') {
        query['after'] = now.toUtc().toIso8601String();
        query['before'] = today.add(const Duration(days: 1)).toUtc().toIso8601String();
      } else if (_day == 'tomorrow') {
        query['after'] = today.add(const Duration(days: 1)).toUtc().toIso8601String();
        query['before'] = today.add(const Duration(days: 2)).toUtc().toIso8601String();
      } else if (_day == 'week') {
        query['after'] = now.toUtc().toIso8601String();
        query['before'] = today.add(const Duration(days: 8)).toUtc().toIso8601String();
      }
      if (_gender != 'any') query['gender'] = _gender;
      final res = await api.get('/trips', query: query) as List<dynamic>;
      // time of day is filtered here, on the phone's local time
      final shown = res.where((t) {
        if (_slot == 'any') return true;
        final h = DateTime.parse((t as Map)['departure_time'] as String).toLocal().hour;
        if (_slot == 'morning') return h >= 5 && h < 12;
        if (_slot == 'afternoon') return h >= 12 && h < 17;
        return h >= 17 || h < 5;
      }).toList();
      if (mounted) setState(() => _trips = shown);
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
            Row(children: [
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _day,
                  decoration: const InputDecoration(labelText: 'Day', prefixIcon: Icon(Icons.event_outlined)),
                  items: const [
                    DropdownMenuItem(value: 'any', child: Text('Any day')),
                    DropdownMenuItem(value: 'today', child: Text('Today')),
                    DropdownMenuItem(value: 'tomorrow', child: Text('Tomorrow')),
                    DropdownMenuItem(value: 'week', child: Text('Next 7 days')),
                  ],
                  onChanged: (v) {
                    setState(() => _day = v ?? 'any');
                    _search();
                  },
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: DropdownButtonFormField<String>(
                  initialValue: _slot,
                  decoration: const InputDecoration(labelText: 'Time', prefixIcon: Icon(Icons.schedule)),
                  items: const [
                    DropdownMenuItem(value: 'any', child: Text('Any time')),
                    DropdownMenuItem(value: 'morning', child: Text('Morning')),
                    DropdownMenuItem(value: 'afternoon', child: Text('Afternoon')),
                    DropdownMenuItem(value: 'evening', child: Text('Evening')),
                  ],
                  onChanged: (v) {
                    setState(() => _slot = v ?? 'any');
                    _search();
                  },
                ),
              ),
            ]),
            const SizedBox(height: 10),
            DropdownButtonFormField<String>(
              initialValue: _gender,
              decoration: const InputDecoration(labelText: 'Who can join', prefixIcon: Icon(Icons.people_outline)),
              items: const [
                DropdownMenuItem(value: 'any', child: Text('All trips')),
                DropdownMenuItem(value: 'female', child: Text('Women only trips')),
                DropdownMenuItem(value: 'male', child: Text('Men only trips')),
              ],
              onChanged: (v) {
                setState(() => _gender = v ?? 'any');
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
