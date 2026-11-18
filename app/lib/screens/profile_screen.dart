import 'package:flutter/material.dart';

import '../api/api_client.dart';
import '../app_state.dart';

class ProfileScreen extends StatefulWidget {
  const ProfileScreen({super.key});

  @override
  State<ProfileScreen> createState() => _ProfileScreenState();
}

class _ProfileScreenState extends State<ProfileScreen> {
  String? _error;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    try {
      await auth.refreshUser();
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _confirmLogout() async {
    final ok = await showDialog<bool>(
      context: context,
      builder: (ctx) => AlertDialog(
        title: const Text('Log out?'),
        content: const Text('You will need to log in again to see your trips.'),
        actions: [
          TextButton(onPressed: () => Navigator.pop(ctx, false), child: const Text('Stay logged in')),
          FilledButton(onPressed: () => Navigator.pop(ctx, true), child: const Text('Log out')),
        ],
      ),
    );
    if (ok == true) await auth.logout();
  }

  @override
  Widget build(BuildContext context) {
    return ListenableBuilder(
      listenable: auth,
      builder: (context, _) {
        final u = auth.user;
        return ListView(
          padding: const EdgeInsets.all(24),
          children: [
            Text('Profile', style: Theme.of(context).textTheme.headlineSmall),
            const SizedBox(height: 16),
            if (u == null && _error == null) const LinearProgressIndicator(),
            if (_error != null) Text(_error!, style: TextStyle(color: Theme.of(context).colorScheme.error)),
            if (u != null) ...[
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${u['full_name']}', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 6),
                      Text('${u['email']}'),
                      Text('Gender: ${u['gender']}'),
                      Text('Phone: ${u['phone'] ?? 'not set'}'),
                      const SizedBox(height: 10),
                      Text('${u['completed_trips_count']} trips completed',
                          style: Theme.of(context).textTheme.titleMedium),
                    ],
                  ),
                ),
              ),
            ],
            const SizedBox(height: 24),
            OutlinedButton(onPressed: _confirmLogout, child: const Text('Log out')),
          ],
        );
      },
    );
  }
}
