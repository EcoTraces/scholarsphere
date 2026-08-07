import 'experience_preferences.dart';

abstract final class LocalizedFormatter {
  static String date(DateTime value, ExperiencePreferences preferences) {
    final day = value.day.toString().padLeft(2, '0');
    final month = value.month.toString().padLeft(2, '0');
    final year = value.year;
    return preferences.countryCode.toUpperCase() == 'US'
        ? '$month/$day/$year'
        : '$day/$month/$year';
  }

  static String currency(num value, ExperiencePreferences preferences) {
    final symbols = {'USD': r'$', 'EUR': 'EUR ', 'GBP': 'GBP ', 'GHS': 'GHS '};
    final code = preferences.currencyCode.toUpperCase();
    return '${symbols[code] ?? '$code '}${value.toStringAsFixed(2)}';
  }

  static DateTime applyTimezoneOffset(DateTime utc, String timezone) {
    final match = RegExp(r'^UTC([+-])(\d{1,2})$').firstMatch(timezone);
    if (match == null) return utc.toUtc();
    final hours = int.parse(match.group(2)!);
    return match.group(1) == '+'
        ? utc.toUtc().add(Duration(hours: hours))
        : utc.toUtc().subtract(Duration(hours: hours));
  }
}
