import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import {
  ActivityIndicator,
  Dimensions,
  Modal,
  Pressable,
  StyleSheet,
  Text,
  View,
} from 'react-native';
import YoutubePlayer from 'react-native-youtube-iframe';

import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';

type Props = {
  visible: boolean;
  videoId: string;
  titulo: string;
  descripcion?: string;
  onClose: () => void;
};

/**
 * Modal con un player de YouTube embebido. Se usa para mostrar tutoriales
 * (registro MPV, pago en linea, etc.) sin sacar al usuario del app. Los
 * controles de play/pausa/fullscreen los maneja el propio player de YouTube.
 */
export function MuniVideoModal({
  visible,
  videoId,
  titulo,
  descripcion,
  onClose,
}: Props) {
  const [ready, setReady] = useState(false);
  const width = Dimensions.get('window').width - Spacing.lg * 2;
  const height = Math.round((width * 9) / 16); // aspect ratio 16:9

  return (
    <Modal
      visible={visible}
      animationType="slide"
      transparent
      onRequestClose={onClose}>
      <View style={styles.backdrop}>
        <View style={styles.card}>
          <View style={styles.header}>
            <View style={{ flex: 1 }}>
              <Text style={styles.titulo}>{titulo}</Text>
              {descripcion ? (
                <Text style={styles.descripcion}>{descripcion}</Text>
              ) : null}
            </View>
            <Pressable onPress={onClose} hitSlop={10} style={styles.closeBtn}>
              <MaterialCommunityIcons
                name="close"
                size={22}
                color={MunicipalityColors.textPrimary}
              />
            </Pressable>
          </View>

          <View style={[styles.playerBox, { width, height }]}>
            {!ready ? (
              <View style={styles.loader}>
                <ActivityIndicator color={MunicipalityColors.primary} />
                <Text style={styles.loaderText}>Cargando video...</Text>
              </View>
            ) : null}
            <YoutubePlayer
              height={height}
              width={width}
              videoId={videoId}
              onReady={() => setReady(true)}
            />
          </View>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  backdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.55)',
    justifyContent: 'center',
    padding: Spacing.lg,
  },
  card: {
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.xl,
    padding: Spacing.lg,
    gap: Spacing.md,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: Spacing.sm,
  },
  titulo: {
    fontSize: 16,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
  },
  descripcion: {
    fontSize: 12,
    color: MunicipalityColors.textSecondary,
    marginTop: 4,
    lineHeight: 16,
  },
  closeBtn: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    backgroundColor: '#F1F5F9',
    borderRadius: 16,
  },
  playerBox: {
    backgroundColor: '#000',
    borderRadius: Radius.md,
    overflow: 'hidden',
    alignSelf: 'center',
  },
  loader: {
    position: 'absolute',
    inset: 0,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    zIndex: 1,
  },
  loaderText: {
    color: MunicipalityColors.white,
    fontSize: 12,
  },
});
