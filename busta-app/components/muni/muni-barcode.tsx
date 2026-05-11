import { useMemo } from 'react';
import { StyleSheet, Text, View } from 'react-native';

import { MunicipalityColors } from '@/constants/theme';

type Props = {
  value: string;
  height?: number;
  background?: string;
  bar?: string;
  showText?: boolean;
};

/**
 * Codigo de barras Code 128 (subset C) escaneable.
 * Codifica el DNI del contribuyente en pares de digitos. Renderiza cada
 * modulo como un View con flex, asi el barcode estira al ancho disponible
 * conservando las proporciones exactas exigidas por la norma Code 128.
 */
export function MuniBarcode({
  value,
  height = 60,
  background = '#FFFFFF',
  bar = '#111111',
  showText = true,
}: Props) {
  const { bars, human } = useMemo(() => buildBars(value), [value]);

  return (
    <View>
      <View style={[styles.wrap, { height, backgroundColor: background }]}>
        {bars.map((b, idx) => (
          <View
            key={idx}
            style={{
              flex: b.weight,
              backgroundColor: b.filled ? bar : background,
            }}
          />
        ))}
      </View>
      {showText && human ? <Text style={styles.text}>{human}</Text> : null}
    </View>
  );
}

type Bar = { weight: number; filled: boolean };

function buildBars(raw: string): { bars: Bar[]; human: string } {
  const digits = (raw || '').replace(/\D/g, '');
  if (!digits) return { bars: [], human: '' };

  const padded = digits.length % 2 === 0 ? digits : '0' + digits;

  // START C = 105
  const values: number[] = [105];
  for (let i = 0; i < padded.length; i += 2) {
    values.push(parseInt(padded.substring(i, i + 2), 10));
  }

  // Checksum = (start + sum(pos * value)) % 103
  let sum = values[0];
  for (let i = 1; i < values.length; i++) sum += values[i] * i;
  values.push(sum % 103);

  // STOP pattern (106) tiene 7 widths.
  values.push(106);

  const bars: Bar[] = [];
  bars.push({ weight: 10, filled: false }); // quiet zone

  for (const v of values) {
    const pattern = CODE128_PATTERNS[v];
    for (let i = 0; i < pattern.length; i++) {
      bars.push({ weight: pattern[i], filled: i % 2 === 0 });
    }
  }

  bars.push({ weight: 10, filled: false }); // quiet zone final
  return { bars, human: padded };
}

const styles = StyleSheet.create({
  wrap: {
    flexDirection: 'row',
    alignItems: 'stretch',
  },
  text: {
    textAlign: 'center',
    fontSize: 11,
    letterSpacing: 2,
    color: MunicipalityColors.textPrimary,
    marginTop: 4,
    fontFamily: 'monospace',
    fontWeight: '600',
  },
});

// Tabla oficial Code 128 (valores 0..106). Los valores 0..102 son data,
// 103/104/105 son START A/B/C y 106 es STOP (7 widths, el resto 6).
const CODE128_PATTERNS: number[][] = [
  [2, 1, 2, 2, 2, 2], [2, 2, 2, 1, 2, 2], [2, 2, 2, 2, 2, 1], [1, 2, 1, 2, 2, 3],
  [1, 2, 1, 3, 2, 2], [1, 3, 1, 2, 2, 2], [1, 2, 2, 2, 1, 3], [1, 2, 2, 3, 1, 2],
  [1, 3, 2, 2, 1, 2], [2, 2, 1, 2, 1, 3], [2, 2, 1, 3, 1, 2], [2, 3, 1, 2, 1, 2],
  [1, 1, 2, 2, 3, 2], [1, 2, 2, 1, 3, 2], [1, 2, 2, 2, 3, 1], [1, 1, 3, 2, 2, 2],
  [1, 2, 3, 1, 2, 2], [1, 2, 3, 2, 2, 1], [2, 2, 3, 2, 1, 1], [2, 2, 1, 1, 3, 2],
  [2, 2, 1, 2, 3, 1], [2, 1, 3, 2, 1, 2], [2, 2, 3, 1, 1, 2], [3, 1, 2, 1, 3, 1],
  [3, 1, 1, 2, 2, 2], [3, 2, 1, 1, 2, 2], [3, 2, 1, 2, 2, 1], [3, 1, 2, 2, 1, 2],
  [3, 2, 2, 1, 1, 2], [3, 2, 2, 2, 1, 1], [2, 1, 2, 1, 2, 3], [2, 1, 2, 3, 2, 1],
  [2, 3, 2, 1, 2, 1], [1, 1, 1, 3, 2, 3], [1, 3, 1, 1, 2, 3], [1, 3, 1, 3, 2, 1],
  [1, 1, 2, 3, 1, 3], [1, 3, 2, 1, 1, 3], [1, 3, 2, 3, 1, 1], [2, 1, 1, 3, 1, 3],
  [2, 3, 1, 1, 1, 3], [2, 3, 1, 3, 1, 1], [1, 1, 2, 1, 3, 3], [1, 1, 2, 3, 3, 1],
  [1, 3, 2, 1, 3, 1], [1, 1, 3, 1, 2, 3], [1, 1, 3, 3, 2, 1], [1, 3, 3, 1, 2, 1],
  [3, 1, 3, 1, 2, 1], [2, 1, 1, 3, 3, 1], [2, 3, 1, 1, 3, 1], [2, 1, 3, 1, 1, 3],
  [2, 1, 3, 3, 1, 1], [2, 1, 3, 1, 3, 1], [3, 1, 1, 1, 2, 3], [3, 1, 1, 3, 2, 1],
  [3, 3, 1, 1, 2, 1], [3, 1, 2, 1, 1, 3], [3, 1, 2, 3, 1, 1], [3, 3, 2, 1, 1, 1],
  [3, 1, 4, 1, 1, 1], [2, 2, 1, 4, 1, 1], [4, 3, 1, 1, 1, 1], [1, 1, 1, 2, 2, 4],
  [1, 1, 1, 4, 2, 2], [1, 2, 1, 1, 2, 4], [1, 2, 1, 4, 2, 1], [1, 4, 1, 1, 2, 2],
  [1, 4, 1, 2, 2, 1], [1, 1, 2, 2, 1, 4], [1, 1, 2, 4, 1, 2], [1, 2, 2, 1, 1, 4],
  [1, 2, 2, 4, 1, 1], [1, 4, 2, 1, 1, 2], [1, 4, 2, 2, 1, 1], [2, 4, 1, 2, 1, 1],
  [2, 2, 1, 1, 1, 4], [4, 1, 3, 1, 1, 1], [2, 4, 1, 1, 1, 2], [1, 3, 4, 1, 1, 1],
  [1, 1, 1, 2, 4, 2], [1, 2, 1, 1, 4, 2], [1, 2, 1, 2, 4, 1], [1, 1, 4, 2, 1, 2],
  [1, 2, 4, 1, 1, 2], [1, 2, 4, 2, 1, 1], [4, 1, 1, 2, 1, 2], [4, 2, 1, 1, 1, 2],
  [4, 2, 1, 2, 1, 1], [2, 1, 2, 1, 4, 1], [2, 1, 4, 1, 2, 1], [4, 1, 2, 1, 2, 1],
  [1, 1, 1, 1, 4, 3], [1, 1, 1, 3, 4, 1], [1, 3, 1, 1, 4, 1], [1, 1, 4, 1, 1, 3],
  [1, 1, 4, 3, 1, 1], [4, 1, 1, 1, 1, 3], [4, 1, 1, 3, 1, 1], [1, 1, 3, 1, 4, 1],
  [1, 1, 4, 1, 3, 1], [3, 1, 1, 1, 4, 1], [4, 1, 1, 1, 3, 1], [2, 1, 1, 4, 1, 2],
  [2, 1, 1, 2, 1, 4], [2, 1, 1, 2, 3, 2], [2, 3, 3, 1, 1, 1, 2],
];
