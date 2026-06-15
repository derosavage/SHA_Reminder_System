import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/payment_api_service.dart';
import '../../auth/domain/auth_repository.dart';

class PaymentRepository {
  final PaymentApiService _apiService;
  final AuthRepository _authRepository;

  PaymentRepository(this._apiService, this._authRepository);

  Future<Map<String, dynamic>> paySha(double amount) async {
    final phone = await _authRepository.getStoredUserId(); // Actually we need phone and ID
    // Note: In a real app, we'd store the phone number in secure storage too.
    // For now, let's assume we have it or get it from the user.
    
    // We'll use the stored National ID as the account reference
    final nationalId = await _authRepository.getStoredNationalId();
    
    // We need the phone number. Let's assume it's stored under 'phone_number'
    final phoneNumber = await _authRepository.getStoredUserId(); // Placeholder
    
    if (nationalId == null) {
      throw Exception('National ID not found. Please log in again.');
    }

    return await _apiService.initiateStkPush(
      phoneNumber: phoneNumber ?? '', // Should be retrieved from storage
      amount: amount,
      accountReference: nationalId,
    );
  }

  Future<List<dynamic>> getTransactions() async {
    final result = await _apiService.getPaymentHistory();
    if (result['success'] == true) {
      return result['data']['transactions'];
    }
    return [];
  }
}

final paymentRepositoryProvider = Provider<PaymentRepository>((ref) {
  final apiService = ref.watch(paymentApiServiceProvider);
  final authRepo = ref.watch(authRepositoryProvider);
  return PaymentRepository(apiService, authRepo);
});
