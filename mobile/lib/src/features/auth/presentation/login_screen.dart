import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import '../../../core/localization/app_localizations.dart';
import '../../../core/utils/validators.dart';
import '../../dashboard/presentation/main_navigation_screen.dart';
import 'providers/auth_provider.dart';

class LoginScreen extends ConsumerStatefulWidget {
  const LoginScreen({super.key});

  @override
  ConsumerState<LoginScreen> createState() => _LoginScreenState();
}

class _LoginScreenState extends ConsumerState<LoginScreen> {
  final _formKey = GlobalKey<FormState>();
  final _phoneController = TextEditingController();
  final _idController = TextEditingController();
  final _otpController = TextEditingController();

  @override
  void dispose() {
    _phoneController.dispose();
    _idController.dispose();
    _otpController.dispose();
    super.dispose();
  }

  void _onSendOtp() {
    if (_formKey.currentState!.validate()) {
      ref.read(authStateProvider.notifier).sendOtp(
            _phoneController.text,
            _idController.text,
          );
    }
  }

  void _onVerifyOtp() async {
    if (_otpController.text.length == 6) {
      final success = await ref.read(authStateProvider.notifier).verifyOtp(_otpController.text);
      if (success && mounted) {
        Navigator.pushReplacement(
          context,
          MaterialPageRoute(builder: (_) => const MainNavigationScreen()),
        );
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    final l10n = ref.watch(l10nProvider);
    final currentLocale = ref.watch(localeProvider);
    final authState = ref.watch(authStateProvider);

    return Scaffold(
      appBar: AppBar(
        actions: [
          TextButton(
            onPressed: () {
              ref.read(localeProvider.notifier).state =
                  currentLocale.languageCode == 'en' ? const Locale('sw') : const Locale('en');
            },
            child: Text(currentLocale.languageCode == 'en' ? 'Swahili' : 'English'),
          ),
        ],
      ),
      body: SafeArea(
        child: SingleChildScrollView(
          padding: const EdgeInsets.all(24.0),
          child: Form(
            key: _formKey,
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              children: [
                const SizedBox(height: 20),
                const Icon(Icons.security, size: 80, color: Color(0xFF006D3E)),
                const SizedBox(height: 24),
                Text(
                  l10n.translate('app_title'),
                  textAlign: TextAlign.center,
                  style: const TextStyle(fontSize: 24, fontWeight: FontWeight.bold),
                ),
                const SizedBox(height: 48),
                if (authState.status != AuthStatus.otpSent) ...[
                  TextFormField(
                    controller: _phoneController,
                    keyboardType: TextInputType.phone,
                    enabled: authState.status != AuthStatus.loading,
                    decoration: InputDecoration(
                      labelText: l10n.translate('phone_label'),
                      prefixText: '+254 ',
                      border: const OutlineInputBorder(),
                    ),
                    validator: Validators.validatePhone,
                  ),
                  const SizedBox(height: 16),
                  TextFormField(
                    controller: _idController,
                    keyboardType: TextInputType.number,
                    enabled: authState.status != AuthStatus.loading,
                    decoration: InputDecoration(
                      labelText: l10n.translate('id_label'),
                      border: const OutlineInputBorder(),
                    ),
                    validator: Validators.validateNationalId,
                  ),
                  const SizedBox(height: 24),
                  if (authState.errorMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(
                        authState.errorMessage!,
                        style: const TextStyle(color: Colors.red, fontSize: 13),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ElevatedButton(
                    onPressed: authState.status == AuthStatus.loading ? null : _onSendOtp,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF006D3E),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: authState.status == AuthStatus.loading
                        ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Text(l10n.translate('send_otp')),
                  ),
                ] else ...[
                  const Text(
                    'Enter the 6-digit code sent to your phone',
                    textAlign: TextAlign.center,
                  ),
                  const SizedBox(height: 24),
                  TextField(
                    controller: _otpController,
                    textAlign: TextAlign.center,
                    keyboardType: TextInputType.number,
                    maxLength: 6,
                    decoration: const InputDecoration(
                      letterSpacing: 8,
                      border: OutlineInputBorder(),
                    ),
                    onChanged: (value) {
                      if (value.length == 6) _onVerifyOtp();
                    },
                  ),
                  const SizedBox(height: 24),
                  if (authState.errorMessage != null)
                    Padding(
                      padding: const EdgeInsets.only(bottom: 16),
                      child: Text(
                        authState.errorMessage!,
                        style: const TextStyle(color: Colors.red, fontSize: 13),
                        textAlign: TextAlign.center,
                      ),
                    ),
                  ElevatedButton(
                    onPressed: authState.status == AuthStatus.loading ? null : _onVerifyOtp,
                    style: ElevatedButton.styleFrom(
                      backgroundColor: const Color(0xFF006D3E),
                      foregroundColor: Colors.white,
                      padding: const EdgeInsets.symmetric(vertical: 16),
                      shape: RoundedRectangleBorder(borderRadius: BorderRadius.circular(8)),
                    ),
                    child: authState.status == AuthStatus.loading
                        ? const SizedBox(height: 20, width: 20, child: CircularProgressIndicator(color: Colors.white, strokeWidth: 2))
                        : Text(l10n.translate('login')),
                  ),
                  TextButton(
                    onPressed: authState.status == AuthStatus.loading
                        ? null
                        : () => ref.read(authStateProvider.notifier).reset(),
                    child: const Text('Change Details'),
                  ),
                ],
              ],
            ),
          ),
        ),
      ),
    );
  }
}
