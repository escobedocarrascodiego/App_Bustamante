# App Municipalidad JLBR (React Native + Expo)

App movil oficial de la Municipalidad Distrital de Jose Luis Bustamante y Rivero (Arequipa, Peru). Consume la API Django del proyecto `../backend`.

## Requisitos

- Node.js 20+
- npm
- Backend corriendo en `http://localhost:8000` (ver `../backend/README.md`)

## Instalacion

```bash
npm install
npx expo install expo-secure-store @react-native-async-storage/async-storage
```

> `expo-secure-store` guarda los tokens JWT en el llavero del dispositivo y
> `AsyncStorage` se usa como fallback en web. Si no los instalas, los tokens
> solo persisten durante la sesion del app.

## Ejecutar

```bash
npm run android    # Emulador Android
npm run ios        # iOS simulator (Mac)
npm run web        # Navegador
```

Por defecto el app apunta a:
- `http://10.0.2.2:8000/api/v1` en Android (emulador)
- `http://localhost:8000/api/v1` en iOS / web

Para cambiar la URL editar `constants/config.ts` o definir `extra.apiBaseUrl` en `app.json`.

## Credenciales de prueba

Ejecuta `python manage.py seed_demo` en el backend y usa:
- **DNI:** 12345678
- **Contrasena:** demo1234

## Identidad visual

Basada en los colores del escudo municipal:
- Azul institucional `#0B3D91`
- Amarillo/dorado `#F5B800`
- Blanco `#FFFFFF`

Definidos en [`constants/theme.ts`](constants/theme.ts) (`MunicipalityColors`, `Spacing`, `Radius`).

## Estructura

```
busta-app/
├── app/                     # rutas (expo-router)
│   ├── (auth)/              # login, registro
│   ├── (tabs)/              # inicio, deudas, tramites, tarjeta, perfil
│   └── tramites/            # nuevo, detalle [id]
├── components/muni/         # UI reutilizable (boton, tarjeta, badge, input, header)
├── constants/               # theme.ts, config.ts
├── services/                # api.ts, endpoints.ts, types.ts, storage.ts
├── store/                   # auth-context.tsx
└── hooks/                   # hooks existentes del template
```

## Flujo de autenticacion

1. El usuario ingresa DNI + contrasena en `/(auth)/login`.
2. El backend devuelve `access` + `refresh` JWT y datos del ciudadano.
3. Los tokens se guardan en `SecureStore` (movil) o `AsyncStorage`/`localStorage` (web).
4. `configureApi()` conecta el cliente HTTP con el store para adjuntar el header `Authorization` y refrescar tokens vencidos automaticamente.
5. `AuthGate` en `app/_layout.tsx` redirige segun el estado a `(auth)` o `(tabs)`.

## Modulos

- **Inicio**: resumen tributario + accesos rapidos + noticias.
- **Deudas**: lista de tributos y multas, totales, pago simulado.
- **Tramites**: listado TUPA, iniciar expediente, seguimiento con historial.
- **Tarjeta ciudadana**: emision + visual digital con codigo y vencimiento, beneficios asociados.
- **Perfil**: datos del ciudadano, contactos municipales, logout.
