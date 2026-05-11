import type { ImageSourcePropType } from 'react-native';

/**
 * Imágenes estáticas empaquetadas con la app.
 * Coloca archivos (p. ej. logo) en `assets/static/`.
 */
export const staticImages = {
  /** Logo institucional. Reemplaza `assets/static/logo.png` con tu diseño. */
  logo: require('../assets/static/logo.png') as ImageSourcePropType,
} as const;
