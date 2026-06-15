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

  Future<bool> verifyOtp(String phoneNumber, String otpCode) async {
    final result = await _apiService.verify_otp(
      phoneNumber: phoneNumber,
      otpCode: otpCode,
    );

    if (result['success'] == true) {
      final token = result['data']['access_token'];
      await _storage.write(key: 'auth_token', value: token);
      return true;
    }
    return false;
  }

  Future<void> logout() async {
    await _storage.delete(key: 'auth_token');
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
