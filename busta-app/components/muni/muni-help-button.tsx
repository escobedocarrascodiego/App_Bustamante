import { MaterialCommunityIcons } from '@expo/vector-icons';
import { useState } from 'react';
import { Pressable, StyleSheet } from 'react-native';

import { MunicipalityColors } from '@/constants/theme';
import type { VideoTutorial } from '@/constants/videos';
import { MuniVideoModal } from './muni-video-modal';

type Props = {
  video: VideoTutorial;
  /** Color del icono. Por defecto blanco (para usarse sobre el header azul). */
  color?: string;
  size?: number;
  /** Si true muestra un circulito de fondo para destacar el boton. */
  pill?: boolean;
};

/**
 * Icono "?" que al tocar abre un modal con el video tutorial. Pensado para
 * embebir en headers o esquinas de pantallas.
 */
export function MuniHelpButton({ video, color, size = 22, pill = true }: Props) {
  const [open, setOpen] = useState(false);
  const iconColor = color ?? MunicipalityColors.white;
  return (
    <>
      <Pressable
        onPress={() => setOpen(true)}
        hitSlop={10}
        style={[
          styles.btn,
          pill && {
            backgroundColor: 'rgba(255,255,255,0.18)',
            padding: 6,
            borderRadius: 999,
          },
        ]}
        accessibilityLabel={`Ver tutorial: ${video.titulo}`}>
        <MaterialCommunityIcons name="help-circle-outline" size={size} color={iconColor} />
      </Pressable>
      <MuniVideoModal
        visible={open}
        videoId={video.videoId}
        titulo={video.titulo}
        descripcion={video.descripcion}
        onClose={() => setOpen(false)}
      />
    </>
  );
}

const styles = StyleSheet.create({
  btn: { alignItems: 'center', justifyContent: 'center' },
});
