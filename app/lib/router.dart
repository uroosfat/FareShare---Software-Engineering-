import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'app_state.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/placeholder_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/signup_screen.dart';

const _tabs = ['/home', '/my-trips', '/requests', '/profile'];

GoRouter buildRouter() {
  return GoRouter(
    initialLocation: '/home',
    refreshListenable: auth, // re-run redirect when the user logs in or out
    redirect: (context, state) {
      final loc = state.matchedLocation;
      final onAuthPage = loc == '/login' || loc == '/signup';
      if (!auth.loggedIn && !onAuthPage) return '/login';
      if (auth.loggedIn && onAuthPage) return '/home';
      return null;
    },
    routes: [
      GoRoute(path: '/login', builder: (c, s) => const LoginScreen()),
      GoRoute(path: '/signup', builder: (c, s) => const SignupScreen()),
      ShellRoute(
        builder: (c, s, child) => MainShell(location: s.matchedLocation, child: child),
        routes: [
          GoRoute(path: '/home', builder: (c, s) => const HomeScreen()),
          GoRoute(
            path: '/my-trips',
            builder: (c, s) => const PlaceholderScreen(
              title: 'My trips',
              note: 'Trips you manage and trips you joined will show here.',
            ),
          ),
          GoRoute(
            path: '/requests',
            builder: (c, s) => const PlaceholderScreen(
              title: 'Requests',
              note: 'Requests you sent and received will show here.',
            ),
          ),
          GoRoute(path: '/profile', builder: (c, s) => const ProfileScreen()),
        ],
      ),
    ],
  );
}

/// Bottom navigation bar shared by the four main tabs.
class MainShell extends StatelessWidget {
  const MainShell({super.key, required this.location, required this.child});

  final String location;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    var index = _tabs.indexWhere((p) => location.startsWith(p));
    if (index < 0) index = 0;
    return Scaffold(
      body: SafeArea(child: child),
      bottomNavigationBar: NavigationBar(
        selectedIndex: index,
        onDestinationSelected: (i) => context.go(_tabs[i]),
        destinations: const [
          NavigationDestination(icon: Icon(Icons.search), label: 'Home'),
          NavigationDestination(icon: Icon(Icons.directions_car), label: 'My trips'),
          NavigationDestination(icon: Icon(Icons.inbox), label: 'Requests'),
          NavigationDestination(icon: Icon(Icons.person), label: 'Profile'),
        ],
      ),
    );
  }
}
