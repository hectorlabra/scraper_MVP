# LeadScraper LATAM

Script Python para automatizar la extracción diaria de leads comerciales en LATAM desde Google Maps, Instagram y directorios públicos, guardando los datos en Google Sheets.

## Descripción

El objetivo principal de este proyecto es proporcionar a agencias de marketing una herramienta para acceder a datos locales de negocios sin esfuerzo manual. La herramienta recopila información como nombres, direcciones, teléfonos, sitios web, perfiles de Instagram y más.

## Funcionalidades Principales

- **Scraping Multi-fuente**: Extracción de datos de Google Maps, Instagram y directorios públicos como Páginas Amarillas, GuiaLocal, y Cylex
- **Procesamiento Inteligente**: Eliminación de duplicados exactos y similares mediante algoritmos de coincidencia difusa
- **Optimización para Grandes Conjuntos de Datos**: Procesamiento en paralelo y por lotes para manejar eficientemente grandes volúmenes de datos
- **Validación de Datos**: Comprobación automática de correos electrónicos y números de teléfono
- **Integración con Google Sheets**: Actualización automática de hojas de cálculo con los datos procesados
- **Manejo de Errores**: Sistema robusto de seguimiento y recuperación de errores
- **Informes Detallados**: Generación de reportes estadísticos del proceso de scraping
- **Optimización de Rendimiento**: Paralelización de scrapers, caché de resultados y esperas inteligentes para mejorar la velocidad y eficiencia

## Tecnologías Utilizadas

- Python, BeautifulSoup, Selenium (scraping)
- Instaloader (Instagram)
- Pandas (procesamiento de datos)
- Google Sheets API (gspread)
- GitHub Actions (automatización)

## Instalación

### Requisitos Previos

- Python 3.7+
- Navegador Chrome (para web scraping)
- Credenciales de Google API (para integración con Google Sheets)

### Configuración

1. Clonar el repositorio:

   ```bash
   git clone https://github.com/yourusername/scraperMVP.git
   cd scraperMVP
   ```

2. Crear y activar entorno virtual:

   ```bash
   python -m venv venv
   source venv/bin/activate  # En Windows: venv\Scripts\activate
   ```

3. Instalar dependencias:

   ```bash
   pip install -r requirements.txt
   ```

4. Configurar variables de entorno:
   - Copiar `.env.template` a `.env`
   - Actualizar los valores de configuración en `.env` con tus credenciales y preferencias

## Configuración

La aplicación utiliza variables de entorno para la configuración. Puedes configurar estas variables en el archivo `.env`:

### Configuración de Google API

```
GOOGLE_SERVICE_ACCOUNT_FILE=config/credentials.json
GOOGLE_SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
GOOGLE_SHEETS_TITLE=LeadScraper Results
GOOGLE_SHEETS_APPEND=True
ENABLE_GOOGLE_SHEETS=True
GOOGLE_SHEETS_BATCH_SIZE=1000
```

### Configuración de Instagram

```
INSTAGRAM_USERNAME=your_instagram_username
INSTAGRAM_PASSWORD=your_instagram_password
INSTAGRAM_HASHTAGS=negociosmexicanos,emprendedoreslatinos
INSTAGRAM_LOCATIONS=111462462,212999109
INSTAGRAM_MAX_POSTS=100
ENABLE_INSTAGRAM=True
```

### Configuración de Google Maps

```
GOOGLE_MAPS_QUERIES=[{"query": "restaurantes", "location": "Ciudad de México, México"}, {"query": "hoteles", "location": "Buenos Aires, Argentina"}]
GOOGLE_MAPS_MAX_RESULTS=100
GOOGLE_MAPS_WAIT_TIME=2.0
ENABLE_GOOGLE_MAPS=True
```

### Configuración de Directorios

```
DIRECTORIES_TO_SCRAPE=paginas_amarillas,guialocal,cylex
DIRECTORY_QUERIES=[{"query": "restaurantes", "location": "Ciudad de México"}, {"query": "hoteles", "location": "Buenos Aires"}]
DIRECTORY_MAX_RESULTS=50
DIRECTORY_WAIT_TIME=3.0
ENABLE_DIRECTORIES=True
```

### Configuración de Procesamiento de Datos

```
DEDUPLICATION_EXACT=True
DEDUPLICATION_FUZZY=True
FUZZY_THRESHOLD=80
MATCH_FIELDS=business_name,phone,email
VALIDATE_EMAILS=True
VALIDATE_PHONES=True
MIN_DATA_QUALITY=0.5
USE_PARALLEL_PROCESSING=True
BATCH_SIZE=5000
```

### Configuración del Navegador y Logging

```
HEADLESS_BROWSER=True
PROXY_ENABLED=False
PROXY_LIST=127.0.0.1:8080,127.0.0.1:8081
LOG_LEVEL=INFO
DEBUG=False
REQUEST_DELAY=2.0
RANDOM_DELAY_RANGE=1.0,3.0
```

## Uso

### Uso Básico

Ejecuta el script principal para iniciar todo el flujo de trabajo:

```bash
python main.py
```

### Opciones de Línea de Comandos

El script acepta varios argumentos de línea de comandos:

- `--config`: Ruta a un archivo de configuración personalizado
- `--output`: Ruta para guardar los resultados
- `--no-sheets`: Deshabilitar la subida a Google Sheets
- `--no-gmaps`: Deshabilitar el scraping de Google Maps
- `--no-insta`: Deshabilitar el scraping de Instagram
- `--no-directories`: Deshabilitar el scraping de Directorios

Ejemplo:

```bash
python main.py --output ./resultados_personalizados --no-insta
```

## Salida

El script genera varios archivos de salida en el directorio `results`:

- Resultados brutos de los scrapers en formato JSON
- Datos procesados y deduplicados en formato CSV
- Informe de resumen en formato JSON

También se muestra un resumen en consola con estadísticas de la ejecución.

## Estructura del Proyecto

```
scraperMVP/
├── main.py                     # Script principal de orquestación
├── scrapers/                   # Módulos de scraping
│   ├── google_maps_scraper.py  # Scraper de Google Maps
│   ├── instagram_scraper.py    # Scraper de Instagram
│   ├── paginas_amarillas_scraper.py  # Scraper de Páginas Amarillas
│   ├── guialocal_scraper.py    # Scraper de GuiaLocal
│   └── cylex_scraper.py        # Scraper de Cylex
├── processing/                 # Módulos de procesamiento
│   └── data_processor.py       # Procesadores de deduplicación y validación
├── integrations/               # Integraciones externas
│   └── google_sheets.py        # Integración con Google Sheets
├── utils/                      # Funciones de utilidad
│   ├── helpers.py              # Funciones auxiliares comunes
│   ├── parallel_scraping.py    # Sistema de paralelización para scrapers
│   ├── browser_pool.py         # Pool de navegadores para optimizar recursos
│   └── cache_manager.py        # Gestor de caché para resultados de scrapers
├── docs/                       # Documentación técnica
│   └── performance_optimization.md # Documentación sobre optimizaciones de rendimiento
├── scripts/                    # Scripts de demostración y utilidad
├── logs/                       # Archivos de registro
├── results/                    # Archivos de salida
├── .env                        # Variables de entorno (no incluidas en repositorio)
├── .env.template               # Plantilla de variables de entorno
└── requirements.txt            # Dependencias del proyecto
```

## Documentación

La documentación completa del proyecto está disponible en el directorio `docs/`:

- [Optimización de Rendimiento](docs/performance_optimization.md): Detalles sobre la paralelización de scrapers, optimización de Selenium y caché de resultados.

## Pruebas

Para probar la aplicación con consultas limitadas:

```bash
LOG_LEVEL=DEBUG python main.py
```

Para probar el manejo de errores, puedes provocar fallos intencionalmente proporcionando valores de configuración inválidos.

## Contribución

1. Haz un fork del repositorio
2. Crea tu rama de características (`git checkout -b feature/caracteristica-increible`)
3. Haz commit de tus cambios (`git commit -m 'Añadir alguna característica increíble'`)
4. Haz push a la rama (`git push origin feature/caracteristica-increible`)
5. Abre un Pull Request

## Estado del Proyecto

Proyecto completado con éxito. Ver `tasks/task_010.txt` para detalles sobre la integración principal.

## Licencia

Este proyecto está licenciado bajo la Licencia MIT - ver el archivo LICENSE para más detalles.

## Aviso Legal

Esta herramienta está destinada para fines legales de generación de leads comerciales. Siempre respeta los términos de servicio y las políticas de scraping de los sitios web. Asegúrate de tener permiso para recopilar los datos y cumple con las leyes de protección de datos.
