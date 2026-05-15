import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import {
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
  type TextInputProps,
} from 'react-native';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Props = TextInputProps & {
  label?: string;
  error?: string;
  hint?: string;
};

/**
 * Input con label, hint y borde adaptado al focus/error.
 *
 * Cuando se le pasa `secureTextEntry`, agrega automaticamente un boton de
 * "ojito" a la derecha que permite alternar la visibilidad del texto. El
 * estado del toggle es local — los consumidores siguen pasando solo
 * `secureTextEntry` y todo funciona.
 */
export function MuniInput({
  label,
  error,
  hint,
  style,
  onFocus,
  onBlur,
  secureTextEntry,
  ...rest
}: Props) {
  const [focused, setFocused] = useState(false);
  const [verPassword, setVerPassword] = useState(false);

  const esPassword = !!secureTextEntry;
  const ocultarTexto = esPassword && !verPassword;

  const borderColor = error
    ? MunicipalityColors.danger
    : focused
      ? MunicipalityColors.primary
      : MunicipalityColors.border;

  return (
    <View style={styles.wrapper}>
      {label ? <Text style={styles.label}>{label}</Text> : null}
      <View style={[styles.inputBox, { borderColor }]}>
        <TextInput
          {...rest}
          secureTextEntry={ocultarTexto}
          onFocus={(e) => {
            setFocused(true);
            onFocus?.(e);
          }}
          onBlur={(e) => {
            setFocused(false);
            onBlur?.(e);
          }}
          placeholderTextColor={MunicipalityColors.textMuted}
          style={[styles.input, esPassword && styles.inputWithEye, style]}
        />
        {esPassword ? (
          <Pressable
            onPress={() => setVerPassword((v) => !v)}
            hitSlop={8}
            style={({ pressed }) => [styles.eyeBtn, pressed && { opacity: 0.6 }]}
            accessibilityRole="button"
            accessibilityLabel={
              verPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'
            }>
            <MaterialCommunityIcons
              name={verPassword ? 'eye-off-outline' : 'eye-outline'}
              size={20}
              color={MunicipalityColors.textMuted}
            />
          </Pressable>
        ) : null}
      </View>
      {error ? (
        <Text style={styles.error}>{error}</Text>
      ) : hint ? (
        <Text style={styles.hint}>{hint}</Text>
      ) : null}
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
  inputBox: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: MunicipalityColors.white,
    borderWidth: 1,
    borderRadius: Radius.md,
  },
  input: {
    flex: 1,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    fontSize: 15,
    color: MunicipalityColors.textPrimary,
  },
  // Cuando hay ojito, dejamos menos padding a la derecha para el icono.
  inputWithEye: {
    paddingRight: Spacing.sm,
  },
  eyeBtn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hint: { fontSize: 12, color: MunicipalityColors.textMuted },
  error: { fontSize: 12, color: MunicipalityColors.danger },
});
