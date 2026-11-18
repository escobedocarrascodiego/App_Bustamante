import * as Haptics from 'expo-haptics';
import type { BottomTabBarButtonProps } from 'expo-router/js-tabs';
import { PlatformPressable } from 'expo-router/react-navigation';

/**
 * Desde SDK 56 expo-router trae su propia copia de react-navigation y ya no es
 * compatible con los paquetes @react-navigation/* sueltos. La API en runtime es
 * la misma; solo cambia de donde se importa.
 */
export function HapticTab(props: BottomTabBarButtonProps) {
  return (
    <PlatformPressable
      {...props}
      onPressIn={(ev) => {
        if (process.env.EXPO_OS === 'ios') {
          // Add a soft haptic feedback when pressing down on the tabs.
          Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
        }
        props.onPressIn?.(ev);
      }}
    />
  );
}
