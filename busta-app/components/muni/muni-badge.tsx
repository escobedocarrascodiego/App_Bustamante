import { StyleSheet, Text, View } from 'react-native';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Tone = 'primary' | 'accent' | 'success' | 'warning' | 'danger' | 'neutral';

type Props = {
  label: string;
  tone?: Tone;
};

const PALETTE: Record<Tone, { bg: string; fg: string }> = {
  primary: { bg: '#E3EBFB', fg: MunicipalityColors.primary },
  accent: { bg: '#FDF3CE', fg: MunicipalityColors.accentDark },
  success: { bg: '#D1FAE5', fg: MunicipalityColors.success },
  warning: { bg: '#FEF3C7', fg: MunicipalityColors.warning },
  danger: { bg: '#FEE2E2', fg: MunicipalityColors.danger },
  neutral: { bg: '#E5E7EB', fg: MunicipalityColors.textSecondary },
};

export function MuniBadge({ label, tone = 'primary' }: Props) {
  const palette = PALETTE[tone];
  return (
    <View style={[styles.badge, { backgroundColor: palette.bg }]}>
      <Text style={[styles.label, { color: palette.fg }]}>{label}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  badge: {
    alignSelf: 'flex-start',
    paddingVertical: 4,
    paddingHorizontal: Spacing.sm,
    borderRadius: Radius.pill,
  },
  label: {
    fontSize: 12,
    fontWeight: '700',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
});
