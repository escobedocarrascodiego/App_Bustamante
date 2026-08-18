/**
 * Atención en ventanilla — pantalla única que combina:
 *   1. Monitor de colas (cómo van las filas, en vivo).
 *   2. Pedir turno (queda RESERVADO, "en camino").
 *   3. Mi turno: "Ya llegué" (check-in), avance y aviso cuando me llaman.
 *
 * Se adapta sola según el estado del turno del usuario. Refresca por polling.
 */
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useRef, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  Vibration,
  View,
} from 'react-native';

import { MuniButton } from '@/components/muni/muni-button';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { ApiError } from '@/services/api';
import { colasApi } from '@/services/endpoints';
import type { ColaServicio, MiTurno } from '@/services/types';

export default function TurnosScreen() {
  const [colas, setColas] = useState<ColaServicio[]>([]);
  const [miTurno, setMiTurno] = useState<MiTurno | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [ocupado, setOcupado] = useState(false);
  const [prioritario, setPrioritario] = useState(false);
  const estadoPrevio = useRef<string | null>(null);

  const cargar = useCallback(async () => {
    try {
      const [c, t] = await Promise.all([
        colasApi.estado().catch(() => [] as ColaServicio[]),
        colasApi.miTurno().catch(() => null),
      ]);
      setColas(c);
      setMiTurno(t);
      // Vibra cuando pasa a "LLAMADO" (te toca).
      if (t?.estado === 'LLAMADO' && estadoPrevio.current !== 'LLAMADO') {
        Vibration.vibrate([0, 400, 200, 400]);
      }
      estadoPrevio.current = t?.estado ?? null;
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
    const id = setInterval(() => void cargar(), 4000);
    return () => clearInterval(id);
  }, [cargar]);

  const pedir = async (servicioId: number) => {
    if (ocupado) return;
    setOcupado(true);
    try {
      const r = await colasApi.pedirTurno(servicioId, prioritario);
      setMiTurno(r.turno);
      setPrioritario(false);
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        await cargar(); // ya tenía un turno
      } else {
        Alert.alert('No se pudo', 'No pudimos generar tu turno. Intenta de nuevo.');
      }
    } finally {
      setOcupado(false);
    }
  };

  const yaLlegue = async () => {
    if (ocupado) return;
    setOcupado(true);
    try {
      const r = await colasApi.yaLlegue();
      setMiTurno(r.turno);
    } catch {
      Alert.alert('No se pudo', 'Intenta de nuevo en un momento.');
    } finally {
      setOcupado(false);
    }
  };

  const cancelar = async () => {
    Alert.alert('Cancelar turno', '¿Seguro que quieres cancelar tu turno?', [
      { text: 'No', style: 'cancel' },
      {
        text: 'Sí, cancelar',
        style: 'destructive',
        onPress: async () => {
          setOcupado(true);
          try {
            await colasApi.cancelar();
            setMiTurno(null);
          } catch {
            // Si ya no es cancelable (te llamaron justo ahora), refrescamos
            // el estado en vez de romper con un error.
            await cargar();
          } finally {
            setOcupado(false);
          }
        },
      },
    ]);
  };

  return (
    <View style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}>
      <MuniHeader title="Atención en ventanilla" subtitle="Turnos de Rentas" />
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
        {loading ? (
          <View style={{ paddingVertical: Spacing.xl }}>
            <ActivityIndicator color={MunicipalityColors.primary} />
          </View>
        ) : (
          <>
            {/* MI TURNO (si tengo uno activo) */}
            {miTurno ? (
              <MiTurnoCard
                turno={miTurno}
                ocupado={ocupado}
                onYaLlegue={yaLlegue}
                onCancelar={cancelar}
              />
            ) : (
              <PedirTurno
                colas={colas}
                prioritario={prioritario}
                onTogglePref={() => setPrioritario((v) => !v)}
                ocupado={ocupado}
                onPedir={pedir}
              />
            )}

            {/* MONITOR DE COLAS */}
            <Text style={styles.sectionTitle}>Cómo van las colas</Text>
            {colas.length === 0 ? (
              <MuniCard>
                <Text style={styles.muted}>No hay colas disponibles ahora.</Text>
              </MuniCard>
            ) : (
              colas.map((c) => (
                <MuniCard key={c.id} style={styles.colaRow}>
                  <View style={{ flex: 1 }}>
                    <Text style={styles.colaNombre}>{c.nombre}</Text>
                    <Text style={styles.muted}>
                      {c.en_espera === 0
                        ? 'Sin espera'
                        : `${c.en_espera} en espera · ~${c.tiempo_estimado_min} min`}
                    </Text>
                  </View>
                  <View style={styles.colaNumWrap}>
                    <Text style={styles.colaNum}>{c.en_espera}</Text>
                  </View>
                </MuniCard>
              ))
            )}
          </>
        )}
      </ScrollView>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Pedir turno (cuando no tengo uno)
// ---------------------------------------------------------------------------
function PedirTurno({
  colas,
  prioritario,
  onTogglePref,
  ocupado,
  onPedir,
}: {
  colas: ColaServicio[];
  prioritario: boolean;
  onTogglePref: () => void;
  ocupado: boolean;
  onPedir: (servicioId: number) => void;
}) {
  return (
    <MuniCard style={{ gap: Spacing.md }}>
      <Text style={styles.cardTitle}>Saca tu turno</Text>
      <Text style={styles.muted}>
        Reserva desde aquí y, cuando llegues a la municipalidad, confirma con
        “Ya llegué”. Tu lugar en la fila se asigna al llegar.
      </Text>

      <Pressable style={styles.prefRow} onPress={onTogglePref}>
        <MaterialCommunityIcons
          name={prioritario ? 'checkbox-marked' : 'checkbox-blank-outline'}
          size={24}
          color={MunicipalityColors.primary}
        />
        <Text style={styles.prefText}>
          Atención preferente (gestante, adulto mayor, discapacidad)
        </Text>
      </Pressable>

      <View style={{ gap: Spacing.sm }}>
        {colas.map((c) => (
          <MuniButton
            key={c.id}
            label={colas.length === 1 ? 'Pedir turno' : c.nombre}
            onPress={() => onPedir(c.id)}
            loading={ocupado}
            disabled={ocupado}
          />
        ))}
      </View>
    </MuniCard>
  );
}

// ---------------------------------------------------------------------------
// Mi turno (adaptativo según estado)
// ---------------------------------------------------------------------------
function MiTurnoCard({
  turno,
  ocupado,
  onYaLlegue,
  onCancelar,
}: {
  turno: MiTurno;
  ocupado: boolean;
  onYaLlegue: () => void;
  onCancelar: () => void;
}) {
  const llamado = turno.estado === 'LLAMADO' || turno.estado === 'EN_ATENCION';

  return (
    <MuniCard
      style={[
        { gap: Spacing.md, borderWidth: 1 },
        llamado
          ? { borderColor: MunicipalityColors.success, backgroundColor: '#F0FDF4' }
          : { borderColor: MunicipalityColors.border },
      ]}>
      <View style={styles.turnoTop}>
        <Text style={styles.turnoLabel}>TU TURNO</Text>
        {turno.prioritario ? (
          <View style={styles.prefBadge}>
            <Text style={styles.prefBadgeText}>PREFERENTE</Text>
          </View>
        ) : null}
      </View>
      <Text style={[styles.turnoCodigo, llamado && { color: MunicipalityColors.success }]}>
        {turno.codigo}
      </Text>
      <Text style={styles.muted}>{turno.servicio}</Text>

      {/* Cuerpo según estado */}
      {turno.estado === 'RESERVADO' ? (
        <>
          <View style={styles.infoBox}>
            <MaterialCommunityIcons name="walk" size={18} color={MunicipalityColors.info} />
            <Text style={styles.infoText}>
              Reservado. Cuando llegues a la municipalidad, toca “Ya llegué”
              para entrar a la fila.
            </Text>
          </View>
          <MuniButton
            label="Ya llegué"
            variant="accent"
            onPress={onYaLlegue}
            loading={ocupado}
            iconLeft={
              <MaterialCommunityIcons name="map-marker-check" size={18} color="#3a2c00" />
            }
          />
        </>
      ) : llamado ? (
        <View style={styles.llamadoBox}>
          <MaterialCommunityIcons name="bell-ring" size={22} color={MunicipalityColors.success} />
          <Text style={styles.llamadoText}>
            {turno.estado === 'LLAMADO' ? '¡Es tu turno! ' : 'Te están atendiendo en '}
            Ventanilla {turno.ventanilla}
          </Text>
        </View>
      ) : (
        <View style={styles.esperaBox}>
          <Text style={styles.esperaNum}>
            {turno.personas_adelante ?? 0}
          </Text>
          <Text style={styles.muted}>
            {turno.personas_adelante === 0
              ? 'Eres el siguiente'
              : 'personas delante de ti'}
          </Text>
        </View>
      )}

      {turno.estado === 'RESERVADO' || turno.estado === 'EN_ESPERA' ? (
        <Pressable onPress={onCancelar} disabled={ocupado} style={styles.cancelar}>
          <Text style={styles.cancelarText}>Cancelar turno</Text>
        </Pressable>
      ) : null}
    </MuniCard>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  cardTitle: { fontSize: 18, fontWeight: '700', color: MunicipalityColors.primary },
  muted: { color: MunicipalityColors.textSecondary, fontSize: 13 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
    marginTop: Spacing.sm,
  },
  prefRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.surface,
    borderRadius: Radius.md,
    padding: Spacing.sm,
  },
  prefText: { flex: 1, fontSize: 13, color: MunicipalityColors.textSecondary },
  // monitor
  colaRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  colaNombre: { fontSize: 15, fontWeight: '700', color: MunicipalityColors.textPrimary },
  colaNumWrap: {
    minWidth: 48,
    height: 48,
    borderRadius: Radius.md,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 8,
  },
  colaNum: { fontSize: 22, fontWeight: '800', color: MunicipalityColors.primary },
  // mi turno
  turnoTop: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  turnoLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textMuted,
    letterSpacing: 1,
  },
  turnoCodigo: {
    fontSize: 52,
    fontWeight: '900',
    color: MunicipalityColors.primary,
    lineHeight: 56,
  },
  prefBadge: {
    backgroundColor: '#FEF3C7',
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 999,
  },
  prefBadgeText: { color: '#92400E', fontWeight: '800', fontSize: 11 },
  infoBox: {
    flexDirection: 'row',
    gap: 8,
    backgroundColor: '#EFF6FF',
    borderRadius: Radius.md,
    padding: Spacing.md,
    alignItems: 'flex-start',
  },
  infoText: { flex: 1, fontSize: 13, color: MunicipalityColors.info, lineHeight: 18 },
  llamadoBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    backgroundColor: '#DCFCE7',
    borderRadius: Radius.md,
    padding: Spacing.md,
  },
  llamadoText: { flex: 1, fontSize: 16, fontWeight: '800', color: MunicipalityColors.success },
  esperaBox: { alignItems: 'center', paddingVertical: Spacing.sm },
  esperaNum: { fontSize: 44, fontWeight: '900', color: MunicipalityColors.primary },
  cancelar: { alignItems: 'center', paddingVertical: 4 },
  cancelarText: { color: MunicipalityColors.danger, fontWeight: '700', fontSize: 13 },
});
