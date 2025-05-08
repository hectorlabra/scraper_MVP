# GitHub Actions - Manejo de Errores y Sistema de Notificaciones

Este documento describe cómo se implementa el manejo de errores y el sistema de notificaciones en el workflow de GitHub Actions para el scraper.

## Estrategia de Manejo de Errores

El workflow incorpora una estrategia robusta de manejo de errores diseñada para:

1. Detectar y registrar errores en cada etapa del proceso
2. Continuar la ejecución cuando sea posible para completar tareas críticas
3. Proporcionar información detallada sobre errores para facilitar la depuración
4. Notificar a los administradores sobre cualquier problema encontrado

### Mecanismos de Manejo de Errores Implementados

#### 1. Ejecución Continua a Pesar de Errores

```yaml
- name: Run scraper
  id: run_scraper
  continue-on-error: true
  run: |
    python main.py | tee scraper_output.log
    echo "EXIT_CODE=$?" >> $GITHUB_ENV
```

El parámetro `continue-on-error: true` permite que el workflow continúe ejecutándose incluso si el script del scraper falla. Esto es crucial para garantizar que:

- Se capturen todos los logs y resultados para diagnóstico
- Las notificaciones de fallo puedan enviarse
- Los artefactos se suban incluso en caso de error

#### 2. Captura y Seguimiento del Código de Salida

El workflow captura el código de salida del script principal y lo utiliza para determinar si la ejecución fue exitosa:

```yaml
echo "EXIT_CODE=$?" >> $GITHUB_ENV

- name: Check for errors
  id: error_check
  run: |
    if [ "${{ env.EXIT_CODE }}" != "0" ]; then
      echo "Scraper completed with errors (exit code: ${{ env.EXIT_CODE }})"
      echo "scraper_status=failed" >> $GITHUB_ENV
    else
      echo "Scraper completed successfully"
      echo "scraper_status=success" >> $GITHUB_ENV
    fi
```

Esta técnica permite:

- Registrar el estado preciso de la ejecución
- Tomar decisiones basadas en el éxito o fracaso del script
- Proporcionar información útil en los logs del workflow

#### 3. Timeout para Prevenir Ejecuciones Bloqueadas

```yaml
jobs:
  scrape:
    name: Run Daily Scraper
    runs-on: ubuntu-latest
    timeout-minutes: 120 # Set a timeout of 2 hours for the job
```

El parámetro `timeout-minutes: 120` establece un límite máximo de ejecución de 2 horas para evitar:

- Ejecuciones infinitas debido a errores no detectados
- Consumo excesivo de minutos de GitHub Actions
- Problemas que podrían surgir si un scraper se queda bloqueado

#### 4. Verificación Previa del Entorno

```yaml
- name: Verify environment setup
  run: python check_env.py
```

El script `check_env.py` verifica que todas las variables de entorno necesarias estén configuradas correctamente antes de ejecutar el scraper principal, lo que ayuda a detectar problemas de configuración de manera temprana.

#### 5. Estado de Salida Apropiado en Caso de Error

```yaml
- name: Exit with error code if failed
  if: env.scraper_status != 'success'
  run: exit 1
```

Este paso final asegura que el workflow tenga un estado de salida apropiado que refleje el resultado real de la ejecución, lo que es útil para:

- Mostrar visualmente el estado en la interfaz de GitHub Actions
- Integraciones con otros sistemas que puedan depender del estado del workflow
- Estadísticas y seguimiento histórico de ejecuciones exitosas vs. fallidas

## Sistema de Notificaciones

El workflow incluye un sistema completo de notificaciones por correo electrónico para mantener informados a los administradores sobre el estado de las ejecuciones programadas.

### Componentes del Sistema de Notificaciones

#### 1. Notificación de Éxito

```yaml
- name: Send success notification
  if: env.scraper_status == 'success'
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: ${{ secrets.SMTP_SERVER }}
    server_port: ${{ secrets.SMTP_PORT }}
    username: ${{ secrets.SMTP_USERNAME }}
    password: ${{ secrets.SMTP_PASSWORD }}
    subject: "✅ [ScraperMVP] Daily scrape completed successfully"
    body: |
      The daily scrape job completed successfully.

      Timestamp: ${{ steps.date.outputs.date }}

      Check the attached files for results and logs.
    to: ${{ secrets.NOTIFICATION_EMAIL }}
    from: ScraperMVP <${{ secrets.SMTP_USERNAME }}>
    attachments: scraper_output.log
```

Esta notificación:

- Se envía solo cuando el scraper se ejecuta correctamente
- Incluye un asunto claramente marcado con un emoji de éxito
- Adjunta el log completo de la ejecución para revisión
- Va dirigida al correo electrónico configurado en los secretos

#### 2. Notificación de Fallo

```yaml
- name: Send failure notification
  if: env.scraper_status != 'success'
  uses: dawidd6/action-send-mail@v3
  with:
    server_address: ${{ secrets.SMTP_SERVER }}
    server_port: ${{ secrets.SMTP_PORT }}
    username: ${{ secrets.SMTP_USERNAME }}
    password: ${{ secrets.SMTP_PASSWORD }}
    subject: "❌ [ScraperMVP] Daily scrape failed"
    body: |
      The daily scrape job failed with exit code: ${{ env.EXIT_CODE }}

      Timestamp: ${{ steps.date.outputs.date }}

      Please check the attached log file for details.
    to: ${{ secrets.NOTIFICATION_EMAIL }}
    from: ScraperMVP <${{ secrets.SMTP_USERNAME }}>
    attachments: scraper_output.log
```

Esta notificación:

- Se envía solo cuando el scraper falla
- Incluye el código de error específico para facilitar la depuración
- Adjunta el log completo que contiene detalles del error
- Tiene un asunto claramente marcado con un emoji de error

### Configuración del Sistema de Notificaciones

Para que las notificaciones funcionen correctamente, se deben configurar los siguientes secretos en GitHub:

| Secreto              | Descripción                                               |
| -------------------- | --------------------------------------------------------- |
| `SMTP_SERVER`        | Servidor SMTP para enviar correos (ej: smtp.gmail.com)    |
| `SMTP_PORT`          | Puerto SMTP (generalmente 587 para TLS)                   |
| `SMTP_USERNAME`      | Nombre de usuario SMTP (generalmente dirección de correo) |
| `SMTP_PASSWORD`      | Contraseña SMTP o token de aplicación                     |
| `NOTIFICATION_EMAIL` | Dirección de correo electrónico del destinatario          |

#### Notas sobre Configuración de Correo

Si utilizas Gmail como servidor SMTP:

1. Es recomendable crear una "Contraseña de aplicación" en lugar de usar la contraseña principal
2. Asegúrate de que la cuenta tenga habilitado el acceso a aplicaciones menos seguras o utiliza la autenticación OAuth2
3. Considera usar una cuenta dedicada para las notificaciones en lugar de una cuenta personal

## Escalabilidad y Mejoras Futuras

El sistema actual de manejo de errores y notificaciones puede expandirse con las siguientes mejoras:

1. **Integración con Slack/Teams**: Añadir notificaciones a plataformas de mensajería para equipos
2. **Panel de monitoreo**: Crear un panel que muestre el estado histórico de ejecuciones
3. **Reintentos automáticos**: Implementar reintentos automáticos para errores transitorios
4. **Alertas diferenciadas**: Categorizar los errores por gravedad y enviar diferentes tipos de alertas
5. **Manejo de errores específicos**: Detectar y manejar tipos específicos de errores de manera personalizada
