import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import 'app_state.dart';
import 'router.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  await auth.load(); // restore the saved login token before showing any screen
  runApp(const FareShareApp());
}

class FareShareApp extends StatefulWidget {
  const FareShareApp({super.key});

  @override
  State<FareShareApp> createState() => _FareShareAppState();
}

class _FareShareAppState extends State<FareShareApp> {
  late final GoRouter _router = buildRouter();

  @override
  Widget build(BuildContext context) {
    return MaterialApp.router(
      title: 'FareShare',
      debugShowCheckedModeBanner: false,
      routerConfig: _router,
      theme: ThemeData(
        useMaterial3: true,
        colorScheme: ColorScheme.fromSeed(seedColor: const Color(0xFF3C4043)),
        inputDecorationTheme: const InputDecorationTheme(
          border: OutlineInputBorder(),
          filled: true,
        ),
      ),
    );
  }
}
