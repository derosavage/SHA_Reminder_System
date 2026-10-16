import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:intl/intl.dart';
import '../../../core/utils/validators.dart';
import '../../../core/localization/app_localizations.dart';
import '../../penalty/presentation/penalty_calculator_screen.dart';
import '../../penalty/presentation/penalty_history_screen.dart';
import 'providers/dashboard_provider.dart';
import 'providers/eligibility_provider.dart';
import 'providers/payment_provider.dart';

class DashboardScreen extends ConsumerWidget {
  const DashboardScreen({super.key});

  void _showPaymentSheet(BuildContext context, WidgetRef ref) {
    final amountController = TextEditingController(text: '300');
    final formKey = GlobalKey<FormState>();
    final l10n = ref.read(l10nProvider);

    showModalBottomSheet(
      context: context,
      isScrollControlled: true,
      shape: const RoundedRectangleBorder(
        borderRadius: BorderRadius.vertical(top: Radius.circular(20)),
      ),
      builder: (context) => Padding(
        padding: EdgeInsets.only(
          bottom: MediaQuery.of(context).viewInsets.bottom,
          left: 20,
          right: 20,
          top: 20,
        ),
        child: Form(
          key: formKey,
          child: Column(
            mainAxisSize: MainAxisSize.min,
            crossAxisAlignment: CrossAxisAlignment.stretch,
            children: [
              Text(
                l10n.translate('pay_sha'),
                style: const TextStyle(fontSize: 20, fontWeight: FontWeight.bold),
                textAlign: TextAlign.center,
              ),
              const SizedBox(height: 20),
              TextFormField(
                controller: amountController,
                keyboardType: TextInputType.number,
                decoration: const InputDecoration(
                  labelText: 'Amount (KES)',
                  border: OutlineInputBorder(),
                  prefixText: 'KES ',
                ),
                validator: Validators.validateAmount,
              ),
              const SizedBox(height: 24),
              Consumer(
                builder: (context, ref, _) {
                  final state = ref.watch(paymentStateProvider);
                  
                  if (state.status == PaymentStatus.success) {
                    return Column(
                      children: [
                        const Icon(Icons.check_circle, color: Colors.green, size: 48),
                        const SizedBox(height: 8),
                        Text(state.message ?? '', textAlign: TextAlign.center),
                        const SizedBox(height: 16),
                        ElevatedButton(
                          onPressed: () {
                            ref.read(paymentStateProvider.notifier).reset();
                            Navigator.pop(context);
                          },
                          child: const Text('Close'),
                        ),
                      ],
                    );
                  }

                  return ElevatedButton(
                    onPressed: state.status == PaymentStatus.loading
                        ? null
                        : () {
                            if (formKey.currentState!.validate()) {
                              final amount = double.parse(amountController.text);
                              ref.read(paymentStateProvider.notifier).initiatePayment(amount);
                            }
                          },
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF006D3E),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: state.status == PaymentStatus.loading
                        ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Text(l10n.translate('pay_sha')),
                  );
                },
              ),
              const SizedBox(height: 20),
            ],
          ),
        ),
      ),
    );
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final dashboardAsync = ref.watch(dashboardDataProvider);
    final l10n = ref.watch(l10nProvider);

    return Scaffold(
      appBar: AppBar(
        title: Text(l10n.translate('app_title')),
        actions: [
          IconButton(
            icon: const Icon(Icons.person_outline),
            onPressed: () {},
          ),
        ],
      ),
      body: RefreshIndicator(
        onRefresh: () => ref.refresh(dashboardDataProvider.future),
        child: dashboardAsync.when(
          data: (state) => _buildContent(context, state, ref),
          loading: () => const Center(child: CircularProgressIndicator()),
          error: (err, stack) => Center(
            child: Column(
              mainAxisAlignment: MainAxisAlignment.center,
              children: [
                const Icon(Icons.error_outline, size: 48, color: Colors.red),
                const SizedBox(height: 16),
                Text('Error: $err'),
                ElevatedButton(
                  onPressed: () => ref.refresh(dashboardDataProvider),
                  child: const Text('Retry'),
                ),
              ],
            ),
          ),
        ),
      ),
      floatingActionButton: FloatingActionButton.extended(
        onPressed: () => _showPaymentSheet(context, ref),
        label: Text(l10n.translate('pay_sha')),
        icon: const Icon(Icons.payment),
      ),
    );
  }

  Widget _buildContent(BuildContext context, EligibilityState state, WidgetRef ref) {
    final l10n = ref.watch(l10nProvider);
    return SingleChildScrollView(
      physics: const AlwaysScrollableScrollPhysics(),
      padding: const EdgeInsets.all(16.0),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          _buildEligibilityCard(context, state, l10n),
          const SizedBox(height: 24),
          const Text(
            'Quick Actions',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 16),
          _buildActionGrid(context, l10n),
          const SizedBox(height: 24),
          const Text(
            'Recent Transactions',
            style: TextStyle(fontSize: 18, fontWeight: FontWeight.bold),
          ),
          const SizedBox(height: 12),
          _buildEmptyTransactions(),
        ],
      ),
    );
  }

  Widget _buildEligibilityCard(BuildContext context, EligibilityState state, AppLocalizations l10n) {
    final statusColor = state.status == EligibilityStatus.active ? Colors.green : Colors.red;
    
    return Card(
      elevation: 0,
      color: Theme.of(context).colorScheme.primaryContainer,
      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(16)),
      child: Padding(
        padding: const EdgeInsets.all(20.0),
        child: Column(
          children: [
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(
                      l10n.translate('eligibility_status'),
                      style: const TextStyle(fontSize: 14, color: Colors.black54),
                    ),
                    const SizedBox(height: 4),
                    Text(
                      l10n.translate(state.status.name),
                      style: TextStyle(
                        fontSize: 24,
                        fontWeight: FontWeight.bold,
                        color: statusColor,
                      ),
                    ),
                  ],
                ),
                Container(
                  padding: const EdgeInsets.all(8),
                  decoration: BoxDecoration(
                    color: statusColor.withOpacity(0.1),
                    shape: BoxShape.circle,
                  ),
                  child: Icon(
                    state.status == EligibilityStatus.active ? Icons.check_circle : Icons.error,
                    color: statusColor,
                    size: 32,
                  ),
                ),
              ],
            ),
            const Divider(height: 32),
            Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(l10n.translate('next_payment') + ':'),
                Text(
                  state.nextDueDate != null 
                      ? DateFormat('dd MMMM yyyy').format(state.nextDueDate!)
                      : 'N/A',
                  style: const TextStyle(fontWeight: FontWeight.bold),
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildActionGrid(BuildContext context, AppLocalizations l10n) {
    return GridView.count(
      shrinkWrap: true,
      physics: const NeverScrollableScrollPhysics(),
      crossAxisCount: 2,
      mainAxisSpacing: 16,
      crossAxisSpacing: 16,
      childAspectRatio: 1.5,
      children: [
        _buildActionCard(
          context,
          l10n.translate('penalty_calc'),
          Icons.calculate_outlined,
          Colors.orange,
          () {
            Navigator.push(
              context,
              MaterialPageRoute(builder: (_) => const PenaltyCalculatorScreen()),
            );
          },
        ),
        _buildActionCard(
          context,
          l10n.translate('history'),
          Icons.history,
          Colors.blue,
          () => Navigator.push(
            context,
            MaterialPageRoute(builder: (_) => const PenaltyHistoryScreen()),
          ),
        ),
        _buildActionCard(
          context,
          'Help &\nGuidance',
          Icons.help_outline,
          Colors.purple,
          () {},
        ),
        _buildActionCard(
          context,
          'Notifications',
          Icons.notifications_none,
          Colors.red,
          () {},
        ),
      ],
    );
  }

  Widget _buildActionCard(
    BuildContext context,
    String title,
    IconData icon,
    Color color,
    VoidCallback onTap,
  ) {
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.all(16),
        decoration: BoxDecoration(
          border: Border.all(color: Colors.grey.shade200),
          borderRadius: BorderRadius.circular(12),
        ),
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Icon(icon, color: color),
            Text(
              title,
              style: const TextStyle(fontWeight: FontWeight.w600, fontSize: 13),
            ),
          ],
        ),
      ),
    );
  }

  Widget _buildEmptyTransactions() {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 40),
      width: double.infinity,
      decoration: BoxDecoration(
        color: Colors.grey.shade50,
        borderRadius: BorderRadius.circular(12),
      ),
      child: Column(
        children: [
          Icon(Icons.receipt_long, size: 48, color: Colors.grey.shade300),
          const SizedBox(height: 12),
          Text(
            'No recent payments found',
            style: TextStyle(color: Colors.grey.shade600),
          ),
        ],
      ),
    );
  }
}
