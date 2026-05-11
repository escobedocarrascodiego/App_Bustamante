import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import {
  KeyboardAvoidingView,
  Linking,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { MuniButton } from '@/components/muni/muni-button';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniInput } from '@/components/muni/muni-input';
import { MuniLogo } from '@/components/muni/muni-logo';
import { MuniVideoModal } from '@/components/muni/muni-video-modal';
import { API_BASE_URL, AppInfo } from '@/constants/config';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { VIDEO_REGISTRO_MPV } from '@/constants/videos';
import { ApiError } from '@/services/api';
import { authApi } from '@/services/endpoints';
import { useAuth } from '@/store/auth-context';
import type { CheckDniResponse } from '@/services/types';

type Estado =
  | { paso: 'DNI' }
  | { paso: 'PASSWORD_LOGIN'; check: CheckDniResponse }
  | { paso: 'PASSWORD_NUEVO'; check: CheckDniResponse }
  | { paso: 'BLOQUEADO'; check: CheckDniResponse };

export default function LoginScreen() {
  const { login, register } = useAuth();

  const [dni, setDni] = useState('');
  const [password, setPassword] = useState('');
  const [passwordConfirm, setPasswordConfirm] = useState('');
  const [estado, setEstado] = useState<Estado>({ paso: 'DNI' });
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [verVideo, setVerVideo] = useState(false);

  const reset = () => {
    setEstado({ paso: 'DNI' });
    setPassword('');
    setPasswordConfirm('');
    setError(null);
  };

  const continuarConDni = async () => {
    if (dni.trim().length < 8) {
      return setError('Ingresa tu DNI de 8 digitos.');
    }
    setError(null);
    setLoading(true);
    try {
      const check = await authApi.checkDni(dni.trim());
      if (check.paso === 'BLOQUEADO') {
        setEstado({ paso: 'BLOQUEADO', check });
      } else if (check.paso === 'PASSWORD_LOGIN') {
        setEstado({ paso: 'PASSWORD_LOGIN', check });
      } else if (check.paso === 'PASSWORD_NUEVO') {
        setEstado({ paso: 'PASSWORD_NUEVO', check });
      }
    } catch (err) {
      setError(parseError(err, 'No pudimos verificar tu DNI.'));
    } finally {
      setLoading(false);
    }
  };

  const ingresarConPassword = async () => {
    if (password.length < 1) {
      return setError('Ingresa tu contraseña.');
    }
    setError(null);
    setLoading(true);
    try {
      await login(dni.trim(), password);
    } catch (err) {
      setError(parseError(err, 'DNI o contraseña incorrectos.'));
    } finally {
      setLoading(false);
    }
  };

  const crearCuenta = async () => {
    if (password.length < 6) {
      return setError('La contraseña debe tener al menos 6 caracteres.');
    }
    if (password !== passwordConfirm) {
      return setError('Las contraseñas no coinciden.');
    }
    setError(null);
    setLoading(true);
    try {
      await register(dni.trim(), password);
    } catch (err) {
      setError(parseError(err, 'No pudimos crear tu cuenta.'));
    } finally {
      setLoading(false);
    }
  };

  const abrirMpv = async (link: string) => {
    const ok = await Linking.canOpenURL(link).catch(() => false);
    if (!ok) return;
    void Linking.openURL(link);
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <ScrollView
          contentContainerStyle={styles.container}
          keyboardShouldPersistTaps="handled">
          <View style={styles.brand}>
            <MuniLogo size={96} circularFrame />
            <Text style={styles.titulo}>Municipalidad Distrital</Text>
            <Text style={styles.subtitulo}>{AppInfo.slogan}</Text>
          </View>

          {estado.paso === 'DNI' ? (
            <MuniCard style={{ gap: Spacing.md }}>
              <Text style={styles.cardTitle}>Ingresa con tu DNI</Text>
              <Text style={styles.helper}>
                Verificaremos si ya tienes una cuenta o si necesitas crear una.
              </Text>
              <MuniInput
                label="DNI"
                keyboardType="number-pad"
                maxLength={8}
                value={dni}
                onChangeText={setDni}
                placeholder="Ej: 12345678"
                autoCapitalize="none"
                autoFocus
              />
              {error ? <Text style={styles.error}>{error}</Text> : null}
              <MuniButton
                label="Continuar"
                onPress={continuarConDni}
                loading={loading}
              />
            </MuniCard>
          ) : null}

          {estado.paso === 'PASSWORD_LOGIN' || estado.paso === 'PASSWORD_NUEVO' ? (
            <MuniCard style={{ gap: Spacing.md }}>
              <Pressable onPress={reset} style={styles.backRow} hitSlop={8}>
                <MaterialCommunityIcons
                  name="chevron-left"
                  size={18}
                  color={MunicipalityColors.primary}
                />
                <Text style={styles.backText}>Cambiar DNI</Text>
              </Pressable>

              <View style={styles.welcomeRow}>
                <View style={styles.avatar}>
                  <MaterialCommunityIcons
                    name="account-circle"
                    size={32}
                    color={MunicipalityColors.primary}
                  />
                </View>
                <View style={{ flex: 1 }}>
                  <Text style={styles.welcomeName}>
                    Hola, {(estado.check.nombre ?? 'ciudadano').toUpperCase()}
                  </Text>
                  {estado.check.email_enmascarado ? (
                    <Text style={styles.welcomeEmail}>
                      Correo: {estado.check.email_enmascarado}
                    </Text>
                  ) : null}
                </View>
              </View>

              <Text style={styles.cardTitle}>
                {estado.paso === 'PASSWORD_LOGIN'
                  ? 'Ingresa tu contraseña'
                  : 'Crea tu contraseña'}
              </Text>
              <Text style={styles.helper}>{estado.check.mensaje}</Text>

              <MuniInput
                label="Contraseña"
                secureTextEntry
                value={password}
                onChangeText={setPassword}
                placeholder="••••••••"
                autoCapitalize="none"
                autoFocus
              />

              {estado.paso === 'PASSWORD_NUEVO' ? (
                <MuniInput
                  label="Confirmar contraseña"
                  secureTextEntry
                  value={passwordConfirm}
                  onChangeText={setPasswordConfirm}
                  placeholder="••••••••"
                  autoCapitalize="none"
                />
              ) : null}

              {error ? <Text style={styles.error}>{error}</Text> : null}

              <MuniButton
                label={estado.paso === 'PASSWORD_LOGIN' ? 'Ingresar' : 'Crear cuenta'}
                onPress={
                  estado.paso === 'PASSWORD_LOGIN'
                    ? ingresarConPassword
                    : crearCuenta
                }
                loading={loading}
              />
            </MuniCard>
          ) : null}

          {estado.paso === 'BLOQUEADO' ? (
            <MuniCard style={{ gap: Spacing.md, alignItems: 'center' }}>
              <View style={styles.lockBox}>
                <MaterialCommunityIcons
                  name="shield-lock-outline"
                  size={48}
                  color={MunicipalityColors.primary}
                />
              </View>
              <Text style={styles.cardTitle}>Necesitas registrarte primero</Text>
              <Text style={[styles.helper, { textAlign: 'center' }]}>
                {estado.check.mensaje}
              </Text>
              <View style={styles.linkBox}>
                <MaterialCommunityIcons
                  name="link-variant"
                  size={14}
                  color={MunicipalityColors.primary}
                />
                <Text style={styles.linkText} numberOfLines={2}>
                  {estado.check.link_registro}
                </Text>
              </View>
              <View style={{ width: '100%', gap: Spacing.sm }}>
                <MuniButton
                  label="Ver tutorial en video"
                  variant="secondary"
                  onPress={() => setVerVideo(true)}
                  iconLeft={
                    <MaterialCommunityIcons
                      name="play-circle-outline"
                      size={18}
                      color={MunicipalityColors.primary}
                    />
                  }
                />
                <MuniButton
                  label="Ir al portal de registro"
                  variant="primary"
                  onPress={() => abrirMpv(estado.check.link_registro)}
                  iconLeft={
                    <MaterialCommunityIcons
                      name="open-in-new"
                      size={18}
                      color={MunicipalityColors.white}
                    />
                  }
                />
                <MuniButton label="Volver" variant="ghost" onPress={reset} />
              </View>
              <Text style={styles.note}>
                Una vez completes el registro en MPV, vuelve y vuelve a ingresar
                tu DNI.
              </Text>
            </MuniCard>
          ) : null}

          {__DEV__ ? <Text style={styles.demo}>API: {API_BASE_URL}</Text> : null}
        </ScrollView>
      </KeyboardAvoidingView>

      <MuniVideoModal
        visible={verVideo}
        videoId={VIDEO_REGISTRO_MPV.videoId}
        titulo={VIDEO_REGISTRO_MPV.titulo}
        descripcion={VIDEO_REGISTRO_MPV.descripcion}
        onClose={() => setVerVideo(false)}
      />
    </SafeAreaView>
  );
}

function parseError(err: unknown, fallback: string): string {
  if (err instanceof ApiError) {
    const data = err.data as { non_field_errors?: string[]; detail?: string };
    return data?.non_field_errors?.[0] ?? data?.detail ?? fallback;
  }
  return 'No se pudo conectar al servidor.';
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: MunicipalityColors.primary },
  container: {
    flexGrow: 1,
    padding: Spacing.lg,
    gap: Spacing.xl,
    justifyContent: 'center',
  },
  brand: { alignItems: 'center', gap: Spacing.sm },
  titulo: {
    color: MunicipalityColors.white,
    fontSize: 22,
    fontWeight: '700',
    marginTop: Spacing.sm,
  },
  subtitulo: {
    color: MunicipalityColors.accent,
    fontSize: 14,
    fontWeight: '500',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: '700',
    color: MunicipalityColors.primary,
  },
  helper: {
    color: MunicipalityColors.textMuted,
    fontSize: 12,
    lineHeight: 16,
  },
  error: {
    color: MunicipalityColors.danger,
    fontSize: 13,
  },
  demo: {
    color: MunicipalityColors.white,
    textAlign: 'center',
    fontSize: 12,
    opacity: 0.8,
  },
  backRow: {
    flexDirection: 'row',
    alignItems: 'center',
    alignSelf: 'flex-start',
    gap: 2,
  },
  backText: {
    color: MunicipalityColors.primary,
    fontWeight: '700',
    fontSize: 13,
  },
  welcomeRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: '#EEF2FF',
    borderRadius: Radius.md,
    padding: Spacing.sm,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: MunicipalityColors.white,
    alignItems: 'center',
    justifyContent: 'center',
  },
  welcomeName: {
    fontSize: 13,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
  },
  welcomeEmail: {
    fontSize: 11,
    color: MunicipalityColors.textSecondary,
    marginTop: 2,
  },
  lockBox: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  linkBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#F8FAFC',
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    width: '100%',
  },
  linkText: {
    flex: 1,
    fontSize: 11,
    color: MunicipalityColors.primary,
    fontWeight: '600',
  },
  note: {
    fontSize: 11,
    color: MunicipalityColors.textMuted,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});
