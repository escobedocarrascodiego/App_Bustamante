import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useCallback, useEffect, useState } from 'react';
import { Linking, Pressable, ScrollView, StyleSheet, Text, View } from 'react-native';

import { MuniButton } from '@/components/muni/muni-button';
import { MuniCard } from '@/components/muni/muni-card';
import { MuniHeader } from '@/components/muni/muni-header';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { catalogosApi } from '@/services/endpoints';
import type { Contacto } from '@/services/types';
import { useAuth } from '@/store/auth-context';

export default function PerfilScreen() {
  const { ciudadano, logout } = useAuth();
  const [contactos, setContactos] = useState<Contacto[]>([]);

  const cargar = useCallback(async () => {
    try {
      const data = await catalogosApi.contactos();
      setContactos(data);
    } catch {
      setContactos([]);
    }
  }, []);

  useEffect(() => {
    void cargar();
  }, [cargar]);

  const llamar = (tel: string) => {
    if (!tel) return;
    Linking.openURL(`tel:${tel.replace(/\s/g, '')}`);
  };

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
});
