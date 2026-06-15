import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/payment_api_service.dart';
import '../../auth/domain/auth_repository.dart';

class PaymentRepository {
  final PaymentApiService _apiService;
  final AuthRepository _authRepository;

  PaymentRepository(this._apiService, this._authRepository);

  Future<Map<String, dynamic>> paySha(double amount) async {
    final nationalId = await _authRepository.getStoredNationalId();
    final phoneNumber = await _authRepository.getStoredPhoneNumber();
    
    if (nationalId == null || phoneNumber == null) {
      throw Exception('User details not found. Please log in again.');
    }

    return await _apiService.initiateStkPush(
      phoneNumber: phoneNumber,
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
