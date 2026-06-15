import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../domain/penalty_repository.dart';

class PenaltyCalculatorScreen extends ConsumerStatefulWidget {
  const PenaltyCalculatorScreen({super.key});

  @override
  ConsumerState<PenaltyCalculatorScreen> createState() => _PenaltyCalculatorScreenState();
}

class _PenaltyCalculatorScreenState extends ConsumerState<PenaltyCalculatorScreen> {
  final _monthsController = TextEditingController();
  final _amountController = TextEditingController(text: '300');

  bool _isLoading = false;
  PenaltyCalculationResult? _result;

  Future<void> _calculate() async {
    final missedMonths = int.tryParse(_monthsController.text) ?? 0;
    final monthlyAmount = double.tryParse(_amountController.text) ?? 300.0;

    if (missedMonths <= 0) {
      setState(() => _result = null);
      return;
    }

    setState(() => _isLoading = true);

    try {
      final repo = ref.read(penaltyRepositoryProvider);
      final result = await repo.calculate(
        missedMonths: missedMonths,
        monthlyContribution: monthlyAmount,
      );
      setState(() => _result = result);
    } catch (e) {
      if (mounted) {
        ScaffoldMessenger.of(context).showSnackBar(
          SnackBar(content: Text('Error: $e')),
        );
      }
    } finally {
      if (mounted) {
        setState(() => _isLoading = false);
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('Penalty Calculator'),
      ),
      body: SingleChildScrollView(
        padding: const EdgeInsets.all(16.0),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            const Text(
              'Estimate your SHA late payment penalties.',
              style: TextStyle(color: Colors.grey),
            ),
            const SizedBox(height: 24),
            TextField(
              controller: _monthsController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Number of Missed Months',
                border: OutlineInputBorder(),
                hintText: 'e.g. 3',
              ),
              onChanged: (_) => _calculate(),
            ),
            const SizedBox(height: 16),
            TextField(
              controller: _amountController,
              keyboardType: TextInputType.number,
              decoration: const InputDecoration(
                labelText: 'Monthly Contribution (KES)',
                border: OutlineInputBorder(),
                prefixText: 'KES ',
              ),
              onChanged: (_) => _calculate(),
            ),
            const SizedBox(height: 32),
            if (_isLoading)
              const Center(child: CircularProgressIndicator())
            else if (_result != null) ...[
              if (_result!.isOffline)
                const Padding(
                  padding: EdgeInsets.only(bottom: 16),
                  child: Row(
                    children: [
                      Icon(Icons.cloud_off, size: 16, color: Colors.orange),
                      SizedBox(width: 8),
                      Text(
                        'Using offline calculator (Estimated)',
                        style: TextStyle(color: Colors.orange, fontSize: 12),
                      ),
                    ],
                  ),
                ),
              _buildResultCard(),
              const SizedBox(height: 24),
              const Text(
                'Breakdown',
                style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
              ),
              const SizedBox(height: 12),
              _buildBreakdownList(),
            ],
          ],
        ),
      ),
    );
  }

  Widget _buildResultCard() {
    return Container(
      padding: const EdgeInsets.all(20),
      decoration: BoxDecoration(
        color: Colors.orange.shade50,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: Colors.orange.shade200),
      ),
      child: Column(
        children: [
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Total Penalty:'),
              Text(
                'KES ${_result!.totalPenalty.toStringAsFixed(2)}',
                style: const TextStyle(fontWeight: FontWeight.bold, color: Colors.red),
              ),
            ],
          ),
          const SizedBox(height: 8),
          Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              const Text('Total Amount Due:', style: TextStyle(fontSize: 16)),
              Text(
                'KES ${_result!.totalDue.toStringAsFixed(2)}',
                style: const TextStyle(
                  fontSize: 20,
                  fontWeight: FontWeight.bold,
                  color: Color(0xFF006D3E),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }

  Widget _buildBreakdownList() {
    return ListView.separated(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      itemCount: _result!.breakdown.length,
      separatorBuilder: (_, __) => const Divider(),
      itemBuilder: (context, index) {
        final item = _result!.breakdown[index];
        final monthNum = item['month_number'] ?? item['month'];
        final penalty = (item['penalty_applied'] ?? item['penalty']).toDouble();

        return ListTile(
          contentPadding: EdgeInsets.zero,
          leading: CircleAvatar(
            backgroundColor: Colors.grey.shade200,
            child: Text('$monthNum'),
          ),
          title: Text('Month $monthNum Contribution'),
          subtitle: Text('Penalty: KES ${penalty.toStringAsFixed(2)}'),
          trailing: Text(
            'KES ${(double.tryParse(_amountController.text) ?? 300 + penalty).toStringAsFixed(2)}',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
        );
      },
    );
  }
}
