import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useLocalSearchParams } from 'expo-router';
import { useEffect, useState } from 'react';
import { ActivityIndicator, ScrollView, StyleSheet, Text, View } from 'react-native';

import { MuniBadge } from '@/components/muni/muni-badge';
import { MuniCard } from '@/components/muni/muni-card';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { tramitesApi } from '@/services/endpoints';
import type { ExpedienteSiapDetalle, ProveidoSiap } from '@/services/types';

const ESTADO_TONO: Record<
  ExpedienteSiapDetalle['estado'],
  Parameters<typeof MuniBadge>[0]['tone']
> = {
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

function fmtFechaHora(iso: string | null): string {
  if (!iso) return '';
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return '';
  return d.toLocaleString('es-PE');
}

export default function DetalleExpedienteSiapScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const [exp, setExp] = useState<ExpedienteSiapDetalle | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!id) return;
    setLoading(true);
    tramitesApi
      .detalleExpedienteSiap(Number(id))
      .then((data) => {
        setExp(data);
        setError(null);
      })
      .catch(() => setError('No se pudo cargar el expediente.'))
      .finally(() => setLoading(false));
  }, [id]);

  if (loading) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={MunicipalityColors.primary} />
      </View>
    );
  }

  if (error || !exp) {
    return (
      <View style={styles.center}>
        <MaterialCommunityIcons
          name="file-search-outline"
          size={48}
          color={MunicipalityColors.textMuted}
        />
        <Text style={styles.muted}>{error ?? 'Expediente no encontrado.'}</Text>
      </View>
    );
  }

  return (
    <ScrollView
      style={{ backgroundColor: MunicipalityColors.surface }}
      contentContainerStyle={styles.content}>
      <MuniCard style={{ gap: Spacing.sm }}>
        <View style={styles.row}>
          <Text style={styles.numero}>{exp.numero || `EXP-${exp.id}`}</Text>
          <MuniBadge label={exp.estado_display} tone={ESTADO_TONO[exp.estado] ?? 'primary'} />
        </View>
        {exp.tipo_nombre ? <Text style={styles.tipo}>{exp.tipo_nombre}</Text> : null}
        {exp.asunto ? <Text style={styles.asunto}>{exp.asunto}</Text> : null}

        <View style={styles.metaGrid}>
          {exp.fecha_ingreso ? (
            <MetaItem
              icon="calendar"
              label="Ingresado"
              value={fmtFecha(exp.fecha_ingreso)}
            />
          ) : null}
          {exp.fecha_vencimiento ? (
            <MetaItem
              icon="clock-outline"
              label="Vence"
              value={fmtFecha(exp.fecha_vencimiento)}
            />
          ) : null}
          {exp.oficina_actual ? (
            <MetaItem
              icon="office-building"
              label="Oficina"
              value={exp.oficina_actual}
            />
          ) : null}
        </View>

        {exp.observacion ? (
          <View style={styles.obsBox}>
            <MaterialCommunityIcons
              name="alert-circle-outline"
              size={16}
              color={MunicipalityColors.danger}
            />
            <Text style={styles.obsText}>{exp.observacion}</Text>
          </View>
        ) : null}
      </MuniCard>

      <Text style={styles.sectionTitle}>
        Linea de vida{' '}
        <Text style={styles.sectionCount}>
          ({exp.linea_vida.length} {exp.linea_vida.length === 1 ? 'movimiento' : 'movimientos'})
        </Text>
      </Text>

      {exp.linea_vida.length === 0 ? (
        <MuniCard>
          <Text style={styles.muted}>
            Aun no hay proveidos registrados para este expediente.
          </Text>
        </MuniCard>
      ) : (
        <View style={{ gap: Spacing.sm }}>
          {exp.linea_vida.map((p, idx) => (
            <ProveidoCard
              key={p.id}
              proveido={p}
              esUltimo={idx === exp.linea_vida.length - 1}
              esPrimero={idx === 0}
            />
          ))}
        </View>
      )}
    </ScrollView>
  );
}

function MetaItem({
  icon,
  label,
  value,
}: {
  icon: React.ComponentProps<typeof MaterialCommunityIcons>['name'];
  label: string;
  value: string;
}) {
  return (
    <View style={styles.metaItem}>
      <View style={styles.metaIconBox}>
        <MaterialCommunityIcons name={icon} size={14} color={MunicipalityColors.primary} />
      </View>
      <View style={{ flex: 1 }}>
        <Text style={styles.metaLabel}>{label}</Text>
        <Text style={styles.metaValue}>{value}</Text>
      </View>
    </View>
  );
}

function ProveidoCard({
  proveido: p,
  esUltimo,
  esPrimero,
}: {
  proveido: ProveidoSiap;
  esUltimo: boolean;
  esPrimero: boolean;
}) {
  return (
    <View style={styles.proveidoRow}>
      <View style={styles.timelineCol}>
        {!esPrimero ? <View style={styles.timelineLineTop} /> : null}
        <View
          style={[
            styles.timelineDot,
            esUltimo && styles.timelineDotActive,
          ]}>
          <MaterialCommunityIcons
            name={esUltimo ? 'circle-slice-8' : 'circle-medium'}
            size={esUltimo ? 16 : 12}
            color={MunicipalityColors.white}
          />
        </View>
        {!esUltimo ? <View style={styles.timelineLineBottom} /> : null}
      </View>

      <View style={styles.proveidoBody}>
        <View style={styles.proveidoHeader}>
          <Text style={styles.proveidoNumero} numberOfLines={1}>
            {p.numero || `Proveido ${p.id}`}
          </Text>
          <Text style={styles.proveidoFecha}>{fmtFechaHora(p.fecha)}</Text>
        </View>

        {p.accion ? (
          <Text style={styles.proveidoAccion} numberOfLines={3}>
            {p.accion}
          </Text>
        ) : null}

        <View style={styles.proveidoMeta}>
          {p.oficina_origen ? (
            <View style={styles.metaPill}>
              <MaterialCommunityIcons
                name="arrow-right-bold-outline"
                size={11}
                color={MunicipalityColors.textMuted}
              />
              <Text style={styles.metaPillText}>De: {p.oficina_origen}</Text>
            </View>
          ) : null}
          {p.oficina_destino ? (
            <View style={styles.metaPill}>
              <MaterialCommunityIcons
                name="arrow-down-bold-outline"
                size={11}
                color={MunicipalityColors.textMuted}
              />
              <Text style={styles.metaPillText}>A: {p.oficina_destino}</Text>
            </View>
          ) : null}
          {p.recibido ? (
            <View style={[styles.metaPill, styles.metaPillSuccess]}>
              <MaterialCommunityIcons
                name="check-circle"
                size={11}
                color={MunicipalityColors.success}
              />
              <Text style={[styles.metaPillText, { color: MunicipalityColors.success }]}>
                Recibido
              </Text>
            </View>
          ) : null}
        </View>
      </View>
    </View>
  );
}

const TIMELINE_WIDTH = 32;

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.surface,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  numero: { fontSize: 16, fontWeight: '800', color: MunicipalityColors.primary },
  asunto: { fontSize: 14, color: MunicipalityColors.textSecondary, lineHeight: 20 },
  tipo: { fontSize: 14, fontWeight: '700', color: MunicipalityColors.textPrimary },
  metaGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
    marginTop: 4,
  },
  metaItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#F8FAFC',
    borderRadius: Radius.md,
    padding: Spacing.sm,
    minWidth: '47%',
    flexGrow: 1,
  },
  metaIconBox: {
    width: 24,
    height: 24,
    borderRadius: 12,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  metaLabel: {
    fontSize: 10,
    color: MunicipalityColors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontWeight: '700',
  },
  metaValue: {
    fontSize: 12,
    color: MunicipalityColors.textPrimary,
    fontWeight: '600',
  },
  obsBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 6,
    backgroundColor: '#FEF2F2',
    borderRadius: Radius.md,
    padding: Spacing.sm,
    marginTop: 4,
  },
  obsText: {
    fontSize: 12,
    color: MunicipalityColors.danger,
    fontWeight: '600',
    flex: 1,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
    marginTop: Spacing.sm,
  },
  sectionCount: {
    fontSize: 12,
    fontWeight: '500',
    color: MunicipalityColors.textMuted,
  },
  muted: { color: MunicipalityColors.textSecondary, fontSize: 13 },
  proveidoRow: {
    flexDirection: 'row',
    gap: Spacing.sm,
  },
  timelineCol: {
    width: TIMELINE_WIDTH,
    alignItems: 'center',
  },
  timelineDot: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: MunicipalityColors.primaryLight,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 2,
  },
  timelineDotActive: {
    backgroundColor: MunicipalityColors.primary,
  },
  timelineLineTop: {
    position: 'absolute',
    top: 0,
    width: 2,
    height: 12,
    backgroundColor: MunicipalityColors.border,
  },
  timelineLineBottom: {
    flex: 1,
    width: 2,
    backgroundColor: MunicipalityColors.border,
    marginTop: -1,
  },
  proveidoBody: {
    flex: 1,
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    padding: Spacing.md,
    gap: 6,
  },
  proveidoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
  },
  proveidoNumero: {
    fontSize: 13,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    flex: 1,
  },
  proveidoFecha: {
    fontSize: 11,
    color: MunicipalityColors.textMuted,
  },
  proveidoAccion: {
    fontSize: 13,
    color: MunicipalityColors.textPrimary,
    lineHeight: 18,
  },
  proveidoMeta: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
    marginTop: 2,
  },
  metaPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    backgroundColor: '#F1F5F9',
    borderRadius: Radius.pill,
    paddingHorizontal: Spacing.sm,
    paddingVertical: 3,
  },
  metaPillSuccess: { backgroundColor: '#DCFCE7' },
  metaPillText: {
    fontSize: 10,
    color: MunicipalityColors.textSecondary,
    fontWeight: '600',
  },
});
