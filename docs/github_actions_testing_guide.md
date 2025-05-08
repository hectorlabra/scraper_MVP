# Guía de Prueba y Validación del Workflow de GitHub Actions

Esta guía proporciona instrucciones para probar y validar el workflow de GitHub Actions que hemos configurado para la ejecución diaria del scraper.

## Requisitos Previos

Antes de realizar las pruebas, asegúrate de haber completado los siguientes pasos:

1. El archivo `.github/workflows/daily-scrape.yml` debe estar presente en tu repositorio
2. Todos los secretos requeridos deben estar configurados en GitHub (consulta `docs/github_actions_secrets_guide.md`)
3. El código debe estar actualizado y subido al repositorio de GitHub

## Métodos de Prueba

### 1. Ejecución Manual del Workflow

La forma más sencilla de probar el workflow es ejecutarlo manualmente:

1. Ve a la pestaña "Actions" en tu repositorio de GitHub
2. Selecciona el workflow "Daily Scrape" en la barra lateral izquierda
3. Haz clic en el botón "Run workflow"
4. Opcional: Marca la casilla "Run the workflow in debug mode" para obtener logs más detallados
5. Haz clic en el botón verde "Run workflow"

Esto iniciará una ejecución manual del workflow, que puedes monitorear en tiempo real.

### 2. Prueba con Error Deliberado

Para probar el manejo de errores y las notificaciones de fallo:

1. Modifica temporalmente el archivo `.env.template` o una variable de entorno crucial en GitHub Secrets para que contenga un valor inválido
2. Ejecuta el workflow manualmente como se describió anteriormente
3. Verifica que:
   - El workflow falla correctamente
   - Se envía una notificación de error al correo electrónico configurado
   - Los logs y resultados se suben como artefactos a pesar del error
4. Restaura el valor correcto de la variable de entorno después de la prueba

### 3. Validación de Resultados

Después de ejecutar el workflow, valida los resultados:

1. Revisa los logs del workflow en la interfaz de GitHub Actions
2. Descarga y examina los artefactos generados:
   - Archivos JSON de resultados en la carpeta `results/`
   - Archivos de log en la carpeta `logs/`
   - El archivo `scraper_output.log`
3. Verifica que se haya recibido la notificación por correo electrónico apropiada
4. Si la ejecución fue exitosa, verifica que los datos se hayan subido correctamente a Google Sheets

## Lista de Verificación para Validación

Utiliza esta lista de verificación para asegurarte de que el workflow funciona correctamente:

- [ ] El workflow se ejecuta sin errores
- [ ] El scraper se inicializa correctamente
- [ ] Las credenciales y variables de entorno se cargan adecuadamente
- [ ] El scraper recopila datos de las fuentes configuradas
- [ ] Los datos se procesan y validan correctamente
- [ ] Los resultados se suben a Google Sheets (si está habilitado)
- [ ] Los artefactos (logs y resultados) se suben correctamente
- [ ] Las notificaciones se envían a la dirección de correo electrónico configurada
- [ ] El manejo de errores funciona como se esperaba (mediante prueba deliberada)
- [ ] La ejecución completa termina dentro del límite de tiempo establecido (120 minutos)

## Solución de Problemas Comunes

### El workflow falla durante la configuración de credenciales

- **Problema**: Error al configurar las credenciales de Google Service Account
- **Solución**: Verifica que el secreto `GOOGLE_SERVICE_ACCOUNT_JSON` contenga el JSON completo y válido de la cuenta de servicio

### El workflow falla durante la ejecución del scraper

- **Problema**: Errores relacionados con la autenticación en servicios externos
- **Solución**: Verifica que las credenciales (Instagram, Google) sean correctas y estén actualizadas

### No se reciben notificaciones por correo

- **Problema**: Las notificaciones no llegan al correo electrónico configurado
- **Solución**: Verifica la configuración SMTP, asegúrate de que el servidor permita el envío desde aplicaciones, y revisa la carpeta de spam

### El workflow supera el límite de tiempo

- **Problema**: La ejecución tarda demasiado y alcanza el límite de 120 minutos
- **Solución**: Considera reducir el alcance del scraping (menos consultas o resultados máximos) o aumenta el límite de tiempo

## Siguiente Pasos Después de la Validación

Una vez que hayas validado que el workflow funciona correctamente:

1. Asegúrate de restaurar cualquier cambio temporal realizado para las pruebas
2. Verifica que la programación cron ('0 2 \* \* \*') sea apropiada para tus necesidades
3. Monitorea las primeras ejecuciones programadas para asegurarte de que todo funcione como se espera
4. Considera establecer alertas adicionales o integraciones para monitorear la salud del workflow a largo plazo
