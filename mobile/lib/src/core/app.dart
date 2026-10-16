import 'package:flutter/material.dart';
import '../features/dashboard/presentation/main_navigation_screen.dart';

class SHAReminderApp extends StatelessWidget {
  const SHAReminderApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'SHA Reminder',
      debugShowCheckedModeBanner: false,
      theme: ThemeData(
        colorScheme: ColorScheme.fromSeed(
          seedColor: const Color(0xFF006D3E), // SHA Green
          primary: const Color(0xFF006D3E),
        ),
        useMaterial3: true,
        appBarTheme: const AppBarTheme(
          centerTitle: true,
          backgroundColor: Colors.white,
          elevation: 0,
        ),
      ),
      home: const MainNavigationScreen(),
    );
  }
}
