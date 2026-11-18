import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../config.dart';

const _days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'];
const _months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

String formatTime(String iso) {
  final d = DateTime.parse(iso).toLocal();
  final h = d.hour % 12 == 0 ? 12 : d.hour % 12;
  final m = d.minute.toString().padLeft(2, '0');
  final ampm = d.hour >= 12 ? 'PM' : 'AM';
  return '${_days[d.weekday - 1]} ${d.day} ${_months[d.month - 1]}, $h:$m $ampm';
}

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
    return ListView(
      padding: const EdgeInsets.all(20),
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
        if (!_loading && _error == null && _trips.isEmpty)
          const Text('No trips found. Try a different pickup place or campus.'),
        for (final t in _trips) _TripCard(trip: t as Map<String, dynamic>),
        const SizedBox(height: 24),
        const Divider(),
        TextButton(onPressed: _checkServer, child: const Text('Check server connection')),
        if (_serverCheck != null) Text(_serverCheck!, style: Theme.of(context).textTheme.bodySmall),
      ],
    );
  }
}

class _TripCard extends StatelessWidget {
  const _TripCard({required this.trip});

  final Map<String, dynamic> trip;

  @override
  Widget build(BuildContext context) {
    final manager = trip['manager'] as Map;
    final locked = trip['locked'] == true;
    final gender = trip['gender_filter'] as String;
    final card = Card(
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
                Text('Rs ${(trip['cost_per_person'] as num).toStringAsFixed(0)}',
                    style: Theme.of(context).textTheme.titleMedium),
              ],
            ),
            const SizedBox(height: 4),
            Text(formatTime(trip['departure_time'] as String)),
            const SizedBox(height: 8),
            Wrap(
              spacing: 6,
              children: [
                if (locked) const Chip(label: Text('Locked')),
                Chip(label: Text('${trip['available_seats']} seats left')),
                Chip(label: Text(gender == 'any' ? 'Anyone' : '${gender[0].toUpperCase()}${gender.substring(1)} only')),
                Chip(label: Text(trip['ride_type'] == 'own_car' ? 'Own car' : 'InDrive group')),
              ],
            ),
            const SizedBox(height: 6),
            Text('${manager['full_name']} · ${manager['completed_trips_count']} trips completed',
                style: Theme.of(context).textTheme.bodySmall),
          ],
        ),
      ),
    );
    return locked ? Opacity(opacity: 0.55, child: card) : card;
  }
}
