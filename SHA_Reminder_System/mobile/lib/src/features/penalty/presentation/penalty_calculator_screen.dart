import 'package:flutter/material.dart';

class PenaltyCalculatorScreen extends StatefulWidget {
  const PenaltyCalculatorScreen({super.key});

  @override
  State<PenaltyCalculatorScreen> createState() => _PenaltyCalculatorScreenState();
}

class _PenaltyCalculatorScreenState extends State<PenaltyCalculatorScreen> {
  final _monthsController = TextEditingController();
  final _amountController = TextEditingController(text: '300');

  double _totalPenalty = 0;
  double _totalDue = 0;
  List<Map<String, dynamic>> _breakdown = [];

  void _calculate() {
    final missedMonths = int.tryParse(_monthsController.text) ?? 0;
    final monthlyAmount = double.tryParse(_amountController.text) ?? 300.0;

    if (missedMonths <= 0) return;

    const rate = 0.02; // 2%
    double penaltySum = 0;
    List<Map<String, dynamic>> tempBreakdown = [];

    for (int i = 1; i <= missedMonths; i++) {
      final monthPenalty = monthlyAmount * rate;
      penaltySum += monthPenalty;

      tempBreakdown.add({
        'month': i,
        'penalty': monthPenalty,
        'running_total': (monthlyAmount * i) + (monthPenalty * i), // Simplified for demo
      });
    }

    setState(() {
      _totalPenalty = penaltySum;
      _totalDue = (monthlyAmount * missedMonths) + penaltySum;
      _breakdown = tempBreakdown;
    });
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
            if (_totalDue > 0) ...[
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
                'KES ${_totalPenalty.toStringAsFixed(2)}',
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
                'KES ${_totalDue.toStringAsFixed(2)}',
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
      itemCount: _breakdown.length,
      separatorBuilder: (_, __) => const Divider(),
      itemBuilder: (context, index) {
        final item = _breakdown[index];
        return ListTile(
          contentPadding: EdgeInsets.zero,
          leading: CircleAvatar(
            backgroundColor: Colors.grey.shade200,
            child: Text('${item['month']}'),
          ),
          title: Text('Month ${item['month']} Contribution'),
          subtitle: Text('Penalty: KES ${item['penalty'].toStringAsFixed(2)}'),
          trailing: Text(
            'KES ${(double.tryParse(_amountController.text) ?? 300 + item['penalty']).toStringAsFixed(2)}',
            style: const TextStyle(fontWeight: FontWeight.w500),
          ),
        );
      },
    );
  }
}
