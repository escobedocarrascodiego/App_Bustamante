import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useCallback, useEffect, useState } from 'react';
import { FlatList, Pressable, RefreshControl, StyleSheet, Text, View } from 'react-native';

import { MuniBadge } from '@/components/muni/muni-badge';
import { MuniButton } from '@/components/muni/muni-button';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MuniHelpButton } from '@/components/muni/muni-help-button';
import { MunicipalityColors, Spacing } from '@/constants/theme';
import { VIDEO_REGISTRO_MPV } from '@/constants/videos';
import { tramitesApi } from '@/services/endpoints';
import type { ExpedienteSiap } from '@/services/types';

const ESTADO_TONO: Record<ExpedienteSiap['estado'], Parameters<typeof MuniBadge>[0]['tone']> = {
  EN_TRAMITE: 'primary',
  OBSERVADO: 'warning',
  RESUELTO: 'success',
  ARCHIVADO: 'neutral',
};

function fmtFecha(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString('es-PE');
}

export default function TramitesScreen() {
  const [expedientes, setExpedientes] = useState<ExpedienteSiap[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const data = await tramitesApi.misExpedientesSiap();
      setExpedientes(data);
    } catch {
      setExpedientes([]);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  return (
    <View style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}>
      <MuniHeader
        title="Mis tramites"
        subtitle="Expedientes presentados"
        right={<MuniHelpButton video={VIDEO_REGISTRO_MPV} />}
      />
      <View style={styles.actions}>
        <MuniButton
          label="Iniciar nuevo tramite"
          variant="accent"
          onPress={() => router.push('/tramites/nuevo')}
        />
      </View>
      <FlatList
        data={expedientes}
        keyExtractor={(e) => String(e.id)}
        contentContainerStyle={styles.content}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void cargar();
            }}
          />
        }
        ItemSeparatorComponent={() => <View style={{ height: Spacing.md }} />}
        ListEmptyComponent={
          loading ? null : (
            <MuniCard>
              <Text style={styles.muted}>
                Aun no tienes expedientes registrados en la plataforma de tramites.
              </Text>
            </MuniCard>
          )
        }
        renderItem={({ item }) => (
          <Pressable onPress={() => router.push(`/tramites/${item.id}`)}>
            <MuniCard style={{ gap: Spacing.sm }}>
              <View style={styles.row}>
                <Text style={styles.numero}>{item.numero || `EXP-${item.id}`}</Text>
                <MuniBadge
                  label={item.estado_display}
                  tone={ESTADO_TONO[item.estado] ?? 'primary'}
                />
              </View>
              {item.tipo_nombre ? <Text style={styles.tipo}>{item.tipo_nombre}</Text> : null}
              {item.asunto ? <Text style={styles.asunto}>{item.asunto}</Text> : null}
              <View style={styles.metaRow}>
                <MaterialCommunityIcons name="calendar" size={14} color={MunicipalityColors.textMuted} />
                <Text style={styles.meta}>Ingresado {fmtFecha(item.fecha_ingreso)}</Text>
              </View>
              {item.fecha_vencimiento ? (
                <View style={styles.metaRow}>
                  <MaterialCommunityIcons name="clock-outline" size={14} color={MunicipalityColors.textMuted} />
                  <Text style={styles.meta}>Vence {fmtFecha(item.fecha_vencimiento)}</Text>
                </View>
              ) : null}
              {item.oficina_actual ? (
                <View style={styles.metaRow}>
                  <MaterialCommunityIcons name="office-building" size={14} color={MunicipalityColors.textMuted} />
                  <Text style={styles.meta}>Oficina: {item.oficina_actual}</Text>
                </View>
              ) : null}
              {item.cantidad_proveidos > 0 ? (
                <View style={styles.metaRow}>
                  <MaterialCommunityIcons name="file-document-multiple-outline" size={14} color={MunicipalityColors.textMuted} />
                  <Text style={styles.meta}>
                    {item.cantidad_proveidos} proveido{item.cantidad_proveidos === 1 ? '' : 's'}
                  </Text>
                </View>
              ) : null}
              {item.observacion ? (
                <Text style={styles.observacion}>Observacion: {item.observacion}</Text>
              ) : null}
            </MuniCard>
          </Pressable>
        )}
      />
    </View>
  );
}

const styles = StyleSheet.create({
  actions: { padding: Spacing.lg, paddingBottom: 0 },
  content: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  numero: { fontWeight: '800', color: MunicipalityColors.primary },
  asunto: { fontSize: 14, color: MunicipalityColors.textPrimary },
  tipo: { fontSize: 15, fontWeight: '700', color: MunicipalityColors.textPrimary },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  meta: { fontSize: 12, color: MunicipalityColors.textMuted },
  muted: { color: MunicipalityColors.textSecondary },
  observacion: {
    fontSize: 12,
    color: MunicipalityColors.danger,
    fontStyle: 'italic',
    marginTop: 2,
  },
});
