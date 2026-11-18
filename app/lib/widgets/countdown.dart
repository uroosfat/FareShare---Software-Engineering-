import 'dart:async';

import 'package:flutter/material.dart';

/// Counts down to an ISO timestamp (mm:ss). Calls onDone once when it reaches zero.
class Countdown extends StatefulWidget {
  const Countdown({super.key, required this.expiresAt, this.onDone, this.prefix = ''});

  final String expiresAt;
  final VoidCallback? onDone;
  final String prefix;

  @override
  State<Countdown> createState() => _CountdownState();
}

class _CountdownState extends State<Countdown> {
  Timer? _timer;
  late Duration _left;
  bool _doneCalled = false;

  Duration _calc() => DateTime.parse(widget.expiresAt).difference(DateTime.now());

  @override
  void initState() {
    super.initState();
    _left = _calc();
    _timer = Timer.periodic(const Duration(seconds: 1), (_) {
      if (!mounted) return;
      final left = _calc();
      setState(() => _left = left);
      if (left <= Duration.zero && !_doneCalled) {
        _doneCalled = true;
        _timer?.cancel();
        widget.onDone?.call();
      }
    });
  }

  @override
  void didUpdateWidget(covariant Countdown oldWidget) {
    super.didUpdateWidget(oldWidget);
    if (oldWidget.expiresAt != widget.expiresAt) {
      _left = _calc();
      _doneCalled = false;
    }
  }

  @override
  void dispose() {
    _timer?.cancel();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    if (_left <= Duration.zero) return const Text('Expired');
    final m = _left.inMinutes.toString().padLeft(2, '0');
    final s = (_left.inSeconds % 60).toString().padLeft(2, '0');
    return Text('${widget.prefix}$m:$s');
  }
}
