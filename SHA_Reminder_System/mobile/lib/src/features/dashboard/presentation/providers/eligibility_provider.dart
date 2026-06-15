import 'package:flutter_riverpod/flutter_riverpod.dart';

enum EligibilityStatus { active, inactive, pending }

class EligibilityState {
  final EligibilityStatus status;
  final DateTime? nextDueDate;
  final double contributionAmount;

  EligibilityState({
    required this.status,
    this.nextDueDate,
    this.contributionAmount = 300.0,
  });
}

final eligibilityProvider = StateProvider<EligibilityState>((ref) {
  return EligibilityState(
    status: EligibilityStatus.active,
    nextDueDate: DateTime(2026, 7, 9),
  );
});
