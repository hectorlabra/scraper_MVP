# Instagram Scraper - Documentación

Este documento describe la implementación y uso del scraper de Instagram para la extracción de perfiles de negocios en LATAM.

## Descripción General

El scraper de Instagram está diseñado para identificar y extraer información de perfiles de negocios en Instagram mediante búsquedas por hashtags y ubicaciones relevantes para LATAM. Utiliza la biblioteca `instaloader` para interactuar con Instagram y aplicar estrategias de manejo de sesiones y limitación de tasa para evitar bloqueos.

## Características Principales

1. **Autenticación y Manejo de Sesiones**

   - Soporte para login con credenciales de Instagram
   - Almacenamiento de cookies de sesión para evitar logins frecuentes
   - Recuperación automática de sesiones existentes

2. **Búsqueda por Hashtags**

   - Búsqueda de publicaciones por hashtags relevantes para negocios LATAM
   - Extracción de información de los autores de las publicaciones
   - Detección de perfiles con características de negocio

3. **Búsqueda por Ubicaciones**

   - Búsqueda de publicaciones por ubicaciones geográficas en LATAM
   - Identificación de negocios por ubicación

4. **Extracción de Datos de Perfil**

   - Nombre del negocio y categoría
   - Información de contacto (teléfono, email, sitio web)
   - Métricas del perfil (seguidores, publicaciones)
   - Extracción de datos de ubicación
   - Identificación de hashtags utilizados

5. **Protección Anti-Bloqueo**
   - Retrasos entre solicitudes con variación aleatoria
   - Manejo de excepciones y errores
   - Limitación configurable de resultados

## Estructura de Datos

El scraper de Instagram produce resultados en la siguiente estructura:

```json
{
  "source": "instagram",
  "scrape_date": "2025-05-05",
  "name": "Nombre del Negocio",
  "username": "usuario_negocio",
  "profile_url": "https://www.instagram.com/usuario_negocio/",
  "description": "Descripción del negocio extraída de la biografía",
  "website": "https://sitio-web-negocio.com",
  "phone": "+1234567890",
  "email": "contacto@negocio.com",
  "category": "Categoría del Negocio",
  "followers": 5000,
  "following": 1200,
  "post_count": 320,
  "is_business_account": true,
  "is_verified": false,
  "location_name": "Ciudad, País",
  "location_lat": 19.4326,
  "location_lng": -99.1332,
  "hashtags": ["negocio", "emprendimiento", "latam"],
  "social_media": {
    "instagram": "https://www.instagram.com/usuario_negocio/"
  }
}
```

## Instalación y Requisitos

El scraper de Instagram requiere las siguientes dependencias:

- Python 3.9+
- Biblioteca instaloader 4.10+
- Bibliotecas estándar: re, os, json, logging, datetime

Todas las dependencias están incluidas en el archivo `requirements.txt` del proyecto.

## Uso del Scraper de Instagram

### Uso desde Python

```python
from scrapers.instagram_scraper import InstagramScraper

# Crear instancia del scraper
scraper = InstagramScraper(
    username='tu_usuario',
    password='tu_contraseña',
    max_results=50
)

# Iniciar sesión (opcional, pero recomendado)
scraper.login()

# Buscar por hashtag
results = scraper.search_by_hashtag('negociosmexicanos', post_limit=30)

# Buscar por ubicación
# location_results = scraper.search_by_location('111462462', post_limit=20)  # ID de Ciudad de México

# Obtener resultados
for business in results:
    print(f"Negocio: {business.get('name')} (@{business.get('username')})")
    print(f"Contacto: {business.get('phone')} | {business.get('email')}")
    print(f"Web: {business.get('website')}")
    print(f"Seguidores: {business.get('followers')}")
    print("---")

# Cerrar sesión
scraper.logout()
```

### Uso desde Línea de Comandos

El scraper incluye un script CLI para uso desde la línea de comandos:

```bash
# Búsqueda por hashtag
python scripts/instagram_cli.py --username tu_usuario --password tu_contraseña --hashtag emprendedoreslatinos --limit 50

# Búsqueda por ubicación
python scripts/instagram_cli.py --username tu_usuario --password tu_contraseña --location 111462462 --limit 30

# Guardar en formato CSV
python scripts/instagram_cli.py --hashtag emprendedoreslatinos --format csv --output results/negocios_latam.csv
```

## Consideraciones Éticas y Legales

Al utilizar el scraper de Instagram, es importante considerar:

1. **Términos de Servicio**: El uso de este scraper debe cumplir con los Términos de Servicio de Instagram.
2. **Protección de Datos**: Los datos extraídos pueden contener información personal y deben tratarse de acuerdo con las leyes de protección de datos aplicables.
3. **Limitación de Tasa**: El scraper implementa retrasos entre solicitudes para respetar los límites de tasa de Instagram, pero se recomienda un uso responsable.
4. **Uso Responsable**: Utilizar el scraper solo para fines legítimos de investigación y marketing.

## Limitaciones Conocidas

1. **Acceso a Datos Limitado**: Instagram restringe ciertos datos a aplicaciones no oficiales.
2. **Cambios en la API**: Instagram puede cambiar su estructura HTML o API sin previo aviso, lo que puede afectar el funcionamiento del scraper.
3. **Limitaciones de Autenticación**: El inicio de sesión puede requerir verificación adicional en algunas cuentas (como autenticación de dos factores).
4. **Detección de Bots**: Instagram implementa medidas para detectar comportamientos automatizados que podrían resultar en restricciones temporales.

## Desarrollo Futuro

Posibles mejoras para futuras versiones:

1. Soporte para autenticación de dos factores
2. Mejora en los algoritmos de detección de perfiles de negocios
3. Integración con análisis de sentimiento para evaluar la reputación de los negocios
4. Expansión de la búsqueda a otras señales como menciones y etiquetas

## Pruebas Unitarias

El módulo incluye pruebas unitarias que se pueden ejecutar con:

```bash
python -m unittest tests/test_instagram_scraper.py
```
