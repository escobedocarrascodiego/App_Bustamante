export type Ciudadano = {
  id: number;
  dni: string;
  nombres: string;
  apellido_paterno: string;
  apellido_materno: string;
  nombre_completo: string;
  email: string;
  celular: string;
  direccion: string;
  fecha_nacimiento: string | null;
  cod_pro: string | null;
  cntr_cod: number | null;
  es_propietario: boolean;
  verificado: boolean;
  fecha_registro: string;
};

export type AuthResponse = {
  access: string;
  refresh: string;
  ciudadano: Ciudadano;
};

export type CheckDniPaso = 'PASSWORD_LOGIN' | 'PASSWORD_NUEVO' | 'BLOQUEADO';

export type CheckDniResponse = {
  paso: CheckDniPaso;
  razon: string;
  mensaje: string;
  nombre?: string;
  apellido_paterno?: string;
  email_enmascarado?: string;
  link_registro: string;
};

export type Paginated<T> = {
  count: number;
  next: string | null;
  previous: string | null;
  results: T[];
};

export type TipoDeuda =
  | 'PREDIAL'
  | 'ARBITRIOS'
  | 'MULTA'
  | 'PAPELETA'
  | 'OTRO';

export type EstadoDeuda =
  | 'PENDIENTE'
  | 'VENCIDA'
  | 'PAGADA'
  | 'FRACCIONADA';

export type Pago = {
  id: number;
  deuda: number;
  monto: string;
  fecha: string;
  medio: 'CAJA' | 'BANCO' | 'APP' | 'WEB';
  numero_operacion: string;
};

export type Deuda = {
  id: number;
  tipo: TipoDeuda;
  tipo_display: string;
  concepto: string;
  anio: number;
  periodo: string;
  monto: string;
  interes: string;
  descuento: string;
  total: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  estado: EstadoDeuda;
  estado_display: string;
  codigo_referencia: string;
  pagos: Pago[];
};

export type ResumenDeudas = {
  total_pendiente: string | number;
  cantidad_pendientes: number;
  por_tipo: { tipo: TipoDeuda; total: string | number }[];
};

export type EstadoBustaCard =
  | 'AL_DIA'
  | 'TIENE_DEUDA'
  | 'NO_PROPIETARIO'
  | 'SIN_CONTRIBUYENTE'
  | 'ERROR';

export type DeudaDetalleItem = {
  origen:
    | 'DEUDA REGISTRADA'
    | 'PREDIAL NO GENERADO (TITULAR)'
    | 'SERENAZGO NO GENERADO'
    | 'ARBITRIOS NO GENERADOS'
    | string;
  concepto: string;
  sub_rubro: string | null;
  anio: number | null;
  mes: number | null;
  predio_cod: string | null;
  prd_con_cod: number | null;        // 1=PU, 4=SC, etc
  condicion_nombre: string | null;
  importe_original: number;
  cargos_reajuste: number;
  pagado: number;
  saldo_pendiente: number;
};

export type CondicionContribuyente = {
  prd_con_cod: number;
  nombre: string;     // "PROPIETARIO UNICO", "SOCIEDAD CONYUGAL", etc.
  deuda_total: number;
};

export type DeudaDetalleResponse = {
  items: DeudaDetalleItem[];
  total: number;
  cntrcod?: number | null;
  prdconcod?: number | null;
  condiciones?: CondicionContribuyente[];
  mensaje: string;
};

export type DeudaMuniResult = {
  cntrcod: number | null;
  nombre: string | null;
  estado_busta_card: EstadoBustaCard;
  tiene_deuda: boolean;
  deuda_total: number;
  mensaje: string;
  anio?: number;
};

export type TipoTramite = {
  id: number;
  codigo: string;
  nombre: string;
  descripcion: string;
  area: number;
  area_nombre: string;
  requisitos: string[];
  costo: string;
  dias_habiles: number;
  activo: boolean;
};

export type SeguimientoExpediente = {
  id: number;
  estado: string;
  estado_display: string;
  comentario: string;
  area: number | null;
  area_nombre: string | null;
  fecha: string;
};

export type Expediente = {
  id: number;
  numero: string;
  uuid: string;
  tipo: number;
  tipo_nombre: string;
  asunto: string;
  detalle: string;
  estado: string;
  estado_display: string;
  fecha_ingreso: string;
  fecha_actualizacion: string;
  fecha_estimada: string | null;
  seguimientos: SeguimientoExpediente[];
};

export type UltimoProveido = {
  fecha: string | null;
  numero: string;
  accion: string;
  oficina: string;
};

export type DocumentoTramite = {
  cod_doc: string;
  nom_doc: string;
  sig_doc: string;
};

export type SolicitudTupa = {
  cod_sol: string;
  nom_sol: string;
  cod_ofi: string;
  pla_sol: number | null;
};

export type OficinaTramite = {
  cod_ofi: string;
  nom_ofi: string;
  sig_ofi: string;
};

export type RegistroMesaPartes = {
  registrado: boolean;
  id_usuaext: number | null;
  id_aspnetusers: string | null;
  link_registro: string;
  mensaje: string;
};

export type CatalogoFormularioTramite = {
  documento: DocumentoTramite | null;
  tipos_solicitud: SolicitudTupa[];
  oficinas: OficinaTramite[];
  oficina_default: OficinaTramite | null;
  registro_mesa_partes: RegistroMesaPartes;
};

export type RegistroTramiteExterno = {
  cod_ingext: number;
  num_docext: string;
  cod_docext: string;
  cod_solext: string;
  fec_ingext: string;
  fec_venext: string;
  id_usuaext: number | null;
  id_aspnetusers: string | null;
  nom_adjext: string | null;
  doc_adjext_guardado: boolean;
  doc_adjext_size: number;
  archivo_local: string | null;
};

export type ExpedienteSiap = {
  id: number;
  numero: string;
  asunto: string;
  tipo_codigo: string | null;
  tipo_nombre: string;
  estado: 'EN_TRAMITE' | 'OBSERVADO' | 'RESUELTO' | 'ARCHIVADO';
  estado_display: string;
  observacion: string;
  fecha_ingreso: string | null;
  fecha_vencimiento: string | null;
  oficina_actual: string;
  cantidad_proveidos: number;
  ultimo_proveido: UltimoProveido | null;
};

export type ProveidoSiap = {
  id: number;
  fecha: string | null;
  numero: string;
  tipo_documento: string;
  accion: string;
  oficina_origen: string;
  oficina_destino: string;
  fecha_recepcion: string | null;
  recibido: boolean;
};

export type ExpedienteSiapDetalle = {
  id: number;
  numero: string;
  asunto: string;
  tipo_codigo: string | null;
  tipo_nombre: string;
  estado: 'EN_TRAMITE' | 'OBSERVADO' | 'RESUELTO' | 'ARCHIVADO';
  estado_display: string;
  observacion: string;
  fecha_ingreso: string | null;
  fecha_vencimiento: string | null;
  oficina_actual: string;
  linea_vida: ProveidoSiap[];
};

export type Beneficio = {
  id: number;
  nombre: string;
  descripcion: string;
  categoria: string;
  categoria_display: string;
  lugar: string;
  direccion: string;
  activo: boolean;
  gratuito: boolean;
  horario: string;
  imagen: string | null;
};

export type Tarjeta = {
  codigo: string;
  uuid: string;
  dni: string;
  nombre_completo: string;
  fecha_emision: string;
  fecha_vencimiento: string;
  activa: boolean;
  bloqueada: boolean;
  vigente: boolean;
};

export type Noticia = {
  id: number;
  titulo: string;
  resumen: string;
  contenido: string;
  imagen: string | null;
  url_fuente: string;
  fecha_publicacion: string;
  destacada: boolean;
};

export type Lugar = {
  id: number;
  nombre: string;
  tipo: string;
  tipo_display: string;
  direccion: string;
  latitud: string | null;
  longitud: string | null;
  telefono: string;
  horario: string;
  descripcion: string;
  imagen: string | null;
};

export type Contacto = {
  id: number;
  area: string;
  responsable: string;
  telefono: string;
  whatsapp: string;
  email: string;
  horario: string;
  orden: number;
};
