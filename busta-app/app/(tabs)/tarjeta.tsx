import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useState } from 'react';
import {
  Alert,
  FlatList,
  RefreshControl,
  StyleSheet,
  Text,
  View,
} from 'react-native';

import { MuniBadge } from '@/components/muni/muni-badge';
import { MuniBarcode } from '@/components/muni/muni-barcode';
import { MuniButton } from '@/components/muni/muni-button';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MuniLogo } from '@/components/muni/muni-logo';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { ApiError } from '@/services/api';
import { deudasApi, tarjetasApi } from '@/services/endpoints';
import type { Beneficio, DeudaMuniResult, Tarjeta } from '@/services/types';
import { useAuth } from '@/store/auth-context';

export default function TarjetaScreen() {
  const { ciudadano } = useAuth();
  const [tarjeta, setTarjeta] = useState<Tarjeta | null>(null);
  const [beneficios, setBeneficios] = useState<Beneficio[]>([]);
  const [estadoMuni, setEstadoMuni] = useState<DeudaMuniResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [emitting, setEmitting] = useState(false);
  const [refreshing, setRefreshing] = useState(false);

  const cargar = useCallback(async () => {
    try {
      const [t, bs, muni] = await Promise.all([
        tarjetasApi
          .miTarjeta()
          .catch((err: unknown) => (err instanceof ApiError && err.status === 404 ? null : Promise.reject(err))),
        tarjetasApi.beneficios().catch(() => []),
        deudasApi.verificarMuni().catch(() => null),
      ]);
      setTarjeta(t);
      setBeneficios(bs);
      setEstadoMuni(muni);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const emitir = async () => {
    setEmitting(true);
    try {
      const t = await tarjetasApi.emitir();
      setTarjeta(t);
    } catch (err) {
      if (err instanceof ApiError && err.status === 403) {
        const data = err.data as { detail?: string };
        Alert.alert('No puedes emitir tu tarjeta', data?.detail ?? 'Regulariza antes de emitir.');
        void cargar();
      } else {
        Alert.alert('Error', 'No se pudo emitir tu tarjeta.');
      }
    } finally {
      setEmitting(false);
    }
  };

  const alDia = estadoMuni?.estado_busta_card === 'AL_DIA';
  const puedeEmitir = alDia;
  // La tarjeta es valida solo si BD dice vigente (activa, NO bloqueada, NO
  // vencida) Y ademas SIAP la reporta al dia. Asi respetamos tanto los
  // bloqueos/vencimientos de la base como la deuda en tiempo real.
  const tarjetaValida = !!tarjeta && tarjeta.vigente && alDia;
  const tarjetaInvalidada = !!tarjeta && !tarjetaValida;

  return (
    <View style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}>
      <MuniHeader title="Tarjeta ciudadana" subtitle="Beneficios y acceso gratuito" />
      <FlatList
        data={tarjetaValida ? beneficios : []}
        keyExtractor={(b) => String(b.id)}
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
        ListHeaderComponent={
          loading ? null : tarjetaValida ? (
            <TarjetaVisual tarjeta={tarjeta!} ciudadano={ciudadano} />
          ) : tarjetaInvalidada ? (
            <TarjetaBloqueada tarjeta={tarjeta!} estadoMuni={estadoMuni} alDia={alDia} />
          ) : (
            <MuniCard style={{ gap: Spacing.md }}>
              <Text style={styles.titleCard}>Aun no tienes tarjeta ciudadana</Text>
              <Text style={styles.muted}>
                Emite tu tarjeta digital para acceder gratuitamente a parques, bibliotecas,
                talleres y mas beneficios del distrito.
              </Text>
              {estadoMuni ? (
                <View style={styles.estadoBox}>
                  <MuniBadge
                    label={
                      estadoMuni.estado_busta_card === 'AL_DIA'
                        ? 'Al dia'
                        : estadoMuni.estado_busta_card === 'TIENE_DEUDA'
                        ? 'Tiene deuda'
                        : estadoMuni.estado_busta_card === 'NO_PROPIETARIO'
                        ? 'Sin predios'
                        : estadoMuni.estado_busta_card === 'SIN_CONTRIBUYENTE'
                        ? 'No registrado'
                        : 'Error'
                    }
                    tone={
                      estadoMuni.estado_busta_card === 'AL_DIA' ? 'success' : 'danger'
                    }
                  />
                  <Text style={styles.muted}>{estadoMuni.mensaje}</Text>
                  {estadoMuni.deuda_total > 0 ? (
                    <Text style={styles.deudaMonto}>
                      S/ {estadoMuni.deuda_total.toFixed(2)}
                    </Text>
                  ) : null}
                </View>
              ) : null}
              <MuniButton
                label={puedeEmitir ? 'Emitir mi tarjeta' : 'No disponible'}
                onPress={emitir}
                loading={emitting}
                disabled={!puedeEmitir}
              />
            </MuniCard>
          )
        }
        ListEmptyComponent={
          loading || !tarjetaValida ? null : (
            <MuniCard>
              <Text style={styles.muted}>No hay beneficios disponibles.</Text>
            </MuniCard>
          )
        }
        ItemSeparatorComponent={() => <View style={{ height: Spacing.sm }} />}
        renderItem={({ item }) => (
          <MuniCard style={{ gap: 6 }}>
            <View style={styles.row}>
              <Text style={styles.beneficioNombre}>{item.nombre}</Text>
              <MuniBadge label={item.categoria_display} tone="accent" />
            </View>
            <Text style={styles.muted}>{item.descripcion}</Text>
            {item.lugar ? (
              <View style={styles.metaRow}>
                <MaterialCommunityIcons name="map-marker" size={14} color={MunicipalityColors.textMuted} />
                <Text style={styles.meta}>{item.lugar}</Text>
              </View>
            ) : null}
            {item.horario ? (
              <View style={styles.metaRow}>
                <MaterialCommunityIcons name="clock-outline" size={14} color={MunicipalityColors.textMuted} />
                <Text style={styles.meta}>{item.horario}</Text>
              </View>
            ) : null}
          </MuniCard>
        )}
      />
    </View>
  );
}

function estaVencida(fecha: string): boolean {
  if (!fecha) return false;
  const [y, m, d] = fecha.split('-').map(Number);
  if (!y || !m || !d) return false;
  const fv = new Date(y, m - 1, d); // medianoche local
  const hoy = new Date();
  hoy.setHours(0, 0, 0, 0);
  return fv < hoy;
}

function TarjetaBloqueada({
  tarjeta,
  estadoMuni,
  alDia,
}: {
  tarjeta: Tarjeta;
  estadoMuni: DeudaMuniResult | null;
  alDia: boolean;
}) {
  // Determinamos el motivo de invalidez por prioridad:
  //  1) deuda (no al dia)  2) vencida  3) bloqueo administrativo
  let titulo = 'Tarjeta inactiva';
  let descripcion =
    'Tu tarjeta ciudadana no está vigente. Acércate a la municipalidad para regularizar.';
  let badge = 'Inactiva';
  let mensajeBox: string | null = null;
  let monto = 0;

  if (!alDia && estadoMuni) {
    titulo = 'Tarjeta inactiva por deuda';
    descripcion =
      'Detectamos una deuda pendiente en tu cuenta. Tu tarjeta queda inactiva ' +
      'hasta que regularices tu situación tributaria.';
    badge = 'Con deuda';
    mensajeBox = estadoMuni.mensaje;
    monto = estadoMuni.deuda_total;
  } else if (estaVencida(tarjeta.fecha_vencimiento)) {
    titulo = 'Tarjeta vencida';
    descripcion =
      'Tu tarjeta ciudadana venció. Acércate a la municipalidad para renovarla.';
    badge = 'Vencida';
  } else if (tarjeta.bloqueada) {
    titulo = 'Tarjeta bloqueada';
    descripcion =
      'Tu tarjeta fue bloqueada por la municipalidad. Consulta en ' +
      'plataforma para más información.';
    badge = 'Bloqueada';
    mensajeBox = tarjeta.motivo_bloqueo || null;
  }

  return (
    <MuniCard style={{ gap: Spacing.md, borderColor: MunicipalityColors.danger, borderWidth: 1 }}>
      <View style={styles.row}>
        <Text style={styles.titleCard}>{titulo}</Text>
        <MuniBadge label={badge} tone="danger" />
      </View>
      <Text style={styles.muted}>{descripcion}</Text>
      {mensajeBox || monto > 0 ? (
        <View style={styles.estadoBox}>
          {mensajeBox ? <Text style={styles.muted}>{mensajeBox}</Text> : null}
          {monto > 0 ? (
            <Text style={styles.deudaMonto}>S/ {monto.toFixed(2)}</Text>
          ) : null}
        </View>
      ) : null}
    </MuniCard>
  );
}

type CiudadanoDTO = {
  direccion?: string;
  nombre_completo?: string;
} | null;

function TarjetaVisual({
  tarjeta,
  ciudadano,
}: {
  tarjeta: Tarjeta;
  ciudadano: CiudadanoDTO;
}) {
  const anio = new Date(tarjeta.fecha_emision || Date.now()).getFullYear();
  const fv = new Date(tarjeta.fecha_vencimiento);
  const fvTxt = Number.isNaN(fv.getTime())
    ? ''
    : `${fv.getDate().toString().padStart(2, '0')}-${(fv.getMonth() + 1)
        .toString()
        .padStart(2, '0')}-${fv.getFullYear()}`;

  return (
    <View style={{ gap: Spacing.md }}>
      <View style={styles.card}>
        <View style={styles.cardHeaderBar}>
          <Text style={styles.cardHeaderBarText}>
            TARJETA DIGITAL DEL BUEN CONTRIBUYENTE BUSTAMANTINO
          </Text>
        </View>

        <View style={styles.cardBody}>
          <View style={styles.cardTopRow}>
            <View style={styles.cardBrandLeft}>
              <MuniLogo size={54} circularFrame />
              <View style={{ flexShrink: 1 }}>
                <Text style={styles.cardMuniName}>JOSE LUIS</Text>
                <Text style={styles.cardMuniName}>BUSTAMANTE</Text>
                <Text style={styles.cardMuniName}>Y RIVERO</Text>
              </View>
            </View>
            <View style={styles.cardBrandRight}>
              <Text style={styles.cardBrandRightLabel}>BUSTACARD</Text>
              <Text style={styles.cardBrandRightYear}>{anio}</Text>
            </View>
          </View>

          <View style={styles.cardInfoBlock}>
            <InfoRow label="CODIGO" value={tarjeta.codigo} />
            <InfoRow label="NOMBRE" value={tarjeta.nombre_completo} />
            <InfoRow label="DNI" value={tarjeta.dni} />
            {ciudadano?.direccion ? (
              <InfoRow label="DIRECCION" value={ciudadano.direccion} />
            ) : null}
          </View>

          <View style={styles.cardBarcode}>
            <MuniBarcode value={tarjeta.dni} height={64} />
          </View>

          {fvTxt ? <Text style={styles.cardFv}>F. V. {fvTxt}</Text> : null}
        </View>
      </View>

      <BeneficiosFijos />
    </View>
  );
}

function InfoRow({ label, value }: { label: string; value: string }) {
  return (
    <View style={styles.infoRow}>
      <Text style={styles.infoLabel}>{label}</Text>
      <Text style={styles.infoSep}>:</Text>
      <Text style={styles.infoValue} numberOfLines={2}>
        {value}
      </Text>
    </View>
  );
}

function BeneficiosFijos() {
  return (
    <MuniCard style={{ gap: Spacing.md }}>
      <View style={styles.benefRow}>
        <MaterialCommunityIcons
          name="format-list-checks"
          size={22}
          color={MunicipalityColors.primary}
        />
        <Text style={styles.benefTitulo}>TUS BENEFICIOS</Text>
      </View>

      <View style={styles.benefItem}>
        <MaterialCommunityIcons name="pool" size={26} color={MunicipalityColors.primary} />
        <View style={{ flex: 1 }}>
          <Text style={styles.benefNombre}>Ingreso Libre a Piscina</Text>
          <Text style={styles.benefHorario}>(Martes - Viernes)</Text>
        </View>
      </View>

      <View style={styles.benefItem}>
        <MaterialCommunityIcons name="pine-tree" size={26} color={MunicipalityColors.primary} />
        <View style={{ flex: 1 }}>
          <Text style={styles.benefNombre}>Ingreso Libre a Parque &apos;Ccoritos&apos;</Text>
          <Text style={styles.benefHorario}>(Martes - Viernes)</Text>
        </View>
      </View>

      <Text style={styles.benefNota}>
        Incluye Titular, Conyuge y 2 menores, o Adulto Mayor con acompanante.
      </Text>

      <View style={styles.benefImportante}>
        <Text style={styles.benefImportanteText}>
          IMPORTANTE: Mostrar DNI fisico + Bustacard digital.
        </Text>
      </View>

      <View style={styles.benefFooter}>
        <Text style={styles.benefArea}>Gerencia de Administracion Tributaria</Text>
        <Text style={styles.benefGracias}>Gracias por tu contribucion!</Text>
      </View>
    </MuniCard>
  );
}

const SILVER = '#D9DCE1';
const SILVER_DARK = '#9AA0A6';
const SILVER_LIGHT = '#EEF0F3';

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, paddingBottom: Spacing.xxl, gap: Spacing.md },
  titleCard: { fontSize: 16, fontWeight: '700', color: MunicipalityColors.primary },
  muted: { color: MunicipalityColors.textSecondary, fontSize: 13 },

  card: {
    backgroundColor: SILVER,
    borderRadius: Radius.xl,
    borderWidth: 1,
    borderColor: SILVER_DARK,
    overflow: 'hidden',
  },
  cardHeaderBar: {
    backgroundColor: MunicipalityColors.primary,
    paddingVertical: 8,
    paddingHorizontal: Spacing.md,
  },
  cardHeaderBarText: {
    color: MunicipalityColors.white,
    fontWeight: '800',
    fontSize: 11,
    letterSpacing: 0.5,
    textAlign: 'center',
  },
  cardBody: {
    padding: Spacing.lg,
    backgroundColor: SILVER_LIGHT,
    gap: Spacing.md,
  },
  cardTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.md,
  },
  cardBrandLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    flexShrink: 1,
  },
  cardMuniName: {
    fontSize: 11,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    letterSpacing: 0.4,
    lineHeight: 13,
  },
  cardBrandRight: { alignItems: 'flex-end' },
  cardBrandRightLabel: {
    fontSize: 14,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    letterSpacing: 1,
  },
  cardBrandRightYear: {
    fontSize: 28,
    fontWeight: '900',
    color: MunicipalityColors.accent,
    letterSpacing: 1,
    marginTop: -2,
  },

  cardInfoBlock: { gap: 2 },
  infoRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 6 },
  infoLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
    minWidth: 76,
    letterSpacing: 0.3,
  },
  infoSep: { fontSize: 12, color: MunicipalityColors.textPrimary },
  infoValue: { flex: 1, fontSize: 12, color: MunicipalityColors.textPrimary },

  cardBarcode: {
    marginTop: Spacing.sm,
    borderRadius: 4,
    overflow: 'hidden',
  },
  cardFv: {
    textAlign: 'center',
    fontSize: 11,
    color: MunicipalityColors.textSecondary,
    letterSpacing: 0.8,
    fontWeight: '600',
  },

  benefRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.sm },
  benefTitulo: {
    fontSize: 16,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    letterSpacing: 0.5,
  },
  benefItem: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.md,
  },
  benefNombre: {
    fontSize: 14,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  benefHorario: { fontSize: 12, color: MunicipalityColors.textSecondary },
  benefNota: {
    fontSize: 12,
    color: MunicipalityColors.textSecondary,
    fontStyle: 'italic',
  },
  benefImportante: {
    backgroundColor: MunicipalityColors.surface,
    borderLeftWidth: 3,
    borderLeftColor: MunicipalityColors.accent,
    padding: Spacing.sm,
    borderRadius: Radius.sm,
  },
  benefImportanteText: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  benefFooter: {
    borderTopWidth: 1,
    borderTopColor: MunicipalityColors.border,
    paddingTop: Spacing.sm,
    alignItems: 'center',
    gap: 2,
  },
  benefArea: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  benefGracias: {
    fontSize: 13,
    fontWeight: '800',
    color: MunicipalityColors.accent,
    fontStyle: 'italic',
  },

  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  beneficioNombre: {
    fontSize: 15,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
    flex: 1,
  },
  metaRow: { flexDirection: 'row', alignItems: 'center', gap: 4 },
  meta: { fontSize: 12, color: MunicipalityColors.textMuted },
  estadoBox: {
    gap: 6,
    padding: Spacing.md,
    borderRadius: Radius.md,
    backgroundColor: MunicipalityColors.surface,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    alignItems: 'flex-start',
  },
  deudaMonto: {
    fontSize: 22,
    fontWeight: '800',
    color: MunicipalityColors.danger,
  },
});
