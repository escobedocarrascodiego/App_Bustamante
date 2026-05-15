import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Linking,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import { WebView } from 'react-native-webview';

import { MuniButton } from '@/components/muni/muni-button';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { catalogosApi } from '@/services/endpoints';
import type { Contacto, Lugar } from '@/services/types';
import { useAuth } from '@/store/auth-context';

type LugarConCoords = Lugar & { latitud: string; longitud: string };

function tieneCoordenadas(l: Lugar): l is LugarConCoords {
  return !!l.latitud && !!l.longitud;
}

function htmlMapa(lugares: Lugar[]): string {
  const puntos = lugares.filter(tieneCoordenadas).map((l) => ({
    nombre: l.nombre,
    descripcion: l.descripcion || '',
    tipo: l.tipo_display || l.tipo || '',
    direccion: l.direccion || '',
    latitud: Number(l.latitud),
    longitud: Number(l.longitud),
  }));
  return `
<!DOCTYPE html>
<html>
<head>
  <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    * { margin:0; padding:0; box-sizing:border-box; }
    html, body, #map {
      width: 100vw;
      height: 100vh;
      overflow: hidden;
      /* Evita que el navegador interprete pan/zoom como scroll de pagina */
      touch-action: none;
      -ms-touch-action: none;
      overscroll-behavior: none;
    }
  </style>
</head>
<body>
  <div id="map"></div>
  <script>
    var map = L.map('map', {
      zoomControl: true,
      tap: true,
      dragging: true,
      touchZoom: true,
      scrollWheelZoom: true,
      doubleClickZoom: true,
      boxZoom: false,
      keyboard: false,
      inertia: true
    }).setView([-16.4321, -71.5350], 14);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map);
    var lugares = ${JSON.stringify(puntos)};
    lugares.forEach(function(l) {
      L.marker([l.latitud, l.longitud])
       .addTo(map)
       .bindPopup(
         '<b>' + l.nombre + '</b>' +
         (l.tipo ? '<br><small>' + l.tipo + '</small>' : '') +
         (l.direccion ? '<br>' + l.direccion : '') +
         (l.descripcion ? '<br><i>' + l.descripcion + '</i>' : '')
       );
    });
  </script>
</body>
</html>
`;
}

export default function PerfilScreen() {
  const { ciudadano, logout } = useAuth();
  const [contactos, setContactos] = useState<Contacto[]>([]);
  const [lugares, setLugares] = useState<Lugar[]>([]);
  const [cargandoLugares, setCargandoLugares] = useState(true);

  const cargar = useCallback(async () => {
    setCargandoLugares(true);
    try {
      const [cs, ls] = await Promise.all([
        catalogosApi.contactos().catch((): Contacto[] => []),
        catalogosApi.lugares().catch((): Lugar[] => []),
      ]);
      setContactos(cs);
      setLugares(ls);
    } finally {
      setCargandoLugares(false);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const llamar = (tel: string) => {
    if (!tel) return;
    Linking.openURL(`tel:${tel.replace(/\s/g, '')}`);
  };

  const lugaresConCoords = useMemo(() => lugares.filter(tieneCoordenadas), [lugares]);
  const html = useMemo(() => htmlMapa(lugares), [lugares]);

  return (
    <View style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}>
      <MuniHeader title="Mi perfil" subtitle={ciudadano?.nombre_completo ?? ''} />
      <ScrollView contentContainerStyle={styles.content}>
        <MuniCard>
          <View style={styles.avatarRow}>
            <View style={styles.avatar}>
              <Text style={styles.avatarText}>
                {ciudadano?.nombres?.[0] ?? '?'}
                {ciudadano?.apellido_paterno?.[0] ?? ''}
              </Text>
            </View>
            <View style={{ flex: 1 }}>
              <Text style={styles.nombre}>{ciudadano?.nombre_completo}</Text>
              <Text style={styles.muted}>DNI {ciudadano?.dni}</Text>
              {ciudadano?.email ? <Text style={styles.muted}>{ciudadano.email}</Text> : null}
              {ciudadano?.celular ? <Text style={styles.muted}>Cel. {ciudadano.celular}</Text> : null}
            </View>
          </View>
        </MuniCard>

        <Text style={styles.sectionTitle}>Lugares de interés</Text>
        {cargandoLugares ? (
          <View style={styles.lugaresLoader}>
            <ActivityIndicator color={MunicipalityColors.primary} />
          </View>
        ) : lugaresConCoords.length === 0 ? (
          <MuniCard>
            <Text style={styles.muted}>No hay lugares registrados aún.</Text>
          </MuniCard>
        ) : (
          // El View envolvente captura los touch events ANTES de que los
          // reciba el ScrollView padre — sin esto, mover/zoom del mapa se
          // interpreta como scroll de la pantalla. nestedScrollEnabled +
          // scrollEnabled=false en el WebView dejan que Leaflet maneje
          // todos sus gestos internamente.
          <View
            style={styles.mapaWrap}
            onStartShouldSetResponder={() => true}
            onMoveShouldSetResponder={() => true}
            onResponderTerminationRequest={() => false}>
            <WebView
              source={{ html }}
              style={styles.mapaWebview}
              originWhitelist={['*']}
              javaScriptEnabled
              domStorageEnabled
              nestedScrollEnabled
              scrollEnabled={false}
              overScrollMode="never"
              bounces={false}
              androidLayerType="hardware"
              setSupportMultipleWindows={false}
            />
          </View>
        )}

        {lugares.length > 0 ? (
          <View style={styles.chipsWrap}>
            {lugares.map((l) => (
              <View key={l.id} style={styles.chip}>
                <Text style={styles.chipNombre} numberOfLines={1}>
                  {l.nombre}
                </Text>
                {l.tipo_display ? (
                  <Text style={styles.chipTipo} numberOfLines={1}>
                    {l.tipo_display}
                  </Text>
                ) : null}
              </View>
            ))}
          </View>
        ) : null}

        <Text style={styles.sectionTitle}>Contactos municipales</Text>
        {contactos.map((c) => (
          <MuniCard key={c.id} style={{ gap: 4 }}>
            <View style={styles.row}>
              <Text style={styles.area}>{c.area}</Text>
              {c.telefono ? (
                <Pressable style={styles.iconBtn} onPress={() => llamar(c.telefono)}>
                  <MaterialCommunityIcons name="phone" size={18} color={MunicipalityColors.primary} />
                </Pressable>
              ) : null}
            </View>
            {c.responsable ? <Text style={styles.muted}>Responsable: {c.responsable}</Text> : null}
            {c.horario ? <Text style={styles.muted}>{c.horario}</Text> : null}
            {c.email ? <Text style={styles.muted}>{c.email}</Text> : null}
          </MuniCard>
        ))}

        <MuniButton label="Cerrar sesion" variant="danger" onPress={logout} />
        <Text style={[styles.muted, { textAlign: 'center' }]}>
          Municipalidad Distrital JLBR - v1.0
        </Text>
      </ScrollView>
    </View>
  );
}

const styles = StyleSheet.create({
  content: { padding: Spacing.lg, gap: Spacing.md, paddingBottom: Spacing.xxl },
  avatarRow: { flexDirection: 'row', alignItems: 'center', gap: Spacing.md },
  avatar: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: MunicipalityColors.primary,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarText: {
    color: MunicipalityColors.accent,
    fontWeight: '800',
    fontSize: 20,
  },
  nombre: {
    fontSize: 16,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  muted: { color: MunicipalityColors.textSecondary, fontSize: 13 },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
    marginTop: Spacing.sm,
  },
  row: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  area: { fontWeight: '700', color: MunicipalityColors.primary, flex: 1 },
  iconBtn: {
    padding: 8,
    borderRadius: Radius.pill,
    backgroundColor: '#E3EBFB',
  },
  // Lugares de interés
  lugaresLoader: {
    paddingVertical: Spacing.lg,
    alignItems: 'center',
  },
  mapaWrap: {
    width: '100%',
    height: 300,
    borderRadius: 12,
    overflow: 'hidden',
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    backgroundColor: MunicipalityColors.white,
  },
  mapaWebview: { flex: 1 },
  chipsWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: Spacing.sm,
  },
  chip: {
    backgroundColor: MunicipalityColors.white,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    borderRadius: Radius.pill,
    paddingHorizontal: Spacing.md,
    paddingVertical: 6,
    maxWidth: '48%',
  },
  chipNombre: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textPrimary,
  },
  chipTipo: {
    fontSize: 10,
    color: MunicipalityColors.textMuted,
    marginTop: 1,
  },
});
