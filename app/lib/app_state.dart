import 'api/api_client.dart';
import 'auth/auth_state.dart';

/// App-wide singletons (kept simple for Sprint 1).
final ApiClient api = ApiClient();
final AuthState auth = AuthState(api);
