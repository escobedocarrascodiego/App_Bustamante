import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { Platform } from 'react-native';

/**
 * Resolucion de la base URL de la API:
 *
 *   1. Override guardado en AsyncStorage (selector del menu oculto de devs).
 *   2. `extra.apiBaseUrl` en `app.json` (default del build).
 *   3. En Expo Go con celular fisico: extrae IP del Metro bundler.
 *   4. Fallback: emulador Android (10.0.2.2) / iOS / web (localhost).
 */
const API_PORT_FALLBACK = 8000;
const API_PATH = '/api/v1';

const STORAGE_KEY = 'jlbr.apiBaseUrl';

export type ApiEnvironmentId = 'dev-local' | 'server-lan' | 'server-public' | 'custom';

export type ApiEnvironment = {
  id: ApiEnvironmentId;
  label: string;
  description: string;
  url: string;
};

/**
 * Entornos predefinidos que se muestran en el selector del menu de desarrolladores.
 * `custom` se reserva para una URL escrita a mano.
 */
export const API_ENVIRONMENTS: readonly ApiEnvironment[] = [
  {
    id: 'dev-local',
    label: 'Dev local',
    description: 'PC del desarrollador en la misma red Wi-Fi.',
    url: 'http://192.168.5.154:8000/api/v1',
  },
  {
    id: 'server-lan',
    label: 'Server LAN',
    description: 'Servidor interno de la municipalidad.',
    url: 'http://10.0.0.4:8052/api/v1',
  },
  {
    id: 'server-public',
    label: 'Server publico',
    description: 'IP publica (recomendado para pruebas en celular con datos).',
    url: 'http://38.224.72.135:8052/api/v1',
  },
] as const;

function firstString(...candidates: unknown[]): string | null {
  for (const c of candidates) {
    if (typeof c === 'string' && c.length > 0) return c;
  }
  return null;
}

function resolveDefaultApiBase(): string {
  const fromExtra = firstString(Constants.expoConfig?.extra?.apiBaseUrl);
  if (fromExtra) return fromExtra;

  const hostUri = firstString(
    Constants.expoConfig?.hostUri,
    Constants.expoGoConfig?.debuggerHost,
  );

  if (hostUri) {
    const host = hostUri.split(':')[0];
    if (host && host !== 'localhost' && host !== '127.0.0.1') {
      return `http://${host}:${API_PORT_FALLBACK}${API_PATH}`;
    }
  }

  if (Platform.OS === 'android') return `http://10.0.2.2:${API_PORT_FALLBACK}${API_PATH}`;
  return `http://localhost:${API_PORT_FALLBACK}${API_PATH}`;
}

const DEFAULT_API_BASE_URL = resolveDefaultApiBase();

// Cache mutable en memoria. Los servicios siempre consultan via getApiBaseUrl()
// para que un cambio en runtime (selector del menu oculto) se propague.
let currentApiBaseUrl: string = DEFAULT_API_BASE_URL;

function normalizeUrl(raw: string): string {
  return raw.trim().replace(/\/+$/, '');
}

/**
 * Carga el override persistido (si existe) y actualiza el cache en memoria.
 * Llamar UNA vez al inicio de la app, antes de hacer requests.
 */
export async function initializeApiBaseUrl(): Promise<string> {
  try {
    const stored = await AsyncStorage.getItem(STORAGE_KEY);
    if (stored && stored.length > 0) {
      currentApiBaseUrl = normalizeUrl(stored);
    }
  } catch (err) {
    if (__DEV__) console.warn('[config] No se pudo leer apiBaseUrl override:', err);
  }
  if (__DEV__) console.log('[BustaApp] API_BASE_URL =', currentApiBaseUrl);
  return currentApiBaseUrl;
}

/** Base URL activa para `/api/v1`. */
export function getApiBaseUrl(): string {
  return currentApiBaseUrl;
}

/** Base URL del chatbot publico (`/api/chatbot`), derivada del API base. */
export function getChatbotBaseUrl(): string {
  return currentApiBaseUrl.replace(/\/api\/v1\/?$/, '/api/chatbot');
}

/** URL por defecto (segun `extra.apiBaseUrl` o el fallback). Solo informativa. */
export function getDefaultApiBaseUrl(): string {
  return DEFAULT_API_BASE_URL;
}

/**
 * Guarda y aplica una nueva URL como override.
 * El cambio queda en AsyncStorage y se refleja inmediatamente en `getApiBaseUrl()`.
 */
export async function setApiBaseUrlOverride(url: string): Promise<void> {
  const normalized = normalizeUrl(url);
  if (!normalized) throw new Error('La URL no puede estar vacia.');
  await AsyncStorage.setItem(STORAGE_KEY, normalized);
  currentApiBaseUrl = normalized;
  if (__DEV__) console.log('[BustaApp] API override aplicado:', currentApiBaseUrl);
}

/** Elimina el override y vuelve a la URL por defecto del build. */
export async function clearApiBaseUrlOverride(): Promise<void> {
  await AsyncStorage.removeItem(STORAGE_KEY);
  currentApiBaseUrl = DEFAULT_API_BASE_URL;
  if (__DEV__) console.log('[BustaApp] API override eliminado, default:', currentApiBaseUrl);
}

export const AppInfo = {
  name: 'Municipalidad JLBR',
  slogan: 'Distrito Jose Luis Bustamante y Rivero',
  soporte: 'tecnologiasinformacion@munibustamante.gob.pe',
};
