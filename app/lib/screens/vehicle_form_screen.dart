import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';

/// Add a vehicle, or edit/delete one when [vehicle] is given.
class VehicleFormScreen extends StatefulWidget {
  const VehicleFormScreen({super.key, this.vehicle});

  final Map<String, dynamic>? vehicle;

  @override
  State<VehicleFormScreen> createState() => _VehicleFormScreenState();
}

class _VehicleFormScreenState extends State<VehicleFormScreen> {
  final _make = TextEditingController();
  final _model = TextEditingController();
  final _color = TextEditingController();
  final _plate = TextEditingController();
  int _seats = 4;
  bool _saving = false;
  String? _error;

  bool get _editing => widget.vehicle != null;

  @override
  void initState() {
    super.initState();
    final v = widget.vehicle;
    if (v != null) {
      _make.text = v['make'] as String;
      _model.text = v['model'] as String;
      _color.text = v['color'] as String;
      _plate.text = v['plate_number'] as String;
      _seats = v['total_seats'] as int;
    }
  }

  @override
  void dispose() {
    _make.dispose();
    _model.dispose();
    _color.dispose();
    _plate.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    if ([_make, _model, _color, _plate].any((c) => c.text.trim().isEmpty)) {
      setState(() => _error = 'Fill in make, model, colour and plate number.');
      return;
    }
    final body = {
      'make': _make.text.trim(),
      'model': _model.text.trim(),
      'color': _color.text.trim(),
      'plate_number': _plate.text.trim(),
      'total_seats': _seats,
    };
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      if (_editing) {
        await api.put('/vehicles/${widget.vehicle!['vehicle_id']}', body);
      } else {
        await api.post('/vehicles', body);
      }
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _delete() async {
    final v = widget.vehicle!;
    final ok = await confirmDialog(
      context,
      title: 'Delete this vehicle?',
      message: '${v['make']} ${v['model']}, ${v['plate_number']} will be removed from your profile.',
      yes: 'Delete',
      no: 'Keep',
    );
    if (!ok) return;
    try {
      await api.delete('/vehicles/${v['vehicle_id']}');
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      // e.g. the vehicle is used by an upcoming trip
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: Text(_editing ? 'Edit vehicle' : 'Add vehicle')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          Row(children: [
            Expanded(child: TextField(controller: _make, decoration: const InputDecoration(labelText: 'Make'))),
            const SizedBox(width: 10),
            Expanded(child: TextField(controller: _model, decoration: const InputDecoration(labelText: 'Model'))),
          ]),
          const SizedBox(height: 12),
          TextField(controller: _color, decoration: const InputDecoration(labelText: 'Colour')),
          const SizedBox(height: 12),
          TextField(controller: _plate, decoration: const InputDecoration(labelText: 'Plate number')),
          const SizedBox(height: 16),
          const Text('Passenger seats'),
          const SizedBox(height: 6),
          Row(children: [
            IconButton.outlined(
              onPressed: _seats > 1 ? () => setState(() => _seats--) : null,
              icon: const Icon(Icons.remove),
            ),
            Padding(
              padding: const EdgeInsets.symmetric(horizontal: 16),
              child: Text('$_seats', style: Theme.of(context).textTheme.titleLarge),
            ),
            IconButton.outlined(
              onPressed: _seats < 4 ? () => setState(() => _seats++) : null,
              icon: const Icon(Icons.add),
            ),
          ]),
          if (_error != null) ...[const SizedBox(height: 12), errorText(context, _error!)],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _saving ? null : _save,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: _saving
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_editing ? 'Save changes' : 'Save vehicle'),
            ),
          ),
          if (_editing) ...[
            const SizedBox(height: 10),
            OutlinedButton(onPressed: _delete, child: const Text('Delete vehicle')),
            const SizedBox(height: 6),
            Text('A vehicle used by an upcoming trip cannot be deleted.',
                textAlign: TextAlign.center, style: Theme.of(context).textTheme.bodySmall),
          ],
        ],
      ),
    );
  }
}
