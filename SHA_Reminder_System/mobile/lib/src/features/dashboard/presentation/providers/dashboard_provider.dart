import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../data/user_api_service.dart';
import 'eligibility_provider.dart';

final dashboardDataProvider = FutureProvider<EligibilityState>((ref) async {
  final userApi = ref.watch(userApiServiceProvider);

  try {
    final response = await userApi.getEligibility();

    // Backend GET /users/eligibility returns:
    // {
    //   "success": true,
    //   "data": {
    //     "eligibility_status": "active" | "inactive",
    //     "is_eligible": bool,
    //     "last_payment_date": "...",
    //     "months_since_last_payment": 0,
    //     "next_payment_due": "2026-06-09",
    //     "contribution_amount": 300.0,
    //     "paybill": "200222",
    //     "account_reference": "12345678"
    //   }
    // }
    final data = (response['data'] is Map<String, dynamic>)
        ? response['data'] as Map<String, dynamic>
        : response;

    final status = data['eligibility_status'] ?? 'inactive';
    final nextPaymentDue = data['next_payment_due'] as String?;
    final amount = (data['contribution_amount'] as num?)?.toDouble() ?? 300.0;

    return EligibilityState(
      status: status == 'active'
          ? EligibilityStatus.active
          : EligibilityStatus.inactive,
      nextDueDate: DateTime.tryParse(nextPaymentDue ?? ''),
      contributionAmount: amount,
    );
  } catch (e) {
    // Return cached or default state if offline/error
    return EligibilityState(status: EligibilityStatus.pending);
  }
});
