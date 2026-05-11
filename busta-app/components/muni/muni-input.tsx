import { useState } from 'react';
import { StyleSheet, Text, TextInput, View, type TextInputProps } from 'react-native';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Props = TextInputProps & {
  label?: string;
  error?: string;
  hint?: string;
};

export function MuniInput({ label, error, hint, style, onFocus, onBlur, ...rest }: Props) {
  const [focused, setFocused] = useState(false);
  const borderColor = error
    ? MunicipalityColors.danger
    : focused
      ? MunicipalityColors.primary
      : MunicipalityColors.border;

  return (
    <View style={styles.wrapper}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <TextInput
        {...rest}
        onFocus={(e) => {
          setFocused(true);
          onFocus?.(e);
        }}
        onBlur={(e) => {
          setFocused(false);
          onBlur?.(e);
        }}
        placeholderTextColor={MunicipalityColors.textMuted}
        style={[styles.input, { borderColor }, style]}
      />
      {error ? <Text style={styles.error}>{error}</Text> : hint ? <Text style={styles.hint}>{hint}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  wrapper: { gap: 6 },
  label: {
    fontSize: 13,
    fontWeight: '600',
    color: MunicipalityColors.textSecondary,
  },
  input: {
    backgroundColor: MunicipalityColors.white,
    borderWidth: 1,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: 15,
    color: MunicipalityColors.textPrimary,
  },
  hint: { fontSize: 12, color: MunicipalityColors.textMuted },
  error: { fontSize: 12, color: MunicipalityColors.danger },
});
