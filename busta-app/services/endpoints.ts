import { api } from './api';
import type {
  AuthResponse,
  Beneficio,
  CatalogoFormularioTramite,
  CheckDniResponse,
  Ciudadano,
  Contacto,
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
