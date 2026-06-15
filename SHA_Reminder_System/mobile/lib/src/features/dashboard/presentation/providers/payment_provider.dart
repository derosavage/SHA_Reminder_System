import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../domain/payment_repository.dart';

enum PaymentStatus { initial, loading, success, error }

class PaymentState {
  final PaymentStatus status;
  final String? message;

  PaymentState({this.status = PaymentStatus.initial, this.message});

  PaymentState copyWith({PaymentStatus? status, String? message}) {
    return PaymentState(
      status: status ?? this.status,
      message: message ?? this.message,
    );
  }
}

class PaymentNotifier extends StateNotifier<PaymentState> {
  final PaymentRepository _repository;

  PaymentNotifier(this._repository) : super(PaymentState());

  Future<void> initiatePayment(double amount) async {
    state = state.copyWith(status: PaymentStatus.loading);
    try {
      final result = await _repository.paySha(amount);
      state = state.copyWith(
        status: PaymentStatus.success,
        message: result['message'] ?? 'Payment initiated successfully',
      );
    } catch (e) {
      state = state.copyWith(
        status: PaymentStatus.error,
        message: e.toString(),
      );
    }
  }

  void reset() {
    state = PaymentState();
  }
}

final paymentStateProvider = StateNotifierProvider<PaymentNotifier, PaymentState>((ref) {
  final repository = ref.watch(paymentRepositoryProvider);
  return PaymentNotifier(repository);
});
