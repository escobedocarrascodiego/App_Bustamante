import { StyleSheet, View, type ViewProps } from 'react-native';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Props = ViewProps & {
  padded?: boolean;
  elevated?: boolean;
};

export function MuniCard({ padded = true, elevated = true, style, children, ...rest }: Props) {
  return (
    <View
      {...rest}
      style={[
        styles.card,
        padded && styles.padded,
        elevated && styles.elevated,
        style,
      ]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
  },
  padded: { padding: Spacing.lg },
  elevated: {
    shadowColor: '#000',
    shadowOpacity: 0.06,
    shadowRadius: 10,
    shadowOffset: { width: 0, height: 3 },
    elevation: 2,
  },
});
