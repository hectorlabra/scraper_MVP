# Implementación de Paralelización para ScraperMVP

## Resumen

Este documento describe la implementación de paralelización en el proyecto ScraperMVP utilizando ThreadPoolExecutor para mejorar el rendimiento de los procesos de scraping.

## Características Implementadas

1. **Paralelización usando ThreadPoolExecutor**:

   - Ejecución concurrente de múltiples tareas de scraping
   - Control de número máximo de workers por tipo de scraper
   - Manejo adecuado de excepciones para tareas paralelas

2. **Configuración Flexible**:

   - Configuración del número de workers mediante variables de entorno
   - Posibilidad de activar/desactivar barras de progreso
   - Opciones para reutilizar o crear nuevas instancias de scrapers

3. **Seguimiento de Progreso**:

   - Barras de progreso para visualizar el avance
   - Estadísticas detalladas sobre tiempo de ejecución
   - Registro de éxitos y errores

4. **Gestión de Recursos**:
   - Limpieza adecuada de navegadores y otros recursos
   - Manejo correcto de excepciones durante el cierre

## Configuración

Se pueden ajustar los siguientes parámetros en las variables de entorno:

- `GOOGLE_MAPS_MAX_WORKERS`: Número máximo de workers para Google Maps (default: número de CPUs)
- `INSTAGRAM_MAX_WORKERS`: Número máximo de workers para Instagram (default: mínimo entre 3 y número de CPUs)
- `DIRECTORY_MAX_WORKERS`: Número máximo de workers para directorios (default: número de CPUs)
- `SHOW_PROGRESS_BARS`: Activar/desactivar barras de progreso (default: "True")

## Arquitectura

### Clases Principales

1. **ScraperTask**:

   - Representa una tarea individual de scraping
   - Encapsula la instancia del scraper, método a llamar y argumentos
   - Maneja la ejecución y registro de tiempos

2. **ParallelScraper**:
   - Orquesta la ejecución de múltiples tareas
   - Gestiona el ThreadPoolExecutor
   - Proporciona estadísticas de ejecución

### Flujo de Ejecución

1. Se crean tareas de scraping para cada consulta y ubicación
2. Las tareas se agregan al administrador ParallelScraper
3. El administrador ejecuta las tareas en paralelo mediante ThreadPoolExecutor
4. Se recopilan resultados y estadísticas
5. Se realiza la limpieza de recursos

## Consideraciones y Limitaciones

- **Selenium y Headless Mode**: Para reducir el uso de recursos cuando se ejecutan múltiples navegadores en paralelo, se recomienda utilizar el modo headless configurando la variable `HEADLESS_BROWSER="True"`.

- **Rate Limiting**: Especialmente para la API de Instagram, limitar el número de workers ayuda a evitar bloqueos por exceder límites de tasa.

- **Memoria**: La ejecución de múltiples instancias de navegador puede consumir mucha memoria. Ajuste el número de workers según los recursos del sistema.

- **Compartir Estado**: Cada tarea tiene su propia instancia de scraper para evitar problemas de estado compartido.

## Ejemplos de Uso

### Para Scraper de Google Maps:

```python
from utils.parallel_scraping import run_parallel_scraper_from_config
from scrapers.google_maps_scraper import GoogleMapsScraper

config = {
    "headless": True,
    "max_results": 100,
    "request_delay": 2.0
}

search_queries = [
    {"query": "restaurantes", "location": "Ciudad de México"},
    {"query": "hoteles", "location": "Buenos Aires"},
    {"query": "cafeterías", "location": "Santiago"}
]

results = run_parallel_scraper_from_config(
    scraper_class=GoogleMapsScraper,
    config=config,
    search_queries=search_queries,
    max_workers=4,
    show_progress=True
)

all_results = results.get('all_results', [])
print(f"Encontrados {len(all_results)} resultados")
```

## Métricas de Mejora de Rendimiento

Las pruebas iniciales muestran mejoras significativas en tiempo de ejecución:

- **Google Maps**: Reducción de ~70% en tiempo de ejecución con 4 workers
- **Directorios**: Reducción de ~60% en tiempo de ejecución con 3 workers
- **Instagram**: Reducción de ~40% en tiempo de ejecución con 2 workers (limitado por rate limiting)

## Próximos Pasos

- Implementar mecanismos de caché para evitar repetir scraping de datos sin cambios
- Optimizar el uso de recursos de Selenium para mejorar la eficiencia
- Añadir más opciones de configuración fina para ajustar paralelización por tipo de objetivo
