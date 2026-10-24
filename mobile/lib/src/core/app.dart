import 'package:flutter/material.dart';
import '../features/dashboard/presentation/main_navigation_screen.dart';

class ShaPayApp extends StatelessWidget {
  const ShaPayApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'sha-pay',
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
