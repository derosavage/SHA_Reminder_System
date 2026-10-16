import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/penalty_repository.dart';

final penaltyHistoryProvider = FutureProvider<List<PenaltyCalculationResult>>((ref) async {
  final repo = ref.watch(penaltyRepositoryProvider);
  return await repo.getHistory();
});

class PenaltyHistoryScreen extends ConsumerWidget {
  const PenaltyHistoryScreen({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final historyAsync = ref.watch(penaltyHistoryProvider);

    return Scaffold(
      appBar: AppBar(
        title: const Text('Calculation History'),
      ),
      body: historyAsync.when(
        data: (history) => history.isEmpty
            ? const Center(child: Text('No history found'))
            : ListView.builder(
                itemCount: history.length,
                itemBuilder: (context, index) {
                  final item = history[index];
                  return Card(
                    margin: const EdgeInsets.symmetric(horizontal: 16, vertical: 8),
                    child: ListTile(
                      title: Text('Total Due: KES ${item.totalDue.toStringAsFixed(2)}'),
                      subtitle: Text(
                        'Penalty: KES ${item.totalPenalty.toStringAsFixed(2)} • '
                        '${item.isOffline ? "Offline" : "Synced"}',
                      ),
                      trailing: const Icon(Icons.chevron_right),
                      onTap: () {
                        // Could show details
                      },
                    ),
                  );
                },
              ),
        loading: () => const Center(child: CircularProgressIndicator()),
        error: (err, stack) => Center(child: Text('Error: $err')),
      ),
    );
  }
}
