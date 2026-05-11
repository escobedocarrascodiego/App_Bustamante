/**
 * Catalogo de videos tutoriales (YouTube). Centralizado aca para que se
 * actualice en un solo lugar si cambian los IDs o aparecen nuevos videos.
 */

export type VideoTutorial = {
  id: string;
  videoId: string;       // ID de YouTube (lo que va despues de ?v=)
  titulo: string;
  descripcion: string;
};

export const VIDEO_REGISTRO_MPV: VideoTutorial = {
  id: 'registro_mpv',
  videoId: '-cFs3vKSh_w',
  titulo: 'Cómo registrarte en Mesa de Partes Virtual',
  descripcion:
    'Paso a paso para crear tu cuenta en el portal MPV y habilitar el ingreso ' +
    'de trámites desde el app.',
};

export const VIDEO_PAGO_EN_LINEA: VideoTutorial = {
  id: 'pago_en_linea',
  videoId: 'tgdWZNwDUg8',
  titulo: 'Cómo pagar tus tributos en línea',
  descripcion:
    'Aprende a cancelar tus deudas (predial, arbitrios, serenazgo) desde el ' +
    'portal de pagos de la Municipalidad.',
};
