import 'package:flutter_riverpod/flutter_riverpod.dart';

enum Environment { dev, staging, prod }

class AppConfig {
  final String baseUrl;
  final String appName;
  final bool debugMode;

  AppConfig({
    required this.baseUrl,
    required this.appName,
    this.debugMode = false,
  });
}

final environmentProvider = Provider<Environment>((ref) {
  // Change this to switch environments
  return Environment.dev;
});

final appConfigProvider = Provider<AppConfig>((ref) {
  final env = ref.watch(environmentProvider);
  
  switch (env) {
    case Environment.prod:
      return AppConfig(
        baseUrl: 'https://api.sha-reminder.ke/api/v1',
        appName: 'SHA Reminder',
      );
    case Environment.staging:
      return AppConfig(
        baseUrl: 'https://staging-api.sha-reminder.ke/api/v1',
        appName: 'SHA Reminder (Staging)',
        debugMode: true,
      );
    case Environment.dev:
    default:
      return AppConfig(
        baseUrl: 'http://192.168.1.5:8000/api/v1',
        appName: 'SHA Dev',
        debugMode: true,
      );
  }
});
