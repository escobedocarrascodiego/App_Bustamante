import { ActivityIndicator, Pressable, StyleSheet, Text, View, type ViewStyle } from 'react-native';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Variant = 'primary' | 'secondary' | 'accent' | 'ghost' | 'danger' | 'success';

type Props = {
  label: string;
  onPress?: () => void;
  variant?: Variant;
  loading?: boolean;
  disabled?: boolean;
  iconLeft?: React.ReactNode;
  iconRight?: React.ReactNode;
  style?: ViewStyle;
  fullWidth?: boolean;
};

export function MuniButton({
  label,
  onPress,
  variant = 'primary',
  loading,
  disabled,
  iconLeft,
  iconRight,
  style,
  fullWidth = true,
}: Props) {
  const isDisabled = disabled || loading;
  const palette = paletteFor(variant);

  return (
    <Pressable
      onPress={onPress}
      disabled={isDisabled}
      style={({ pressed }) => [
        styles.base,
        { backgroundColor: palette.background, borderColor: palette.border },
        fullWidth && styles.fullWidth,
        pressed && !isDisabled && { opacity: 0.85 },
        isDisabled && styles.disabled,
        style,
      ]}>
      <View style={styles.content}>
        {loading ? (
          <ActivityIndicator color={palette.label} />
        ) : (
          <>
            {iconLeft}
            <Text style={[styles.label, { color: palette.label }]}>{label}</Text>
            {iconRight}
          </>
        )}
      </View>
    </Pressable>
  );
}

function paletteFor(variant: Variant) {
  switch (variant) {
    case 'secondary':
      return {
        background: MunicipalityColors.white,
        border: MunicipalityColors.primary,
        label: MunicipalityColors.primary,
      };
    case 'accent':
      return {
        background: MunicipalityColors.accent,
        border: MunicipalityColors.accent,
        label: MunicipalityColors.primaryDark,
      };
    case 'ghost':
      return {
        background: 'transparent',
        border: 'transparent',
        label: MunicipalityColors.primary,
      };
    case 'danger':
      return {
        background: MunicipalityColors.danger,
        border: MunicipalityColors.danger,
        label: MunicipalityColors.white,
      };
    case 'success':
      return {
        background: MunicipalityColors.success,
        border: MunicipalityColors.success,
        label: MunicipalityColors.white,
      };
    default:
      return {
        background: MunicipalityColors.primary,
        border: MunicipalityColors.primary,
        label: MunicipalityColors.white,
      };
  }
}

const styles = StyleSheet.create({
  base: {
    borderRadius: Radius.md,
    paddingVertical: Spacing.md,
    paddingHorizontal: Spacing.lg,
    borderWidth: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  fullWidth: { alignSelf: 'stretch' },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
  },
  label: {
    fontSize: 16,
    fontWeight: '600',
    letterSpacing: 0.3,
  },
  disabled: { opacity: 0.55 },
});
