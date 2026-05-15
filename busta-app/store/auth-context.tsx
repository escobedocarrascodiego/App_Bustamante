import { createContext, useContext, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';

import { authApi } from '@/services/endpoints';
import { configureApi } from '@/services/api';
import { tokenStorage } from '@/services/storage';
import type { Ciudadano, DatosPersonalesOmitido } from '@/services/types';

type AuthStatus = 'loading' | 'authenticated' | 'guest';

type AuthContextValue = {
  status: AuthStatus;
  ciudadano: Ciudadano | null;
  login: (dni: string, password: string) => Promise<void>;
  register: (dni: string, password: string) => Promise<void>;
  registerOmitido: (
    dni: string,
    password: string,
    datosPersonales?: DatosPersonalesOmitido,
  ) => Promise<void>;
  verificarMpv: () => Promise<{ exito: boolean; mensaje: string }>;
  logout: () => Promise<void>;
  refreshPerfil: () => Promise<void>;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading');
  const [ciudadano, setCiudadano] = useState<Ciudadano | null>(null);
  const tokensRef = useRef<{ access: string | null; refresh: string | null }>({
    access: null,
    refresh: null,
  });

  useEffect(() => {
    configureApi({
      getAccess: () => tokensRef.current.access,
      getRefresh: () => tokensRef.current.refresh,
      setTokens: async (pair) => {
        tokensRef.current = pair;
        await tokenStorage.save(pair);
      },
      onUnauthorized: () => {
        tokensRef.current = { access: null, refresh: null };
        setCiudadano(null);
        setStatus('guest');
        void tokenStorage.clear();
      },
    });

    (async () => {
      const stored = await tokenStorage.load();
      if (stored.access && stored.refresh) {
        tokensRef.current = stored;
        try {
          const perfil = await authApi.perfil();
          setCiudadano(perfil);
          setStatus('authenticated');
          return;
        } catch {
          await tokenStorage.clear();
        }
      }
      setStatus('guest');
    })();
  }, []);

  const aplicarSesion = async (
    accion: 'login' | 'register',
    data: { access: string; refresh: string; ciudadano: Ciudadano },
  ) => {
    if (__DEV__) console.log(`[auth] ${accion} OK, ciudadano=`, data.ciudadano?.dni);
    tokensRef.current = { access: data.access, refresh: data.refresh };
    setCiudadano(data.ciudadano);
    setStatus('authenticated');
    try {
      await tokenStorage.save({ access: data.access, refresh: data.refresh });
    } catch (err) {
      if (__DEV__) console.warn('[auth] tokenStorage.save fallo:', err);
    }
  };

  const login = async (dni: string, password: string) => {
    const data = await authApi.login(dni, password);
    await aplicarSesion('login', data);
  };

  const register = async (dni: string, password: string) => {
    const data = await authApi.register(dni, password);
    await aplicarSesion('register', data);
  };

  const registerOmitido = async (
    dni: string,
    password: string,
    datosPersonales?: DatosPersonalesOmitido,
  ) => {
    const data = await authApi.registerOmitido(dni, password, datosPersonales);
    await aplicarSesion('register', data);
  };

  const verificarMpv = async (): Promise<{ exito: boolean; mensaje: string }> => {
    try {
      const data = await authApi.verificarMpv();
      // Refresca el ciudadano localmente (verificado=true si paso ok)
      setCiudadano(data.ciudadano);
      return { exito: data.mpv_registrado, mensaje: data.mensaje };
    } catch {
      return {
        exito: false,
        mensaje:
          'No pudimos verificar tu registro ahora mismo. Revisa tu conexion e intenta de nuevo.',
      };
    }
  };

  const logout = async () => {
    tokensRef.current = { access: null, refresh: null };
    await tokenStorage.clear();
    setCiudadano(null);
    setStatus('guest');
  };

  const refreshPerfil = async () => {
    try {
      const perfil = await authApi.perfil();
      setCiudadano(perfil);
    } catch {
      // silencioso
    }
  };

  const value = useMemo(
    () => ({
      status,
      ciudadano,
      login,
      register,
      registerOmitido,
      verificarMpv,
      logout,
      refreshPerfil,
    }),
    [status, ciudadano],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth debe usarse dentro de AuthProvider');
  return ctx;
}
