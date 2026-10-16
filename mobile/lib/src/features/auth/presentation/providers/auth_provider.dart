import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/auth_repository.dart';

enum AuthStatus { initial, loading, otpSent, authenticated, error }

class AuthState {
  final AuthStatus status;
  final String? errorMessage;
  final String? phoneNumber;
  final String? nationalId;

  AuthState({
    this.status = AuthStatus.initial,
    this.errorMessage,
    this.phoneNumber,
    this.nationalId,
  });

  AuthState copyWith({
    AuthStatus? status,
    String? errorMessage,
    String? phoneNumber,
    String? nationalId,
  }) {
    return AuthState(
      status: status ?? this.status,
      errorMessage: errorMessage ?? this.errorMessage,
      phoneNumber: phoneNumber ?? this.phoneNumber,
      nationalId: nationalId ?? this.nationalId,
    );
  }
}

class AuthNotifier extends StateNotifier<AuthState> {
  final AuthRepository _repository;

  AuthNotifier(this._repository) : super(AuthState());

  Future<void> sendOtp(String phone, String nationalId) async {
    state = state.copyWith(status: AuthStatus.loading);
    try {
      // For registration/login
      await _repository.login(phone);
      state = state.copyWith(
        status: AuthStatus.otpSent,
        phoneNumber: phone,
        nationalId: nationalId,
      );
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: e.toString(),
      );
    }
  }

  Future<bool> verifyOtp(String code) async {
    state = state.copyWith(status: AuthStatus.loading);
    try {
      final success = await _repository.verifyOtp(
        phoneNumber: state.phoneNumber!,
        otpCode: code,
        nationalId: state.nationalId,
      );
      
      if (success) {
        state = state.copyWith(status: AuthStatus.authenticated);
        return true;
      } else {
        state = state.copyWith(
          status: AuthStatus.error,
          errorMessage: 'Invalid OTP code',
        );
        return false;
      }
    } catch (e) {
      state = state.copyWith(
        status: AuthStatus.error,
        errorMessage: e.toString(),
      );
      return false;
    }
  }

  void reset() {
    state = AuthState();
  }
}

final authStateProvider = StateNotifierProvider<AuthNotifier, AuthState>((ref) {
  final repository = ref.watch(authRepositoryProvider);
  return AuthNotifier(repository);
});
