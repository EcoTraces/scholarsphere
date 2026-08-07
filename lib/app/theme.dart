import 'package:flutter/material.dart';

ThemeData buildScholarSphereTheme({bool highContrast = false}) {
  const ink = Color(0xFF14213D);
  const teal = Color(0xFF007C72);
  final canvas = highContrast ? Colors.white : const Color(0xFFF7F8FA);

  final scheme =
      ColorScheme.fromSeed(
        seedColor: teal,
        brightness: Brightness.light,
        surface: Colors.white,
      ).copyWith(
        primary: highContrast ? Colors.black : teal,
        onPrimary: Colors.white,
        secondary: highContrast
            ? const Color(0xFF7A3E00)
            : const Color(0xFFE09F3E),
      );

  return ThemeData(
    useMaterial3: true,
    colorScheme: scheme,
    scaffoldBackgroundColor: canvas,
    fontFamily: 'Arial',
    textTheme: const TextTheme(
      headlineLarge: TextStyle(
        color: ink,
        fontSize: 32,
        fontWeight: FontWeight.w700,
      ),
      headlineSmall: TextStyle(
        color: ink,
        fontSize: 22,
        fontWeight: FontWeight.w700,
      ),
      titleLarge: TextStyle(
        color: ink,
        fontSize: 18,
        fontWeight: FontWeight.w700,
      ),
      bodyLarge: TextStyle(color: Color(0xFF344054), height: 1.45),
      bodyMedium: TextStyle(color: Color(0xFF596579), height: 1.4),
    ),
    inputDecorationTheme: InputDecorationTheme(
      filled: true,
      fillColor: Colors.white,
      border: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFFD8DEE8)),
      ),
      enabledBorder: OutlineInputBorder(
        borderRadius: BorderRadius.circular(8),
        borderSide: const BorderSide(color: Color(0xFFD8DEE8)),
      ),
    ),
    cardTheme: CardThemeData(
      margin: EdgeInsets.zero,
      color: Colors.white,
      elevation: 0,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(8),
        side: const BorderSide(color: Color(0xFFE1E6ED)),
      ),
    ),
  );
}
