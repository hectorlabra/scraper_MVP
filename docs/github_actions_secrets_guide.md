# GitHub Actions Secrets Configuration Guide

Este documento proporciona instrucciones sobre cómo configurar los secretos y variables de entorno necesarios para el workflow de GitHub Actions.

## Secretos requeridos

Los siguientes secretos deben configurarse en tu repositorio de GitHub para que el workflow funcione correctamente:

| Nombre del Secreto             | Descripción                                                            | Formato / Ejemplo                                                               |
| ------------------------------ | ---------------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| `GOOGLE_SERVICE_ACCOUNT_JSON`  | Contenido completo del archivo JSON de la cuenta de servicio de Google | Archivo JSON completo                                                           |
| `GOOGLE_SHEETS_SPREADSHEET_ID` | ID de la hoja de cálculo de Google Sheets                              | `1BxiMVs0XRA5nFMdKvBdBZjgmUUqptlbs74OgvE2upms`                                  |
| `INSTAGRAM_USERNAME`           | Nombre de usuario de Instagram                                         | `usuario_instagram`                                                             |
| `INSTAGRAM_PASSWORD`           | Contraseña de Instagram                                                | `contraseña_segura`                                                             |
| `SMTP_SERVER`                  | Servidor SMTP para enviar notificaciones                               | `smtp.gmail.com`                                                                |
| `SMTP_PORT`                    | Puerto SMTP                                                            | `587`                                                                           |
| `SMTP_USERNAME`                | Usuario SMTP (generalmente el correo electrónico)                      | `ejemplo@gmail.com`                                                             |
| `SMTP_PASSWORD`                | Contraseña SMTP o token de aplicación                                  | `contraseña_o_token`                                                            |
| `NOTIFICATION_EMAIL`           | Correo electrónico donde se enviarán las notificaciones                | `destinatario@ejemplo.com`                                                      |
| `ADDITIONAL_ENV_VARS`          | Variables de entorno adicionales (opcional)                            | Formato de variables de entorno múltiples: `VARIABLE1=valor1\nVARIABLE2=valor2` |

## Cómo configurar los secretos en GitHub

1. Ve a la página principal de tu repositorio en GitHub
2. Haz clic en "Settings" (Configuración) en la barra superior
3. En el menú lateral izquierdo, haz clic en "Secrets and variables" y luego en "Actions"
4. Haz clic en "New repository secret"
5. Ingresa el nombre del secreto (por ejemplo, `GOOGLE_SERVICE_ACCOUNT_JSON`)
6. Pega el valor del secreto en el campo "Value"
7. Haz clic en "Add secret"
8. Repite estos pasos para cada secreto requerido

## Configuración especial para GOOGLE_SERVICE_ACCOUNT_JSON

Para el secreto `GOOGLE_SERVICE_ACCOUNT_JSON`, debes copiar todo el contenido del archivo JSON de la cuenta de servicio de Google. Este archivo contiene credenciales sensibles, por lo que debe manejarse con cuidado:

1. Abre el archivo JSON de la cuenta de servicio (ubicado en `config/scrapermvp-f254174c1385.json` en tu repositorio)
2. Copia todo el contenido del archivo, incluyendo las llaves de apertura y cierre `{}`
3. Pega este contenido como el valor del secreto `GOOGLE_SERVICE_ACCOUNT_JSON`

## Secreto opcional: ADDITIONAL_ENV_VARS

El secreto `ADDITIONAL_ENV_VARS` te permite configurar variables de entorno adicionales sin tener que modificar el workflow. Cada variable debe estar en una línea separada con el formato `NOMBRE=valor`. Por ejemplo:

```
GOOGLE_MAPS_MAX_RESULTS=200
ENABLE_DIRECTORIES=True
DIRECTORY_WAIT_TIME=5.0
```

## Notas de seguridad

- Nunca compartas estos secretos en el código fuente o en los logs
- Revisa periódicamente y rota las credenciales, especialmente para servicios externos
- Limita los permisos de la cuenta de servicio de Google a lo estrictamente necesario
- Considera usar tokens de aplicación en lugar de contraseñas para servicios como Gmail

## Solución de problemas

Si el workflow falla debido a problemas con los secretos:

1. Verifica que todos los secretos requeridos estén configurados correctamente
2. Asegúrate de que las credenciales sean válidas y estén activas
3. Verifica si hay errores específicos en los logs del workflow relacionados con la autenticación
4. Para problemas con la cuenta de servicio de Google, verifica que tenga los permisos necesarios en Google Sheets
