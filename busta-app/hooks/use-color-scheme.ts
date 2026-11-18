import { useColorScheme as useRNColorScheme } from 'react-native';

/**
 * Devuelve siempre 'light' | 'dark'. El hook de React Native puede devolver
 * null (sin preferencia del sistema) o 'unspecified', y ninguno de los dos
 * sirve para indexar las paletas de `constants/theme`.
 */
export function useColorScheme(): 'light' | 'dark' {
  return useRNColorScheme() === 'dark' ? 'dark' : 'light';
}
