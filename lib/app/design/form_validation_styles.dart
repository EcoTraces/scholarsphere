import 'package:flutter/material.dart';

/// Semantic colors for form-validation feedback, shared across every form in
/// the app so "met requirement," "approaching a limit," and "muted caption"
/// always read the same way regardless of which screen you're on.
///
/// [success] and [warning] are picked to hold >=4.5:1 contrast against a
/// white/near-white field background (WCAG AA for normal-size text), since
/// they label live text, not just decorative fills. Error state intentionally
/// reuses `Theme.of(context).colorScheme.error` rather than a constant here,
/// so it stays in sync with the app's single source of truth for error color.
class ValidationPalette {
  const ValidationPalette._();

  static const success = Color(0xFF2E7D32);
  static const warning = Color(0xFFB54708);
  static const muted = Color(0xFF98A2B3);
}

/// A "Fields marked * are required" caption, shown once per form so users
/// never have to guess which fields are optional.
class RequiredFieldsLegend extends StatelessWidget {
  const RequiredFieldsLegend({super.key});

  @override
  Widget build(BuildContext context) {
    final style = Theme.of(
      context,
    ).textTheme.bodySmall?.copyWith(color: ValidationPalette.muted);
    return Row(
      mainAxisSize: MainAxisSize.min,
      children: [
        const Icon(Icons.info_outline, size: 14, color: ValidationPalette.muted),
        const SizedBox(width: 6),
        Text('Fields marked * are required.', style: style),
      ],
    );
  }
}

/// Drop-in [TextField.buildCounter] / [TextFormField.buildCounter] that
/// replaces Flutter's default "12/100" with a plain-language count, and
/// escalates color as the limit approaches so the warning is visible before
/// someone hits a hard stop, not just at 0 characters left.
Widget? characterCounterBuilder(
  BuildContext context, {
  required int currentLength,
  required int? maxLength,
  required bool isFocused,
}) {
  if (maxLength == null || maxLength == 0) return null;
  final remaining = maxLength - currentLength;
  final ratio = currentLength / maxLength;
  final theme = Theme.of(context);
  final color = ratio >= 1
      ? theme.colorScheme.error
      : ratio >= 0.9
      ? ValidationPalette.warning
      : ValidationPalette.muted;
  return Text(
    '$remaining characters left',
    style: theme.textTheme.bodySmall?.copyWith(
      color: color,
      fontWeight: ratio >= 0.9 ? FontWeight.w600 : FontWeight.w400,
    ),
  );
}

/// One line of a live requirement checklist (e.g. a password rule). The icon
/// and label crossfade between "unmet" and "met" instead of snapping, so the
/// checkmark reads as a direct response to typing rather than a jump-cut.
class AnimatedRequirementRow extends StatelessWidget {
  const AnimatedRequirementRow({
    super.key,
    required this.label,
    required this.met,
  });

  final String label;
  final bool met;

  @override
  Widget build(BuildContext context) {
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    final duration = reduceMotion
        ? Duration.zero
        : const Duration(milliseconds: 180);
    final color = met ? ValidationPalette.success : ValidationPalette.muted;
    final bodySmall = Theme.of(context).textTheme.bodySmall ?? const TextStyle();
    return Padding(
      padding: const EdgeInsets.only(bottom: 4),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          AnimatedSwitcher(
            duration: duration,
            transitionBuilder: (child, animation) => ScaleTransition(
              scale: animation,
              child: FadeTransition(opacity: animation, child: child),
            ),
            child: Icon(
              met ? Icons.check_circle : Icons.radio_button_unchecked,
              key: ValueKey(met),
              size: 14,
              color: color,
            ),
          ),
          const SizedBox(width: 6),
          AnimatedDefaultTextStyle(
            duration: duration,
            style: bodySmall.copyWith(
              fontSize: 12,
              color: color,
              fontWeight: met ? FontWeight.w600 : FontWeight.w400,
            ),
            child: Text(label),
          ),
        ],
      ),
    );
  }
}

/// Summary bar above a requirement checklist ("3 of 5 met" + a fill that
/// tracks progress), so the state of the whole list is legible at a glance
/// instead of requiring the user to read every row.
class RequirementProgress extends StatelessWidget {
  const RequirementProgress({super.key, required this.met, required this.total});

  final int met;
  final int total;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    final reduceMotion = MediaQuery.of(context).disableAnimations;
    final ratio = total == 0 ? 0.0 : met / total;
    final complete = total > 0 && met == total;
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Row(
          mainAxisAlignment: MainAxisAlignment.spaceBetween,
          children: [
            Text(
              'Password strength',
              style: theme.textTheme.bodySmall?.copyWith(
                color: ValidationPalette.muted,
                fontWeight: FontWeight.w600,
              ),
            ),
            Text(
              '$met of $total met',
              style: theme.textTheme.bodySmall?.copyWith(
                color: complete ? ValidationPalette.success : ValidationPalette.muted,
                fontWeight: FontWeight.w600,
              ),
            ),
          ],
        ),
        const SizedBox(height: 6),
        ClipRRect(
          borderRadius: BorderRadius.circular(4),
          child: TweenAnimationBuilder<double>(
            tween: Tween(begin: 0, end: ratio),
            duration: reduceMotion
                ? Duration.zero
                : const Duration(milliseconds: 220),
            curve: Curves.easeOut,
            builder: (context, value, _) => LinearProgressIndicator(
              value: value,
              minHeight: 6,
              backgroundColor: const Color(0xFFE7EAF0),
              valueColor: AlwaysStoppedAnimation(
                complete ? ValidationPalette.success : theme.colorScheme.primary,
              ),
            ),
          ),
        ),
      ],
    );
  }
}

/// Small caption that appears under a disabled submit/save button explaining
/// *why* it's disabled, so "the button won't click" never becomes a mystery.
/// Reserves no space when hidden, and grows/shrinks smoothly when the form's
/// validity changes instead of causing a layout jump.
class SubmitBlockedHint extends StatelessWidget {
  const SubmitBlockedHint({
    super.key,
    required this.visible,
    required this.message,
  });

  final bool visible;
  final String message;

  @override
  Widget build(BuildContext context) {
    final theme = Theme.of(context);
    return AnimatedSize(
      duration: const Duration(milliseconds: 150),
      curve: Curves.easeOut,
      alignment: Alignment.topCenter,
      child: visible
          ? Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Row(
                mainAxisSize: MainAxisSize.min,
                children: [
                  const Icon(
                    Icons.info_outline,
                    size: 14,
                    color: ValidationPalette.muted,
                  ),
                  const SizedBox(width: 6),
                  Flexible(
                    child: Text(
                      message,
                      style: theme.textTheme.bodySmall?.copyWith(
                        color: ValidationPalette.muted,
                      ),
                    ),
                  ),
                ],
              ),
            )
          : const SizedBox.shrink(),
    );
  }
}
