import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';

/// Manager confirms the pickup point once at least one rider is accepted.
class ConfirmPickupScreen extends StatefulWidget {
  const ConfirmPickupScreen({super.key, required this.tripId});

  final int tripId;

  @override
  State<ConfirmPickupScreen> createState() => _ConfirmPickupScreenState();
}

class _ConfirmPickupScreenState extends State<ConfirmPickupScreen> {
  final _point = TextEditingController();
  List<dynamic> _riders = [];
  bool _loading = true;
  bool _busy = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  @override
  void dispose() {
    _point.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    try {
      final res = await api.get('/trips/${widget.tripId}/riders') as List;
      if (mounted) setState(() => _riders = res);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _loading = false);
    }
  }

  Future<void> _confirm() async {
    if (_point.text.trim().isEmpty) {
      snack(context, 'Enter the pickup point');
      return;
    }
    final ok = await confirmDialog(
      context,
      title: 'Confirm pickup?',
      message: 'Any requests still waiting will be declined and the trip will close for new riders.',
      yes: 'Confirm',
    );
    if (!ok) return;
    setState(() => _busy = true);
    try {
      await api.post('/trips/${widget.tripId}/confirm', {'pickup_point': _point.text.trim()});
      if (!mounted) return;
      snack(context, 'Pickup confirmed');
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
      appBar: AppBar(title: const Text('Confirm pickup')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Text('Accepted riders', style: Theme.of(context).textTheme.titleMedium),
          const SizedBox(height: 8),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) errorText(context, _error!),
          if (!_loading && _error == null && _riders.isEmpty)
            const Text('No accepted riders yet. Accept at least one request first.'),
          for (final r in _riders)
            Card(
              child: ListTile(
                leading: const CircleAvatar(child: Icon(Icons.person)),
                title: Text('${(r as Map)['rider']['full_name']}'),
                subtitle: Text('Phone: ${r['rider']['phone'] ?? 'not shared'}'),
              ),
            ),
          const SizedBox(height: 16),
          TextField(
            controller: _point,
            maxLength: 150,
            decoration: const InputDecoration(
              labelText: 'Pickup point',
              hintText: 'e.g. Clifton Bridge bus stop',
              prefixIcon: Icon(Icons.place_outlined),
            ),
          ),
          const SizedBox(height: 8),
          FilledButton(
            onPressed: _busy || _riders.isEmpty ? null : _confirm,
            child: const Padding(padding: EdgeInsets.symmetric(vertical: 12), child: Text('Confirm pickup')),
          ),
        ],
      ),
    );
  }
}
