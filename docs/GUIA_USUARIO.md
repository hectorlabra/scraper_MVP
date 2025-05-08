# Guía de Usuario de ScraperMVP: ¡Tu Aliado para Encontrar Leads!

¡Bienvenido/a a ScraperMVP! Esta herramienta ha sido diseñada para ayudarte a encontrar información de contacto de posibles clientes (leads) de forma automática, directamente desde diversas fuentes en internet, y lo mejor de todo, ¡entregándotelos ordenaditos en una Hoja de Cálculo de Google!

**¿Para quién es esta guía?**

Esta guía está pensada para ti, aunque no seas un experto en computación. Usaremos un lenguaje sencillo y analogías para que entiendas cada paso. ¡Verás que es más fácil de lo que parece!

**¿Qué es ScraperMVP en palabras simples?**

Imagina que tienes un asistente personal súper rápido que puede navegar por internet, visitar páginas amarillas, directorios de empresas, mapas, y hasta algunas redes sociales. Este asistente busca nombres de negocios, números de teléfono, correos electrónicos, sitios web, etc., según lo que tú le pidas. Luego, anota toda esa información de forma ordenada en una lista para ti. ¡Eso es ScraperMVP!

**¿Qué aprenderás en esta guía?**

Te llevaremos de la mano a través de 9 partes:

1.  **Preparando tu Computadora:** Lo básico que necesitas tener instalado.
2.  **Obteniendo los Archivos de ScraperMVP:** Cómo descargar la herramienta.
3.  **Configurando la "Caja Mágica" (Entorno Virtual):** Un espacio especial para que ScraperMVP funcione sin problemas.
4.  **Instalando las Piezas de la Herramienta (Dependencias):** Como armar un juguete, ScraperMVP necesita sus piezas.
5.  **Configurando los "Secretos" (Archivo `.env` y Credenciales):** Información clave para que ScraperMVP acceda a servicios como Google Sheets.
6.  **¡A Buscar Leads! (Ejecutando ScraperMVP):** El momento de la acción.
7.  **Tus Leads Directo a tu Hoja de Cálculo (Google Sheets):** La forma más fácil de ver y usar tus leads.
8.  **"¡Houston, Tenemos un Problema!" - Solución de Problemas Básicos:** Para esos pequeños contratiempos.
9.  **Usando ScraperMVP como un Profesional (Mejores Prácticas y Consejos):** Para sacarle el máximo provecho.

¡Empecemos!

---

## Parte 1: Preparando tu Computadora (Lo Básico)

Antes de que ScraperMVP pueda hacer su magia, necesitamos asegurarnos de que tu computadora tenga algunas herramientas básicas. Es como preparar los ingredientes antes de cocinar.

**Necesitarás tres cosas principales:**

1.  **Python:** Es el lenguaje de programación en el que está escrito ScraperMVP.

    - **Analogía:** Piensa en Python como el idioma que ScraperMVP "habla". Tu computadora necesita entender ese idioma.
    - **Cómo verificar si lo tienes (y obtenerlo si no):**
      - Abre la "Terminal" (o "Símbolo del sistema"/"PowerShell" en Windows).
        - **En macOS:** Ve a `Aplicaciones > Utilidades > Terminal`.
        - **En Windows:** Busca "cmd" o "PowerShell" en el menú de inicio.
      - Escribe `python --version` o `python3 --version` y presiona Enter.
      - Si ves un número de versión (ej: `Python 3.9.1`), ¡genial! Ya lo tienes. Idealmente, necesitas la versión 3.7 o superior.
      - Si dice "comando no encontrado" o una versión muy antigua (como Python 2.x), necesitas instalarlo.
      - **Para instalar Python:** Ve a [python.org](https://www.python.org/downloads/), descarga el instalador para tu sistema operativo (Windows o macOS) y sigue las instrucciones. **Importante para Windows:** Durante la instalación, asegúrate de marcar la casilla que dice "Add Python to PATH" o "Agregar Python al PATH".

2.  **Pip:** Es el administrador de paquetes de Python. Viene incluido con Python si instalaste una versión reciente.

    - **Analogía:** Si Python es el idioma, Pip es como una tienda de herramientas que nos permite conseguir fácilmente las "piezas" adicionales que ScraperMVP necesita.
    - **Cómo verificar si lo tienes:**
      - En la Terminal, escribe `pip --version` o `pip3 --version` y presiona Enter.
      - Si ves un número de versión, ¡perfecto!
      - Si no, y acabas de instalar Python, cierra y vuelve a abrir la Terminal. A veces necesita reiniciarse para reconocer los nuevos comandos. Si sigue sin aparecer, es posible que algo haya salido mal en la instalación de Python, o que necesites instalarlo por separado (aunque es raro con las versiones modernas de Python).

3.  **Una Terminal (o Símbolo del Sistema / PowerShell):** Es una ventana donde puedes escribir comandos para darle instrucciones directas a tu computadora. Ya la usamos para verificar Python y Pip.
    - **Analogía:** Es como el panel de control principal de tu computadora, donde puedes dar órdenes directas sin usar el mouse.

¡Eso es todo por ahora! Con estos tres elementos, tu computadora está lista para el siguiente paso.

---

## Parte 2: Obteniendo los Archivos de ScraperMVP

Ahora que tu computadora está preparada, es momento de traer los "planos" y las "piezas" de ScraperMVP a tu máquina. Hay dos formas principales de hacerlo:

**Opción 1: Descargar como un Archivo ZIP (La más sencilla para no técnicos)**

Si te proporcionaron ScraperMVP como un proyecto en una plataforma como GitHub, GitLab, o similar, usualmente hay un botón para descargar todo el proyecto como un archivo `.zip`.

1.  **Ve a la página del proyecto ScraperMVP.** (Ej: `https://github.com/tu-usuario/scraperMVP`)
2.  **Busca un botón verde que diga "Code" o "Código".** Haz clic en él.
3.  **En el menú desplegable, selecciona "Download ZIP" o "Descargar ZIP".**
    - _(Placeholder para imagen: Captura de pantalla del botón "Code" y "Download ZIP" en GitHub)_
4.  **Guarda el archivo ZIP** en una carpeta que recuerdes fácilmente (ej: `Documentos/Proyectos/ScraperMVP`).
5.  **Descomprime el archivo ZIP:**
    - **En macOS:** Haz doble clic en el archivo ZIP. Se creará una carpeta con el mismo nombre (probablemente algo como `scraperMVP-main` o `scraperMVP-master`).
    - **En Windows:** Haz clic derecho en el archivo ZIP y selecciona "Extraer todo...". Sigue las instrucciones.
6.  **Renombra la carpeta (opcional pero recomendado):** La carpeta descomprimida podría tener un nombre como `scraperMVP-main`. Puedes renombrarla a simplemente `ScraperMVP` para que sea más fácil de recordar y escribir en la terminal.

¡Listo! Ya tienes todos los archivos de ScraperMVP en tu computadora.

**Opción 2: Usar Git (Si estás familiarizado o quieres aprender)**

Git es un sistema de control de versiones. Si tienes Git instalado y sabes usarlo, esta es una forma más robusta de obtener y mantener actualizado ScraperMVP. Si no sabes qué es Git, ¡no te preocupes y usa la Opción 1!

1.  **Instala Git:** Si no lo tienes, ve a [git-scm.com/downloads](https://git-scm.com/downloads) y descárgalo.
2.  **Abre tu Terminal.**
3.  **Navega a la carpeta donde quieres guardar ScraperMVP.** Por ejemplo, si quieres guardarlo en `Documentos/Proyectos`, escribe:
    ```bash
    cd Documentos/Proyectos
    ```
4.  **Clona el repositorio:** Necesitarás la URL del repositorio (usualmente termina en `.git`). La encuentras en la página principal del proyecto, bajo el mismo botón "Code" (busca la opción HTTPS o SSH).
    ```bash
    git clone https://github.com/tu-usuario/scraperMVP.git
    ```
    Esto creará una carpeta llamada `scraperMVP` (o el nombre del repositorio) con todos los archivos.

**¿Qué hay dentro de la carpeta de ScraperMVP?**

Verás varios archivos y quizás algunas subcarpetas. Algunos importantes que reconocerás más adelante:

- `main.py`: El "cerebro" de ScraperMVP.
- `requirements.txt`: Una lista de las "piezas" adicionales que necesita.
- Carpeta `config/`: Donde guardaremos información sensible.
- Carpeta `results/`: Donde se guardarán los leads encontrados (a veces).
- Carpeta `logs/`: Registros de lo que hace la herramienta.

No te preocupes por entender cada archivo ahora. Lo importante es que ya tienes ScraperMVP en tu computadora. ¡Vamos al siguiente paso!

---

## Parte 3: Configurando la "Caja Mágica" (Entorno Virtual - venv)

Ahora que tenemos los archivos de ScraperMVP, vamos a crear un espacio de trabajo especial y aislado para él. Esto se llama "entorno virtual".

**¿Qué es un Entorno Virtual y por qué lo necesitamos?**

- **Analogía:** Imagina que ScraperMVP es un chef muy particular que necesita su propia cocina con sus propios utensilios y versiones específicas de ingredientes. No quieres que sus utensilios se mezclen con los del resto de tu casa (otros programas en tu computadora) ni que use una versión de harina que no le gusta.
- Un entorno virtual es como esa **cocina privada para ScraperMVP**. Dentro de ella, podemos instalar las "piezas" (dependencias) que ScraperMVP necesita, en las versiones exactas que necesita, sin afectar a otros programas de Python que puedas tener o instalar en el futuro.
- **Beneficios:**
  - **Evita conflictos:** Diferentes proyectos de Python pueden necesitar diferentes versiones de la misma "pieza". Los entornos virtuales evitan que se peleen.
  - **Mantiene tu sistema limpio:** Las piezas de ScraperMVP se quedan dentro de su entorno, no esparcidas por tu sistema.
  - **Facilita la reproducción:** Si necesitas instalar ScraperMVP en otra computadora, el entorno virtual ayuda a asegurar que todo funcione igual.

**Creando el Entorno Virtual (usaremos `venv`, que viene con Python):**

1.  **Abre tu Terminal.**
2.  **Navega a la carpeta principal de ScraperMVP.** Esta es la carpeta que descargaste y descomprimiste (o clonaste). Por ejemplo:
    ```bash
    cd Documentos/Proyectos/ScraperMVP
    ```
    (Reemplaza `Documentos/Proyectos/ScraperMVP` con la ruta real donde guardaste la herramienta).
3.  **Crea el entorno virtual.** Escribe el siguiente comando y presiona Enter:

    - En macOS o Linux: `python3 -m venv .venv`
    - En Windows: `python -m venv .venv`

    _Explicación del comando:_

    - `python3` o `python`: Llama a Python.
    - `-m venv`: Le dice a Python que use su módulo incorporado llamado `venv`.
    - `.venv`: Es el nombre que le daremos a la carpeta que contendrá nuestro entorno virtual. El punto al inicio (`.`) es una convención para indicar que es una carpeta un poco "oculta" o de configuración, y `venv` es simplemente un nombre común. Podrías llamarla de otra forma, pero `.venv` es estándar.

    Después de ejecutar el comando, verás que se ha creado una nueva subcarpeta llamada `.venv` dentro de tu carpeta ScraperMVP. ¡Esa es la cocina privada!

4.  **Activa el Entorno Virtual.** Crear el entorno es como construir la cocina. Ahora necesitas "entrar" en ella para empezar a usarla.

    - **En macOS o Linux:**
      ```bash
      source .venv/bin/activate
      ```
    - **En Windows (Símbolo del sistema - cmd):**
      ```bash
      .\.venv\Scripts\activate.bat
      ```
    - **En Windows (PowerShell):**
      ```bash
      .\.venv\Scripts\Activate.ps1
      ```
      (Si en PowerShell te da un error sobre ejecución de scripts, puede que necesites ejecutar primero: `Set-ExecutionPolicy Unrestricted -Scope Process` y luego intentar activar de nuevo. Responde "S" o "A" si te pregunta).

    **¿Cómo sabes si funcionó?** Verás que el inicio de la línea en tu terminal cambia. Ahora tendrá `(.venv)` al principio. Por ejemplo:
    `(.venv) TuUsuario@TuMac ScraperMVP %` (en macOS)
    `(.venv) C:\Ruta\A\ScraperMVP>` (en Windows)

    _(Placeholder para imagen: Terminal con entorno virtual activado en macOS/Linux)_
    _(Placeholder para imagen: Terminal con entorno virtual activado en Windows)_

En resumen, el entorno virtual es una herramienta poderosa que te permite gestionar de manera eficiente las dependencias y configuraciones de tus proyectos en Python, manteniendo tu sistema limpio y evitando conflictos entre proyectos.

---

## Parte 4: Instalando las Piezas de la Herramienta (Dependencias - `requirements.txt`)

Con nuestra "cocina privada" (el entorno virtual) lista y activada, es hora de llenarla con todos los utensilios e ingredientes especiales que ScraperMVP necesita para funcionar. Estas "piezas" se llaman **dependencias**.

**¿Qué son las Dependencias?**

- **Analogía:** Siguiendo con nuestra cocina, ScraperMVP (el chef) no puede hacer todos sus platillos desde cero. Necesita herramientas específicas (como una batidora especial, un tipo de sartén) e ingredientes pre-hechos (como una salsa base). Estas son las dependencias.
- Son bibliotecas de código que otros programadores han creado y que ScraperMVP utiliza para realizar tareas comunes, como:
  - Navegar por páginas web (`requests`, `selenium`).
  - Extraer información de esas páginas (`beautifulsoup4`, `lxml`).
  - Conectarse a Google Sheets (`google-api-python-client`, `gspread`).
  - Manejar datos (`pandas`).
  - Y muchas otras cosas.

**El Archivo `requirements.txt`**

ScraperMVP es considerado y viene con una lista de compras: el archivo `requirements.txt`. Este archivo de texto simple enumera todas las dependencias que necesita y, a veces, las versiones específicas de cada una.

**Instalando las Dependencias:**

1.  **Asegúrate de que tu Entorno Virtual esté Activado.** Debes ver `(.venv)` al inicio de la línea de tu terminal. Si no, actívalo (revisa la Parte 3).
2.  **Asegúrate de estar en la Carpeta Principal de ScraperMVP.** Esta es la carpeta donde se encuentra el archivo `requirements.txt`. Si seguiste los pasos anteriores, ya deberías estar ahí.
3.  **Usa `pip` para instalar todo desde la lista.** Escribe el siguiente comando y presiona Enter:

    ```bash
    pip install -r requirements.txt
    ```

    - _(Placeholder para imagen: Terminal mostrando la instalación de dependencias con pip)_

    Este comando leerá el archivo `requirements.txt` y descargará e instalará todas esas "piezas" necesarias dentro de tu entorno virtual. Verás un montón de texto en la terminal mientras esto sucede. ¡No te asustes! Es normal. Solo asegúrate de que al final no aparezcan mensajes de error en rojo muy grandes.

¡Listo! Con esto, tu "caja mágica" (el entorno virtual) ahora tiene todas las herramientas (dependencias) que ScraperMVP necesita para funcionar.

---

## Parte 5: Configurando los "Secretos" (Archivo `.env` y Credenciales de Google Cloud)

ScraperMVP necesita acceder a algunos servicios en tu nombre, especialmente a Google Sheets para guardar los leads. Para hacer esto de forma segura, no podemos escribir contraseñas directamente en el código. En su lugar, usaremos un archivo especial para guardar esta información sensible (los "secretos") y configuraremos el acceso a Google.

**Analogía:** Piensa que le vas a dar a tu asistente (ScraperMVP) una llave especial para que pueda entrar a tu archivador (Google Sheets) y dejar documentos (los leads), pero sin darle la llave maestra de toda tu casa.

**Paso 1: El Archivo `.env` (Variables de Entorno)**

Muchos proyectos usan un archivo llamado `.env` (se pronuncia "dot env") para guardar configuraciones que varían entre usuarios o entornos (como tus credenciales personales).

1.  **Busca un archivo de ejemplo:** Dentro de la carpeta de ScraperMVP, es muy probable que encuentres un archivo llamado `.env.example`, `sample.env`, o `config.example.py`. Este es una plantilla.
2.  **Crea tu propio archivo `.env`:**
    - Copia el archivo `.env.example` (o similar) y renombra la copia a simplemente `.env`.
    - **Importante:** El archivo debe llamarse exactamente `.env` (punto e n v). Algunos sistemas operativos ocultan archivos que empiezan con punto. Asegúrate de que tu explorador de archivos los muestre si es necesario.
3.  **Abre el archivo `.env` con un editor de texto simple** (como Bloc de Notas en Windows, TextEdit en macOS en modo texto plano, o VS Code si lo tienes).

    Verás líneas como estas (el contenido exacto variará):

    ```ini
    # Credenciales de Google Sheets
    GOOGLE_SHEET_ID="AQUI_VA_EL_ID_DE_TU_HOJA_DE_CALCULO"
    GOOGLE_APPLICATION_CREDENTIALS="config/tu_archivo_de_credenciales.json"

    # Configuraciones de Scrapers (ejemplos)
    # TARGET_KEYWORDS="restaurantes, hoteles"
    # TARGET_LOCATIONS="Ciudad de Mexico, Guadalajara"
    ```

    Las líneas que empiezan con `#` son comentarios y son ignoradas.

**Paso 2: Configuración de Google Cloud para Google Sheets**

Esta es la parte más técnica, pero la haremos paso a paso. Necesitamos crear unas "credenciales" para que ScraperMVP pueda hablar con la API de Google Sheets.

**Analogía:** Vamos a la "oficina de administración de Google" para obtener un pase especial (credencial) para nuestro asistente (ScraperMVP).

1.  **Ve a la Consola de Google Cloud:** Abre tu navegador web y ve a [console.cloud.google.com](https://console.cloud.google.com/). Inicia sesión con tu cuenta de Google (la que usarás para la Hoja de Cálculo donde irán los leads).

2.  **Crea un Nuevo Proyecto (o selecciona uno existente):**

    - Si es tu primera vez, puede que te pida crear un proyecto. Dale un nombre (ej: "ScraperMVP Leads") y créalo.
    - Si ya tienes proyectos, asegúrate de seleccionar el correcto en la parte superior de la página.
    - _(Placeholder para imagen: Selector de proyectos en Google Cloud Console)_

3.  **Habilita la API de Google Sheets:**

    - En el menú de navegación (☰ a la izquierda) o en la barra de búsqueda, busca "APIs y Servicios" y ve a "Biblioteca".
    - En la barra de búsqueda de la Biblioteca, escribe "Google Sheets API" y selecciónala de los resultados.
    - Haz clic en el botón "Habilitar". Si ya está habilitada, ¡genial!
    - _(Placeholder para imagen: Página de Google Sheets API con el botón Habilitar)_

4.  **Crea Credenciales (Service Account - Cuenta de Servicio):**

    - Una vez habilitada la API, en el menú de "APIs y Servicios", ve a "Credenciales".
    - Haz clic en "+ CREAR CREDENCIALES" y selecciona "Cuenta de servicio".
      - _(Placeholder para imagen: Botón "+ CREAR CREDENCIALES" y opción "Cuenta de servicio")_
    - **Nombre de la cuenta de servicio:** Dale un nombre descriptivo (ej: "scrapermvp-sheets-access"). Se generará un ID debajo.
    - Haz clic en "CREAR Y CONTINUAR".
    - **Rol (Opcional para este paso, pero recomendado):** Puedes omitir asignar un rol a nivel de proyecto por ahora o seleccionar "Proyecto > Lector" si quieres. Haremos los permisos más específicos a nivel de la hoja de cálculo. Haz clic en "CONTINUAR".
    - **Conceder acceso a usuarios (Opcional):** Puedes omitir esto. Haz clic en "LISTO".
    - Ahora deberías ver tu nueva cuenta de servicio en la lista.

5.  **Genera una Clave JSON para la Cuenta de Servicio:**

    - En la lista de cuentas de servicio, haz clic en la dirección de correo electrónico de la cuenta que acabas de crear (termina en `@...iam.gserviceaccount.com`).
    - Ve a la pestaña "CLAVES".
    - Haz clic en "AGREGAR CLAVE" y selecciona "Crear clave nueva".
      - _(Placeholder para imagen: Pestaña CLAVES, botón AGREGAR CLAVE y opción Crear clave nueva)_
    - Elige el tipo de clave "JSON". Haz clic en "CREAR".
    - **¡MUY IMPORTANTE!** Se descargará automáticamente un archivo `.json` (ej: `nombre-del-proyecto-xxxxxx.json`). **Este archivo es tu "llave secreta". Guárdalo bien y no lo compartas públicamente.**
    - _(Placeholder para imagen: Diálogo de selección de tipo de clave JSON)_

6.  **Guarda el Archivo JSON en tu Proyecto ScraperMVP:**
    - Mueve el archivo `.json` que acabas de descargar a la subcarpeta `config/` dentro de tu carpeta principal de ScraperMVP.
    - Renombra el archivo JSON si quieres a algo más simple, por ejemplo: `scrapermvp-credentials.json`. **Asegúrate de que el nombre que elijas coincida exactamente con lo que pondrás en el archivo `.env`**.

**Paso 3: Configura tu Hoja de Cálculo de Google Sheets**

1.  **Crea una Nueva Hoja de Cálculo (o usa una existente):** Ve a [sheets.google.com](https://sheets.google.com) y crea una hoja de cálculo donde quieres que ScraperMVP guarde los leads.
2.  **Obtén el ID de la Hoja de Cálculo:**
    - Abre tu hoja. Mira la URL en la barra de direcciones de tu navegador. Se verá algo así:
      `https://docs.google.com/spreadsheets/d/ABC123xyz789_ESTE_ES_EL_ID_LARGO/edit#gid=0`
    - El ID de la hoja es esa cadena larga de letras, números y guiones bajos entre `/d/` y `/edit`. Cópialo.
3.  **Comparte la Hoja de Cálculo con tu Cuenta de Servicio:**
    - Dentro de tu Hoja de Cálculo, haz clic en el botón "Compartir" (arriba a la derecha).
    - En el campo "Añadir personas y grupos", pega la dirección de correo electrónico de la Cuenta de Servicio que copiaste en el "Paso 2.4" (la que termina en `@...iam.gserviceaccount.com`).
    - Asegúrate de que tenga permisos de **"Editor"**. Esto es crucial para que ScraperMVP pueda escribir datos en la hoja.
    - _(Placeholder para imagen: Diálogo de "Compartir" en Google Sheets mostrando la cuenta de servicio con permisos de Editor)_
    - Haz clic en "Compartir" o "Guardar".

**Paso 4: Completa tu Archivo `.env`**

Ahora vuelve a tu archivo `.env` y edítalo con la información correcta:

```ini
# Credenciales de Google Sheets
GOOGLE_SHEET_ID="AQUI_PEGAS_EL_ID_DE_TU_HOJA_DE_CALCULO"
GOOGLE_APPLICATION_CREDENTIALS="config/nombre_de_tu_archivo.json" # Ej: config/scrapermvp-credentials.json

# Otras configuraciones que pueda tener ScraperMVP...
# API_KEY_OTRO_SERVICIO="TU_CLAVE_DE_API_SI_ES_NECESARIA"
```

- _(Placeholder para imagen: Ejemplo de archivo .env en un editor de texto)_

- Reemplaza `"AQUI_PEGAS_EL_ID_DE_TU_HOJA_DE_CALCULO"` con el ID que copiaste de la URL de tu hoja.
- Reemplaza `"config/nombre_de_tu_archivo.json"` con la ruta y nombre correctos de tu archivo JSON de credenciales (ej: `config/scrapermvp-credentials.json` si lo guardaste así en la carpeta `config`).

**¡Uf! Esa fue la parte más larga.** Pero si seguiste todos los pasos, ScraperMVP ahora tiene todo lo que necesita para acceder de forma segura a tu Hoja de Cálculo de Google y empezar a llenarla de leads.

**Importante sobre el archivo `.env` y el JSON de credenciales:**

- **NUNCA los subas a repositorios públicos (como GitHub).** Si tu proyecto ScraperMVP está en Git, asegúrate de que el archivo `.gitignore` (debería venir uno) incluya `.env` y `*.json` dentro de la carpeta `config/` para evitar que se suban accidentalmente. Estos archivos contienen información sensible.

¡Estás listo para la acción!

---

## Parte 6: ¡A Buscar Leads! (Ejecutando ScraperMVP)

¡Ha llegado el momento de la verdad! Ya tienes todo configurado y estás listo para que ScraperMVP se ponga a trabajar y te consiga esos valiosos leads.

**¿Cómo "despertamos" a ScraperMVP?**

Imagina que tienes un control remoto para ScraperMVP. Ese "control remoto" es tu Terminal. Para iniciar la búsqueda de leads, sigue estos pasos:

1.  **Abre tu Terminal:** Si la cerraste, ábrela de nuevo.
2.  **Activa el Entorno Virtual:** Recuerda que ScraperMVP vive en su propia "burbuja". Antes de darle órdenes, tienes que entrar a esa burbuja. Escribe el siguiente comando y presiona Enter:
    - En macOS o Linux: `source .venv/bin/activate`
    - En Windows: `.\\.venv\\Scripts\\activate`
    - Verás que el nombre del entorno (`.venv`) aparece al inicio de la línea de comandos. ¡Estás dentro!
3.  **Navega a la Carpeta Correcta:** Asegúrate de que estás en la carpeta principal de ScraperMVP, donde está el archivo `main.py`. Si seguiste los pasos anteriores, ya deberías estar ahí. Si no, usa el comando `cd` para navegar (por ejemplo, `cd ruta/a/scraperMVP`).
4.  **¡Lanza el Cohete!:** Ahora, para iniciar ScraperMVP, escribe el siguiente comando y presiona Enter:

    ```bash
    python main.py
    ```

    - _(Placeholder para imagen: Terminal ejecutando el comando python main.py)_

**¿Qué verás en la Terminal?**

Una vez que ejecutes el comando, ScraperMVP comenzará a trabajar. Es como si estuvieras viendo el panel de control de una nave espacial:

- **Mensajes de Inicio:** Verás información sobre los scrapers que se están iniciando (Google Maps, Páginas Amarillas, etc.).
- **Progreso de la Búsqueda:** ScraperMVP te irá mostrando mensajes sobre lo que está haciendo: "Buscando en \[nombre de la fuente]...", "Encontrados X leads...", "Guardando información...".
- **Posibles Errores (¡no te asustes!):** A veces, alguna búsqueda individual puede fallar (quizás una página web no cargó bien o la información no estaba donde se esperaba). ScraperMVP está diseñado para manejar estos pequeños contratiempos y continuar con el resto. Verás mensajes si algo así ocurre.
- **Finalización:** Cuando ScraperMVP termine su trabajo, te lo indicará.

**¿Dónde están tus tesoros (los leads)?**

ScraperMVP guarda la información que recolecta en varios lugares:

1.  **La Carpeta `results/`:**

    - Aquí encontrarás archivos (generalmente en formato JSON, que es como un texto organizado) con los datos crudos de los leads que ScraperMVP ha encontrado. Cada vez que ejecutes la herramienta, se podría generar un nuevo archivo con la fecha y hora para que no se mezclen.
    - **Analogía:** Piensa en esta carpeta como el almacén donde llegan todas las cajas con los productos que pediste. Están ahí, pero quizás necesites organizarlas un poco para usarlas fácilmente.

2.  **La Carpeta `logs/`:**

    - Esta carpeta contiene "bitácoras de vuelo". Son archivos de texto que registran todo lo que ScraperMVP hizo, incluyendo los mensajes que viste en la terminal y detalles más técnicos.
    - **Analogía:** Es como la caja negra de un avión. Si algo no sale como esperabas, esta bitácora puede ayudar a entender qué pasó. Para ti, como usuario no técnico, probablemente no necesites mirar mucho aquí, pero es bueno saber que existe.

3.  **El Dashboard (Resumen Visual Rápido):**
    - ScraperMVP también puede generar un archivo HTML llamado `dashboard.html` (o similar) dentro de una carpeta como `utils/dashboard_output/` o directamente en la carpeta principal. Si abres este archivo con tu navegador web (Chrome, Firefox, Safari), verás un resumen visual rápido de cuántos leads se encontraron, cuántos fallaron por cada scraper, etc.
    - **Analogía:** Es como un pequeño tablero en tu coche que te da un vistazo rápido de la velocidad y la gasolina, pero no todos los detalles del motor.
    - **Importante:** Este dashboard es útil para un vistazo rápido, pero **la forma principal y más cómoda de acceder y gestionar tus leads será a través de Google Sheets**, como veremos en la siguiente sección.

**¿Cuánto tiempo tarda?**

La duración de la búsqueda dependerá de cuántas fuentes de datos esté configurado para revisar ScraperMVP y qué tan rápido respondan esas fuentes. Puede tardar desde unos minutos hasta bastante más si la búsqueda es extensa. ¡Ten paciencia y deja que la herramienta haga su magia!

En la siguiente parte, veremos cómo acceder a tus leads de forma organizada y lista para usar directamente en una Hoja de Cálculo de Google. ¡La mejor parte!

---

## Parte 7: Tus Leads Directo a tu Hoja de Cálculo (Google Sheets)

¡Esta es la parte que estabas esperando! Olvídate de los archivos JSON complicados o de tener que copiar y pegar datos manualmente. ScraperMVP está diseñado para enviar los leads que encuentra directamente a una Hoja de Cálculo de Google (Google Sheets) que tú elijas. ¡Así de fácil!

**¿Por qué Google Sheets?**

- **Accesible desde cualquier lugar:** Solo necesitas una conexión a internet.
- **Fácil de usar:** Si has usado Excel o cualquier hoja de cálculo, te sentirás como en casa.
- **Colaborativo:** Puedes compartir la hoja con tu equipo fácilmente.
- **Organizado:** Los leads aparecerán en filas y columnas, listos para que los filtres, ordenes y trabajes con ellos.

**¿Cómo funciona la magia?**

Recuerdas que en la "Parte 5: Configurando los Secretos" preparamos las credenciales de Google Cloud y compartiste tu Hoja de Cálculo con una dirección de correo electrónico especial (la del Service Account)? ¡Esa fue la preparación para este momento!

Cuando ScraperMVP encuentra un lead (un negocio con su nombre, teléfono, email, etc.), utiliza esas credenciales para:

1.  Conectarse de forma segura a tu cuenta de Google.
2.  Abrir la Hoja de Cálculo que le indicaste en el archivo `.env`.
3.  Escribir la información del lead en una nueva fila.

**¿Qué tienes que hacer tú?**

¡Casi nada! Si configuraste todo correctamente en la Parte 5:

1.  **Ejecuta ScraperMVP:** Como aprendiste en la Parte 6.
2.  **Abre tu Hoja de Cálculo de Google:** Mientras ScraperMVP trabaja (o después de que termine), ve a Google Drive y abre la hoja que preparaste.
3.  **¡Observa cómo llegan los leads!** Verás cómo nuevas filas con información de contacto empiezan a aparecer automáticamente. Cada columna representará un dato específico (Nombre del Negocio, Teléfono, Email, Sitio Web, etc.).

    ```
    - _(Placeholder para imagen: Ejemplo de Hoja de Cálculo de Google Sheets con leads cargados por ScraperMVP)_

    _(Los nombres de las columnas pueden variar un poco según la configuración de ScraperMVP, pero la idea es la misma)._

    **Ventajas de tener tus leads en Google Sheets:**

    - **Información Centralizada:** Todos tus leads en un solo lugar.
    - **Fácil Gestión:** Puedes añadir notas, marcar leads contactados, asignar responsables, etc.
    - **Filtrar y Ordenar:** ¿Quieres ver solo los leads de una ciudad específica? ¿O los que tienen email? ¡Los filtros de Google Sheets son tus amigos!
    - **Listo para la Acción:** Desde aquí puedes empezar tu proceso de ventas o marketing.

    **¿Y si no aparecen los leads?**

    Si ejecutas ScraperMVP y no ves que se añadan datos a tu hoja:

    1.  **Revisa la Terminal:** Mira si ScraperMVP mostró algún mensaje de error relacionado con Google Sheets.
    2.  **Verifica la Configuración (Parte 5):**
        - ¿Está correcto el `GOOGLE_SHEET_ID` en tu archivo `.env`?
        - ¿Compartiste la Hoja de Cálculo con la dirección de correo correcta del "Service Account"? (Es una dirección larga que termina en `@...iam.gserviceaccount.com`).
        - ¿Le diste permisos de "Editor" a esa cuenta de servicio sobre la hoja?
        - ¿Está el archivo JSON de credenciales (`scrapermvp-xxxx.json`) en la carpeta `config/` y bien nombrado en el `.env`?
        - ¿Activaste la API de Google Sheets en tu proyecto de Google Cloud?
    3.  **Consulta la Parte 8 (Solución de Problemas):** Allí daremos más pistas.
    ```

Esta integración con Google Sheets es el corazón de cómo ScraperMVP te entrega valor. ¡Ahora tienes una máquina que no solo busca leads, sino que te los sirve en bandeja de plata!

---

## Parte 8: "¡Houston, Tenemos un Problema!" - Solución de Problemas Básicos

A veces, incluso con la mejor preparación, las cosas no salen exactamente como esperamos. ¡No te preocupes! Muchos problemas comunes tienen soluciones sencillas. Aquí te presentamos una guía para los contratiempos más habituales.

**Analogía:** Piensa en esta sección como el manual de tu coche cuando se enciende una luz en el tablero.

**Problema 1: ScraperMVP no se ejecuta o da un error de "comando no encontrado".**

- **Síntoma:** Escribes `python main.py` y la terminal dice algo como `python: command not found` o `main.py: No such file or directory`.
- **Causas y Soluciones:**
  1.  **¿Activaste el Entorno Virtual?** Es el paso más común que se olvida.
      - **Solución:** Asegúrate de haber ejecutado `source .venv/bin/activate` (macOS/Linux) o `.\.venv\Scripts\activate` (Windows) _antes_ de intentar correr `python main.py`. Deberías ver `(.venv)` al inicio de la línea de tu terminal.
  2.  **¿Estás en la carpeta correcta?** ScraperMVP solo puede encontrar `main.py` si estás "parado" en la carpeta donde vive ese archivo.
      - **Solución:** Usa el comando `ls` (macOS/Linux) o `dir` (Windows) para ver los archivos de la carpeta actual. Si no ves `main.py`, usa `cd` para navegar a la carpeta correcta (ej. `cd ScraperMVP`).
  3.  **¿Instalaste Python correctamente?** (Referencia: Parte 1)
      - **Solución:** Abre una _nueva_ terminal (sin activar el entorno virtual) y escribe `python --version` o `python3 --version`. Si no te da una versión, Python no está bien instalado o no está en el PATH del sistema. Revisa la Parte 1.

**Problema 2: Error de "Módulo no encontrado" (ModuleNotFoundError).**

- **Síntoma:** La terminal muestra un error como `ModuleNotFoundError: No module named 'requests'` (o cualquier otro nombre de módulo como `beautifulsoup4`, `google-api-python-client`, etc.).
- **Causa:** Faltan una o más "piezas" (dependencias) que ScraperMVP necesita para funcionar.
- **Soluciones:**
  1.  **¿Activaste el Entorno Virtual?** Las piezas se instalan _dentro_ de la burbuja del entorno virtual. Si no está activo, ScraperMVP no las encuentra.
      - **Solución:** Activa el entorno virtual (ver Problema 1) e intenta de nuevo.
  2.  **¿Instalaste las dependencias?** (Referencia: Parte 4)
      - **Solución:** Con el entorno virtual activado, ejecuta: `pip install -r requirements.txt`. Asegúrate de que el comando termine sin errores.

**Problema 3: Los leads no aparecen en mi Hoja de Cálculo de Google Sheets.**

- **Síntoma:** ScraperMVP parece funcionar (ves mensajes en la terminal), pero tu hoja de Google Sheets sigue vacía.
- **Causas y Soluciones (Referencia: Parte 5 y Parte 7):**
  1.  **Revisa los mensajes de la Terminal:** ScraperMVP podría estar indicando un error específico al intentar conectarse o escribir en Google Sheets. Busca mensajes como "API Error", "Permission Denied", "Sheet not found", etc.
  2.  **Configuración del archivo `.env`:**
      - `GOOGLE_SHEET_ID`: ¿Es el ID correcto de tu hoja? Es una cadena larga de letras y números que está en la URL de tu hoja. Ejemplo: `https://docs.google.com/spreadsheets/d/ESTE_ES_EL_ID/edit`.
      - `GOOGLE_APPLICATION_CREDENTIALS`: ¿Apunta al nombre correcto de tu archivo JSON de credenciales? (Ej: `config/scrapermvp-f254174c1385.json`). ¿Está ese archivo realmente en la carpeta `config/`?
  3.  **Permisos en Google Cloud y Google Sheets:**
      - **API de Google Sheets Habilitada:** ¿Activaste la "Google Sheets API" en tu proyecto de Google Cloud Console?
      - **Cuenta de Servicio Compartida:** ¿Compartiste tu Hoja de Cálculo con la dirección de correo electrónico del "Service Account" (la que parece `xxxx@yyyy.iam.gserviceaccount.com`)?
      - **Permisos de Editor:** Al compartir, ¿le diste permisos de "Editor" a esa cuenta de servicio? Solo "Lector" no es suficiente.
  4.  **Conexión a Internet:** Parece obvio, pero ¿tiene tu computadora conexión a internet? ScraperMVP la necesita para hablar con Google.

**Problema 4: ScraperMVP se detiene inesperadamente o muestra muchos errores de una fuente específica (ej. "Error al scrapear Google Maps").**

- \*\*Causas y Soluciones:
  1.  **Cambios en la Página Web:** Las páginas web cambian su estructura a veces. Si un scraper estaba diseñado para una estructura antigua, puede fallar.
      - **Solución:** Este es un problema más técnico. Si es persistente, el desarrollador de ScraperMVP podría necesitar actualizar el código del scraper. Puedes intentar buscar leads de otras fuentes si están disponibles.
  2.  **Bloqueos por IP o Límites de Tasa:** Algunas páginas web pueden bloquear temporalmente tu acceso si haces demasiadas solicitudes muy rápido.
      - **Solución:** Espera un tiempo (varias horas o un día) e intenta de nuevo. Si el problema persiste, podría ser necesario usar proxies o ajustar la velocidad del scraper (esto es más avanzado).
  3.  **Credenciales Incorrectas para APIs Específicas:** Si un scraper usa una API que requiere una clave (como Google Maps API), y esa clave es incorrecta, inválida o ha excedido su cuota.
      - **Solución:** Verifica las claves de API en tu archivo `.env` y en la consola del proveedor de la API (ej. Google Cloud Console para Google Maps). Asegúrate de que la API esté habilitada y que tu plan de facturación (si es necesario) esté activo.
  4.  **Problemas de Red:** Una conexión a internet inestable puede causar fallos.

**Problema 5: El archivo `dashboard.html` no se genera o está vacío.**

- **Causas y Soluciones:**
  1.  **ScraperMVP no completó ninguna búsqueda:** Si la herramienta se detuvo muy pronto por otro error, es posible que no haya llegado a generar el dashboard.
      - **Solución:** Soluciona el error principal primero.
  2.  **No se encontraron leads:** Si la búsqueda fue muy específica y no hubo resultados, el dashboard podría estar vacío o mostrar ceros.
  3.  **Ruta del Dashboard:** Verifica si el dashboard se está guardando en la ubicación esperada (usualmente `utils/dashboard_output/index.html` o similar).

**¿Cuándo pedir ayuda más técnica?**

Si has intentado estas soluciones y el problema persiste, o si los mensajes de error son muy crípticos:

- **Copia el mensaje de error exacto:** Esto es crucial.
- **Describe los pasos que seguiste:** ¿Qué estabas haciendo cuando ocurrió el error?
- **Contacta a la persona que te proporcionó ScraperMVP** o al desarrollador. Con la información que recopiles, podrán ayudarte mejor.

¡No te desanimes por los obstáculos! Son parte del proceso de aprendizaje con cualquier herramienta.

---

## Parte 9: Usando ScraperMVP como un Profesional (Mejores Prácticas y Consejos)

¡Felicidades! Ya sabes cómo instalar, configurar y ejecutar ScraperMVP, e incluso cómo solucionar algunos problemas comunes. Ahora, veamos algunos consejos para que uses la herramienta de la forma más eficiente y obtengas los mejores resultados.

**Analogía:** Ya sabes conducir tu coche. Ahora aprenderás a mantenerlo en buen estado y a conducirlo de forma inteligente para ahorrar gasolina y llegar más rápido a tu destino.

**1. Define Bien tu Búsqueda (Antes de Empezar):**

- **¿A quién buscas?** ¿Qué tipo de negocios o profesionales son tus leads ideales? (Ej: "restaurantes en Ciudad de México", "abogados especializados en temas laborales en Guadalajara", "tiendas de ropa para bebés online").
- **¿Qué información es crucial?** ¿Necesitas sí o sí el email? ¿El teléfono es suficiente? ¿La dirección física es importante?
- **Configura los Scrapers:** ScraperMVP puede tener opciones para especificar palabras clave, ubicaciones, categorías, etc. Revisa si el archivo `main.py` o algún archivo de configuración te permite ajustar estos parámetros. Cuanto más específica sea tu búsqueda, más relevantes serán los leads.
  - _Nota: La forma de configurar esto puede variar. Consulta si hay un archivo `config.ini`, `settings.py` o si los parámetros se pasan directamente al ejecutar `main.py`._

**2. Sé Paciente y Ejecuta en Momentos Adecuados:**

- **Búsquedas Largas:** Si vas a buscar en muchas fuentes o categorías amplias, la herramienta puede tardar bastante. Ejecútala cuando no necesites tu computadora para tareas urgentes, o incluso déjala trabajando durante la noche (asegúrate de que la computadora no entre en suspensión).
- **Evita Sobrecargar:** No ejecutes múltiples instancias de ScraperMVP al mismo tiempo a menos que sepas que tu sistema y conexión a internet pueden manejarlo. Podrías causar bloqueos o un rendimiento lento.

**3. Revisa Regularmente tu Hoja de Google Sheets:**

- **Calidad sobre Cantidad:** No te obsesiones solo con el número de leads. Revisa la calidad de la información. ¿Son realmente los negocios que buscabas? ¿Los datos de contacto parecen correctos?
- **Limpia y Organiza:** Usa las funciones de Google Sheets para:
  - Eliminar duplicados (aunque ScraperMVP intenta hacerlo, siempre es bueno revisar).
  - Marcar leads ya contactados.
  - Añadir notas o columnas personalizadas (ej. "Nivel de Interés", "Fecha de Próximo Contacto").

**4. Entiende las Limitaciones (Y Sé Ético):**

- **No Toda la Información es Pública:** ScraperMVP solo puede recolectar información que los negocios han decidido hacer pública en internet. No esperes encontrar datos privados.
- **Las Páginas Cambian:** Los scrapers dependen de la estructura de las páginas web. Si una página cambia mucho, el scraper correspondiente podría dejar de funcionar hasta que se actualice.
- **Respeta los Términos de Servicio:** No uses ScraperMVP para actividades que puedan violar los términos de servicio de las páginas web que escanea o para enviar spam. El objetivo es encontrar prospectos legítimos para tu negocio.

**5. Mantén tu Entorno Actualizado (Ocasionalmente):**

- **Python y Pip:** Muy de vez en cuando, puede ser útil actualizar Python o Pip, pero si todo funciona, no es estrictamente necesario tocarlo.
- **Dependencias de ScraperMVP:** Si el desarrollador de ScraperMVP lanza una nueva versión o te indica que actualices las "piezas" (dependencias), puedes hacerlo (con tu entorno virtual activado) con:
  ```bash
  pip install --upgrade -r requirements.txt
  ```
  O si hay una dependencia específica que actualizar:
  ```bash
  pip install --upgrade nombre_de_la_dependencia
  ```

**6. Haz Copias de Seguridad de tus Datos Importantes:**

- **Archivo `.env`:** Contiene tus "secretos". Guárdalo en un lugar seguro si necesitas reinstalar ScraperMVP en el futuro.
- **Hoja de Google Sheets:** Google Drive hace esto automáticamente, pero si tienes una lista de leads muy valiosa, puedes hacer una copia manual de la hoja de cálculo de vez en cuando (`Archivo > Hacer una copia`).
- **Archivos de `results/`:** Si los datos crudos en formato JSON son importantes para ti, considera copiarlos a otra ubicación periódicamente.

**7. El Dashboard: Tu Vistazo Rápido:**

- Recuerda que el `dashboard.html` te da un resumen rápido del rendimiento de los scrapers. Es útil para ver si alguna fuente está fallando consistentemente o cuál es la más productiva. No reemplaza a Google Sheets para la gestión de leads, pero lo complementa.

**8. Aprende de los Logs (Si te Atreves un Poco Más):**

- Si algo va mal y quieres entender un poco más antes de pedir ayuda, los archivos en la carpeta `logs/` pueden darte pistas. Ábrelos con un editor de texto. Busca palabras como "ERROR", "WARNING" o el nombre de la fuente que te está dando problemas.

Siguiendo estos consejos, no solo usarás ScraperMVP, sino que lo dominarás para potenciar tu búsqueda de leads. ¡Mucha suerte!

---
