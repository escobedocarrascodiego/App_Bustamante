import { MaterialCommunityIcons } from '@expo/vector-icons';
import DateTimePicker from '@react-native-community/datetimepicker';
import * as DocumentPicker from 'expo-document-picker';
import { router } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import {
  ActivityIndicator,
  Alert,
  KeyboardAvoidingView,
  Linking,
  Modal,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';

import { MuniButton } from '@/components/muni/muni-button';
import { MuniVideoModal } from '@/components/muni/muni-video-modal';
import { MunicipalityColors, Radius, Spacing } from '@/constants/theme';
import { VIDEO_REGISTRO_MPV } from '@/constants/videos';
import { tramitesApi } from '@/services/endpoints';
import type {
  CatalogoFormularioTramite,
  OficinaTramite,
  SolicitudTupa,
} from '@/services/types';

type ArchivoSeleccionado = {
  nombre: string;
  uri: string;
  tipo: string;
  tamano: number;
};

function formatearFecha(d: Date): string {
  const dd = String(d.getDate()).padStart(2, '0');
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  return `${dd}/${mm}/${d.getFullYear()}`;
}

export default function NuevoTramiteScreen() {
  const [catalogo, setCatalogo] = useState<CatalogoFormularioTramite | null>(null);
  const [cargandoCatalogo, setCargandoCatalogo] = useState(true);

  const [fecha, setFecha] = useState<Date>(new Date());
  const [mostrarDate, setMostrarDate] = useState(false);

  const [nroDoc, setNroDoc] = useState('');
  const [tipoSolCod, setTipoSolCod] = useState<string | null>(null);
  const [busquedaTipo, setBusquedaTipo] = useState('');
  const [mostrarTipos, setMostrarTipos] = useState(false);

  const [descripcion, setDescripcion] = useState('');
  const [oficinaRecibeCod, setOficinaRecibeCod] = useState<string | null>(null);
  const [oficinaVerificaCod, setOficinaVerificaCod] = useState<string | null>(null);
  const [pickerAbierto, setPickerAbierto] = useState<'recibe' | 'verifica' | null>(null);
  const [busquedaOfi, setBusquedaOfi] = useState('');

  const [archivo, setArchivo] = useState<ArchivoSeleccionado | null>(null);
  const [enviando, setEnviando] = useState(false);

  useEffect(() => {
    tramitesApi
      .catalogoFormulario()
      .then((cat) => {
        setCatalogo(cat);
        const def = cat.oficina_default?.cod_ofi ?? null;
        setOficinaRecibeCod(def);
        setOficinaVerificaCod(def);
      })
      .catch(() => setCatalogo(null))
      .finally(() => setCargandoCatalogo(false));
  }, []);

  const tipoSolSeleccionado = useMemo<SolicitudTupa | null>(
    () => catalogo?.tipos_solicitud.find((s) => s.cod_sol === tipoSolCod) ?? null,
    [catalogo, tipoSolCod],
  );

  const tiposFiltrados = useMemo<SolicitudTupa[]>(() => {
    if (!catalogo) return [];
    const q = busquedaTipo.trim().toLowerCase();
    if (!q) return catalogo.tipos_solicitud;
    return catalogo.tipos_solicitud.filter(
      (s) => s.nom_sol.toLowerCase().includes(q) || s.cod_sol.toLowerCase().includes(q),
    );
  }, [catalogo, busquedaTipo]);

  const oficinasFiltradas = useMemo<OficinaTramite[]>(() => {
    if (!catalogo) return [];
    const q = busquedaOfi.trim().toLowerCase();
    if (!q) return catalogo.oficinas;
    return catalogo.oficinas.filter(
      (o) => o.nom_ofi.toLowerCase().includes(q) || o.cod_ofi.toLowerCase().includes(q),
    );
  }, [catalogo, busquedaOfi]);

  const oficinaRecibe = useMemo(
    () => catalogo?.oficinas.find((o) => o.cod_ofi === oficinaRecibeCod) ?? null,
    [catalogo, oficinaRecibeCod],
  );
  const oficinaVerifica = useMemo(
    () => catalogo?.oficinas.find((o) => o.cod_ofi === oficinaVerificaCod) ?? null,
    [catalogo, oficinaVerificaCod],
  );

  const seleccionarArchivo = async () => {
    try {
      const res = await DocumentPicker.getDocumentAsync({
        type: ['application/pdf'],
        multiple: false,
        copyToCacheDirectory: true,
      });
      if (res.canceled) return;
      const a = res.assets?.[0];
      if (!a) return;
      setArchivo({
        nombre: a.name,
        uri: a.uri,
        tipo: a.mimeType ?? 'application/pdf',
        tamano: a.size ?? 0,
      });
    } catch {
      Alert.alert('Error', 'No se pudo abrir el selector de archivos.');
    }
  };

  const enviar = async () => {
    if (!tipoSolSeleccionado) {
      return Alert.alert('Falta informacion', 'Selecciona el tipo de solicitud TUPA.');
    }
    if (descripcion.trim().length < 5) {
      return Alert.alert(
        'Descripcion',
        'Describe la solicitud con al menos 5 caracteres.',
      );
    }
    if (!oficinaRecibeCod || !oficinaVerificaCod) {
      return Alert.alert('Oficinas', 'Selecciona oficina que recibe y oficina que verifica.');
    }

    const form = new FormData();
    form.append('cod_solext', tipoSolSeleccionado.cod_sol);
    form.append('des_solext', descripcion.trim().toUpperCase());
    form.append('ofi_recext', oficinaRecibeCod);
    form.append('ofi_traext', oficinaVerificaCod);
    form.append('fecha', formatearFecha(fecha));
    if (archivo) {
      form.append('adjunto', {
        uri: archivo.uri,
        name: archivo.nombre,
        type: archivo.tipo || 'application/pdf',
      } as unknown as Blob);
    }

    setEnviando(true);
    try {
      const res = await tramitesApi.registrarTramiteExterno(form);
      Alert.alert(
        'Tramite registrado',
        `Tu tramite fue ingresado a SIAP.\nNro. documento: ${res.num_docext}`,
        [{ text: 'OK', onPress: () => router.back() }],
      );
    } catch (e: unknown) {
      const detalle =
        (e && typeof e === 'object' && 'data' in e
          ? ((e as { data?: { detail?: string } }).data?.detail ?? '')
          : '') || 'No se pudo registrar el tramite. Intenta nuevamente.';
      Alert.alert('Error', detalle);
    } finally {
      setEnviando(false);
    }
  };

  if (cargandoCatalogo) {
    return (
      <View style={styles.loaderWrap}>
        <ActivityIndicator color={MunicipalityColors.primary} />
        <Text style={styles.loaderText}>Cargando catalogo...</Text>
      </View>
    );
  }

  if (catalogo && catalogo.registro_mesa_partes?.registrado === false) {
    return (
      <BloqueoRegistroMesaPartes
        link={catalogo.registro_mesa_partes.link_registro}
        mensaje={catalogo.registro_mesa_partes.mensaje}
      />
    );
  }

  return (
    <KeyboardAvoidingView
      style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}
      behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
    <ScrollView
      style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}
      contentContainerStyle={styles.scroll}
      keyboardShouldPersistTaps="handled"
      showsVerticalScrollIndicator={false}>
      <View style={styles.heroBar}>
        <MaterialCommunityIcons
          name="file-document-edit-outline"
          size={22}
          color={MunicipalityColors.white}
        />
        <Text style={styles.heroTitle}>Nuevo tramite virtual</Text>
      </View>

      <View style={styles.card}>
        <Text style={styles.sectionTitle}>Datos del tramite</Text>
        <View style={styles.warnPill}>
          <MaterialCommunityIcons
            name="alert-circle-outline"
            size={14}
            color={MunicipalityColors.danger}
          />
          <Text style={styles.warnText}>Llena la solicitud en MAYUSCULAS</Text>
        </View>

        <Field label="Fecha de solicitud" icon="calendar">
          <Pressable style={styles.input} onPress={() => setMostrarDate(true)}>
            <Text style={styles.inputText}>{formatearFecha(fecha)}</Text>
            <MaterialCommunityIcons
              name="calendar-blank-outline"
              size={18}
              color={MunicipalityColors.textSecondary}
            />
          </Pressable>
        </Field>

        <Field label="Tipo de documento" icon="file-document-outline">
          <View style={[styles.input, styles.readonlyBox]}>
            <Text style={styles.inputText}>
              {(catalogo?.documento?.nom_doc ?? 'TRAMITE').toUpperCase()}
            </Text>
            <Text style={styles.codigoSmall}>
              {catalogo?.documento?.cod_doc ?? ''}
            </Text>
          </View>
        </Field>

        <Field label="Nro. documento" icon="numeric">
          <TextInput
            style={[styles.input, styles.inputTextable]}
            value={nroDoc}
            onChangeText={setNroDoc}
            placeholder="Ej. 001"
            placeholderTextColor={MunicipalityColors.textMuted}
            keyboardType="number-pad"
          />
        </Field>

        <Field label="Tipo de solicitud TUPA" icon="format-list-bulleted-type">
          <Pressable
            style={styles.input}
            onPress={() => {
              setBusquedaTipo('');
              setMostrarTipos(true);
            }}>
            <Text
              style={[
                styles.inputText,
                !tipoSolSeleccionado && styles.placeholderText,
              ]}
              numberOfLines={2}>
              {tipoSolSeleccionado
                ? tipoSolSeleccionado.nom_sol.toUpperCase()
                : 'SELECCIONAR TIPO DE SOLICITUD'}
            </Text>
            <MaterialCommunityIcons
              name="chevron-down"
              size={18}
              color={MunicipalityColors.textSecondary}
            />
          </Pressable>
          {tipoSolSeleccionado ? (
            <Text style={styles.helperText}>
              Codigo: {tipoSolSeleccionado.cod_sol}
              {tipoSolSeleccionado.pla_sol
                ? ` · Plazo ${tipoSolSeleccionado.pla_sol} dias`
                : ''}
            </Text>
          ) : null}
        </Field>

        <Field label="Descripcion de la solicitud" icon="text-long">
          <TextInput
            style={[styles.input, styles.inputTextable, styles.inputMulti]}
            value={descripcion}
            onChangeText={(v) => setDescripcion(v.toUpperCase())}
            placeholder="ESPECIFIQUE LA SOLICITUD..."
            placeholderTextColor={MunicipalityColors.textMuted}
            multiline
            numberOfLines={4}
            textAlignVertical="top"
          />
        </Field>

        <Field label="Oficina que recibe" icon="domain">
          <Pressable
            style={styles.input}
            onPress={() => {
              setBusquedaOfi('');
              setPickerAbierto('recibe');
            }}>
            <Text
              style={[styles.inputText, !oficinaRecibe && styles.placeholderText]}
              numberOfLines={2}>
              {oficinaRecibe ? oficinaRecibe.nom_ofi.toUpperCase() : 'SELECCIONAR OFICINA'}
            </Text>
            <MaterialCommunityIcons
              name="chevron-down"
              size={18}
              color={MunicipalityColors.textSecondary}
            />
          </Pressable>
        </Field>

        <Field label="Oficina que verifica conformidad" icon="shield-check-outline">
          <Pressable
            style={styles.input}
            onPress={() => {
              setBusquedaOfi('');
              setPickerAbierto('verifica');
            }}>
            <Text
              style={[styles.inputText, !oficinaVerifica && styles.placeholderText]}
              numberOfLines={2}>
              {oficinaVerifica
                ? oficinaVerifica.nom_ofi.toUpperCase()
                : 'SELECCIONAR OFICINA'}
            </Text>
            <MaterialCommunityIcons
              name="chevron-down"
              size={18}
              color={MunicipalityColors.textSecondary}
            />
          </Pressable>
        </Field>

        <Field label="Adjuntar PDF" icon="paperclip">
          <View style={styles.fileBox}>
            <Pressable style={styles.fileBtn} onPress={seleccionarArchivo}>
              <MaterialCommunityIcons
                name="cloud-upload-outline"
                size={18}
                color={MunicipalityColors.white}
              />
              <Text style={styles.fileBtnText}>Seleccionar</Text>
            </Pressable>
            {archivo ? (
              <View style={styles.fileChip}>
                <MaterialCommunityIcons
                  name="file-pdf-box"
                  size={20}
                  color={MunicipalityColors.danger}
                />
                <View style={{ flex: 1 }}>
                  <Text style={styles.fileChipName} numberOfLines={1}>
                    {archivo.nombre}
                  </Text>
                  <Text style={styles.fileChipMeta}>
                    {(archivo.tamano / 1024).toFixed(1)} KB
                  </Text>
                </View>
                <Pressable onPress={() => setArchivo(null)}>
                  <MaterialCommunityIcons
                    name="close-circle"
                    size={20}
                    color={MunicipalityColors.textMuted}
                  />
                </Pressable>
              </View>
            ) : (
              <Text style={styles.fileEmpty}>Sin archivo seleccionado</Text>
            )}
          </View>
        </Field>

        <View style={styles.actions}>
          <MuniButton
            label="Cancelar"
            variant="ghost"
            onPress={() => router.back()}
            fullWidth={false}
          />
          <MuniButton
            label="Guardar tramite"
            variant="success"
            onPress={enviar}
            loading={enviando}
            iconLeft={
              <MaterialCommunityIcons name="check-circle" size={18} color="#FFFFFF" />
            }
          />
        </View>
      </View>

      {mostrarDate ? (
        <DateTimePicker
          value={fecha}
          mode="date"
          display={Platform.OS === 'ios' ? 'spinner' : 'default'}
          onChange={(_, d) => {
            setMostrarDate(Platform.OS === 'ios');
            if (d) setFecha(d);
          }}
        />
      ) : null}

      <SelectorModal
        visible={mostrarTipos}
        titulo="Tipo de solicitud TUPA"
        placeholder="Buscar por nombre o codigo..."
        valor={busquedaTipo}
        onCambioBusqueda={setBusquedaTipo}
        onCerrar={() => setMostrarTipos(false)}>
        {tiposFiltrados.length === 0 ? (
          <Text style={styles.emptyList}>Sin resultados.</Text>
        ) : (
          tiposFiltrados.map((s) => (
            <Pressable
              key={s.cod_sol}
              style={[styles.itemLista, tipoSolCod === s.cod_sol && styles.itemListaActivo]}
              onPress={() => {
                setTipoSolCod(s.cod_sol);
                setMostrarTipos(false);
              }}>
              <Text style={styles.itemCodigo}>{s.cod_sol}</Text>
              <Text style={styles.itemNombre} numberOfLines={2}>
                {s.nom_sol}
              </Text>
            </Pressable>
          ))
        )}
      </SelectorModal>

      <SelectorModal
        visible={pickerAbierto !== null}
        titulo={pickerAbierto === 'recibe' ? 'Oficina que recibe' : 'Oficina que verifica'}
        placeholder="Buscar oficina..."
        valor={busquedaOfi}
        onCambioBusqueda={setBusquedaOfi}
        onCerrar={() => setPickerAbierto(null)}>
        {oficinasFiltradas.length === 0 ? (
          <Text style={styles.emptyList}>Sin resultados.</Text>
        ) : (
          oficinasFiltradas.map((o) => (
            <Pressable
              key={o.cod_ofi}
              style={[
                styles.itemLista,
                (pickerAbierto === 'recibe' ? oficinaRecibeCod : oficinaVerificaCod) ===
                  o.cod_ofi && styles.itemListaActivo,
              ]}
              onPress={() => {
                if (pickerAbierto === 'recibe') setOficinaRecibeCod(o.cod_ofi);
                else if (pickerAbierto === 'verifica') setOficinaVerificaCod(o.cod_ofi);
                setPickerAbierto(null);
              }}>
              <Text style={styles.itemCodigo}>{o.cod_ofi}</Text>
              <Text style={styles.itemNombre} numberOfLines={2}>
                {o.nom_ofi}
              </Text>
            </Pressable>
          ))
        )}
      </SelectorModal>
    </ScrollView>
    </KeyboardAvoidingView>
  );
}

function BloqueoRegistroMesaPartes({
  link,
  mensaje,
}: {
  link: string;
  mensaje: string;
}) {
  const [verVideo, setVerVideo] = useState(false);
  const abrirRegistro = async () => {
    const ok = await Linking.canOpenURL(link).catch(() => false);
    if (!ok) {
      return Alert.alert(
        'No se pudo abrir',
        'No pudimos abrir el portal en el navegador. Copia el enlace e ingresa manualmente:\n\n' +
          link,
      );
    }
    void Linking.openURL(link);
  };

  return (
    <ScrollView
      style={{ flex: 1, backgroundColor: MunicipalityColors.surface }}
      contentContainerStyle={{ padding: Spacing.lg, paddingBottom: Spacing.xxl }}>
      <View style={styles.heroBar}>
        <MaterialCommunityIcons
          name="account-alert-outline"
          size={22}
          color={MunicipalityColors.white}
        />
        <Text style={styles.heroTitle}>Registro requerido</Text>
      </View>

      <View style={[styles.card, { alignItems: 'center', gap: Spacing.lg }]}>
        <View style={styles.bloqueoIconWrap}>
          <MaterialCommunityIcons
            name="shield-lock-outline"
            size={48}
            color={MunicipalityColors.primary}
          />
        </View>
        <Text style={styles.bloqueoTitulo}>
          No estas registrado en la Mesa de Partes Virtual
        </Text>
        <Text style={styles.bloqueoMensaje}>{mensaje}</Text>

        <View style={styles.bloqueoLinkBox}>
          <MaterialCommunityIcons
            name="link-variant"
            size={16}
            color={MunicipalityColors.primary}
          />
          <Text style={styles.bloqueoLink} numberOfLines={2}>
            {link}
          </Text>
        </View>

        <View style={{ width: '100%', gap: Spacing.sm }}>
          <MuniButton
            label="Ver tutorial en video"
            variant="secondary"
            onPress={() => setVerVideo(true)}
            iconLeft={
              <MaterialCommunityIcons
                name="play-circle-outline"
                size={18}
                color={MunicipalityColors.primary}
              />
            }
          />
          <MuniButton
            label="Ir al portal de registro"
            variant="primary"
            onPress={abrirRegistro}
            iconLeft={
              <MaterialCommunityIcons
                name="open-in-new"
                size={18}
                color={MunicipalityColors.white}
              />
            }
          />
          <MuniButton
            label="Volver"
            variant="ghost"
            onPress={() => router.back()}
          />
        </View>

        <Text style={styles.bloqueoNota}>
          Una vez completes el registro, regresa al app y vuelve a intentarlo.
        </Text>
      </View>

      <MuniVideoModal
        visible={verVideo}
        videoId={VIDEO_REGISTRO_MPV.videoId}
        titulo={VIDEO_REGISTRO_MPV.titulo}
        descripcion={VIDEO_REGISTRO_MPV.descripcion}
        onClose={() => setVerVideo(false)}
      />
    </ScrollView>
  );
}

function Field({
  label,
  icon,
  children,
}: {
  label: string;
  icon: React.ComponentProps<typeof MaterialCommunityIcons>['name'];
  children: React.ReactNode;
}) {
  return (
    <View style={styles.field}>
      <View style={styles.fieldLabelRow}>
        <MaterialCommunityIcons name={icon} size={14} color={MunicipalityColors.primary} />
        <Text style={styles.fieldLabel}>{label}</Text>
      </View>
      {children}
    </View>
  );
}

function SelectorModal({
  visible,
  titulo,
  placeholder,
  valor,
  onCambioBusqueda,
  onCerrar,
  children,
}: {
  visible: boolean;
  titulo: string;
  placeholder: string;
  valor: string;
  onCambioBusqueda: (s: string) => void;
  onCerrar: () => void;
  children: React.ReactNode;
}) {
  return (
    <Modal visible={visible} animationType="slide" transparent onRequestClose={onCerrar}>
      <View style={styles.modalBackdrop}>
        <View style={styles.modalBox}>
          <View style={styles.modalHeader}>
            <Text style={styles.modalTitulo}>{titulo}</Text>
            <Pressable onPress={onCerrar} hitSlop={8}>
              <MaterialCommunityIcons
                name="close"
                size={22}
                color={MunicipalityColors.textPrimary}
              />
            </Pressable>
          </View>
          <View style={styles.searchRow}>
            <MaterialCommunityIcons
              name="magnify"
              size={18}
              color={MunicipalityColors.textMuted}
            />
            <TextInput
              style={styles.searchInput}
              placeholder={placeholder}
              placeholderTextColor={MunicipalityColors.textMuted}
              value={valor}
              onChangeText={onCambioBusqueda}
            />
          </View>
          <ScrollView style={{ maxHeight: 480 }}>{children}</ScrollView>
        </View>
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  loaderWrap: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.surface,
  },
  loaderText: { color: MunicipalityColors.textSecondary, fontSize: 13 },
  scroll: { paddingBottom: Spacing.xxl },
  heroBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: MunicipalityColors.primary,
    paddingHorizontal: Spacing.lg,
    paddingVertical: Spacing.md,
  },
  heroTitle: {
    color: MunicipalityColors.white,
    fontSize: 16,
    fontWeight: '700',
    letterSpacing: 0.3,
  },
  card: {
    margin: Spacing.lg,
    padding: Spacing.lg,
    backgroundColor: MunicipalityColors.white,
    borderRadius: Radius.lg,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    gap: Spacing.md,
    shadowColor: '#000',
    shadowOpacity: 0.05,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 2,
  },
  sectionTitle: {
    fontSize: 15,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
  },
  warnPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    backgroundColor: '#FEF2F2',
    borderRadius: Radius.pill,
    paddingHorizontal: Spacing.md,
    paddingVertical: 4,
    marginBottom: Spacing.sm,
  },
  warnText: { color: MunicipalityColors.danger, fontSize: 11, fontWeight: '700' },
  field: { gap: 6 },
  fieldLabelRow: { flexDirection: 'row', alignItems: 'center', gap: 6 },
  fieldLabel: {
    fontSize: 12,
    fontWeight: '700',
    color: MunicipalityColors.textSecondary,
    textTransform: 'uppercase',
    letterSpacing: 0.4,
  },
  input: {
    backgroundColor: '#F8FAFC',
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    paddingHorizontal: Spacing.md,
    paddingVertical: Platform.OS === 'ios' ? 12 : 10,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: Spacing.sm,
    minHeight: 44,
  },
  inputTextable: {
    color: MunicipalityColors.textPrimary,
    fontSize: 14,
  },
  inputMulti: {
    minHeight: 96,
    paddingTop: 10,
    textAlignVertical: 'top',
  },
  inputText: {
    fontSize: 14,
    color: MunicipalityColors.textPrimary,
    flex: 1,
    fontWeight: '500',
  },
  placeholderText: { color: MunicipalityColors.textMuted, fontWeight: '400' },
  helperText: { fontSize: 11, color: MunicipalityColors.textMuted, marginTop: 2 },
  readonlyBox: { backgroundColor: '#EEF2FF' },
  codigoSmall: {
    fontSize: 11,
    color: MunicipalityColors.primary,
    fontWeight: '700',
    letterSpacing: 0.4,
  },
  fileBox: { gap: Spacing.sm },
  fileBtn: {
    flexDirection: 'row',
    alignSelf: 'flex-start',
    alignItems: 'center',
    gap: 6,
    backgroundColor: MunicipalityColors.primary,
    paddingHorizontal: Spacing.md,
    paddingVertical: 10,
    borderRadius: Radius.md,
  },
  fileBtnText: { color: MunicipalityColors.white, fontSize: 13, fontWeight: '700' },
  fileEmpty: {
    fontSize: 12,
    color: MunicipalityColors.textMuted,
    fontStyle: 'italic',
  },
  fileChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: Spacing.sm,
    backgroundColor: '#F8FAFC',
    borderRadius: Radius.md,
    borderWidth: 1,
    borderColor: MunicipalityColors.border,
    padding: Spacing.sm,
  },
  fileChipName: {
    fontSize: 13,
    color: MunicipalityColors.textPrimary,
    fontWeight: '600',
  },
  fileChipMeta: { fontSize: 11, color: MunicipalityColors.textMuted },
  actions: {
    flexDirection: 'row',
    justifyContent: 'flex-end',
    alignItems: 'center',
    gap: Spacing.sm,
    marginTop: Spacing.md,
  },
  modalBackdrop: {
    flex: 1,
    backgroundColor: 'rgba(15, 23, 42, 0.45)',
    justifyContent: 'flex-end',
  },
  modalBox: {
    backgroundColor: MunicipalityColors.white,
    borderTopLeftRadius: Radius.xl,
    borderTopRightRadius: Radius.xl,
    padding: Spacing.lg,
    gap: Spacing.md,
    maxHeight: '85%',
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  modalTitulo: {
    fontSize: 16,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
  },
  searchRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#F1F5F9',
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    paddingVertical: Platform.OS === 'ios' ? 10 : 6,
    color: MunicipalityColors.textPrimary,
  },
  itemLista: {
    paddingVertical: Spacing.sm,
    paddingHorizontal: Spacing.sm,
    borderBottomWidth: StyleSheet.hairlineWidth,
    borderBottomColor: MunicipalityColors.border,
    gap: 2,
  },
  itemListaActivo: { backgroundColor: '#EEF2FF' },
  itemCodigo: {
    fontSize: 11,
    fontWeight: '800',
    color: MunicipalityColors.primary,
    letterSpacing: 0.4,
  },
  itemNombre: { fontSize: 13, color: MunicipalityColors.textPrimary },
  emptyList: {
    padding: Spacing.lg,
    color: MunicipalityColors.textMuted,
    fontSize: 13,
    textAlign: 'center',
  },
  bloqueoIconWrap: {
    width: 88,
    height: 88,
    borderRadius: 44,
    backgroundColor: '#EEF2FF',
    alignItems: 'center',
    justifyContent: 'center',
  },
  bloqueoTitulo: {
    fontSize: 18,
    fontWeight: '800',
    color: MunicipalityColors.textPrimary,
    textAlign: 'center',
  },
  bloqueoMensaje: {
    fontSize: 14,
    color: MunicipalityColors.textSecondary,
    textAlign: 'center',
    lineHeight: 20,
  },
  bloqueoLinkBox: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    backgroundColor: '#F8FAFC',
    borderRadius: Radius.md,
    paddingHorizontal: Spacing.md,
    paddingVertical: Spacing.sm,
    width: '100%',
  },
  bloqueoLink: {
    fontSize: 12,
    color: MunicipalityColors.primary,
    fontWeight: '600',
    flex: 1,
  },
  bloqueoNota: {
    fontSize: 12,
    color: MunicipalityColors.textMuted,
    textAlign: 'center',
    fontStyle: 'italic',
  },
});
