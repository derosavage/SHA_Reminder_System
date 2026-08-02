// Basic smoke tests for the SHA Reminder Flutter app.

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:sha_reminder/src/features/dashboard/presentation/main_navigation_screen.dart';

void main() {
  testWidgets('Main navigation renders with 3 destinations',
      (WidgetTester tester) async {
    await tester.pumpWidget(
      const ProviderScope(
        child: MaterialApp(home: MainNavigationScreen()),
      ),
    );
    // Pump a few frames; do NOT use pumpAndSettle because the dashboard
    // fires an async network call via FutureProvider in tests.
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 100));

    final navBar = tester.widget<NavigationBar>(find.byType(NavigationBar));
    expect(navBar.destinations.length, 3);
    expect(find.text('Home'), findsOneWidget);
    expect(find.text('Calculator'), findsOneWidget);
    expect(find.text('History'), findsOneWidget);
  });
}
