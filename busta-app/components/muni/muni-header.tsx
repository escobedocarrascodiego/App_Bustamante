import { StyleSheet, Text, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { MunicipalityColors, Spacing } from '@/constants/theme';

type Props = {
  title: string;
  subtitle?: string;
  right?: React.ReactNode;
};

export function MuniHeader({ title, subtitle, right }: Props) {
  return (
    <SafeAreaView edges={['top']} style={styles.safe}>
      <View style={styles.content}>
        <View style={{ flex: 1 }}>
          <Text style={styles.title}>{title}</Text>
          {subtitle ? <Text style={styles.subtitle}>{subtitle}</Text> : null}
        </View>
        {right}
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { backgroundColor: MunicipalityColors.primary },
  content: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.lg,
    gap: Spacing.md,
  },
  title: {
    color: MunicipalityColors.white,
    fontSize: 20,
    fontWeight: '700',
  },
  subtitle: {
    color: MunicipalityColors.accent,
    fontSize: 13,
    marginTop: 2,
    fontWeight: '500',
  },
});
