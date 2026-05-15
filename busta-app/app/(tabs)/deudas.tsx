import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  FlatList,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { MuniBadge } from '@/components/muni/muni-badge';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MuniHelpButton } from '@/components/muni/muni-help-button';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { VIDEO_PAGO_EN_LINEA } from '@/constants/videos';
import { deudasApi } from '@/services/endpoints';
import type {
  CondicionContribuyente,
  DeudaDetalleItem,
} from '@/services/types';

type Grupo = {
  origen: string;
  total: number;
  items: DeudaDetalleItem[];
};

const ORIGEN_TONO: Record<string, Parameters<typeof MuniBadge>[0]['tone']> = {
  'DEUDA REGISTRADA': 'danger',
  'PREDIAL NO GENERADO (TITULAR)': 'warning',
  'SERENAZGO NO GENERADO': 'warning',
  'ARBITRIOS NO GENERADOS': 'warning',
};

const ORIGEN_ICON: Record<
  string,
  React.ComponentProps<typeof MaterialCommunityIcons>['name']
> = {
  'DEUDA REGISTRADA': 'file-document-alert-outline',
  'PREDIAL NO GENERADO (TITULAR)': 'home-city-outline',
  'SERENAZGO NO GENERADO': 'shield-outline',
  'ARBITRIOS NO GENERADOS': 'broom',
};

const MES_CORTO = [
  '',
  'Ene',
  'Feb',
  'Mar',
  'Abr',
  'May',
  'Jun',
  'Jul',
  'Ago',
  'Set',
  'Oct',
  'Nov',
  'Dic',
];

export default function DeudasScreen() {
  const [items, setItems] = useState<DeudaDetalleItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [condiciones, setCondiciones] = useState<CondicionContribuyente[]>([]);
  const [prdconcodSel, setPrdconcodSel] = useState<number | null>(null);

  const cargar = useCallback(async (prdconcod?: number | null) => {
    try {
      const resp = await deudasApi.detalle(prdconcod ?? undefined);
      setItems(resp.items ?? []);
      setTotal(Number(resp.total ?? 0));
      setCondiciones(resp.condiciones ?? []);
      setPrdconcodSel(resp.prdconcod ?? null);
    } catch {
      setItems([]);
      setTotal(0);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const seleccionarCondicion = (prdconcod: number | null) => {
    if (prdconcod === prdconcodSel) return;
    setPrdconcodSel(prdconcod);
    setLoading(true);
    void cargar(prdconcod);
  };

  const grupos = useMemo<Grupo[]>(() => {
    const mapa = new Map<string, Grupo>();
    for (const it of items) {
      const grupo = mapa.get(it.origen) ?? {
        origen: it.origen,
        total: 0,
        items: [],
      };
      grupo.total += Number(it.saldo_pendiente) || 0;
      grupo.items.push(it);
      mapa.set(it.origen, grupo);
    }
    return Array.from(mapa.values()).sort((a, b) => b.total - a.total);
  }, [items]);

  return (
    <View style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}>
      <MuniHeader
        title="Mis deudas"
        subtitle="Predial, arbitrios y serenazgo"
        right={<MuniHelpButton video={VIDEO_PAGO_EN_LINEA} />}
      />
      <FlatList
        data={grupos}
        keyExtractor={(g) => g.origen}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={() => {
              setRefreshing(true);
              void cargar();
            }}
          />
        }
        contentContainerStyle={styles.content}
        ListHeaderComponent={
          <View style={{ gap: Spacing.md }}>
            {condiciones.length > 1 ? (
              <SelectorCondiciones
                condiciones={condiciones}
                seleccionado={prdconcodSel}
                onSeleccionar={seleccionarCondicion}
              />
            ) : null}
            <MuniCard style={{ gap: 4 }}>
              <Text style={styles.totalLabel}>Total pendiente</Text>
              <Text style={styles.totalMonto}>S/ {total.toFixed(2)}</Text>
              {condiciones.length === 1 ? (
                <View style={styles.condicionRow}>
                  <MaterialCommunityIcons
                    name="account-tie-outline"
                    size={14}
                    color={MunicipalityColors.primary}
                  />
                  <Text style={styles.condicionText}>
                    Condición: {condiciones[0].nombre}
                  </Text>
                </View>
              ) : null}
              <Text style={styles.muted}>
                {items.length} registro(s) en {grupos.length} origen(es)
              </Text>
            </MuniCard>
          </View>
        }
        ListEmptyComponent={
          loading ? (
            <View style={{ paddingVertical: Spacing.xl }}>
              <ActivityIndicator color={MunicipalityColors.primary} />
            </View>
          ) : (
            <MuniCard>
              <Text style={styles.muted}>
                No se encontraron deudas pendientes para tu contribuyente.
              </Text>
            </MuniCard>
          )
        }
        ItemSeparatorComponent={() => <View style={{ height: Spacing.md }} />}
        renderItem={({ item }) => <GrupoCard grupo={item} />}
      />
    </View>
  );
}

function GrupoCard({ grupo }: { grupo: Grupo }) {
  const icon = ORIGEN_ICON[grupo.origen] ?? 'alert-circle-outline';
  const tono = ORIGEN_TONO[grupo.origen] ?? 'primary';
  return (
    <MuniCard style={{ gap: Spacing.md }}>
      <View style={styles.grupoHeader}>
        <View style={styles.grupoTitulo}>
          <MaterialCommunityIcons name={icon} size={20} color={MunicipalityColors.primary} />
          <Text style={styles.grupoNombre}>{grupo.origen}</Text>
        </View>
        <MuniBadge label={`S/ ${grupo.total.toFixed(2)}`} tone={tono} />
      </View>
      <View style={{ gap: Spacing.sm }}>
        {grupo.items.map((it, idx) => (
          <DetalleFila key={`${grupo.origen}-${idx}`} item={it} />
        ))}
      </View>
    </MuniCard>
  );
}

function DetalleFila({ item }: { item: DeudaDetalleItem }) {
  const periodo = formatearPeriodo(item.anio, item.mes);
  const muestraReajuste = Number(item.cargos_reajuste) > 0;
  const muestraPagado = Number(item.pagado) > 0;
  return (
    <View style={styles.fila}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={styles.concepto}>{item.concepto}</Text>
        <Text style={styles.metaFila}>
          {periodo}
          {item.predio_cod ? ` · Predio ${item.predio_cod}` : ''}
        </Text>
        {item.predio_direccion ? (
          <View style={styles.direccionRow}>
            <MaterialCommunityIcons
              name="map-marker-outline"
              size={12}
              color={MunicipalityColors.textMuted}
            />
            <Text style={styles.direccionText} numberOfLines={2}>
              {item.predio_direccion}
            </Text>
          </View>
        ) : null}
        {muestraReajuste || muestraPagado ? (
          <Text style={styles.metaFila}>
            {muestraReajuste ? `Reajuste S/ ${item.cargos_reajuste.toFixed(2)}` : ''}
            {muestraReajuste && muestraPagado ? ' · ' : ''}
            {muestraPagado ? `Pagado S/ ${item.pagado.toFixed(2)}` : ''}
          </Text>
        ) : null}
      </View>
      <View style={{ alignItems: 'flex-end' }}>
        <Text style={styles.saldoLabel}>Saldo</Text>
        <Text style={styles.saldoMonto}>S/ {Number(item.saldo_pendiente).toFixed(2)}</Text>
      </View>
    </View>
  );
}

function formatearPeriodo(anio: number | null, mes: number | null): string {
  if (!anio) return 'Sin periodo';
  if (!mes) return `${anio}`;
  const nombre = MES_CORTO[mes] ?? String(mes);
  return `${nombre} ${anio}`;
}

function SelectorCondiciones({
  condiciones,
  seleccionado,
  onSeleccionar,
}: {
  condiciones: CondicionContribuyente[];
  seleccionado: number | null;
  onSeleccionar: (prdconcod: number | null) => void;
}) {
  const totalGlobal = condiciones.reduce(
    (acc, c) => acc + Number(c.deuda_total),
    0,
  );
  return (
    <View style={styles.selectorBox}>
      <View style={styles.selectorTituloRow}>
        <MaterialCommunityIcons
          name="account-switch-outline"
          size={16}
          color={MunicipalityColors.primary}
        />
        <Text style={styles.selectorTitulo}>Selecciona tu condición</Text>
      </View>
      <ScrollView
        horizontal
        showsHorizontalScrollIndicator={false}
        contentContainerStyle={styles.selectorScroll}>
        <Pressable
          onPress={() => onSeleccionar(null)}
          style={[styles.selectorChip, seleccionado === null && styles.selectorChipActivo]}>
          <Text
            style={[
              styles.selectorChipNombre,
              seleccionado === null && styles.selectorChipNombreActivo,
            ]}>
            TODAS
          </Text>
          <Text
            style={[
              styles.selectorChipMonto,
              seleccionado === null && styles.selectorChipMontoActivo,
            ]}>
            S/ {totalGlobal.toFixed(2)}
          </Text>
        </Pressable>
        {condiciones.map((c) => {
          const activo = c.prd_con_cod === seleccionado;
          return (
            <Pressable
              key={c.prd_con_cod}
              onPress={() => onSeleccionar(c.prd_con_cod)}
              style={[
                styles.selectorChip,
                activo && styles.selectorChipActivo,
              ]}>
              <Text
                style={[
                  styles.selectorChipNombre,
                  activo && styles.selectorChipNombreActivo,
                ]}
                numberOfLines={1}>
                {c.nombre || `Cond. ${c.prd_con_cod}`}
              </Text>
              <Text
                style={[
                  styles.selectorChipMonto,
                  activo && styles.selectorChipMontoActivo,
                ]}>
                S/ {Number(c.deuda_total).toFixed(2)}
              </Text>
            </Pressable>
          );
        })}
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, paddingBottom: Spacing.xxl },
  totalLabel: {
    color: MunicipalityColors.textMuted,
    fontSize: 12,
    textTransform: 'uppercase',
    letterSpacing: 0.8,
    fontWeight: '700',
  },
  totalMonto: {
    fontSize: 30,
    fontWeight: '800',
    color: MunicipalityColors.primary,
  },
  condicionRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    marginTop: 2,
    marginBottom: 2,
  },
  condicionText: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.primary,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  muted: { color: MunicipalityColors.textSecondary, fontSize: 13 },
  grupoHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.md,
  },
  grupoTitulo: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    flex: 1,
  },
  grupoNombre: {
    fontSize: 14,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
    flex: 1,
  },
  fila: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.md,
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.sm,
    backgroundColor: MunicipalityColors.surface,
    borderRadius: Radius.md,
  },
  concepto: {
    fontSize: 14,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  metaFila: { fontSize: 12, color: MunicipalityColors.textMuted },
  direccionRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: 3,
    marginTop: 1,
  },
  direccionText: {
    flex: 1,
    fontSize: 11,
    color: MunicipalityColors.textMuted,
    fontStyle: 'italic',
    lineHeight: 14,
  },
  saldoLabel: {
    fontSize: 10,
    color: MunicipalityColors.textMuted,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    fontWeight: '700',
  },
  saldoMonto: { fontSize: 16, fontWeight: '800', color: MunicipalityColors.primary },
  selectorBox: {
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    padding: Spacing.md,
    gap: Spacing.sm,
  },
  selectorTituloRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  selectorTitulo: {
    fontSize: 12,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    textTransform: 'uppercase',
    letterSpacing: 0.6,
  },
  selectorScroll: { gap: Spacing.sm, paddingVertical: 2 },
  selectorChip: {
    minWidth: 180,
    backgroundColor: '#F8FAFC',
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    gap: 4,
  },
  selectorChipActivo: {
    backgroundColor: '#EEF2FF',
    borderColor: MunicipalityColors.primary,
  },
  selectorChipNombre: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textSecondary,
  },
  selectorChipNombreActivo: { color: MunicipalityColors.primary },
  selectorChipMonto: {
    fontSize: 14,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
  },
  selectorChipMontoActivo: { color: MunicipalityColors.primary },
});
