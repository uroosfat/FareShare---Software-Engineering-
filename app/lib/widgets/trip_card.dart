import 'package:flutter/material.dart';

import '../utils.dart';

class TripCard extends StatelessWidget {
  const TripCard({super.key, required this.trip, this.onTap, this.tags = const [], this.actions = const []});

  final Map<String, dynamic> trip;
  final VoidCallback? onTap;
  final List<String> tags; // extra chips, e.g. "Manager", "Pending"
  final List<Widget> actions;

  @override
  Widget build(BuildContext context) {
    final manager = trip['manager'] as Map;
    final locked = trip['locked'] == true;
    final gender = trip['gender_filter'] as String;
    final card = Card(
      child: InkWell(
        onTap: onTap,
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
                  for (final t in tags) Chip(label: Text(t)),
                  if (locked) const Chip(label: Text('Locked')),
                  Chip(label: Text('${trip['available_seats']} seats left')),
                  Chip(label: Text(gender == 'any' ? 'Anyone' : '${capitalize(gender)} only')),
                  Chip(label: Text(trip['ride_type'] == 'own_car' ? 'Own car' : 'InDrive group')),
                ],
              ),
              const SizedBox(height: 6),
              Text('${manager['full_name']} · ${manager['completed_trips_count']} trips completed',
                  style: Theme.of(context).textTheme.bodySmall),
              if (actions.isNotEmpty) ...[
                const SizedBox(height: 8),
                Wrap(spacing: 8, children: actions),
              ],
            ],
          ),
        ),
      ),
    );
    return locked ? Opacity(opacity: 0.55, child: card) : card;
  }
}
