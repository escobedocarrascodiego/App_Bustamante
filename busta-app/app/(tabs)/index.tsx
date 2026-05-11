import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from 'react-native';

import { MuniBadge } from '@/components/muni/muni-badge';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MuniLogo } from '@/components/muni/muni-logo';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { catalogosApi, deudasApi } from '@/services/endpoints';
import type { DeudaDetalleResponse, Noticia } from '@/services/types';
import { useAuth } from '@/store/auth-context';

type AccesoRapido = {
  icono: React.ComponentProps<typeof MaterialCommunityIcons>['name'];
  titulo: string;
  onPress: () => void;
};

export default function InicioScreen() {
  const { ciudadano } = useAuth();
  const [resumen, setResumen] = useState<DeudaDetalleResponse | null>(null);
  const [noticias, setNoticias] = useState<Noticia[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [r, n] = await Promise.all([
        deudasApi.detalle().catch(() => null),
        catalogosApi.noticias().catch(() => []),
      ]);
      setResumen(r);
      setNoticias(n.slice(0, 3));
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

        <Text style={styles.sectionTitle}>Noticias municipales</Text>
        {noticias.length === 0 ? (
          <MuniCard>
            <Text style={styles.muted}>No hay noticias recientes.</Text>
          </MuniCard>
        ) : (
          noticias.map((n) => (
            <MuniCard key={n.id} style={{ gap: 6 }}>
              <View style={{ flexDirection: 'row', alignItems: 'center', gap: Spacing.sm }}>
                {n.destacada ? <MuniBadge label="Destacada" tone="accent" /> : null}
                <Text style={styles.fecha}>
                  {new Date(n.fecha_publicacion).toLocaleDateString('es-PE')}
                </Text>
              </View>
              <Text style={styles.noticiaTitulo}>{n.titulo}</Text>
              <Text numberOfLines={3} style={styles.muted}>
                {n.resumen || n.contenido}
              </Text>
            </MuniCard>
          ))
        )}
      </ScrollView>
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
  verMas: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: Spacing.sm,
  },
  verMasText: { color: MunicipalityColors.primary, fontWeight: '700' },
  fecha: { fontSize: 12, color: MunicipalityColors.textMuted },
  noticiaTitulo: {
    fontSize: 15,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
});
