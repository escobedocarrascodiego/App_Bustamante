import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router, type Href } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { WebView } from 'react-native-webview';

import { MuniBannerMpv } from '@/components/muni/muni-banner-mpv';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniChatFab } from '@/components/muni/muni-chat-fab';
import { MuniHeader } from '@/components/muni/muni-header';
import { MuniLogo } from '@/components/muni/muni-logo';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { deudasApi } from '@/services/endpoints';
import type { DeudaDetalleResponse } from '@/services/types';
import { useAuth } from '@/store/auth-context';

const NOTAS_PRENSA_URL = 'https://munibustamante.gob.pe/notas-de-prensa';

type AccesoRapido = {
  icono: React.ComponentProps<typeof MaterialCommunityIcons>['name'];
  titulo: string;
  onPress: () => void;
};

export default function InicioScreen() {
  const { ciudadano } = useAuth();
  const [resumen, setResumen] = useState<DeudaDetalleResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [cargandoWeb, setCargandoWeb] = useState(true);

  const cargar = useCallback(async () => {
    try {
      const r = await deudasApi.detalle().catch(() => null);
      setResumen(r);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const accesos: AccesoRapido[] = [
    { icono: 'cash-multiple', titulo: 'Mis deudas', onPress: () => router.push('/(tabs)/deudas') },
    { icono: 'file-document-plus', titulo: 'Nuevo tramite', onPress: () => router.push('/tramites/nuevo') },
    { icono: 'card-account-details', titulo: 'Mi tarjeta', onPress: () => router.push('/(tabs)/tarjeta') },
    { icono: 'phone', titulo: 'Contactos', onPress: () => router.push('/(tabs)/perfil') },
  ];

  return (
    <View style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}>
      <MuniHeader
        title={`Hola, ${ciudadano?.nombres?.split(' ')[0] ?? 'vecino'}`}
        subtitle="Municipalidad JLBR"
        right={<MuniLogo size={40} />}
      />
      <ScrollView
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void cargar();
            }}
          />
        }>
        <MuniBannerMpv permitirVerificar />
        <MuniCard>
          <Text style={styles.sectionLabel}>Resumen tributario</Text>
          {loading ? (
            <Text style={styles.muted}>Cargando...</Text>
          ) : resumen ? (
            <>
              <Text style={styles.totalMonto}>S/ {Number(resumen.total).toFixed(2)}</Text>
              <Text style={styles.muted}>
                {resumen.items.length} concepto(s) pendiente(s)
              </Text>
              <Pressable onPress={() => router.push('/(tabs)/deudas')} style={styles.verMas}>
                <Text style={styles.verMasText}>Ver detalle</Text>
                <MaterialCommunityIcons
                  name="arrow-right"
                  size={16}
                  color={MunicipalityColors.primary}
                />
              </Pressable>
            </>
          ) : (
            <Text style={styles.muted}>No se pudo obtener tu resumen.</Text>
          )}
        </MuniCard>

        <Text style={styles.sectionTitle}>Accesos rapidos</Text>
        <View style={styles.grid}>
          {accesos.map((a) => (
            <Pressable key={a.titulo} onPress={a.onPress} style={styles.accesoItem}>
              <View style={styles.accesoIcon}>
                <MaterialCommunityIcons name={a.icono} size={26} color={MunicipalityColors.primary} />
              </View>
              <Text style={styles.accesoLabel}>{a.titulo}</Text>
            </Pressable>
          ))}
        </View>

        {/* Acceso al gestor de turnos (una sola tarjeta, sin saturar la grilla) */}
        <Pressable onPress={() => router.push('/turnos' as Href)} style={styles.turnosCard}>
          <View style={styles.turnosIcon}>
            <MaterialCommunityIcons name="ticket-confirmation" size={26} color={MunicipalityColors.white} />
          </View>
          <View style={{ flex: 1 }}>
            <Text style={styles.turnosTitle}>Atencion en ventanilla</Text>
            <Text style={styles.turnosSub}>Mira la cola en vivo y saca tu turno</Text>
          </View>
          <MaterialCommunityIcons name="arrow-right" size={22} color={MunicipalityColors.primary} />
        </Pressable>

        <Text style={styles.sectionTitle}>Noticias municipales</Text>
        {/*
          El View captura gestos para que el ScrollView padre no se "robe"
          el swipe vertical mientras el dedo esta sobre el WebView. Sin
          esto el ScrollView gana y el WebView nunca llega a scrollear su
          contenido HTML. nestedScrollEnabled habilita la cooperacion del
          scroll nativo en Android.
        */}
        <View
          style={styles.notasWrap}
          onStartShouldSetResponder={() => true}
          onMoveShouldSetResponder={() => true}
          onResponderTerminationRequest={() => false}>
          <WebView
            source={{ uri: NOTAS_PRENSA_URL }}
            style={styles.notasWebview}
            onLoadStart={() => setCargandoWeb(true)}
            onLoadEnd={() => setCargandoWeb(false)}
            startInLoadingState={false}
            javaScriptEnabled
            domStorageEnabled
            nestedScrollEnabled
            scrollEnabled
            androidLayerType="hardware"
          />
          {cargandoWeb ? (
            <View style={styles.notasLoader} pointerEvents="none">
              <ActivityIndicator color={MunicipalityColors.primary} />
              <Text style={styles.notasLoaderText}>Cargando notas de prensa...</Text>
            </View>
          ) : null}
        </View>
      </ScrollView>

      {/* FAB del chatbot: solo visible en Inicio */}
      <MuniChatFab />
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  sectionLabel: {
    color: MunicipalityColors.textMuted,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    fontWeight: '700',
  },
  totalMonto: {
    fontSize: 32,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    marginTop: 4,
  },
  muted: { color: MunicipalityColors.textSecondary, fontSize: 14 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
    marginTop: Spacing.sm,
  },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: Spacing.md },
  accesoItem: {
    flexBasis: '47%',
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    alignItems: 'flex-start',
    gap: Spacing.sm,
  },
  accesoIcon: {
    backgroundColor: '#E3EBFB',
    padding: 10,
    borderRadius: Radius.md,
  },
  accesoLabel: { fontWeight: '700', color: MunicipalityColors.textPrimary },
  turnosCard: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.lg,
    padding: Spacing.lg,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
  },
  turnosIcon: {
    backgroundColor: MunicipalityColors.primary,
    padding: 10,
    borderRadius: Radius.md,
  },
  turnosTitle: { fontWeight: '800', color: MunicipalityColors.textPrimary, fontSize: 15 },
  turnosSub: { color: MunicipalityColors.textSecondary, fontSize: 12, marginTop: 2 },
  verMas: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: Spacing.sm,
  },
  verMasText: { color: MunicipalityColors.primary, fontWeight: '700' },
  notasWrap: {
    width: '100%',
    height: 420,
    borderRadius: Radius.lg,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    backgroundColor: MunicipalityColors.white,
  },
  notasWebview: { flex: 1 },
  notasLoader: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.white,
  },
  notasLoaderText: { color: MunicipalityColors.textMuted, fontSize: 12 },
});
