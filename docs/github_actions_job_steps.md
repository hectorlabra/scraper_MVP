# GitHub Actions Job Steps - Daily Scrape Workflow

Este documento detalla los pasos del trabajo configurados en el workflow de GitHub Actions para la ejecución automatizada diaria del scraper.

## Resumen del Workflow

El workflow **daily-scrape.yml** está diseñado para ejecutar automáticamente el scraper de datos una vez al día, procesar los datos recopilados y notificar sobre los resultados. El workflow también se puede ejecutar manualmente según sea necesario.

## Explicación detallada de los pasos

### 1. Configuración del entorno

#### Checkout del código

```yaml
- name: Checkout code
  uses: actions/checkout@v3
```

- Este paso clona el repositorio completo en el entorno de ejecución de GitHub Actions.
- Permite que el workflow tenga acceso a todos los archivos del proyecto.

#### Configuración de Python

```yaml
- name: Set up Python
  uses: actions/setup-python@v4
  with:
    python-version: "3.10"
```

- Instala Python 3.10 en el entorno de ejecución.
- Esta versión es compatible con todas las dependencias del proyecto.

#### Instalación de Chrome

```yaml
- name: Install Chrome
  run: |
    wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | sudo apt-key add -
    echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" | sudo tee /etc/apt/sources.list.d/google-chrome.list
    sudo apt-get update
    sudo apt-get install -y google-chrome-stable
```

- Instala Google Chrome, necesario para los scrapers basados en Selenium.
- Utiliza la versión estable más reciente de Chrome.

#### Instalación de dependencias

```yaml
- name: Install dependencies
  run: |
    python -m pip install --upgrade pip
    pip install -r requirements.txt
```

- Actualiza pip a la última versión.
- Instala todas las dependencias especificadas en el archivo requirements.txt.

### 2. Configuración de credenciales y variables de entorno

#### Configuración de la cuenta de servicio de Google

```yaml
- name: Setup service account credentials
  run: |
    echo "${{ secrets.GOOGLE_SERVICE_ACCOUNT_JSON }}" > config/service-account.json
    echo "GOOGLE_SERVICE_ACCOUNT_FILE=config/service-account.json" >> .env
```

- Crea el archivo de cuenta de servicio de Google a partir del secreto.
- Actualiza el archivo .env para apuntar al archivo de credenciales.

#### Configuración de variables de entorno

```yaml
- name: Setup environment variables
  run: |
    echo "GOOGLE_SHEETS_SPREADSHEET_ID=${{ secrets.GOOGLE_SHEETS_SPREADSHEET_ID }}" >> .env
    echo "GOOGLE_SHEETS_TITLE=LeadScraper Results $(date +'%Y-%m-%d')" >> .env
    echo "INSTAGRAM_USERNAME=${{ secrets.INSTAGRAM_USERNAME }}" >> .env
    echo "INSTAGRAM_PASSWORD=${{ secrets.INSTAGRAM_PASSWORD }}" >> .env
    echo "GOOGLE_MAPS_WAIT_TIME=5.0" >> .env
    echo "HEADLESS_BROWSER=True" >> .env
    echo "LOG_LEVEL=INFO" >> .env

    # Optional: Configure additional environment variables from GitHub secrets
    if [ -n "${{ secrets.ADDITIONAL_ENV_VARS }}" ]; then
      echo "${{ secrets.ADDITIONAL_ENV_VARS }}" >> .env
    fi
```

- Configura todas las variables de entorno necesarias para el scraper.
- Utiliza los secretos almacenados en GitHub.
- Permite variables adicionales a través del secreto ADDITIONAL_ENV_VARS.

#### Verificación del entorno

```yaml
- name: Verify environment setup
  run: python check_env.py
```

- Ejecuta el script de verificación del entorno para asegurar que todo esté configurado correctamente.
- Detecta problemas de configuración antes de la ejecución principal.

### 3. Ejecución del scraper

#### Ejecución del script principal

```yaml
- name: Run scraper
  id: run_scraper
  continue-on-error: true # Continue to next steps even if this fails
  run: |
    mkdir -p logs
    mkdir -p results
    python main.py | tee scraper_output.log
    # Save exit code for later use
    echo "EXIT_CODE=$?" >> $GITHUB_ENV
```

- Crea los directorios necesarios para los logs y resultados.
- Ejecuta el script principal y guarda la salida en un archivo de log.
- Captura el código de salida para determinar si la ejecución fue exitosa.
- Utiliza `continue-on-error: true` para asegurar que el workflow continúe incluso si el scraper falla.

#### Comprobación de errores

```yaml
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

- Determina si el scraper se ejecutó correctamente basándose en el código de salida.
- Guarda el estado del scraper como variable de entorno para pasos posteriores.

### 4. Gestión de resultados y notificaciones

#### Subida de resultados como artefactos

```yaml
- name: Upload results
  uses: actions/upload-artifact@v3
  with:
    name: scraper-results
    path: |
      results/
      logs/
      scraper_output.log
    retention-days: 7
```

- Sube los resultados, logs y la salida del scraper como artefactos del workflow.
- Establece un periodo de retención de 7 días para estos artefactos.

#### Notificación de éxito

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

- Envía una notificación por correo electrónico cuando el scraper se ejecuta correctamente.
- Incluye el archivo de log como adjunto.

#### Notificación de fallo

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

- Envía una notificación por correo electrónico cuando el scraper falla.
- Incluye el código de error y el archivo de log como información de diagnóstico.

#### Salida con código de error

```yaml
- name: Exit with error code if failed
  if: env.scraper_status != 'success'
  run: exit 1
```

- Asegura que el workflow termine con un código de error si el scraper falló.
- Esto marca el workflow como fallido en la interfaz de GitHub.

## Personalización

El workflow está diseñado para ser configurado principalmente a través de secretos y variables de entorno, lo que permite la personalización sin modificar el archivo de workflow. Para cambios más significativos en el comportamiento del workflow, edita el archivo `.github/workflows/daily-scrape.yml` directamente.
