/**
 * Pantalla modal del Asistente Municipal (chatbot rule-based).
 *
 * Flujo en 2 etapas (igual al bot de Telegram):
 *  1. ETAPA 'seleccion_gerencia':
 *     - Muestra mensaje de bienvenida + selector de gerencias.
 *     - Input bar deshabilitado.
 *  2. ETAPA 'conversacion':
 *     - Se activa al elegir gerencia. Toda pregunta se manda con
 *       gerencia_id para que el backend filtre la busqueda CONTAINS().
 *     - Mostramos un boton "Cambiar área" sobre el input para volver
 *       a la etapa 1.
 *
 * Al montar:
 *  - POST /sesion/nueva/  guarda sesion_id en useRef.
 *  - GET  /gerencias/      llena el selector.
 */
import { MaterialCommunityIcons } from '@expo/vector-icons';
import { router } from 'expo-router';
import { useEffect, useRef, useState } from 'react';
import {
  Animated,
  Easing,
  FlatList,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  StyleSheet,
  Text,
  TextInput,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

import { chatbotApi } from '@/services/endpoints';
import type {
  FaqChatbot,
  GerenciaChatbot,
  RolMensajeChat,
} from '@/services/types';

// ----- Constantes del feature -----
const CHAT_PRIMARY = '#185FA5'; // azul header y burbuja usuario
const CHAT_ACCENT = '#EFA400'; // amarillo del avatar bot
const CHAT_BG = '#F5F5F5';
const BOT_BORDER = '#E0E0E0';
const TIMESTAMP_COLOR = '#999';
const BOT_TEXT_COLOR = '#1A1A1A';
const MENSAJE_BIENVENIDA =
  '¡Hola! Soy el asistente virtual de la Municipalidad de José Luis ' +
  'Bustamante y Rivero. Puedo ayudarte con consultas sobre predial, ' +
  'arbitrios, trámites, licencias y más. ¿En qué te puedo ayudar hoy?';
const MENSAJE_ERROR_RED =
  'Lo siento, hubo un problema de conexión. Intenta de nuevo en un momento.';

// ----- Tipos locales -----
type EtapaChat = 'seleccion_gerencia' | 'conversacion';

type Mensaje = {
  id: string;
  rol: RolMensajeChat;
  contenido: string;
  timestamp: Date;
  es_escribiendo?: boolean;
  es_selector_gerencias?: boolean;
  // Menu de FAQs (segundo nivel): botones con las preguntas frecuentes de la
  // gerencia + opcion "Escribir mi propia consulta".
  es_selector_faqs?: boolean;
  faqs?: FaqChatbot[];
};

function uid(): string {
  return `${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

function formatearHora(d: Date): string {
  const hh = String(d.getHours()).padStart(2, '0');
  const mm = String(d.getMinutes()).padStart(2, '0');
  return `${hh}:${mm}`;
}

export default function ChatScreen() {
  const sesionRef = useRef<string | null>(null);
  const flatListRef = useRef<FlatList<Mensaje>>(null);

  const [mensajes, setMensajes] = useState<Mensaje[]>([
    {
      id: uid(),
      rol: 'bot',
      contenido: MENSAJE_BIENVENIDA,
      timestamp: new Date(),
    },
  ]);
  const [inputText, setInputText] = useState('');
  const [esperando, setEsperando] = useState(false);

  // ----- Flujo en 2 etapas con gerencia -----
  const [etapa, setEtapa] = useState<EtapaChat>('seleccion_gerencia');
  const [gerencias, setGerencias] = useState<GerenciaChatbot[]>([]);
  const [gerenciaSeleccionada, setGerenciaSeleccionada] =
    useState<GerenciaChatbot | null>(null);
  // Menu de FAQs: el input de texto queda bloqueado hasta que el vecino
  // elija "Escribir mi propia consulta". Asi le damos el camino hecho.
  const [modoTexto, setModoTexto] = useState(false);

  // Inicia la sesion + carga gerencias al montar
  useEffect(() => {
    let cancelado = false;
    void (async () => {
      try {
        const data = await chatbotApi.nuevaSesion();
        if (!cancelado) sesionRef.current = data.sesion_id;
      } catch {
        // sesion_id queda null — al primer envio el catch de enviar() reintenta
        if (__DEV__) console.warn('[chat] no se pudo crear sesion al montar');
      }
      try {
        const lista = await chatbotApi.gerencias();
        if (!cancelado) setGerencias(lista);
      } catch {
        if (!cancelado) {
          if (__DEV__) console.warn('[chat] no se pudo cargar gerencias');
          // Si no hay gerencias, dejamos que el usuario igual escriba
          // (busqueda sin filtro) — pasamos a conversacion automaticamente.
          setEtapa('conversacion');
        }
      }
    })();
    return () => {
      cancelado = true;
    };
  }, []);

  // Auto-scroll al ultimo mensaje cada vez que la lista cambia
  useEffect(() => {
    const t = setTimeout(() => {
      flatListRef.current?.scrollToEnd({ animated: true });
    }, 50);
    return () => clearTimeout(t);
  }, [mensajes, esperando, etapa]);

  const seleccionarGerencia = async (gerencia: GerenciaChatbot) => {
    if (esperando) return;
    setGerenciaSeleccionada(gerencia);
    setEtapa('conversacion');
    setModoTexto(false);
    const ahora = new Date();
    setMensajes((prev) => [
      ...prev,
      {
        id: uid(),
        rol: 'usuario',
        contenido: gerencia.nombre,
        timestamp: ahora,
      },
    ]);

    // Cargar las FAQs de la gerencia para mostrarlas como botones (menu de
    // segundo nivel). Si no hay FAQs o falla, habilitamos el texto libre.
    setEsperando(true);
    try {
      const data = await chatbotApi.faqsDeGerencia(gerencia.id);
      const faqs = data.faqs ?? [];
      if (faqs.length > 0) {
        setMensajes((prev) => [
          ...prev,
          {
            id: uid(),
            rol: 'bot',
            contenido: `Has seleccionado ${gerencia.nombre}. ¿Qué deseas consultar?`,
            timestamp: new Date(),
            es_selector_faqs: true,
            faqs,
          },
        ]);
      } else {
        setModoTexto(true);
        setMensajes((prev) => [
          ...prev,
          {
            id: uid(),
            rol: 'bot',
            contenido: `Perfecto, te ayudo con ${gerencia.nombre}. Escribe tu consulta.`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch {
      setModoTexto(true);
      setMensajes((prev) => [
        ...prev,
        {
          id: uid(),
          rol: 'bot',
          contenido: `Perfecto, te ayudo con ${gerencia.nombre}. ¿Cuál es tu pregunta?`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setEsperando(false);
    }
  };

  // Responde directamente al presionar un boton de FAQ (cero error de match).
  const seleccionarFaq = async (faq: FaqChatbot) => {
    if (esperando) return;
    setMensajes((prev) => [
      ...prev,
      { id: uid(), rol: 'usuario', contenido: faq.pregunta, timestamp: new Date() },
    ]);
    setEsperando(true);
    try {
      if (!sesionRef.current) {
        const nueva = await chatbotApi.nuevaSesion();
        sesionRef.current = nueva.sesion_id;
      }
      const resp = await chatbotApi.enviarMensaje(
        sesionRef.current,
        faq.pregunta,
        gerenciaSeleccionada?.id,
        faq.id,
      );
      setMensajes((prev) => [
        ...prev,
        { id: uid(), rol: 'bot', contenido: resp.respuesta, timestamp: new Date() },
      ]);
    } catch {
      setMensajes((prev) => [
        ...prev,
        { id: uid(), rol: 'bot', contenido: MENSAJE_ERROR_RED, timestamp: new Date() },
      ]);
    } finally {
      setEsperando(false);
    }
  };

  const habilitarTexto = () => {
    if (esperando) return;
    setModoTexto(true);
  };

  const volverASeleccionGerencia = () => {
    if (esperando) return;
    setGerenciaSeleccionada(null);
    setEtapa('seleccion_gerencia');
    setModoTexto(false);
    setMensajes((prev) => [
      ...prev,
      {
        id: uid(),
        rol: 'bot',
        contenido: 'Selecciona el área sobre la que quieres consultar:',
        timestamp: new Date(),
      },
    ]);
  };

  const enviar = async () => {
    const texto = inputText.trim();
    if (!texto || esperando || etapa !== 'conversacion') return;

    const mensajeUsuario: Mensaje = {
      id: uid(),
      rol: 'usuario',
      contenido: texto,
      timestamp: new Date(),
    };
    setMensajes((prev) => [...prev, mensajeUsuario]);
    setInputText('');
    setEsperando(true);

    try {
      // Reintenta crear sesion si fallo al montar
      if (!sesionRef.current) {
        const nueva = await chatbotApi.nuevaSesion();
        sesionRef.current = nueva.sesion_id;
      }
      const resp = await chatbotApi.enviarMensaje(
        sesionRef.current,
        texto,
        gerenciaSeleccionada?.id,
      );

      const mensajeBot: Mensaje = {
        id: uid(),
        rol: 'bot',
        contenido: resp.respuesta,
        timestamp: new Date(),
      };
      setMensajes((prev) => [...prev, mensajeBot]);
    } catch {
      const mensajeError: Mensaje = {
        id: uid(),
        rol: 'bot',
        contenido: MENSAJE_ERROR_RED,
        timestamp: new Date(),
      };
      setMensajes((prev) => [...prev, mensajeError]);
    } finally {
      setEsperando(false);
    }
  };

  // Construimos la lista virtual: mensajes reales + selector (si etapa lo
  // requiere) + "escribiendo" (si esta esperando respuesta).
  const datosLista: Mensaje[] = [...mensajes];
  if (etapa === 'seleccion_gerencia' && gerencias.length > 0) {
    datosLista.push({
      id: '__selector_gerencias__',
      rol: 'bot',
      contenido: 'Selecciona el área sobre la que quieres consultar:',
      timestamp: new Date(),
      es_selector_gerencias: true,
    });
  }
  if (esperando) {
    datosLista.push({
      id: '__escribiendo__',
      rol: 'bot',
      contenido: '',
      timestamp: new Date(),
      es_escribiendo: true,
    });
  }

  // El input se habilita solo en conversacion Y cuando el vecino eligio
  // "Escribir mi propia consulta" (modoTexto). Mientras tanto usa los botones.
  const inputBloqueado = etapa !== 'conversacion' || !modoTexto;
  const sendBtnDeshabilitado =
    inputBloqueado || esperando || inputText.trim().length === 0;

  return (
    <SafeAreaView style={styles.container} edges={['top', 'left', 'right', 'bottom']}>
      {/* HEADER */}
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Asistente Municipal</Text>
        <Pressable
          onPress={() => router.back()}
          hitSlop={12}
          style={styles.headerCloseBtn}
          accessibilityLabel="Cerrar chat">
          <MaterialCommunityIcons name="close" size={22} color="#FFFFFF" />
        </Pressable>
      </View>

      {/* LISTA + INPUT */}
      <KeyboardAvoidingView
        style={styles.body}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}>
        <FlatList
          ref={flatListRef}
          data={datosLista}
          keyExtractor={(item) => item.id}
          contentContainerStyle={styles.listaContent}
          renderItem={({ item }) => (
            <BurbujaMensaje
              mensaje={item}
              gerencias={gerencias}
              onSeleccionarGerencia={seleccionarGerencia}
              seleccionDeshabilitada={esperando || etapa !== 'seleccion_gerencia'}
              onSeleccionarFaq={seleccionarFaq}
              onEscribir={habilitarTexto}
              faqsDeshabilitado={esperando}
            />
          )}
          onContentSizeChange={() =>
            flatListRef.current?.scrollToEnd({ animated: true })
          }
        />

        {/* Boton "Cambiar área" visible solo en etapa conversacion */}
        {etapa === 'conversacion' && gerenciaSeleccionada ? (
          <View style={styles.cambiarAreaWrap}>
            <Pressable
              onPress={volverASeleccionGerencia}
              hitSlop={8}
              disabled={esperando}
              style={({ pressed }) => [
                styles.cambiarAreaBtn,
                pressed && { opacity: 0.6 },
              ]}
              accessibilityLabel="Cambiar el área del chat">
              <MaterialCommunityIcons
                name="swap-horizontal"
                size={14}
                color="#666"
              />
              <Text style={styles.cambiarAreaText}>Cambiar área</Text>
            </Pressable>
          </View>
        ) : null}

        <View style={[styles.inputBar, inputBloqueado && styles.inputBarBloqueada]}>
          <TextInput
            value={inputText}
            onChangeText={setInputText}
            placeholder={
              etapa !== 'conversacion'
                ? 'Selecciona una gerencia primero...'
                : !modoTexto
                  ? 'Elige una opción de arriba…'
                  : 'Escribe tu consulta...'
            }
            placeholderTextColor="#999"
            style={[styles.textInput, inputBloqueado && styles.textInputBloqueado]}
            multiline={false}
            returnKeyType="send"
            onSubmitEditing={enviar}
            editable={!esperando && !inputBloqueado}
          />
          <Pressable
            onPress={enviar}
            disabled={sendBtnDeshabilitado}
            style={[
              styles.sendBtn,
              sendBtnDeshabilitado && styles.sendBtnDisabled,
            ]}
            accessibilityLabel="Enviar mensaje">
            <MaterialCommunityIcons name="send" size={20} color="#FFFFFF" />
          </Pressable>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

// ---------------------------------------------------------------------------
// Burbuja de mensaje (usuario / bot / "escribiendo" / selector de gerencias)
// ---------------------------------------------------------------------------
type BurbujaProps = {
  mensaje: Mensaje;
  gerencias: GerenciaChatbot[];
  onSeleccionarGerencia: (g: GerenciaChatbot) => void;
  seleccionDeshabilitada: boolean;
  onSeleccionarFaq: (f: FaqChatbot) => void;
  onEscribir: () => void;
  faqsDeshabilitado: boolean;
};

function BurbujaMensaje({
  mensaje,
  gerencias,
  onSeleccionarGerencia,
  seleccionDeshabilitada,
  onSeleccionarFaq,
  onEscribir,
  faqsDeshabilitado,
}: BurbujaProps) {
  if (mensaje.rol === 'usuario') {
    return (
      <View style={styles.filaUsuario}>
        <View style={styles.burbujaUsuario}>
          <Text style={styles.textoUsuario}>{mensaje.contenido}</Text>
        </View>
        <Text style={[styles.timestamp, styles.timestampDerecha]}>
          {formatearHora(mensaje.timestamp)}
        </Text>
      </View>
    );
  }

  // Bot — puede ser texto, "escribiendo", o un selector de gerencias.
  return (
    <View style={styles.filaBot}>
      <View style={styles.filaBotRow}>
        <View style={styles.avatarBot}>
          <Text style={styles.avatarBotText}>MB</Text>
        </View>
        <View style={styles.burbujaBotWrap}>
          <View style={styles.burbujaBot}>
            {mensaje.es_escribiendo ? (
              <IndicadorEscribiendo />
            ) : (
              <Text style={styles.textoBot}>{mensaje.contenido}</Text>
            )}
          </View>

          {/* Botones de gerencia debajo del texto de la misma burbuja */}
          {mensaje.es_selector_gerencias ? (
            <SelectorGerencias
              gerencias={gerencias}
              onSeleccionar={onSeleccionarGerencia}
              deshabilitado={seleccionDeshabilitada}
            />
          ) : null}

          {/* Menu de FAQs (segundo nivel) + opcion de escribir */}
          {mensaje.es_selector_faqs && mensaje.faqs ? (
            <SelectorFaqs
              faqs={mensaje.faqs}
              onSeleccionar={onSeleccionarFaq}
              onEscribir={onEscribir}
              deshabilitado={faqsDeshabilitado}
            />
          ) : null}

          {!mensaje.es_escribiendo &&
          !mensaje.es_selector_gerencias &&
          !mensaje.es_selector_faqs ? (
            <Text style={[styles.timestamp, styles.timestampIzquierda]}>
              {formatearHora(mensaje.timestamp)}
            </Text>
          ) : null}
        </View>
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------
// Selector de gerencias (lista de botones inline en el chat)
// ---------------------------------------------------------------------------
function SelectorGerencias({
  gerencias,
  onSeleccionar,
  deshabilitado,
}: {
  gerencias: GerenciaChatbot[];
  onSeleccionar: (g: GerenciaChatbot) => void;
  deshabilitado: boolean;
}) {
  if (gerencias.length === 0) return null;
  return (
    <View style={styles.selectorWrap}>
      {gerencias.map((g) => (
        <Pressable
          key={g.id}
          onPress={() => onSeleccionar(g)}
          disabled={deshabilitado}
          style={({ pressed }) => [
            styles.selectorBtn,
            pressed && !deshabilitado && styles.selectorBtnPressed,
            deshabilitado && styles.selectorBtnDisabled,
          ]}
          accessibilityLabel={`Seleccionar gerencia ${g.nombre}`}>
          <Text style={styles.selectorBtnText} numberOfLines={2}>
            {g.nombre}
          </Text>
        </Pressable>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------
// Selector de FAQs (menu de segundo nivel) + "Escribir mi propia consulta"
// ---------------------------------------------------------------------------
function SelectorFaqs({
  faqs,
  onSeleccionar,
  onEscribir,
  deshabilitado,
}: {
  faqs: FaqChatbot[];
  onSeleccionar: (f: FaqChatbot) => void;
  onEscribir: () => void;
  deshabilitado: boolean;
}) {
  if (faqs.length === 0) return null;
  return (
    <View style={styles.selectorWrap}>
      {faqs.map((f) => (
        <Pressable
          key={f.id}
          onPress={() => onSeleccionar(f)}
          disabled={deshabilitado}
          style={({ pressed }) => [
            styles.selectorBtn,
            pressed && !deshabilitado && styles.selectorBtnPressed,
            deshabilitado && styles.selectorBtnDisabled,
          ]}
          accessibilityLabel={`Consultar ${f.pregunta}`}>
          <Text style={styles.selectorBtnText} numberOfLines={3}>
            {f.pregunta}
          </Text>
        </Pressable>
      ))}
      <Pressable
        onPress={onEscribir}
        disabled={deshabilitado}
        style={({ pressed }) => [
          styles.escribirBtn,
          pressed && !deshabilitado && { opacity: 0.7 },
          deshabilitado && styles.selectorBtnDisabled,
        ]}
        accessibilityLabel="Escribir mi propia consulta">
        <MaterialCommunityIcons name="pencil-outline" size={15} color="#666" />
        <Text style={styles.escribirBtnText}>Escribir mi propia consulta…</Text>
      </Pressable>
    </View>
  );
}

// ---------------------------------------------------------------------------
// 3 puntos animados (loop de opacity con delays escalonados)
// ---------------------------------------------------------------------------
function IndicadorEscribiendo() {
  return (
    <View style={styles.puntosWrap}>
      <Punto delay={0} />
      <Punto delay={200} />
      <Punto delay={400} />
    </View>
  );
}

function Punto({ delay }: { delay: number }) {
  const opacity = useRef(new Animated.Value(0.2)).current;

  useEffect(() => {
    const ciclo = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, {
          toValue: 1,
          duration: 300,
          delay,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
        Animated.timing(opacity, {
          toValue: 0.2,
          duration: 300,
          easing: Easing.inOut(Easing.ease),
          useNativeDriver: true,
        }),
      ]),
    );
    ciclo.start();
    return () => ciclo.stop();
  }, [opacity, delay]);

  return <Animated.View style={[styles.punto, { opacity }]} />;
}

// ---------------------------------------------------------------------------
// Styles
// ---------------------------------------------------------------------------
const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: CHAT_PRIMARY },
  body: { flex: 1, backgroundColor: CHAT_BG },

  // Header
  header: {
    backgroundColor: CHAT_PRIMARY,
    paddingHorizontal: 16,
    paddingVertical: 14,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  headerTitle: {
    color: '#FFFFFF',
    fontSize: 18,
    fontWeight: '600',
  },
  headerCloseBtn: {
    width: 32,
    height: 32,
    alignItems: 'center',
    justifyContent: 'center',
    borderRadius: 16,
    backgroundColor: 'rgba(255,255,255,0.18)',
  },

  // Lista
  listaContent: {
    padding: 12,
    paddingBottom: 16,
    gap: 10,
  },

  // Fila usuario
  filaUsuario: {
    alignItems: 'flex-end',
    marginVertical: 2,
  },
  burbujaUsuario: {
    backgroundColor: CHAT_PRIMARY,
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 18,
    borderBottomRightRadius: 4,
    maxWidth: '75%',
  },
  textoUsuario: {
    color: '#FFFFFF',
    fontSize: 15,
    lineHeight: 20,
  },

  // Fila bot
  filaBot: {
    alignItems: 'flex-start',
    marginVertical: 2,
  },
  filaBotRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 8,
    maxWidth: '85%',
  },
  avatarBot: {
    width: 28,
    height: 28,
    borderRadius: 14,
    backgroundColor: CHAT_ACCENT,
    alignItems: 'center',
    justifyContent: 'center',
  },
  avatarBotText: {
    color: '#FFFFFF',
    fontSize: 11,
    fontWeight: '700',
  },
  burbujaBotWrap: {
    flexShrink: 1,
  },
  burbujaBot: {
    backgroundColor: '#FFFFFF',
    paddingHorizontal: 12,
    paddingVertical: 10,
    borderRadius: 18,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
    borderColor: BOT_BORDER,
    maxWidth: '100%',
  },
  textoBot: {
    color: BOT_TEXT_COLOR,
    fontSize: 15,
    lineHeight: 20,
  },

  // Timestamp
  timestamp: {
    color: TIMESTAMP_COLOR,
    fontSize: 11,
    marginTop: 4,
  },
  timestampDerecha: { textAlign: 'right' },
  timestampIzquierda: { textAlign: 'left', marginLeft: 4 },

  // Indicador escribiendo
  puntosWrap: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingVertical: 2,
  },
  punto: {
    width: 7,
    height: 7,
    borderRadius: 4,
    backgroundColor: '#888',
  },

  // Input bar
  inputBar: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: '#FFFFFF',
    borderTopWidth: 1,
    borderTopColor: BOT_BORDER,
    paddingHorizontal: 12,
    paddingVertical: 10,
  },
  textInput: {
    flex: 1,
    fontSize: 15,
    color: '#1A1A1A',
    paddingHorizontal: 14,
    paddingVertical: Platform.OS === 'ios' ? 10 : 8,
    borderWidth: 1,
    borderColor: BOT_BORDER,
    borderRadius: 20,
    backgroundColor: '#F5F5F5',
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: CHAT_PRIMARY,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendBtnDisabled: { opacity: 0.5 },
  inputBarBloqueada: { opacity: 0.6 },
  textInputBloqueado: { color: '#999' },

  // Selector de gerencias (botones inline dentro de la burbuja del bot)
  selectorWrap: {
    marginTop: 8,
    gap: 8,
  },
  selectorBtn: {
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderColor: CHAT_PRIMARY,
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 12,
  },
  selectorBtnPressed: {
    backgroundColor: '#EEF4FB',
  },
  selectorBtnDisabled: {
    opacity: 0.45,
  },
  selectorBtnText: {
    color: CHAT_PRIMARY,
    fontSize: 14,
    fontWeight: '600',
  },
  escribirBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    backgroundColor: '#F0F0F0',
    borderRadius: 10,
    paddingHorizontal: 12,
    paddingVertical: 10,
    marginTop: 2,
  },
  escribirBtnText: {
    color: '#666',
    fontSize: 13,
    fontWeight: '600',
  },

  // Boton "Cambiar área" sobre el input bar
  cambiarAreaWrap: {
    paddingHorizontal: 16,
    paddingTop: 6,
    paddingBottom: 4,
    backgroundColor: CHAT_BG,
    alignItems: 'flex-start',
  },
  cambiarAreaBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 6,
    paddingVertical: 2,
  },
  cambiarAreaText: {
    color: '#666',
    fontSize: 12,
    fontWeight: '500',
  },
});
