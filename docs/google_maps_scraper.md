# Google Maps Scraper - Documentación

## Descripción

El `GoogleMapsScraper` es un componente de nuestro sistema LeadScraper LATAM diseñado para extraer información de negocios desde Google Maps. Esta herramienta permite realizar búsquedas de negocios por categoría y ubicación, y extraer datos relevantes como nombres, direcciones, números de teléfono, sitios web y más.

## Características principales

- Búsqueda de negocios por categoría y ubicación en Google Maps
- Extracción de información detallada (nombre, dirección, teléfono, sitio web, valoración, etc.)
- Resistencia a la detección con mecanismos anti-bot
- Navegación a través de múltiples páginas de resultados
- Manejo de errores y reintentos automáticos
- Opciones de configuración flexibles

## Requisitos

- Python 3.8+
- Selenium 4.32.0+
- undetected-chromedriver 3.5.5+ (opcional)
- Google Chrome instalado
- Bibliotecas adicionales: véase `requirements.txt`

## Instalación

Asegúrate de tener instaladas todas las dependencias necesarias:

```bash
# Activar el entorno virtual
source venv/bin/activate

# Instalar dependencias
pip install selenium==4.32.0 undetected-chromedriver==3.5.5
```

## Uso básico

### Desde scripts

```python
from scrapers.google_maps_scraper import GoogleMapsScraper

# Crear una instancia del scraper
scraper = GoogleMapsScraper(
    max_results=50,                # Número máximo de resultados a extraer
    headless=False,                # True para ejecutar sin interfaz gráfica
    request_delay=3.0,             # Retraso base entre acciones (segundos)
    random_delay_range=(2.0, 5.0), # Rango de retraso aleatorio adicional
    use_undetected_driver=False    # True para usar undetected-chromedriver
)

try:
    # Realizar búsqueda
    results = scraper.scrape(
        query="restaurantes",       # Término de búsqueda
        location="Ciudad de México" # Ubicación
    )

    # Procesar resultados
    print(f"Se encontraron {len(results)} negocios:")
    for business in results:
        print(f"Nombre: {business.get('name')}")
        print(f"Dirección: {business.get('address')}")
        print(f"Teléfono: {business.get('phone')}")
        print(f"Sitio web: {business.get('website')}")
        print("----")

finally:
    # Siempre cerrar el scraper al finalizar
    scraper.close()
```

### Desde línea de comandos

El scraper también puede utilizarse desde la línea de comandos mediante el script `scripts/gmaps_scraper_cli.py`:

```bash
# Activar el entorno virtual
source venv/bin/activate

# Ejecutar el scraper CLI
python scripts/gmaps_scraper_cli.py "restaurantes" --location "Ciudad de México" --max-results 50 --output "results/restaurantes_cdmx.json"
```

### Opciones de línea de comandos

- `query`: Término de búsqueda (obligatorio)
- `--location, -l`: Ubicación para la búsqueda
- `--max-results, -m`: Número máximo de resultados a extraer
- `--headless`: Ejecutar en modo headless (sin interfaz gráfica)
- `--output, -o`: Ruta del archivo de salida JSON
- `--delay, -d`: Retraso entre acciones en segundos
- `--debug`: Habilitar registro de depuración
- `--use-undetected`: Usar undetected-chromedriver (más evasivo pero puede tener problemas de compatibilidad)

## Datos extraídos

El scraper extrae los siguientes datos de cada negocio (cuando están disponibles):

- `name`: Nombre del negocio
- `address`: Dirección completa
- `phone`: Número de teléfono
- `website`: URL del sitio web
- `rating`: Valoración (de 1 a 5)
- `reviews_count`: Número de reseñas
- `categories`: Categorías del negocio
- `place_id`: Identificador único de Google Maps
- `source`: Fuente de los datos (siempre "google_maps")

## Opciones avanzadas

### Configuración del scraper

```python
scraper = GoogleMapsScraper(
    # Opciones básicas
    max_results=100,                # Número máximo de resultados
    headless=True,                  # Ejecutar sin interfaz gráfica
    request_delay=3.0,              # Retraso base entre acciones
    random_delay_range=(2.0, 5.0),  # Rango de retraso aleatorio adicional

    # Opciones avanzadas
    max_retry_count=3,              # Número máximo de reintentos
    enable_proxies=False,           # Usar proxies (configurados en .env)
    use_undetected_driver=True      # Usar undetected-chromedriver
)
```

### Detección y manejo de CAPTCHAs

El scraper incluye mecanismos para detectar y manejar CAPTCHAs y bloqueos. Si se detecta un CAPTCHA, el scraper realiza una pausa extendida y luego intenta continuar. En casos persistentes, se recomienda:

1. Cambiar la dirección IP
2. Reducir la frecuencia de las solicitudes (aumentar `request_delay`)
3. Alternar entre modo headless y no-headless
4. Utilizar proxies diferentes

## Ejemplo de demo

Para probar rápidamente la funcionalidad del scraper con ejemplos predefinidos:

```bash
# Activar el entorno virtual
source venv/bin/activate

# Ejecutar la demostración
python scripts/demo_google_maps.py
```

Este script ejecutará búsquedas de ejemplo en diferentes países de América Latina y mostrará los resultados.

## Solución de problemas

### El navegador se cierra inmediatamente

Asegúrate de que tienes instalada la versión correcta de ChromeDriver compatible con tu versión de Chrome. Si usas `use_undetected_driver=True`, prueba con `use_undetected_driver=False` para usar el modo de compatibilidad.

### Se detectan pocos o ningún resultado

- Verifica tu conexión a Internet
- Asegúrate de que los términos de búsqueda sean válidos
- Aumenta el tiempo de espera (`request_delay`)
- Intenta sin modo headless para diagnosticar el problema visualmente

### Error de SSL o certificado

En sistemas macOS, pueden ocurrir errores de certificado SSL. El scraper intenta manejarlos automáticamente, pero si persisten, considera configurar el entorno Python para aceptar certificados:

```bash
# Desde el terminal:
/Applications/Python*/Install\ Certificates.command
```

## Consideraciones de uso

- Este scraper está diseñado para uso académico y de investigación.
- Usa velocidades de extracción razonables para evitar problemas con los servidores de Google.
- El uso excesivo puede resultar en bloqueos temporales de IP.
- Respeta siempre los términos de servicio de Google.
