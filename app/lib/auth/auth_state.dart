import 'package:flutter/foundation.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';

import '../api/api_client.dart';

/// Who is logged in. The token is kept in secure storage so the user stays logged in
/// after closing the app.
class AuthState extends ChangeNotifier {
  AuthState(this.api) {
    api.onUnauthorized = () => logout();
  }

  final ApiClient api;
  final FlutterSecureStorage _storage = const FlutterSecureStorage();
  static const String _tokenKey = 'fareshare_token';

  Map<String, dynamic>? user;

  bool get loggedIn => api.token != null;

  /// Read the saved token at app start (fast: no network call).
  Future<void> load() async {
    try {
      api.token = await _storage.read(key: _tokenKey);
    } catch (_) {
      api.token = null; // storage unavailable: behave as logged out
    }
  }

  Future<void> login(String email, String password) async {
    final res = await api.post('/auth/login', {'email': email, 'password': password});
    await _saveSession(res as Map<String, dynamic>);
  }

  Future<void> register({
    required String fullName,
    required String email,
    required String password,
    required String gender,
    String? phone,
  }) async {
    final res = await api.post('/auth/register', {
      'full_name': fullName,
      'email': email,
      'password': password,
      'gender': gender,
      if (phone != null && phone.isNotEmpty) 'phone': phone,
    });
    await _saveSession(res as Map<String, dynamic>);
  }

  Future<void> refreshUser() async {
    final res = await api.get('/me');
    user = Map<String, dynamic>.from(res as Map);
    notifyListeners();
  }

  Future<void> logout() async {
    api.token = null;
    user = null;
    try {
      await _storage.delete(key: _tokenKey);
    } catch (_) {}
    notifyListeners();
  }

  Future<void> _saveSession(Map<String, dynamic> res) async {
    api.token = res['token'] as String;
    user = Map<String, dynamic>.from(res['user'] as Map);
    try {
      await _storage.write(key: _tokenKey, value: api.token);
    } catch (_) {}
    notifyListeners(); // the router reacts and moves to Home
  }
}
