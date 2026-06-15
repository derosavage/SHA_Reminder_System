import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

class AppLocalizations {
  final Locale locale;
  AppLocalizations(this.locale);

  static final Map<String, Map<String, String>> _localizedValues = {
    'en': {
      'app_title': 'SHA Reminder',
      'eligibility_status': 'Eligibility Status',
      'active': 'ACTIVE',
      'inactive': 'INACTIVE',
      'next_payment': 'Next Payment Due',
      'pay_sha': 'Pay SHA',
      'penalty_calc': 'Penalty\nCalculator',
      'history': 'Calculation\nHistory',
      'phone_label': 'Phone Number',
      'id_label': 'National ID Number',
      'login': 'Verify & Login',
      'send_otp': 'Send OTP',
      'calculate': 'Calculate',
      'total_due': 'Total Amount Due',
      'penalty': 'Total Penalty',
    },
    'sw': {
      'app_title': 'Kumbusho la SHA',
      'eligibility_status': 'Hali ya Kujiunga',
      'active': 'IMEIDHINISHWA',
      'inactive': 'HAIJAIDHINISHWA',
      'next_payment': 'Malipo Yanayofuata',
      'pay_sha': 'Lipa SHA',
      'penalty_calc': 'Kikokotoo cha\nAdhabu',
      'history': 'Historia ya\nMahesabu',
      'phone_label': 'Nambari ya Simu',
      'id_label': 'Nambari ya Kitambulisho',
      'login': 'Thibitisha na Ingia',
      'send_otp': 'Tuma OTP',
      'calculate': 'Hesabu',
      'total_due': 'Jumla ya Malipo',
      'penalty': 'Jumla ya Adhabu',
    },
  };

  String translate(String key) {
    return _localizedValues[locale.languageCode]?[key] ?? key;
  }
}

final localeProvider = StateProvider<Locale>((ref) => const Locale('en'));

final l10nProvider = Provider<AppLocalizations>((ref) {
  final locale = ref.watch(localeProvider);
  return AppLocalizations(locale);
});

extension AppLocalizationsExtension on BuildContext {
  String l10n(String key) => ProviderScope.containerOf(this).read(l10nProvider).translate(key);
}
