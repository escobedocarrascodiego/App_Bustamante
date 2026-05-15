import { MaterialCommunityIcons } from '@expo/vector-icons';
import { Tabs } from 'expo-router';
import React from 'react';
import { useSafeAreaInsets } from 'react-native-safe-area-context';

import { HapticTab } from '@/components/haptic-tab';
import { MunicipalityColors } from '@/constants/theme';

type TabIconName = React.ComponentProps<typeof MaterialCommunityIcons>['name'];

function tabIcon(name: TabIconName) {
  return ({ color, size }: { color: string; size: number }) => (
    <MaterialCommunityIcons name={name} size={size} color={color} />
  );
}

export default function TabLayout() {
  const insets = useSafeAreaInsets();
  // Altura base de la tab bar + espacio extra para no quedar tapados por
  // la gesture bar / home indicator del sistema (Android moderno e iOS).
  const baseHeight = 62;
  const safeBottom = insets.bottom;

  return (
    <Tabs
      screenOptions={{
        tabBarActiveTintColor: MunicipalityColors.primary,
        tabBarInactiveTintColor: MunicipalityColors.textMuted,
        tabBarStyle: {
          backgroundColor: MunicipalityColors.white,
          borderTopColor: MunicipalityColors.border,
          paddingTop: 6,
          paddingBottom: safeBottom,
          height: baseHeight + safeBottom,
        },
        tabBarLabelStyle: { fontSize: 11, fontWeight: '600' },
        headerShown: false,
        tabBarButton: HapticTab,
      }}>
      <Tabs.Screen
        name="index"
        options={{ title: 'Inicio', tabBarIcon: tabIcon('home-city') }}
      />
      <Tabs.Screen
        name="deudas"
        options={{ title: 'Deudas', tabBarIcon: tabIcon('cash-multiple') }}
      />
      <Tabs.Screen
        name="tramites"
        options={{ title: 'Tramites', tabBarIcon: tabIcon('file-document-multiple') }}
      />
      <Tabs.Screen
        name="tarjeta"
        options={{ title: 'Tarjeta', tabBarIcon: tabIcon('card-account-details') }}
      />
      <Tabs.Screen
        name="perfil"
        options={{ title: 'Perfil', tabBarIcon: tabIcon('account-circle') }}
      />
    </Tabs>
  );
}
