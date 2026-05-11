import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Base URL de la API de la municipalidad.
 *
 * Resolucion:
 *   1. `extra.apiBaseUrl` en `app.json` si esta definido (produccion / staging).
 *   2. En Expo Go con celular fisico: extrae IP del Metro bundler.
 *   3. Fallback: emulador Android (10.0.2.2) / iOS / web (localhost).
 */
const API_PORT = 8000;
const API_PATH = '/api/v1';

function firstString(...candidates: unknown[]): string | null {
  for (const c of candidates) {
    if (typeof c === 'string' && c.length > 0) return c;
  }
  return null;
}

function resolveApiBase(): string {
  const fromExtra = firstString(Constants.expoConfig?.extra?.apiBaseUrl);
  if (fromExtra) return fromExtra;

  // Orden de prioridad para encontrar la IP del host de Expo Go.
  const hostUri = firstString(
    Constants.expoConfig?.hostUri,
    Constants.expoGoConfig?.debuggerHost,
  );

  if (hostUri) {
    const host = hostUri.split(':')[0];
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return `http://${host}:${API_PORT}${API_PATH}`;
    }
  }

  if (Platform.OS === 'android') return `http://10.0.2.2:${API_PORT}${API_PATH}`;
  return `http://localhost:${API_PORT}${API_PATH}`;
}

export const API_BASE_URL = resolveApiBase();

export const AppInfo = {
  name: 'Municipalidad JLBR',
  slogan: 'Distrito Jose Luis Bustamante y Rivero',
  soporte: 'tecnologiasinformacion@munibustamante.gob.pe',
};

if (__DEV__) {
  // eslint-disable-next-line no-console
  console.log('[BustaApp] API_BASE_URL =', API_BASE_URL);
}
