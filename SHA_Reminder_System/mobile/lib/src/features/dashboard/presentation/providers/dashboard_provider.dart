import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/user_api_service.dart';
import 'eligibility_provider.dart';

final dashboardDataProvider = FutureProvider<EligibilityState>((ref) async {
  final userApi = ref.watch(userApiServiceProvider);

  try {
    final data = await userApi.getEligibility();

    // Assuming backend returns something like:
    // { "status": "active", "next_payment_date": "2026-07-09T00:00:00", "amount": 300.0 }

    return EligibilityState(
      status: data['status'] == 'active'
          ? EligibilityStatus.active
          : EligibilityStatus.inactive,
      nextDueDate: DateTime.tryParse(data['next_payment_date'] ?? ''),
      contributionAmount: (data['amount'] ?? 300.0).toDouble(),
    );
  } catch (e) {
    // Return cached or default state if offline/error
    return EligibilityState(status: EligibilityStatus.pending);
  }
});
