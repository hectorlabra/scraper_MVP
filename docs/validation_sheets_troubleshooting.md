# Solución de Problemas: ValidationProcessor + Google Sheets

Este documento proporciona soluciones a problemas comunes en la integración entre ValidationProcessor y Google Sheets.

## Error: "The user does not have sufficient permissions for this file"

Este error ocurre cuando la cuenta de servicio de Google no tiene los permisos necesarios para acceder a las APIs requeridas o a una hoja específica.

### Solución:

1. **Asegúrate de que las APIs necesarias estén habilitadas:**

   - Google Sheets API
   - Google Drive API

   Puedes habilitarlas en la [Consola de Google Cloud](https://console.cloud.google.com/apis/library).

2. **Crea una nueva hoja propiedad de la cuenta de servicio:**

   ```bash
   python scripts/setup_google_integration.py
   ```

   Este script creará una nueva hoja de cálculo que será propiedad de la cuenta de servicio, garantizando permisos completos.

3. **Comprueba que la cuenta de servicio tiene permisos adecuados:**
   Si estás usando una hoja existente, asegúrate de que esté compartida con el email de la cuenta de servicio (verificable en el archivo de credenciales JSON).

## Error: "API has not been used in project before or it is disabled"

Este error indica que las APIs necesarias no están habilitadas en el proyecto de Google Cloud.

### Solución:

1. Ve a la [Biblioteca de APIs](https://console.cloud.google.com/apis/library) en la Consola de Google Cloud
2. Busca y habilita:
   - Google Sheets API
   - Google Drive API
3. Espera unos minutos para que los cambios surtan efecto

## Error: "Credentials file not found"

Este error ocurre cuando el sistema no puede localizar el archivo de credenciales de la cuenta de servicio.

### Solución:

1. Asegúrate de que el archivo de credenciales existe y está en la ruta correcta
2. Configura la variable de entorno `GOOGLE_SERVICE_ACCOUNT_FILE` para que apunte a la ubicación del archivo
3. Alternativamente, coloca el archivo en la ubicación predeterminada: `config/scrapermvp-f254174c1385.json`

## Error: "Cannot create spreadsheet"

Este error puede ocurrir cuando hay problemas con los permisos de la cuenta de servicio.

### Solución:

1. Verifica que la cuenta de servicio tenga los roles adecuados (mínimo "Editor")
2. Asegúrate de que las APIs de Google Sheets y Drive estén habilitadas
3. Utiliza el script de configuración para crear una nueva hoja:
   ```bash
   python scripts/setup_google_integration.py
   ```

## Verificación Completa de la Integración

Para verificar que toda la integración funciona correctamente:

```bash
python scripts/verify_validation_sheets_integration.py
```

Este script realizará comprobaciones completas de la configuración y mostrará mensajes detallados si encuentra problemas.

## Demostración de la Integración Completa

Para ver una demostración del flujo completo desde la validación hasta la carga en Google Sheets:

```bash
python scripts/demo_validation_sheets_integration.py
```

## Recursos Adicionales

- [Documentación de la API de Google Sheets](https://developers.google.com/sheets/api)
- [Guía de la API de Google Drive](https://developers.google.com/drive)
- [Documentación de cuentas de servicio de Google Cloud](https://cloud.google.com/iam/docs/service-accounts)
