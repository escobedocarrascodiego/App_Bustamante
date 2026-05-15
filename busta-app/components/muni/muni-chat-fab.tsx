import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { Platform, Pressable, StyleSheet } from 'react-native';

const CHAT_FAB_COLOR = '#185FA5';

type Props = {
  /** Margen desde el bottom del contenedor padre. Default 16. */
  bottom?: number;
  /** Margen desde el right del contenedor padre. Default 16. */
  right?: number;
};

/**
 * Floating Action Button del chatbot. Se posiciona en absoluto sobre su
 * contenedor padre — por ahora solo se renderiza desde la pantalla Inicio.
 * Al tocarlo abre la ruta `/chat` como modal.
 */
export function MuniChatFab({ bottom = 16, right = 16 }: Props) {
  return (
    <Pressable
      // El cast a `never` es necesario solo hasta que expo-router regenere
      // sus types (.expo/types/router.d.ts) al proximo `expo start`. La ruta
      // `/chat` existe en disco (app/chat.tsx) y Metro la registra solo.
      onPress={() => router.push('/chat' as never)}
      style={({ pressed }) => [
        styles.fab,
        { bottom, right },
        pressed && styles.fabPressed,
      ]}
      accessibilityLabel="Abrir asistente virtual"
      accessibilityRole="button">
      <MaterialCommunityIcons
        name="chat-processing"
        size={26}
        color="#FFFFFF"
      />
    </Pressable>
  );
}

const styles = StyleSheet.create({
  fab: {
    position: 'absolute',
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: CHAT_FAB_COLOR,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 999,
    ...Platform.select({
      ios: {
        shadowColor: '#000',
        shadowOpacity: 0.25,
        shadowRadius: 6,
        shadowOffset: { width: 0, height: 3 },
      },
      android: { elevation: 6 },
    }),
  },
  fabPressed: { opacity: 0.85 },
});
