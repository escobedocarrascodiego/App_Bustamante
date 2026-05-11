/**
 * Tema institucional de la Municipalidad Distrital de Jose Luis Bustamante y Rivero.
 * Basado en los colores del escudo: azul institucional, amarillo/dorado y blanco.
 */

import { Platform } from 'react-native';

export const MunicipalityColors = {
  primary: '#0B3D91',        // Azul institucional
  primaryDark: '#072A66',
  primaryLight: '#2E5AB8',
  accent: '#F5B800',          // Amarillo/dorado del escudo
  accentDark: '#C28F00',
  white: '#FFFFFF',
  surface: '#F5F7FB',
  border: '#E2E8F0',
  textPrimary: '#1F2937',
  textSecondary: '#4B5563',
  textMuted: '#6B7280',
  success: '#15803D',
  warning: '#D97706',
  danger: '#B91C1C',
  info: '#0369A1',
} as const;

const tintColorLight = MunicipalityColors.primary;
const tintColorDark = MunicipalityColors.accent;

export const Colors = {
  light: {
    text: MunicipalityColors.textPrimary,
    background: MunicipalityColors.white,
    surface: MunicipalityColors.surface,
    tint: tintColorLight,
    icon: MunicipalityColors.textMuted,
    tabIconDefault: MunicipalityColors.textMuted,
    tabIconSelected: tintColorLight,
    border: MunicipalityColors.border,
  },
  dark: {
    text: '#ECEDEE',
    background: '#0B1220',
    surface: '#111827',
    tint: tintColorDark,
    icon: '#9BA1A6',
    tabIconDefault: '#9BA1A6',
    tabIconSelected: tintColorDark,
    border: '#1F2937',
  },
};

export const Spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
} as const;

export const Radius = {
  sm: 6,
  md: 10,
  lg: 14,
  xl: 20,
  pill: 999,
} as const;

export const Fonts = Platform.select({
  ios: {
    sans: 'system-ui',
    serif: 'ui-serif',
    rounded: 'ui-rounded',
    mono: 'ui-monospace',
  },
  default: {
    sans: 'normal',
    serif: 'serif',
    rounded: 'normal',
    mono: 'monospace',
  },
  web: {
    sans: "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif",
    serif: "Georgia, 'Times New Roman', serif",
    rounded: "'SF Pro Rounded', 'Hiragino Maru Gothic ProN', Meiryo, 'MS PGothic', sans-serif",
    mono: "SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace",
  },
});
