import { Platform } from 'react-native';

/**
 * Almacenamiento de tokens con fallback en memoria.
 * En produccion instalar `expo-secure-store` (movil) y `@react-native-async-storage/async-storage` (web).
 *   npx expo install expo-secure-store @react-native-async-storage/async-storage
 * Mientras no esten instalados, los tokens persisten solo durante la sesion del app.
 */

type Store = {
  getItem: (k: string) => Promise<string | null>;
  setItem: (k: string, v: string) => Promise<void>;
  removeItem: (k: string) => Promise<void>;
};

function createMemoryStore(): Store {
  const map = new Map<string, string>();
  return {
    getItem: async (k) => map.get(k) ?? null,
    setItem: async (k, v) => void map.set(k, v),
    removeItem: async (k) => void map.delete(k),
  };
}

function loadNative(): Store | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const SecureStore = require('expo-secure-store');
    return {
      getItem: (k) => SecureStore.getItemAsync(k),
      setItem: (k, v) => SecureStore.setItemAsync(k, v),
      removeItem: (k) => SecureStore.deleteItemAsync(k),
    };
  } catch {
    return null;
  }
}

function loadWeb(): Store | null {
  try {
    // eslint-disable-next-line @typescript-eslint/no-require-imports
    const AsyncStorage = require('@react-native-async-storage/async-storage').default;
    return {
      getItem: (k) => AsyncStorage.getItem(k),
      setItem: (k, v) => AsyncStorage.setItem(k, v),
      removeItem: (k) => AsyncStorage.removeItem(k),
    };
  } catch {
    if (typeof window !== 'undefined' && window.localStorage) {
      return {
        getItem: async (k) => window.localStorage.getItem(k),
        setItem: async (k, v) => window.localStorage.setItem(k, v),
        removeItem: async (k) => window.localStorage.removeItem(k),
      };
    }
    return null;
  }
}

const store: Store =
  (Platform.OS === 'web' ? loadWeb() : loadNative()) ?? createMemoryStore();

export const tokenStorage = {
  async load() {
    const [access, refresh] = await Promise.all([
      store.getItem('jlbr.access'),
      store.getItem('jlbr.refresh'),
    ]);
    return { access, refresh };
  },
  async save(tokens: { access: string; refresh: string }) {
    await Promise.all([
      store.setItem('jlbr.access', tokens.access),
      store.setItem('jlbr.refresh', tokens.refresh),
    ]);
  },
  async updateAccess(access: string) {
    await store.setItem('jlbr.access', access);
  },
  async clear() {
    await Promise.all([
      store.removeItem('jlbr.access'),
      store.removeItem('jlbr.refresh'),
    ]);
  },
};
