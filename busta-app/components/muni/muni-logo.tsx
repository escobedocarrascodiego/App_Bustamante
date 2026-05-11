import { Image, type ImageStyle, type StyleProp, View } from 'react-native';

import { staticImages } from '@/constants/assets';
import { MunicipalityColors } from '@/constants/theme';

type Props = {
  size?: number;
  /** Si true, muestra un marco circular (como el escudo del login). */
  circularFrame?: boolean;
  style?: StyleProp<ImageStyle>;
};

/**
 * Logo municipal desde `assets/static/logo.png`.
 */
export function MuniLogo({ size = 96, circularFrame, style }: Props) {
  const inner = (
    <Image
      accessibilityRole="image"
      accessibilityLabel="Logo de la municipalidad"
      source={staticImages.logo}
      style={[{ width: size, height: size, resizeMode: 'contain' }, style]}
    />
  );
  if (!circularFrame) {
    return inner;
  }
  const pad = 6;
  const innerSize = size - 8 - pad * 2;
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: MunicipalityColors.accent,
        alignItems: 'center',
        justifyContent: 'center',
        borderWidth: 4,
        borderColor: MunicipalityColors.white,
        overflow: 'hidden',
        padding: pad,
      }}>
      <Image
        accessibilityRole="image"
        accessibilityLabel="Logo de la municipalidad"
        source={staticImages.logo}
        style={[{ width: innerSize, height: innerSize, resizeMode: 'contain' }, style]}
      />
    </View>
  );
}
