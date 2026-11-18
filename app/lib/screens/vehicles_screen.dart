import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';

class VehiclesScreen extends StatefulWidget {
  const VehiclesScreen({super.key});

  @override
  State<VehiclesScreen> createState() => _VehiclesScreenState();
}

class _VehiclesScreenState extends State<VehiclesScreen> {
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
      final res = await api.get('/vehicles') as List;
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

  Future<void> _open([Map<String, dynamic>? vehicle]) async {
    await context.push<bool>('/vehicle-form', extra: vehicle);
    if (mounted) _load();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('My vehicles')),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _open(),
        icon: const Icon(Icons.add),
        label: const Text('Add vehicle'),
      ),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          const Text('Vehicles you can use when you post an Own car trip.'),
          const SizedBox(height: 12),
          if (_loading) const LinearProgressIndicator(),
          if (_error != null) errorText(context, _error!),
          if (!_loading && _error == null && _items.isEmpty)
            const Text('No vehicles yet. Add a car to offer rides as the trip manager.'),
          for (final v in _items)
            Card(
              child: ListTile(
                leading: const Icon(Icons.directions_car),
                title: Text('${(v as Map)['make']} ${v['model']}'),
                subtitle: Text('${v['color']} · ${v['plate_number']} · ${v['total_seats']} seats'),
                trailing: TextButton(
                  onPressed: () => _open(Map<String, dynamic>.from(v)),
                  child: const Text('Edit'),
                ),
              ),
            ),
        ],
      ),
    );
  }
}
