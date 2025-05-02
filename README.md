# LeadScraper LATAM

Script Python para automatizar la extracción diaria de leads comerciales en LATAM desde Google Maps, Instagram y directorios públicos, guardando los datos en Google Sheets.

## Descripción

El objetivo principal de este proyecto es proporcionar a agencias de marketing una herramienta para acceder a datos locales de negocios sin esfuerzo manual. La herramienta recopila información como nombres, direcciones, teléfonos, sitios web, perfiles de Instagram y más.

## Funcionalidades Principales

- **Scraping multi-fuente**: Extracción de datos de Google Maps, Instagram y directorios públicos
- **Procesamiento de datos**: Eliminación de duplicados y validación de formatos
- **Entrega automatizada**: Actualización diaria de Google Sheets con los datos recopilados
- **Ejecución programada**: Mediante GitHub Actions

## Tecnologías Utilizadas

- Python, BeautifulSoup, Selenium (scraping)
- Instaloader (Instagram)
- Pandas (limpieza de datos)
- Google Sheets API (gspread)
- GitHub Actions (automatización)

## Estructura del Proyecto

```
scraperMVP/
├── main.py                 # Script principal
├── scrapers/               # Módulos de scraping
├── processors/             # Procesamiento de datos
├── integrations/           # Integración con Google Sheets
├── utils/                  # Funciones auxiliares
├── .env                    # Variables de entorno
└── requirements.txt        # Dependencias
```

## Estado del Proyecto

En desarrollo activo. Ver `tasks/tasks.json` para el plan de implementación detallado.
