import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'app_state.dart';
import 'screens/change_password_screen.dart';
import 'screens/complete_trip_screen.dart';
import 'screens/confirm_pickup_screen.dart';
import 'screens/edit_profile_screen.dart';
import 'screens/home_screen.dart';
import 'screens/login_screen.dart';
import 'screens/my_trips_screen.dart';
import 'screens/post_trip_screen.dart';
import 'screens/profile_screen.dart';
import 'screens/requests_screen.dart';
import 'screens/signup_screen.dart';
import 'screens/trip_details_screen.dart';
import 'screens/vehicle_form_screen.dart';
import 'screens/vehicles_screen.dart';

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
      // Full-screen pages (no bottom bar)
      GoRoute(
        path: '/trip/:id',
        builder: (c, s) => TripDetailsScreen(tripId: int.parse(s.pathParameters['id']!)),
      ),
      GoRoute(
        path: '/post-trip',
        builder: (c, s) => PostTripScreen(trip: s.extra as Map<String, dynamic>?),
      ),
      GoRoute(
        path: '/confirm-trip/:id',
        builder: (c, s) => ConfirmPickupScreen(tripId: int.parse(s.pathParameters['id']!)),
      ),
      GoRoute(
        path: '/complete-trip/:id',
        builder: (c, s) => CompleteTripScreen(tripId: int.parse(s.pathParameters['id']!)),
      ),
      GoRoute(path: '/vehicles', builder: (c, s) => const VehiclesScreen()),
      GoRoute(
        path: '/vehicle-form',
        builder: (c, s) => VehicleFormScreen(vehicle: s.extra as Map<String, dynamic>?),
      ),
      GoRoute(path: '/edit-profile', builder: (c, s) => const EditProfileScreen()),
      GoRoute(path: '/change-password', builder: (c, s) => const ChangePasswordScreen()),
      ShellRoute(
        builder: (c, s, child) => MainShell(location: s.matchedLocation, child: child),
        routes: [
          GoRoute(path: '/home', builder: (c, s) => const HomeScreen()),
          GoRoute(path: '/my-trips', builder: (c, s) => const MyTripsScreen()),
          GoRoute(path: '/requests', builder: (c, s) => const RequestsScreen()),
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
