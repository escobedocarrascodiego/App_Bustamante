/* eslint-disable @typescript-eslint/no-require-imports */
/**
 * Config plugin que fuerza el trafico HTTP en texto plano (cleartext) en Android.
 *
 * Por que se necesita:
 *   - Desde Android 9 (API 28) el cleartext esta deshabilitado por defecto.
 *   - La propiedad `android.usesCleartextTraffic` en `app.json` NO esta en el
 *     schema oficial de Expo y se ignora silenciosamente.
 *   - `expo-build-properties` con `usesCleartextTraffic: true` setea el flag
 *     en el AndroidManifest, pero si alguna libreria nativa (p. ej. ciertas
 *     versiones de react-native-webview) inyecta su propio
 *     `android:networkSecurityConfig`, ese archivo XML SOBREESCRIBE el flag.
 *
 * Lo que hace este plugin:
 *   1. Crea `android/app/src/main/res/xml/network_security_config.xml` con
 *      `cleartextTrafficPermitted="true"` para TODOS los dominios.
 *   2. Anade `android:networkSecurityConfig="@xml/network_security_config"`
 *      al `<application>` del AndroidManifest.
 *   3. Anade tambien `android:usesCleartextTraffic="true"` como respaldo.
 *
 * Resultado: la app puede hablar con cualquier IP/dominio por HTTP plano.
 *
 * NOTA DE SEGURIDAD: esto desactiva una proteccion importante. Solo se
 * justifica porque los backends de la municipalidad estan expuestos por IP
 * sin certificado SSL. Cuando se migre a HTTPS, eliminar este plugin.
 */
const { withAndroidManifest, withDangerousMod, AndroidConfig } = require('@expo/config-plugins');
const fs = require('fs');
const path = require('path');

const NETWORK_SECURITY_CONFIG_XML = `<?xml version="1.0" encoding="utf-8"?>
<network-security-config>
  <base-config cleartextTrafficPermitted="true">
    <trust-anchors>
      <certificates src="system" />
    </trust-anchors>
  </base-config>
</network-security-config>
`;

function withCleartextTraffic(config) {
  config = withAndroidManifest(config, async (cfg) => {
    const application = AndroidConfig.Manifest.getMainApplicationOrThrow(cfg.modResults);
    application.$['android:usesCleartextTraffic'] = 'true';
    application.$['android:networkSecurityConfig'] = '@xml/network_security_config';
    return cfg;
  });

  config = withDangerousMod(config, [
    'android',
    async (cfg) => {
      const xmlDir = path.join(
        cfg.modRequest.platformProjectRoot,
        'app',
        'src',
        'main',
        'res',
        'xml',
      );
      fs.mkdirSync(xmlDir, { recursive: true });
      fs.writeFileSync(
        path.join(xmlDir, 'network_security_config.xml'),
        NETWORK_SECURITY_CONFIG_XML,
        'utf8',
      );
      return cfg;
    },
  ]);

  return config;
}

module.exports = withCleartextTraffic;
