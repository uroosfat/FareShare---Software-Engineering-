import 'dart:convert';

import 'package:http/http.dart' as http;

import '../config.dart';

class ApiException implements Exception {
  ApiException(this.statusCode, this.message);
  final int statusCode; // 0 = could not reach the server
  final String message;

  @override
  String toString() => message;
}

/// Thin wrapper around http: adds the base URL, the login token and readable errors.
class ApiClient {
  String? token;

  /// Called when the server says the token is no longer valid (HTTP 401 while logged in).
  void Function()? onUnauthorized;

  Uri _uri(String path, [Map<String, String>? query]) {
    final clean = <String, String>{};
    query?.forEach((k, v) {
      if (v.trim().isNotEmpty) clean[k] = v.trim();
    });
    return Uri.parse('$apiBaseUrl$path').replace(queryParameters: clean.isEmpty ? null : clean);
  }

  Map<String, String> get _headers => {
        'Content-Type': 'application/json',
        if (token != null) 'Authorization': 'Bearer $token',
      };

  Future<dynamic> _send(Future<http.Response> Function() call) async {
    late http.Response res;
    try {
      // The free server sleeps when idle; the first call can take up to a minute.
      res = await call().timeout(const Duration(seconds: 90));
    } on Exception {
      throw ApiException(0, 'Could not reach the server. Check your internet and try again.');
    }
    dynamic body;
    if (res.body.isNotEmpty) {
      try {
        body = jsonDecode(utf8.decode(res.bodyBytes));
      } catch (_) {
        body = null;
      }
    }
    if (res.statusCode >= 200 && res.statusCode < 300) return body;

    if (res.statusCode == 401 && token != null) onUnauthorized?.call();
    throw ApiException(res.statusCode, _errorText(body, res.statusCode));
  }

  String _errorText(dynamic body, int code) {
    if (body is Map && body['detail'] != null) {
      final d = body['detail'];
      if (d is String) return d;
      if (d is List && d.isNotEmpty && d.first is Map) {
        final first = d.first as Map;
        final field = (first['loc'] is List && (first['loc'] as List).length > 1)
            ? '${(first['loc'] as List).last}: '
            : '';
        return '$field${first['msg']}';
      }
    }
    return 'Something went wrong (error $code).';
  }

  Future<dynamic> get(String path, {Map<String, String>? query}) =>
      _send(() => http.get(_uri(path, query), headers: _headers));

  Future<dynamic> post(String path, [Map<String, dynamic>? body]) =>
      _send(() => http.post(_uri(path), headers: _headers, body: jsonEncode(body ?? {})));

  Future<dynamic> put(String path, Map<String, dynamic> body) =>
      _send(() => http.put(_uri(path), headers: _headers, body: jsonEncode(body)));

  Future<dynamic> delete(String path) =>
      _send(() => http.delete(_uri(path), headers: _headers));
}
