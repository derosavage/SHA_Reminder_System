import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_secure_storage/flutter_secure_storage.dart';
import '../data/auth_api_service.dart';

class AuthRepository {
  final AuthApiService _apiService;
  final FlutterSecureStorage _storage;

  AuthRepository(this._apiService, this._storage);

  Future<void> login(String phoneNumber) async {
    await _apiService.login(phoneNumber);
  }

  Future<bool> verifyOtp({
    required String phoneNumber,
    required String otpCode,
    String? nationalId,
  }) async {
    final result = await _apiService.verifyOtp(
      phoneNumber: phoneNumber,
      otpCode: otpCode,
    );

    if (result['success'] == true) {
      final data = result['data'];
      await _storage.write(key: 'auth_token', value: data['access_token']);
      await _storage.write(key: 'user_id', value: data['user_id']);
      await _storage.write(key: 'phone_number', value: phoneNumber);
      if (nationalId != null) {
        await _storage.write(key: 'national_id', value: nationalId);
      }
      return true;
    }
    return false;
  }

  Future<String?> getStoredNationalId() async => await _storage.read(key: 'national_id');
  Future<String?> getStoredUserId() async => await _storage.read(key: 'user_id');
  Future<String?> getStoredPhoneNumber() async => await _storage.read(key: 'phone_number');

  Future<void> logout() async {
    await _storage.deleteAll();
  }

  Future<bool> isAuthenticated() async {
    final token = await _storage.read(key: 'auth_token');
    return token != null;
  }
}

final authRepositoryProvider = Provider<AuthRepository>((ref) {
  final apiService = ref.watch(authApiServiceProvider);
  const storage = FlutterSecureStorage();
  return AuthRepository(apiService, storage);
});
