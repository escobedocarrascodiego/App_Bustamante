/**
 * Banner que se muestra cuando el ciudadano omitio el registro en Mesa
 * de Partes Virtual. Aparece en Inicio (con boton "Ya me registre" para
 * re-verificar) y en Tramites (sin opcion de re-verificar — solo informa).
 */
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Linking,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { useAuth } from '@/store/auth-context';

const LINK_REGISTRO_MPV =
  'http://mesa-partes-virtual.munibustamante.gob.pe:9090/Account/Register';

type Props = {
  /**
   * Si true muestra el boton "Ya me registre" que llama a verificar-mpv.
   * En Tramites lo dejamos en false: el banner es solo informativo y la
   * unica manera de salir es completando el registro real en MPV.
   */
  permitirVerificar: boolean;
};

export function MuniBannerMpv({ permitirVerificar }: Props) {
  const { ciudadano, verificarMpv } = useAuth();
  const [verificando, setVerificando] = useState(false);

  // Si ya esta verificado, no se muestra
  if (!ciudadano || ciudadano.verificado) return null;

  const abrirMpv = async () => {
    const ok = await Linking.canOpenURL(LINK_REGISTRO_MPV).catch(() => false);
    if (!ok) {
      Alert.alert(
        'No se pudo abrir',
        'Abre manualmente este enlace en tu navegador:\n\n' +
          LINK_REGISTRO_MPV,
      );
      return;
    }
    void Linking.openURL(LINK_REGISTRO_MPV);
  };

  const onVerificar = async () => {
    if (verificando) return;
    setVerificando(true);
    try {
      const res = await verificarMpv();
      Alert.alert(
        res.exito ? '¡Listo!' : 'Aún no detectamos tu registro',
        res.mensaje,
      );
    } finally {
      setVerificando(false);
    }
  };

  return (
    <View style={styles.banner}>
      <View style={styles.iconWrap}>
        <MaterialCommunityIcons
          name="alert-circle-outline"
          size={20}
          color="#92400E"
        />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.titulo}>
          {permitirVerificar
            ? 'Completa tu registro en Mesa de Partes Virtual'
            : 'Necesitas registrarte en Mesa de Partes Virtual'}
        </Text>
        <Text style={styles.descripcion}>
          {permitirVerificar
            ? 'Para iniciar trámites desde el app debes tener una cuenta MPV. ' +
              'Si ya la creaste, toca "Ya me registré" para verificar.'
            : 'Sin tu cuenta MPV no podemos iniciar trámites a tu nombre. ' +
              'Crea tu cuenta en el portal y vuelve al app.'}
        </Text>
        <View style={styles.actions}>
          <Pressable
            onPress={abrirMpv}
            style={({ pressed }) => [
              styles.btn,
              styles.btnPrimary,
              pressed && { opacity: 0.85 },
            ]}>
            <Text style={styles.btnPrimaryText}>Registrarme</Text>
          </Pressable>
          {permitirVerificar ? (
            <Pressable
              onPress={onVerificar}
              disabled={verificando}
              style={({ pressed }) => [
                styles.btn,
                styles.btnSecondary,
                pressed && { opacity: 0.7 },
                verificando && { opacity: 0.6 },
              ]}>
              {verificando ? (
                <ActivityIndicator size="small" color="#92400E" />
              ) : (
                <Text style={styles.btnSecondaryText}>Ya me registré</Text>
              )}
            </Pressable>
          ) : null}
        </View>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  banner: {
    flexDirection: 'row',
    backgroundColor: '#FEF3C7', // amber-100
    borderWidth: 1,
    borderColor: '#FCD34D', // amber-300
    borderRadius: Radius.lg,
    padding: Spacing.md,
    gap: Spacing.sm,
  },
  iconWrap: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#FDE68A', // amber-200
    alignItems: 'center',
    justifyContent: 'center',
  },
  titulo: {
    fontSize: 13,
    fontWeight: '800',
    color: '#78350F', // amber-900
    marginBottom: 2,
  },
  descripcion: {
    fontSize: 12,
    color: '#92400E', // amber-800
    lineHeight: 16,
    marginBottom: Spacing.sm,
  },
  actions: {
    flexDirection: 'row',
    gap: Spacing.sm,
    flexWrap: 'wrap',
  },
  btn: {
    paddingHorizontal: Spacing.md,
    paddingVertical: 8,
    borderRadius: Radius.md,
    alignItems: 'center',
    justifyContent: 'center',
    minWidth: 100,
  },
  btnPrimary: {
    backgroundColor: '#B45309', // amber-700
  },
  btnPrimaryText: {
    color: MunicipalityColors.white,
    fontSize: 12,
    fontWeight: '700',
  },
  btnSecondary: {
    backgroundColor: 'transparent',
    borderWidth: 1,
    borderColor: '#B45309',
  },
  btnSecondaryText: {
    color: '#92400E',
    fontSize: 12,
    fontWeight: '700',
  },
});
