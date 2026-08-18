import { DarkTheme, DefaultTheme, ThemeProvider } from '@react-navigation/native';
import { Stack, router, useSegments } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { View } from 'react-native';
import 'react-native-reanimated';
import { SafeAreaProvider } from 'react-native-safe-area-context';

import { initializeApiBaseUrl } from '@/constants/config';
import { useColorScheme } from '@/hooks/use-color-scheme';
import { AuthProvider, useAuth } from '@/store/auth-context';

export const unstable_settings = {
  anchor: '(tabs)',
};

function AuthGate() {
  const { status } = useAuth();
  const segments = useSegments();

  useEffect(() => {
    if (__DEV__) console.log('[AuthGate] status=', status, 'segments=', segments);
    if (status === 'loading') return;
    const inAuthGroup = segments[0] === '(auth)';
    const sinRuta = segments.length === 0;

    if (status === 'guest' && !inAuthGroup) {
      if (__DEV__) console.log('[AuthGate] redirect -> /(auth)/login');
      router.replace('/(auth)/login');
    } else if (status === 'authenticated' && (inAuthGroup || sinRuta)) {
      if (__DEV__) console.log('[AuthGate] redirect -> /(tabs)');
      router.replace('/(tabs)');
    }
  }, [status, segments]);

  return null;
}

export default function RootLayout() {
  const colorScheme = useColorScheme();
  const [apiReady, setApiReady] = useState(false);

  useEffect(() => {
    // Carga el override de URL guardado (si existe) ANTES de montar el AuthProvider,
    // porque el AuthProvider hace authApi.perfil() apenas se monta.
    void initializeApiBaseUrl().finally(() => setApiReady(true));
  }, []);

  if (!apiReady) {
    return <View style={{ flex: 1, backgroundColor: '#0B3D91' }} />;
  }

  return (
    <SafeAreaProvider>
      <AuthProvider>
        <ThemeProvider value={colorScheme === 'dark' ? DarkTheme : DefaultTheme}>
          <AuthGate />
          <Stack>
            <Stack.Screen name="(auth)" options={{ headerShown: false }} />
            <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
            <Stack.Screen name="tramites/[id]" options={{ title: 'Detalle de expediente' }} />
            <Stack.Screen name="tramites/nuevo" options={{ title: 'Nuevo tramite' }} />
            <Stack.Screen name="turnos" options={{ headerShown: false }} />
            <Stack.Screen name="modal" options={{ presentation: 'modal', title: 'Modal' }} />
            <Stack.Screen
              name="chat"
              options={{ presentation: 'modal', headerShown: false }}
            />
          </Stack>
          <StatusBar style="light" />
        </ThemeProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}
