import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../data/penalty_api_service.dart';
import '../data/penalty_local_service.dart';

class PenaltyCalculationResult {
  final double totalPenalty;
  final double totalDue;
  final List<dynamic> breakdown;
  final bool isOffline;

  PenaltyCalculationResult({
    required this.totalPenalty,
    required this.totalDue,
    required this.breakdown,
    this.isOffline = false,
  });
}

class PenaltyRepository {
  final PenaltyApiService _apiService;
  final PenaltyLocalService _localService;

  PenaltyRepository(this._apiService, this._localService);

  Future<PenaltyCalculationResult> calculate({
    required int missedMonths,
    double monthlyContribution = 300.0,
  }) async {
    PenaltyCalculationResult result;
    try {
      final data = await _apiService.calculatePenalty(
        missedMonths: missedMonths,
        monthlyContribution: monthlyContribution,
      );

      result = PenaltyCalculationResult(
        totalPenalty: (data['penalty_amount'] ?? 0.0).toDouble(),
        totalDue: (data['total_amount_due'] ?? 0.0).toDouble(),
        breakdown: data['months_breakdown'] ?? [],
        isOffline: false,
      );
    } catch (e) {
      // Fallback to local calculation if API fails
      result = _calculateLocally(missedMonths, monthlyContribution);
    }

    // Save to local database for history/audit
    await _localService.saveCalculation(result, missedMonths, monthlyContribution);

    return result;
  }

  Future<List<PenaltyCalculationResult>> getHistory() async {
    return await _localService.getAllCalculations();
  }

  PenaltyCalculationResult _calculateLocally(int missedMonths, double monthlyAmount) {
    const rate = 0.02;
    double penaltySum = 0;
    List<Map<String, dynamic>> breakdown = [];

    for (int i = 1; i <= missedMonths; i++) {
      final monthPenalty = monthlyAmount * rate;
      penaltySum += monthPenalty;
      breakdown.add({
        'month_number': i,
        'penalty_applied': monthPenalty,
        'running_total': (monthlyAmount * i) + penaltySum,
      });
    }

    return PenaltyCalculationResult(
      totalPenalty: penaltySum,
      totalDue: (monthlyAmount * missedMonths) + penaltySum,
      breakdown: breakdown,
      isOffline: true,
    );
  }
}

final penaltyRepositoryProvider = Provider<PenaltyRepository>((ref) {
  final apiService = ref.watch(penaltyApiServiceProvider);
  final localService = ref.watch(penaltyLocalServiceProvider);
  return PenaltyRepository(apiService, localService);
});
