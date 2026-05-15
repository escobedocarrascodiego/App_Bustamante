import { getChatbotBaseUrl } from '@/constants/config';
import { api } from './api';
import type {
  AuthResponse,
  Beneficio,
  CatalogoFormularioTramite,
  ChatbotEnviarMensajeResponse,
  ChatbotHistorialResponse,
  ChatbotNuevaSesionResponse,
  GerenciaChatbot,
  CheckDniResponse,
  Ciudadano,
  Contacto,
  DatosPersonalesOmitido,
  Deuda,
  DeudaDetalleResponse,
  DeudaMuniResult,
  Expediente,
  ExpedienteSiap,
  ExpedienteSiapDetalle,
  Lugar,
  Noticia,
  Paginated,
  RegistroTramiteExterno,
  ResumenDeudas,
  Tarjeta,
  TipoTramite,
  VerificarMpvResponse,
} from './types';

type AnyList<T> = T[] | Paginated<T>;

function unwrapList<T>(data: AnyList<T>): T[] {
  if (Array.isArray(data)) return data;
  return data.results;
}

export const authApi = {
  checkDni: (dni: string) =>
    api.post<CheckDniResponse>('/ciudadanos/check-dni/', { dni }, { auth: false }),
  login: (dni: string, password: string) =>
    api.post<AuthResponse>(
      '/ciudadanos/login/',
      { dni, password },
      { auth: false },
    ),
  register: (dni: string, password: string) =>
    api.post<AuthResponse>(
      '/ciudadanos/register/',
      { dni, password },
      { auth: false },
    ),
  registerOmitido: (
    dni: string,
    password: string,
    datosPersonales?: DatosPersonalesOmitido,
  ) =>
    api.post<AuthResponse>(
      '/ciudadanos/register-omitido/',
      datosPersonales
        ? { dni, password, ...datosPersonales }
        : { dni, password },
      { auth: false },
    ),
  verificarMpv: () =>
    api.post<VerificarMpvResponse>('/ciudadanos/verificar-mpv/'),
  perfil: () => api.get<Ciudadano>('/ciudadanos/perfil/'),
  actualizarPerfil: (payload: Partial<Ciudadano>) =>
    api.patch<Ciudadano>('/ciudadanos/perfil/', payload),
};

export const deudasApi = {
  listar: async () => unwrapList(await api.get<AnyList<Deuda>>('/deudas/')),
  resumen: () => api.get<ResumenDeudas>('/deudas/resumen/'),
  verificarMuni: () => api.get<DeudaMuniResult>('/deudas/muni/'),
  detalle: (prdconcod?: number) =>
    api.get<DeudaDetalleResponse>(
      prdconcod ? `/deudas/detalle/?prdconcod=${prdconcod}` : '/deudas/detalle/',
    ),
  pagar: (id: number, numeroOperacion?: string) =>
    api.post(`/deudas/${id}/pagar/`, { numero_operacion: numeroOperacion ?? '' }),
};

export const tramitesApi = {
  tipos: async () => unwrapList(await api.get<AnyList<TipoTramite>>('/tramites/tipos/')),
  misExpedientes: async () =>
    unwrapList(await api.get<AnyList<Expediente>>('/tramites/expedientes/')),
  misExpedientesSiap: () =>
    api.get<ExpedienteSiap[]>('/tramites/mis-expedientes-siap/'),
  detalleExpedienteSiap: (codIng: number) =>
    api.get<ExpedienteSiapDetalle>(`/tramites/expediente-siap/${codIng}/`),
  catalogoFormulario: () =>
    api.get<CatalogoFormularioTramite>('/tramites/catalogo-formulario/'),
  registrarTramiteExterno: (form: FormData) =>
    api.post<RegistroTramiteExterno>('/tramites/registrar-tramite-externo/', form),
  iniciarExpediente: (payload: { tipo: number; asunto: string; detalle?: string }) =>
    api.post<Expediente>('/tramites/expedientes/', payload),
  detalleExpediente: (id: number) =>
    api.get<Expediente>(`/tramites/expedientes/${id}/`),
};

export const tarjetasApi = {
  miTarjeta: () => api.get<Tarjeta>('/tarjetas/mi-tarjeta/'),
  emitir: () => api.post<Tarjeta>('/tarjetas/mi-tarjeta/'),
  beneficios: async () =>
    unwrapList(await api.get<AnyList<Beneficio>>('/tarjetas/beneficios/')),
};

export const catalogosApi = {
  noticias: async () => unwrapList(await api.get<AnyList<Noticia>>('/catalogos/noticias/')),
  lugares: async () => unwrapList(await api.get<AnyList<Lugar>>('/catalogos/lugares/')),
  contactos: async () =>
    unwrapList(await api.get<AnyList<Contacto>>('/catalogos/contactos/')),
};

/**
 * Chatbot publico — vive bajo `/api/chatbot/` (fuera del prefijo v1).
 * Endpoints publicos: no requieren JWT, pero si hay sesion autenticada el
 * backend asocia el ciudadano a la conversacion para reportes.
 */
export const chatbotApi = {
  gerencias: () =>
    api.get<GerenciaChatbot[]>('/gerencias/', {
      baseUrl: getChatbotBaseUrl(),
      auth: true,
    }),
  nuevaSesion: () =>
    api.post<ChatbotNuevaSesionResponse>(
      '/sesion/nueva/',
      undefined,
      { baseUrl: getChatbotBaseUrl(), auth: true },
    ),
  enviarMensaje: (
    sesion_id: string,
    mensaje: string,
    gerencia_id?: number,
  ) =>
    api.post<ChatbotEnviarMensajeResponse>(
      '/mensaje/',
      gerencia_id !== undefined
        ? { sesion_id, mensaje, gerencia_id }
        : { sesion_id, mensaje },
      { baseUrl: getChatbotBaseUrl(), auth: true },
    ),
  historial: (sesion_id: string) =>
    api.get<ChatbotHistorialResponse>(
      `/sesion/historial/?sesion_id=${encodeURIComponent(sesion_id)}`,
      { baseUrl: getChatbotBaseUrl(), auth: true },
    ),
};
