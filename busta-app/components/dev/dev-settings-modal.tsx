import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useEffect, useMemo, useState } from 'react';
import {
  Alert,
  KeyboardAvoidingView,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { MuniButton } from '@/components/muni/muni-button';
import { MuniInput } from '@/components/muni/muni-input';
import {
  API_ENVIRONMENTS,
  clearApiBaseUrlOverride,
  getApiBaseUrl,
  getDefaultApiBaseUrl,
  setApiBaseUrlOverride,
  type ApiEnvironmentId,
} from '@/constants/config';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Props = {
  visible: boolean;
  onClose: () => void;
  /**
   * Se llama despues de aplicar un cambio de entorno. La app deberia
   * limpiar la sesion (logout) para que los tokens viejos no se usen
   * contra un backend distinto.
   */
  onAfterApply?: () => void;
};

type Seleccion =
  | { tipo: 'preset'; id: Exclude<ApiEnvironmentId, 'custom'> }
  | { tipo: 'custom' };

function matchPreset(
  url: string,
): Exclude<ApiEnvironmentId, 'custom'> | null {
  for (const env of API_ENVIRONMENTS) {
    if (env.url === url) return env.id as Exclude<ApiEnvironmentId, 'custom'>;
  }
  return null;
}

export function DevSettingsModal({ visible, onClose, onAfterApply }: Props) {
  const urlActual = getApiBaseUrl();
  const urlDefault = getDefaultApiBaseUrl();
  const presetActual = useMemo(() => matchPreset(urlActual), [urlActual]);

  const [seleccion, setSeleccion] = useState<Seleccion>(
    presetActual ? { tipo: 'preset', id: presetActual } : { tipo: 'custom' },
  );
  const [customUrl, setCustomUrl] = useState<string>(
    presetActual ? '' : urlActual,
  );
  const [aplicando, setAplicando] = useState(false);

  useEffect(() => {
    if (!visible) return;
    const actual = getApiBaseUrl();
    const preset = matchPreset(actual);
    if (preset) {
      setSeleccion({ tipo: 'preset', id: preset });
      setCustomUrl('');
    } else {
      setSeleccion({ tipo: 'custom' });
      setCustomUrl(actual);
    }
  }, [visible]);

  const aplicar = async () => {
    let urlObjetivo: string;
    if (seleccion.tipo === 'custom') {
      const url = customUrl.trim();
      if (!/^https?:\/\//i.test(url)) {
        Alert.alert(
          'URL invalida',
          'La URL personalizada debe empezar con http:// o https://',
        );
        return;
      }
      urlObjetivo = url;
    } else {
      const env = API_ENVIRONMENTS.find((e) => e.id === seleccion.id);
      if (!env) return;
      urlObjetivo = env.url;
    }

    try {
      setAplicando(true);
      await setApiBaseUrlOverride(urlObjetivo);
      Alert.alert(
        'Entorno actualizado',
        `Ahora la app usara:\n\n${urlObjetivo}\n\nSe cerrara tu sesion. Si no ves cambios, cierra la app por completo y vuelve a abrirla.`,
        [
          {
            text: 'OK',
            onPress: () => {
              onClose();
              onAfterApply?.();
            },
          },
        ],
      );
    } catch (err) {
      Alert.alert(
        'Error',
        err instanceof Error ? err.message : 'No se pudo guardar la URL.',
      );
    } finally {
      setAplicando(false);
    }
  };

  const restaurarDefault = async () => {
    try {
      setAplicando(true);
      await clearApiBaseUrlOverride();
      Alert.alert(
        'Listo',
        `Se restauro la URL por defecto:\n\n${getDefaultApiBaseUrl()}\n\nSe cerrara tu sesion.`,
        [
          {
            text: 'OK',
            onPress: () => {
              onClose();
              onAfterApply?.();
            },
          },
        ],
      );
    } finally {
      setAplicando(false);
    }
  };

  return (
    <Modal
      visible={visible}
      animationType="slide"
      presentationStyle="formSheet"
      onRequestClose={onClose}>
      <KeyboardAvoidingView
        style={{ flex: 1 }}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
        <View style={styles.header}>
          <View style={{ flex: 1 }}>
            <Text style={styles.title}>Selector de entorno</Text>
            <Text style={styles.subtitle}>Menu de desarrolladores</Text>
          </View>
          <Pressable onPress={onClose} hitSlop={12} style={styles.closeBtn}>
            <MaterialCommunityIcons
              name="close"
              size={22}
              color={MunicipalityColors.textPrimary}
            />
          </Pressable>
        </View>

        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled">
          <View style={styles.infoBox}>
            <Text style={styles.infoLabel}>URL activa</Text>
            <Text style={styles.infoValue}>{urlActual}</Text>
            <Text style={styles.infoLabel}>URL por defecto del build</Text>
            <Text style={styles.infoValueMuted}>{urlDefault}</Text>
          </View>

          <Text style={styles.sectionTitle}>Elige un entorno</Text>

          {API_ENVIRONMENTS.map((env) => {
            const checked =
              seleccion.tipo === 'preset' && seleccion.id === env.id;
            return (
              <Pressable
                key={env.id}
                onPress={() =>
                  setSeleccion({
                    tipo: 'preset',
                    id: env.id as Exclude<ApiEnvironmentId, 'custom'>,
                  })
                }
                style={[styles.option, checked && styles.optionChecked]}>
                <MaterialCommunityIcons
                  name={checked ? 'radiobox-marked' : 'radiobox-blank'}
                  size={22}
                  color={
                    checked
                      ? MunicipalityColors.primary
                      : MunicipalityColors.textMuted
                  }
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.optionLabel}>{env.label}</Text>
                  <Text style={styles.optionDesc}>{env.description}</Text>
                  <Text style={styles.optionUrl}>{env.url}</Text>
                </View>
              </Pressable>
            );
          })}

          <Pressable
            onPress={() => setSeleccion({ tipo: 'custom' })}
            style={[
              styles.option,
              seleccion.tipo === 'custom' && styles.optionChecked,
            ]}>
            <MaterialCommunityIcons
              name={
                seleccion.tipo === 'custom'
                  ? 'radiobox-marked'
                  : 'radiobox-blank'
              }
              size={22}
              color={
                seleccion.tipo === 'custom'
                  ? MunicipalityColors.primary
                  : MunicipalityColors.textMuted
              }
            />
            <View style={{ flex: 1 }}>
              <Text style={styles.optionLabel}>Custom</Text>
              <Text style={styles.optionDesc}>
                Escribe una URL libre (incluye http:// y /api/v1).
              </Text>
            </View>
          </Pressable>

          {seleccion.tipo === 'custom' ? (
            <View style={{ marginTop: Spacing.sm }}>
              <MuniInput
                label="URL personalizada"
                value={customUrl}
                onChangeText={setCustomUrl}
                placeholder="http://192.168.1.10:8000/api/v1"
                autoCapitalize="none"
                autoCorrect={false}
                keyboardType="url"
              />
            </View>
          ) : null}

          <View style={{ height: Spacing.md }} />

          <MuniButton
            label="Aplicar y cerrar sesion"
            onPress={aplicar}
            loading={aplicando}
          />
          <View style={{ height: Spacing.sm }} />
          <MuniButton
            label="Restaurar URL por defecto"
            variant="secondary"
            onPress={restaurarDefault}
            loading={aplicando}
          />
          <View style={{ height: Spacing.sm }} />
          <MuniButton
            label="Cancelar"
            variant="ghost"
            onPress={onClose}
            disabled={aplicando}
          />

          <Text style={styles.footer}>
            Tip: si el cambio no se ve reflejado al instante, cierra la app
            por completo (desliza desde recientes) y vuelve a abrirla.
          </Text>
        </ScrollView>
      </KeyboardAvoidingView>
    </Modal>
  );
}

const styles = StyleSheet.create({
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: Spacing.lg,
    paddingTop: Spacing.lg,
    paddingBottom: Spacing.md,
    borderBottomWidth: 1,
    borderBottomColor: MunicipalityColors.border,
    backgroundColor: MunicipalityColors.white,
  },
  title: {
    fontSize: 18,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
  },
  subtitle: {
    fontSize: 12,
    color: MunicipalityColors.textMuted,
    marginTop: 2,
  },
  closeBtn: {
    width: 36,
    height: 36,
    borderRadius: 18,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: MunicipalityColors.surface,
  },
  content: {
    padding: Spacing.lg,
    paddingBottom: Spacing.xxl,
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.surface,
    flexGrow: 1,
  },
  infoBox: {
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.md,
    padding: Spacing.md,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    gap: 4,
    marginBottom: Spacing.md,
  },
  infoLabel: {
    fontSize: 11,
    fontWeight: '700',
    color: MunicipalityColors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
  },
  infoValue: {
    fontSize: 13,
    color: MunicipalityColors.primary,
    fontWeight: '700',
    marginBottom: 6,
  },
  infoValueMuted: {
    fontSize: 12,
    color: MunicipalityColors.textSecondary,
  },
  sectionTitle: {
    fontSize: 13,
    fontWeight: '700',
    color: MunicipalityColors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    marginTop: Spacing.sm,
    marginBottom: Spacing.xs,
  },
  option: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    padding: Spacing.md,
  },
  optionChecked: {
    borderColor: MunicipalityColors.primary,
    backgroundColor: '#EEF2FF',
  },
  optionLabel: {
    fontSize: 14,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  optionDesc: {
    fontSize: 12,
    color: MunicipalityColors.textMuted,
    marginTop: 2,
  },
  optionUrl: {
    fontSize: 11,
    color: MunicipalityColors.primary,
    marginTop: 4,
    fontWeight: '600',
  },
  footer: {
    fontSize: 11,
    color: MunicipalityColors.textMuted,
    fontStyle: 'italic',
    textAlign: 'center',
    marginTop: Spacing.md,
  },
});
