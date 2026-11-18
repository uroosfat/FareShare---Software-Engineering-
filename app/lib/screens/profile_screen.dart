import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../api/api_client.dart';
import '../app_state.dart';
import '../utils.dart';

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
      if (mounted) setState(() => _error = null);
    } on ApiException catch (e) {
      if (mounted) setState(() => _error = e.message);
    }
  }

  Future<void> _confirmLogout() async {
    final ok = await confirmDialog(
      context,
      title: 'Log out?',
      message: 'You will need to log in again to see your trips.',
      yes: 'Log out',
      no: 'Stay logged in',
    );
    if (ok) await auth.logout();
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
            if (_error != null) errorText(context, _error!),
            if (u != null)
              Card(
                child: Padding(
                  padding: const EdgeInsets.all(16),
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text('${u['full_name']}', style: Theme.of(context).textTheme.titleLarge),
                      const SizedBox(height: 6),
                      Text('${u['email']}'),
                      Text('Gender: ${capitalize('${u['gender']}')}'),
                      Text('Phone: ${u['phone'] ?? 'not set'}'),
                      const SizedBox(height: 10),
                      Text('${u['completed_trips_count']} trips completed',
                          style: Theme.of(context).textTheme.titleMedium),
                    ],
                  ),
                ),
              ),
            const SizedBox(height: 12),
            Card(
              child: Column(children: [
                ListTile(
                  leading: const Icon(Icons.edit_outlined),
                  title: const Text('Edit profile'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/edit-profile'),
                ),
                ListTile(
                  leading: const Icon(Icons.directions_car_outlined),
                  title: const Text('My vehicles'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/vehicles'),
                ),
                ListTile(
                  leading: const Icon(Icons.lock_outline),
                  title: const Text('Change password'),
                  trailing: const Icon(Icons.chevron_right),
                  onTap: () => context.push('/change-password'),
                ),
              ]),
            ),
            const SizedBox(height: 20),
            OutlinedButton(onPressed: _confirmLogout, child: const Text('Log out')),
          ],
        );
      },
    );
  }
}
