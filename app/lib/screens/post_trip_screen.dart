import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../config.dart';
import '../utils.dart';

/// Post a new trip, or edit one when [trip] is given (the manager's own trip).
class PostTripScreen extends StatefulWidget {
  const PostTripScreen({super.key, this.trip});

  final Map<String, dynamic>? trip;

  @override
  State<PostTripScreen> createState() => _PostTripScreenState();
}

class _PostTripScreenState extends State<PostTripScreen> {
  final _origin = TextEditingController();
  final _cost = TextEditingController(text: '200');
  String _campus = campuses.first;
  DateTime? _date;
  TimeOfDay? _time;
  int _seats = 3;
  String _who = 'any';
  String _ride = 'own_car';
  int? _vehicleId;
  List<Map<String, dynamic>> _vehicles = [];
  bool _saving = false;
  String? _error;

  bool get _editing => widget.trip != null;
  String get _myGender => (auth.user?['gender'] as String?) ?? 'female';

  @override
  void initState() {
    super.initState();
    final t = widget.trip;
    if (t != null) {
      _origin.text = t['origin_area'] as String;
      _campus = campuses.contains(t['destination_area']) ? t['destination_area'] as String : campuses.first;
      final dep = DateTime.parse(t['departure_time'] as String).toLocal();
      _date = DateTime(dep.year, dep.month, dep.day);
      _time = TimeOfDay(hour: dep.hour, minute: dep.minute);
      _seats = (t['available_seats'] as int) + ((t['accepted_riders'] as int?) ?? 0);
      _cost.text = (t['cost_per_person'] as num).toStringAsFixed(0);
      _who = t['gender_filter'] as String;
      _ride = t['ride_type'] as String;
      _vehicleId = (t['vehicle'] as Map?)?['vehicle_id'] as int?;
    }
    _loadData();
  }

  @override
  void dispose() {
    _origin.dispose();
    _cost.dispose();
    super.dispose();
  }

  Future<void> _loadData() async {
    try {
      if (auth.user == null) await auth.refreshUser();
      final res = await api.get('/vehicles') as List;
      if (!mounted) return;
      setState(() {
        _vehicles = res.map((e) => Map<String, dynamic>.from(e as Map)).toList();
        if (_vehicleId == null && _vehicles.isNotEmpty) _vehicleId = _vehicles.first['vehicle_id'] as int;
      });
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  int get _maxSeats {
    if (_ride == 'own_car' && _vehicleId != null) {
      for (final v in _vehicles) {
        if (v['vehicle_id'] == _vehicleId) return v['total_seats'] as int;
      }
    }
    return 4;
  }

  Future<void> _pickDate() async {
    final now = DateTime.now();
    final d = await showDatePicker(
      context: context,
      initialDate: _date ?? now,
      firstDate: DateTime(now.year, now.month, now.day),
      lastDate: now.add(const Duration(days: 90)),
    );
    if (d != null) setState(() => _date = d);
  }

  Future<void> _pickTime() async {
    final t = await showTimePicker(context: context, initialTime: _time ?? const TimeOfDay(hour: 8, minute: 0));
    if (t != null) setState(() => _time = t);
  }

  Future<void> _save() async {
    if (_origin.text.trim().isEmpty) {
      setState(() => _error = 'Enter the pickup area.');
      return;
    }
    if (_date == null || _time == null) {
      setState(() => _error = 'Choose the date and time.');
      return;
    }
    if (_ride == 'own_car' && _vehicleId == null) {
      setState(() => _error = 'Add a vehicle first, or choose InDrive group.');
      return;
    }
    final cost = double.tryParse(_cost.text.trim());
    if (cost == null || cost < 0) {
      setState(() => _error = 'Enter a valid cost per person.');
      return;
    }
    final when = DateTime(_date!.year, _date!.month, _date!.day, _time!.hour, _time!.minute);
    final body = {
      'origin_area': _origin.text.trim(),
      'destination_area': _campus,
      'departure_time': when.toUtc().toIso8601String(),
      'seats': _seats > _maxSeats ? _maxSeats : _seats,
      'cost_per_person': cost,
      'gender_filter': _who,
      'ride_type': _ride,
      'vehicle_id': _ride == 'own_car' ? _vehicleId : null,
    };
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      if (_editing) {
        await api.put('/trips/${widget.trip!['trip_id']}', body);
      } else {
        await api.post('/trips', body);
      }
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _cancelTrip() async {
    final ok = await confirmDialog(
      context,
      title: 'Cancel this trip?',
      message: 'The trip is removed from Home and your riders are notified.',
      yes: 'Cancel trip',
      no: 'Keep trip',
    );
    if (!ok) return;
    try {
      await api.post('/trips/${widget.trip!['trip_id']}/cancel');
      if (mounted) context.pop(true);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  @override
  Widget build(BuildContext context) {
    final seats = _seats > _maxSeats ? _maxSeats : _seats;
    return Scaffold(
      appBar: AppBar(title: Text(_editing ? 'Edit trip' : 'Post a trip')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _origin,
            decoration: const InputDecoration(labelText: 'From (pickup area)', hintText: 'e.g. Clifton'),
          ),
          const SizedBox(height: 12),
          DropdownButtonFormField<String>(
            initialValue: _campus,
            decoration: const InputDecoration(labelText: 'To (campus)'),
            items: [for (final c in campuses) DropdownMenuItem(value: c, child: Text(c))],
            onChanged: (v) => setState(() => _campus = v ?? _campus),
          ),
          const SizedBox(height: 12),
          Row(children: [
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _pickDate,
                icon: const Icon(Icons.calendar_today),
                label: Text(_date == null ? 'Date' : '${_date!.day}/${_date!.month}/${_date!.year}'),
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: OutlinedButton.icon(
                onPressed: _pickTime,
                icon: const Icon(Icons.access_time),
                label: Text(_time == null ? 'Time' : _time!.format(context)),
              ),
            ),
          ]),
          const SizedBox(height: 12),
          Row(children: [
            const Text('Seats'),
            const SizedBox(width: 12),
            IconButton.outlined(
              onPressed: seats > 1 ? () => setState(() => _seats = seats - 1) : null,
              icon: const Icon(Icons.remove),
            ),
            Padding(padding: const EdgeInsets.symmetric(horizontal: 12), child: Text('$seats')),
            IconButton.outlined(
              onPressed: seats < _maxSeats ? () => setState(() => _seats = seats + 1) : null,
              icon: const Icon(Icons.add),
            ),
            const SizedBox(width: 20),
            Expanded(
              child: TextField(
                controller: _cost,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(labelText: 'Cost per person (Rs)'),
              ),
            ),
          ]),
          const SizedBox(height: 16),
          const Text('Who can join'),
          const SizedBox(height: 6),
          SegmentedButton<String>(
            segments: [
              const ButtonSegment(value: 'any', label: Text('Anyone')),
              ButtonSegment(value: 'female', label: const Text('Female only'), enabled: _myGender == 'female'),
              ButtonSegment(value: 'male', label: const Text('Male only'), enabled: _myGender == 'male'),
            ],
            selected: {_who},
            onSelectionChanged: (s) => setState(() => _who = s.first),
          ),
          const SizedBox(height: 4),
          Text('You can only post trips for your own gender, or for anyone.',
              style: Theme.of(context).textTheme.bodySmall),
          const SizedBox(height: 16),
          const Text('Ride type'),
          const SizedBox(height: 6),
          SegmentedButton<String>(
            segments: const [
              ButtonSegment(value: 'own_car', label: Text('Own car')),
              ButtonSegment(value: 'indrive_group', label: Text('InDrive group')),
            ],
            selected: {_ride},
            onSelectionChanged: (s) => setState(() => _ride = s.first),
          ),
          const SizedBox(height: 12),
          if (_ride == 'own_car')
            if (_vehicles.isEmpty)
              Card(
                child: ListTile(
                  title: const Text('No vehicles yet'),
                  subtitle: const Text('Add a car to offer rides as the trip manager.'),
                  trailing: TextButton(
                    onPressed: () async {
                      await context.push<bool>('/vehicle-form');
                      _loadData();
                    },
                    child: const Text('Add vehicle'),
                  ),
                ),
              )
            else
              DropdownButtonFormField<int>(
                key: ValueKey('veh-$_vehicleId-${_vehicles.length}'),
                initialValue: _vehicleId,
                decoration: const InputDecoration(labelText: 'Vehicle'),
                items: [
                  for (final v in _vehicles)
                    DropdownMenuItem(
                      value: v['vehicle_id'] as int,
                      child: Text('${v['make']} ${v['model']}, ${v['color']} (${v['total_seats']} seats)'),
                    ),
                ],
                onChanged: (v) => setState(() => _vehicleId = v),
              )
          else
            const Text('No vehicle needed. The group books the InDrive together and splits the fare.'),
          if (_error != null) ...[const SizedBox(height: 12), errorText(context, _error!)],
          const SizedBox(height: 20),
          FilledButton(
            onPressed: _saving ? null : _save,
            child: Padding(
              padding: const EdgeInsets.symmetric(vertical: 14),
              child: _saving
                  ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(strokeWidth: 2))
                  : Text(_editing ? 'Save changes' : 'Post trip'),
            ),
          ),
          if (_editing) ...[
            const SizedBox(height: 10),
            OutlinedButton(onPressed: _cancelTrip, child: const Text('Cancel this trip')),
          ],
        ],
      ),
    );
  }
}
