# EvalúaFP 1.2.10 beta — Biblioteca territorial de calendarios generales FP

**Nueva función:** archivar, versionar, comparar y reutilizar fechas generales de calendario escolar de FP **por comunidad o ámbito educativo y curso académico**, con fuente y confirmación docente. La biblioteca excluye municipio, isla, días propios del centro, evaluaciones, horas, FEOE y notas. Las fechas se cargan solo como **borrador pendiente de confirmación**, y las fiestas insulares conocidas no pueden registrarse como generales para Canarias. [Cambios 1.2.10](CAMBIOS_v1210_BETA.md) · [Instrucciones](docs/BIBLIOTECA_CALENDARIOS_GENERALES_1.2.10.md).

**Alcance:** hay soporte informático para los 19 ámbitos, pero no están precargados ni contrastados todos sus calendarios oficiales. «Revisado por docente» no acredita vigencia jurídica. Es código fuente beta; no se han recompilado ejecutables nativos. **Compilación Windows:** ejecutar `crear_exe_windows.bat`.

---

# EvalúaFP 1.2.9 beta — Anexos escolares complejos e IA con citas verificables

**Nueva fase de temporalización:** reconstrucción local de determinadas tablas FP de PDF/Word con cabeceras por etapa y fechas, asociación conservadora de líneas contiguas y preparación de un fragmento editable para IA. La **IA es optativa** y solo recibe el fragmento explícitamente autorizado; las fechas y citas se comprueban contra ese texto. Todas las propuestas requieren revisión del docente y quedan sin confirmar. [Novedades 1.2.9](CAMBIOS_v129_BETA.md) · [Guía práctica](docs/CALENDARIOS_ANEXOS_IA_1.2.9.md).

**Límites:** el cotejo de citas no certifica la autenticidad o vigencia normativa de un documento; no existen aún calendarios completos para los 19 ámbitos. La lectura OCR depende del equipo y no se ha recompilado un ejecutable por esta versión. Se entrega código fuente beta.

---

# EvalúaFP 1.2.8 beta — Importar fechas desde resoluciones de calendario

**Nueva fase:** lectura local de archivos PDF, DOCX, TXT y Markdown con una vista previa de fechas literales, su procedencia (página/párrafo/fila) y avisos de ambigüedad. El docente selecciona las fechas que desea llevar a un borrador **sin confirmar**, sin modificar datos de evaluación. Se verifica que el archivo mencione comunidad, curso y FP antes de habilitar la carga. [Novedades 1.2.8](CAMBIOS_v128_BETA.md) · [Guía técnica](docs/EXTRACCION_CALENDARIO_1.2.8.md).

**Precauciones:** no certifica la vigencia normativa, no descarga todos los calendarios oficiales ni interpreta automáticamente anexos escaneados sin OCR. No hay nuevos ejecutables compilados; es código fuente beta. Las resoluciones conjuntas para varias etapas necesitan especial cotejo docente.

---

# EvalúaFP 1.2.7 beta — Calendarios escolares versionados

**Novedad:** consulta de fuentes oficiales para los 19 ámbitos educativos, conservación de versiones de calendarios de centro por comunidad/curso/municipio/isla, registro de correcciones y comparación de fechas. Las versiones se recuperan como **borradores sin confirmar**, sin modificar horarios, RA/CE ni calificaciones. [Cambios 1.2.7](CAMBIOS_v127_BETA.md) · [Guía técnica](docs/CALENDARIOS_ESCOLARES_v127.md).

**Alcance:** disponer de enlaces de consulta para 19 ámbitos **no equivale a haber precargado sus 19 calendarios escolares oficiales**. Las fechas verificadas incorporadas al catálogo siguen siendo parciales y la confirmación compete al docente. Entrega de **código fuente beta**, sin nuevos ejecutables recompilados.

---

# EvalúaFP 1.2.6 beta — Vigilancia de modificaciones del BOE

**Nueva fase:** cada módulo puede consultar bajo demanda los metadatos de una disposición oficial del BOE, conservar la primera referencia, detectar diferencias posteriores y mantener alertas hasta que el docente registre una revisión. No se modifica el currículo ni se presume vigencia jurídica. La verificación de boletines autonómicos sigue pendiente. [Cambios de esta beta](CAMBIOS_v126_BETA.md) · [Nota técnica](docs/MONITOR_CAMBIOS_BOE_1.2.6.md).

**Distribución:** código fuente beta con pruebas; no contiene ejecutables recompilados. Pruebe la API del BOE en el equipo de destino antes de utilizar la función con documentación real.

---

# EvalúaFP 1.2.5 beta — Buscador nacional de títulos y módulos

**Nueva fase:** el profesor puede buscar por denominación los títulos de Grado Básico, Medio, Superior y cursos de especialización en los índices públicos de TodoFP, sin conocer la URL de cada ficha. Al abrir el título se propone su lista informativa de módulos y los enlaces curriculares del territorio. **No se inventan códigos de título, horas, RA/CE ni calendarios**. Consulta [novedades 1.2.5](CAMBIOS_v125_BETA.md) y [guía técnica](docs/INDICE_TITULOS_OFICIALES_v125.md).

**Límites:** la consulta en vivo de TodoFP no pudo probarse en el entorno de compilación. Esta entrega contiene **fuentes**, no nuevos EXE. El catálogo nacional codificado y los calendarios oficiales de todos los cursos siguen pendientes.

---

# EvalúaFP 1.2.4 beta — Explorar módulos y currículos de TodoFP por comunidad

**Nueva ayuda nacional:** desde la creación de un módulo o la programación didáctica se puede consultar una ficha de ciclo de TodoFP, localizar módulos identificados y abrir los currículos/modificaciones enlazados para la administración educativa seleccionada. Los códigos que no constan, las horas y la vigencia **siguen pendientes de contrastar por el docente**. La consulta no altera automáticamente RA/CE, notas ni calendario.

Consulta [los cambios de la versión](CAMBIOS_v124_BETA.md) y [la especificación técnica](docs/EXPLORADOR_TODOFP_1.2.4.md).

**Instalación:** haga una copia de seguridad y extraiga las fuentes en una carpeta nueva. Esta entrega no incluye un ejecutable recompilado. La consulta necesita Internet y no ha podido probarse en vivo contra TodoFP desde este entorno, por lo que se distribuye como **beta**.

---

# EvalúaFP 1.2.3 beta — Catálogo territorial de títulos y módulos

**Actualización de 20/11/2026:** búsqueda e importación de fichas de títulos y módulos en los 19 ámbitos educativos españoles, con código, grado, familia, fuente normativa, curso académico y revisión docente; selección del módulo desde la ficha sin recrear sus datos. La importación **no confirma automáticamente RA/CE, horas, legislación ni calendarios**. Es un catálogo incremental local, no una réplica completa de los registros estatales. Consulte [Cambios 1.2.3](CAMBIOS_v123_BETA.md) y [la guía técnica](docs/CATALOGO_FP_NACIONAL_1.2.3.md).

**Instalación:** haga una copia de seguridad de los datos. El ZIP incluye código fuente; no contiene ejecutables recompilados. Para Windows, siga `CREAR_VERSION_PENDRIVE.bat` después de extraer la carpeta completa en una ubicación nueva. Para actualizar desde 1.2.2, use el parche específico y valide las pruebas antes de utilizarlo con datos reales.

---

# EvalúaFP 1.2.2 beta — Historial curricular y comparación de RA/CE

**Novedad:** archivo por módulo, comunidad y curso de disposiciones curriculares revisadas por el docente, con procedencia, SHA-256 y comparación de enunciados RA/CE entre versiones. Todo ello **sin sobrescribir calificaciones, ponderaciones ni los criterios que se estén utilizando**. Incluye un índice local incremental de módulos con fuentes archivadas; **no es un catálogo nacional completo ni un verificador automático de vigencia**.

Consulte [los cambios](CAMBIOS_v122_BETA.md) y [las instrucciones técnicas](docs/HISTORIAL_CURRICULAR_1.2.2.md).

**Instalación:** descargue las fuentes completas o aplique el parche únicamente sobre las fuentes 1.2.1; haga copia de seguridad de SQLite y de los documentos antes de recompilar el portátil. No se incluyen ejecutables ya compilados.

---

# EvalúaFP 1.2.1 beta — Revisión curricular RA/CE

**Nueva funcionalidad integrada:** lectura local de RA/CE desde PDF, DOCX, TXT y Markdown con cita de página o párrafo, identificación por código de módulo, comparación con criterios existentes y ponderaciones iguales propuestas a dos decimales. La función **no sobrescribe notas ni RA/CE existentes**: genera una vista previa para revisión docente. Se mantienen las herramientas de programación, evaluación, FEOE y fuentes oficiales de 1.2.0.

**Documentación:** [Cambios y límites 1.2.1](CAMBIOS_v121_BETA.md), [Guía del generador de programación](docs/GUIA_GENERADOR_INTELIGENTE_1.1.6.md) y [Fuentes normativas](docs/VERIFICACION_OFICIAL_1.2.0.md).

**Distribución:** código fuente beta para Windows, Linux y macOS. Los ejecutables portátiles requieren compilación y comprobación en cada plataforma. **Antes de actualizar, haga copia de seguridad de la carpeta de datos y de SQLite**. La aplicación puede configurarse para los 19 ámbitos educativos españoles, pero no dispone todavía de un repositorio exhaustivo de todos los currículos oficiales autonómicos y cursos académicos.

---

# EvalúaFP 1.2.0 beta — Consulta normativa y anexos horarios oficiales

**Novedades:** búsqueda de disposiciones candidatas en la API oficial del BOE, análisis de metadatos y modificaciones disponibles, lectura local de tablas horarias desde PDF/DOCX (OCR opcional si se instala Tesseract), revisión docente previa y protección frente a importar tablas de otro ciclo. Consulte [el documento de cambios](CAMBIOS_v120_BETA.md) y [la guía técnica](docs/VERIFICACION_OFICIAL_1.2.0.md).

**Límites:** no existe todavía una base nacional completa de horas, RA/CE y calendarios verificados para todas las familias profesionales; no se aprueban normas por IA; las consultas vivas al BOE y la recompilación del portátil están pendientes de pruebas de aceptación externas. Este ZIP contiene fuentes, no nuevos EXE. Guarde copia de seguridad antes de actualizar.

---

# EvalúaFP 1.1.8 beta — Cobertura territorial nacional y calendarios versionados

**Primera fase nacional:** el asistente admite 17 comunidades autónomas y Ceuta y Melilla. Cada programación queda asociada a una administración educativa y un curso académico. Si no hay calendario o carga horaria oficial identificada y contrastada, **no se completan automáticamente datos de otra comunidad** y se solicita verificación docente. Se conserva el motor de programación con IA, importación integral y programa mínimo FEOE de la beta anterior.

**IMPORTANTE:** admitir 19 territorios **no significa disponer de un catálogo completo de currículos oficiales, módulos y calendarios de los 19 territorios**. Las horas verificadas se limitan actualmente a referencias parciales de Canarias; para otros módulos y territorios se requiere confirmación manual de la fuente y de las horas. No hay un servicio universal en tiempo real de normas/currículos.

**Lea [los cambios, las instrucciones y los límites de la 1.1.8](CAMBIOS_v118_BETA.md).**

**Instalación Windows:** haga primero copia de seguridad de los datos, extraiga las fuentes en una carpeta nueva y ejecute `CREAR_VERSION_PENDRIVE.bat`. Los ZIP entregados contienen **código fuente**, no ejecutables compilados. Conserve la versión portátil anterior hasta verificar el comportamiento en su ordenador.

---

# EvalúaFP 1.1.7.1 beta — Programa mínimo en empresa (FEOE)

**Novedad:** desde la preparación del módulo se propone un **programa formativo mínimo en empresa** descargable por separado (Word/PDF), a partir de CE confirmados y con tareas y evidencias sencillas, editables y adaptables. La IA externa puede seleccionar CE transferibles y redactar propuestas si se configura una clave y se autoriza el envío; sin clave hay una propuesta local orientativa. **Nunca se considera un plan individual oficial aprobado**. Consulte [los cambios y limitaciones](CAMBIOS_v1171_FEOE_MINIMO.md).

**Instalación Windows:** extraiga las fuentes en carpeta nueva y ejecute `CREAR_VERSION_PENDRIVE.bat`. Haga copia de seguridad de la versión anterior y sus datos. Los ZIP de fuentes no son EXE ya compilados.

---

# EvalúaFP Local 1.1.6 beta — Generador inteligente de programación

**Novedades y límites:** [CAMBIOS_v116_BETA.md](CAMBIOS_v116_BETA.md).

## Nueva beta 1.1.5.1 — Importación integral de programaciones

Al utilizar «Ya tengo una programación», EvalúaFP ahora extrae **todos los apartados recuperables**, no solo RA y CE. Se ofrecen en un panel de revisión editable antes de incorporar datos a un borrador; se preservan los campos previamente editados, el original y los apartados sin clasificar. Las horas y la FEOE procedentes del documento se proponen por separado y deben confirmarse. Consulta [el informe de cambios](CAMBIOS_v1151_IMPORTACION.md).

**Distribución:** código fuente beta. Para obtener un portátil Windows es necesario ejecutar `CREAR_VERSION_PENDRIVE.bat` en Windows después de realizar una copia de seguridad de los datos actuales. No sustituir el EXE público por un prototipo sin probar.

# EvalúaFP Local

## Actualización 1.1.2-beta — Auditoría de bloqueo y navegación

Se han añadido límites a las consultas de la API local, cancelación de lecturas obsoletas, recuperación de errores con reintento y avisos visibles en acciones y cambios de selección. Se han corregido la generación de códigos de unidades didácticas tras eliminaciones intermedias y la detección del estado de los botones de materiales.

**Pruebas:** 92 pruebas Python superadas y recorridos de Chromium con API simulada, incluidos fallos de servidor, navegación simultánea y seis pasos del asistente. Consulta el informe técnico en [`docs/INFORME_AUDITORIA_1.1.2.md`](docs/INFORME_AUDITORIA_1.1.2.md).

La versión se distribuye como **fuentes revisadas**; no sustituye las aplicaciones portátiles compiladas anteriormente. Debe recompilarse en el sistema de destino.


**Versión de trabajo: 1.1.2-beta — Inicio guiado y borradores de programación didáctica.**

Esta evolución añade un menú por tareas, tres vías de preparación de módulos, importación de currículos con revisión visual, un asistente de programación con exportación DOCX/PDF/Markdown y generación de exámenes simplificada. Las herramientas detalladas de la versión 1.0.6 siguen disponibles. No hay aprobación automática de programaciones ni cambios silenciosos de RA, CE, ponderaciones o calificaciones.

> **Estado de distribución:** se ofrece el código fuente beta y las instrucciones para compilar. Los antiguos binarios 1.0.6 no incluyen esta actualización. Consulte [Guía del inicio guiado](docs/INICIO_GUIADO_v1.1.md) y [Cambios 1.1 beta](CAMBIOS_v110_BETA.md).

---


**Aplicación local para la creación, corrección asistida y evaluación de instrumentos de Formación Profesional, organizada por resultados de aprendizaje (RA) y criterios de evaluación (CE).**

**Versión del código:** 1.1.2-beta · **Desarrollador:** Francisco Javier González Rolo · **Sistema principal:** Windows 10/11 (x64) · **Base de datos:** SQLite · **Interfaz:** HTML/CSS/JavaScript con ventana WebView2.

> **Estado:** proyecto en desarrollo. La ejecución automatizada de 72 pruebas ha concluido correctamente en el entorno de desarrollo; la compilación, la ventana gráfica y el instalador deben verificarse en Windows antes de distribuir la aplicación. La calificación definitiva requiere validación docente.


## Novedades v1.0.6 — Ponderaciones automáticas y web de presentación

### Criterios equivalentes cuando la programación no indica pesos

**Regla por defecto establecida para EvalúaFP:** todos los criterios de evaluación (CE) tendrán la **misma ponderación global en el módulo**, salvo que la programación didáctica establezca expresamente otra distribución. Cada resultado de aprendizaje (RA) obtiene un peso proporcional a la cantidad de criterios que contiene.

- **Peso global de un CE:** `100 / número total de CE del módulo`.
- **Peso de un RA:** `100 × número de CE de ese RA / número total de CE del módulo`.
- **Peso de cada CE dentro de su RA:** `100 / número de CE de ese RA`.

**Ejemplo:** un módulo tiene RA1 con 3 CE y RA2 con 5 CE (8 CE en total). Cada CE representa **12,50 %** del módulo; RA1 pesa **37,50 %** y RA2 pesa **62,50 %**. Dentro de RA1, los CE pesan aproximadamente 33,33 % cada uno; dentro de RA2, 20 % cada uno. Los redondeos se ajustan en centésimas para que cada conjunto cierre exactamente en 100 %.

Al **confirmar una extracción curricular**, al **añadir RA o CE manualmente** y al **consultar normativa oficial**, la aplicación completa únicamente las ponderaciones que no estén expresamente establecidas. La información se guarda con una marca de origen en la tabla SQLite `weight_origins`:

| Origen | Significado | ¿Se recalcula al cambiar los CE? |
|---|---|---|
| `default` | Propuesta automática de EvalúaFP | Sí |
| `programming` | Peso expresamente recogido en la programación confirmada | No |
| `manual` | Peso editado y confirmado por el docente | No |
| `existing` | Valor anterior a la incorporación del registro de procedencia | No, por precaución |

En **Programaciones y CE**, junto a cada peso aparece su procedencia. Para sustituir un peso por otro, utilice **Editar RA** o **Editar CE**; si deja el campo en blanco, ese elemento vuelve al cálculo automático. Las decisiones manuales se conservan aunque posteriormente se vuelva a importar una programación.

Si solo algunos porcentajes son expresos, EvalúaFP distribuye el **porcentaje restante** entre los elementos sin ponderar, proporcionalmente al número de criterios en los RA y por partes iguales en los CE del mismo RA. Si los valores expresos ya superan el 100 %, **no los sobrescribe ni los normaliza silenciosamente**: la evaluación mostrará una advertencia. Un RA sin CE permanece sin ponderación definitiva.

> **La formación en empresa se trata por separado.** Esta regla de distribución curricular **no establece automáticamente un porcentaje de FE** ni convierte una programación incongruente (por ejemplo, cinco RA del 20 % y un 25 % adicional de empresa) en una distribución válida. El docente debe validar la política de evaluación y, cuando corresponda, formalizar su corrección.

### Landing de presentación gratuita

Se incorpora una web estática, adaptable a móviles, en [`docs/index.html`](docs/index.html). Sus recursos se incluyen en `docs/assets/`: estilos, interacción, icono y **capturas de la interfaz real** de EvalúaFP con un grupo ficticio etiquetado como demostración. La web presenta el flujo de evaluación, la corrección multipágina, el cuaderno RA/CE, el modo USB y una calculadora ilustrativa de los pesos automáticos.

- **Visualización local:** abra `docs/index.html` en un navegador; no precisa ejecutar el servidor de EvalúaFP.
- **Publicación gratuita:** en el repositorio, configure **Settings → Pages → Deploy from a branch → main /docs** (cuando la opción esté disponible). GitHub Pages no se activa únicamente con añadir los archivos; es necesaria la configuración del repositorio.
- **Descarga:** la web enlaza al ZIP del código fuente público, que requiere compilación para obtener un `.exe`. No se anuncia un instalador Windows ya verificado.
- **Costes:** la aplicación se promociona sin coste de licencia de uso, pero el proveedor de IA que elija el docente puede cobrar por consumo. No se incluye ni se presupone una clave API gratuita.

### Alcance de esta actualización

- Migración **no destructiva** de SQLite para registrar procedencia de pesos; al abrir una base existente se completan los pesos NULL sin alterar los porcentajes expresos.
- Reequilibrado automático únicamente de criterios y resultados marcados como automáticos.
- Se conservan los datos antiguos con pesos expresos sin modificar.
- Se han ejecutado **72 pruebas automatizadas** del proyecto; el ejecutable y el instalador de Windows requieren aún validación real.

## Novedades v1.0.5 — Exámenes manuales y consulta curricular oficial

### Vinculación autónoma de preguntas manuales a RA y CE

En **Exámenes y rúbricas → Crear un examen manual**:

1. El docente redacta las preguntas en el editor JSON con `kind`, `prompt`, `points`, `ideal_answer` y `rubric`. **No es necesario indicar el criterio de antemano**.
2. Pulse **«Analizar preguntas y proponer RA/CE con IA»** y autorice el envío de los enunciados y los RA/CE confirmados (no se envían datos del alumnado).
3. La IA compara lo realmente evaluado en cada pregunta con los CE del catálogo curricular y propone hasta cuatro CE con **peso porcentual sobre esa pregunta**, confianza y justificación. No inventa identificadores.
4. Revise la propuesta en pantalla y edite el JSON cuando sea necesario. Una pregunta sin correspondencia inequívoca queda pendiente para asignación docente.
5. Marque la confirmación de revisión curricular y guarde el examen. Las asociaciones se conservan en `exam_question_criteria` de SQLite, sin borrar las relaciones antiguas.

**Ejemplo de dos CE para una pregunta de 10 puntos:**

```json
{
  "kind": "problema",
  "prompt": "Enunciado completo del supuesto contable...",
  "points": 10,
  "ideal_answer": "Solución desarrollada...",
  "rubric": [{"criterion": "Procedimiento", "weight_pct": 100}],
  "criteria_allocations": [
    {"criterion_id": 21, "weight_pct": 60, "rationale": "Procedimiento contable"},
    {"criterion_id": 22, "weight_pct": 40, "rationale": "Registro de operaciones"}
  ]
}
```

Los `criterion_id` del ejemplo son ilustrativos: deben corresponder a los identificadores que devuelve **tu propia base SQLite**. Las ponderaciones de esta asignación distribuyen los **puntos de una pregunta**; no son las ponderaciones oficiales de los RA o CE en la programación. En el libro de notas, una pregunta de 10 puntos calificada con 8 reparte 4,8 y 3,2 puntos entre los dos CE del ejemplo, sin duplicar la puntuación.

### Consulta oficial cuando faltan RA o CE

En **Programaciones y CE → Consultar RA/CE en el BOE** puede indicar un identificador `BOE-A-AAAA-NNN`. Para **Técnica Contable (0441)**, se propone el Real Decreto 1631/2009 (`BOE-A-2009-19148`). La aplicación descarga únicamente de `www.boe.es`, extrae los apartados identificados por número y letra y muestra **fuente y fecha de consulta**. Requiere Internet; si no es posible identificar el bloque curricular de forma fiable, no se importa nada.

Las propuestas normativas **no se incorporan sin confirmación docente**, no completan automáticamente las ponderaciones y no sustituyen la comprobación de la normativa autonómica de Canarias ni la vigencia de la disposición. Los pesos de RA y CE ya configurados se preservan si la norma no recoge otros valores.

Si en un examen manual no existen CE confirmados o una pregunta queda sin correspondencia, aparece un acceso para consultar el BOE, conservando el borrador del examen. Para títulos distintos de Técnica Contable hay que introducir el identificador oficial correcto.

### Actualización y seguridad

- Crear previamente copia de la base SQLite y documentos originales; después sustituir los archivos fuente y **recompilar el EXE**.
- Una migración no destructiva añade `exam_question_criteria` a SQLite y recupera con peso 100 % los CE de preguntas antiguas.
- Las asociaciones múltiples afectan a la agregación de puntos por CE y a la incorporación de notas validadas en la evaluación del módulo.
- La API de IA, la consulta del BOE y la confirmación de la asignación se realizan por separado. El docente sigue siendo responsable de la evaluación.
- Las **65 pruebas automatizadas** se han superado en el entorno local. La compilación en Windows y la consulta en directo al BOE requieren comprobación en el equipo de destino.

## Funcionalidades

- **Programaciones de FP:** registro de módulos, RA, CE, unidades, trimestres y ponderaciones; importación y revisión asistida de documentos didácticos.
- **Materiales didácticos:** asociación de PDF, DOCX, TXT y Markdown con una programación; generación de preguntas basada en contenido disponible y referencias a los pasajes usados. Los PDF escaneados sin texto extraíble precisan OCR previo.
- **Exámenes:** tipo test, desarrollo y problemas prácticos; dificultad baja/media/alta; varios modelos (A–F); banco de al menos tres preguntas por cada una solicitada, controlando repeticiones internas.
- **PDF de examen:** encabezado con centro, módulo, RA/CE, datos del alumno, duración y modelo; PDF del alumnado separado de solucionario, rúbricas y resultados.
- **Entregas:** importación de PDF e imágenes multipágina; carga masiva por ZIP con código del alumno y orden de páginas. Reconocimiento de continuaciones entre páginas y revisión de transcripciones ambiguas.
- **Corrección asistida por IA:** proveedores OpenAI o compatibles configurables; propuestas por pregunta con rúbrica y justificación, siempre sujetas a revisión y cierre docente.
- **Evaluación del módulo:** instrumentos internos, notas manuales o importadas, relación de evidencias con CE y RA, ponderaciones, seguimiento por unidad y trimestre, recuperaciones, cierres e informes individuales PDF.
- **Additio:** exportación del alumnado, hojas para configuración curricular RA/CE, relaciones y ponderaciones, y calificaciones **consolidadas por RA y CE**, no por prueba.
- **Modo portátil USB:** configuración de carpetas relativas al ejecutable y copias; SQLite y documentos originales en el dispositivo; claves API cifradas que requieren contraseña para desbloqueo.

## Estructura del repositorio

```text
app.py                       Servidor local e inicio de la aplicación
web/                         Interfaz HTML, CSS y JavaScript
manual_alignment.py          Clasificación de preguntas manuales en CE
curriculum_official.py        Consulta segura y extracción curricular del BOE
assets/                      Icono y recursos gráficos
ia.py                        Conexión con proveedores de IA
logic.py                     Exámenes, entregas y lógica de negocio
materiales.py                Procesamiento de fuentes documentales
database.py                  Persistencia SQLite
evaluacion.py                Evaluación curricular por RA y CE
exportaciones.py             Excel, CSV y soporte para Additio
exam_pdf.py / eval_pdf.py    Exámenes, solucionarios e informes PDF
storage_config.py            Carpetas y almacenamiento portátil
scripts/                     Preparación, pruebas, compilación e instalador
instalador/                  Proyecto de Inno Setup
tests/                       Pruebas automatizadas
ejemplos/                    Ejemplos sin datos personales
docs/                        Documentación complementaria e historial
```

## Inicio en Windows desde el código fuente

1. Descarga o clona este repositorio y extrae su contenido en una carpeta con permisos de escritura.
2. Ejecuta `INICIAR_EVALUAFP.bat`. La primera ejecución necesita Internet para preparar Python y dependencias.
3. La aplicación se abrirá en su ventana propia (en equipos compatibles con Edge WebView2).
4. Como alternativa, ejecuta `iniciar_navegador_windows.bat` para utilizar la interfaz mediante el navegador y el servicio local.

### Compilar el ejecutable y el instalador

| Archivo | Uso |
|---|---|
| `PREPARAR_ENTORNO.bat` | Prepara Python gestionado y bibliotecas sin depender de una instalación previa. |
| `crear_exe_windows.bat` | Ejecuta las pruebas, empaqueta con PyInstaller y valida `dist/EvaluaFP.exe`. |
| `crear_instalador_windows.bat` | Usa el EXE y compila `dist/Instalar_EvaluaFP.exe` mediante Inno Setup 6/7. |
| `CREAR_VERSION_PENDRIVE.bat` | Crea `dist/EvaluaFP_Portatil/` para copiar toda esa carpeta al USB. |
| `DIAGNOSTICO_WINDOWS.bat` | Genera información útil para investigar problemas de instalación. |

No es necesario Inno Setup para generar el EXE portátil. Si falla Inno Setup, el ejecutable previamente compilado puede seguir utilizándose.

Para ejecutar las pruebas en un entorno Python ya preparado:

```powershell
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Para compilar se requieren además las dependencias de `requirements-build.txt`. Véase [Instalación y distribución](docs/INSTALACION.md).

## Uso desde pendrive

Ejecuta `CREAR_VERSION_PENDRIVE.bat` en Windows y copia **la carpeta completa** `dist/EvaluaFP_Portatil/` al dispositivo, no solamente su ejecutable. La configuración de ejemplo `ejemplos/EvaluaFP.portable.json` describe las rutas relativas, que no dependen de la letra de unidad.

```text
EvaluaFP_Portatil/
  EvaluaFP_Portatil.exe
  EvaluaFP.portable.json
  EvaluaFP_Datos/       # SQLite, originales, configuración cifrada
  EvaluaFP_Copias/      # Copias de seguridad
```

El cifrado de una clave API no equivale a cifrar las calificaciones o documentos de alumnado. Utiliza una unidad USB cifrada, no desconectes el dispositivo mientras la aplicación está abierta y conserva copias fuera del pendrive.

## RA/CE, instrumentos y Additio

Las **evidencias** (pruebas, portfolios, prácticas, trabajos, observación, evaluación en empresa) se almacenan con su origen y valoración. El sistema calcula la calificación consolidada de cada **CE** y, a partir de ellos, la de cada **RA**, unidad, trimestre y módulo según los pesos configurados. **Cuando no hay ponderaciones expresas se aplica la regla automática igualitaria por CE y proporcional por número de CE para cada RA**, según se detalla al comienzo del README.

Desde **Evaluación del módulo → Resultados**, la exportación para Additio separa:

1. Archivos para configurar RA y CE, sus códigos, descripciones y relaciones.
2. Hojas de ponderaciones y correspondencias curriculares.
3. Matrices Excel/CSV/TSV de **notas por RA y CE** y alumnado.
4. Exportación interna de evidencias e informes para su trazabilidad.

No se garantiza una sincronización automática con Additio. Verifica el asistente de importación disponible en tu cuenta y las columnas antes de traspasar calificaciones. Las notas definitivas se exportan únicamente cuando hay cierre docente vigente. La programación de Técnica Contable utilizada como ejemplo incluía cinco RA de 20 % más FE del 25 %: el total 125 % se considera incoherente y debe ser validado por el docente antes del cierre.

## Seguridad y protección de datos

- **No subas a GitHub** ficheros SQLite reales, exámenes de estudiantes, copias de seguridad, claves API ni las carpetas `EvaluaFP_Datos` y `EvaluaFP_Copias`. El archivo `.gitignore` ayuda, pero no sustituye una revisión manual.
- La API se almacena cifrada con contraseña maestra y no mediante hash irreversible: la aplicación debe poder recuperarla para consultar el proveedor seleccionado.
- Los documentos enviados a servicios externos de IA pueden contener datos personales; revisa las condiciones del proveedor y las obligaciones de protección de datos del centro.
- Una valoración automática **no sustituye la validación y responsabilidad del profesorado**.
- Un repositorio público no implica que los datos del centro deban publicarse. Más información en [Seguridad](SECURITY.md).

## Documentación

- [Landing pública de EvalúaFP](docs/index.html) · interfaz real y datos ficticios

- [Guía de instalación y distribución](docs/INSTALACION.md)
- [Arquitectura y almacenamiento](docs/ARQUITECTURA.md)
- [Seguridad y tratamiento de datos](SECURITY.md)
- [Historial detallado de versiones](docs/HISTORIAL_DE_VERSIONES.md)

## Autoría y derechos

**Desarrollador: Francisco Javier González Rolo.** El código se publica aquí para su consulta y desarrollo. No se incluye una licencia de código abierto porque no se ha establecido expresamente una; para permitir reutilización por terceros, deberá añadirse una licencia elegida por el titular. Los derechos sobre recursos didácticos, exámenes y documentos de terceros corresponden a sus respectivos titulares.

## Corrección 1.0.3 — archivos con tildes al importar programaciones

En la versión 1.0.2, la subida de archivos con nombres como
`Programación Didáctica — Técnica Contable 2026_2027.docx`
podía devolver `expected string or bytes-like object, got 'Header'`.
Se ha corregido el analizador MIME de `multipart/form-data` para procesar
encabezados y parámetros Unicode (UTF-8 y RFC 2231). Afecta a la subida de
programaciones, materiales didácticos y exámenes. El cambio no modifica
la estructura SQLite ni exige borrar datos; requiere recompilar el EXE.

Para aplicar el parche sobre el código 1.0.2, sustituye `app.py`,
`web/index.html` y añade `tests/test_multipart_unicode.py`. Después ejecuta
`crear_exe_windows.bat` o `CREAR_VERSION_PENDRIVE.bat`.

## Compilaciones portátiles para Linux y macOS

EvalúaFP puede compilarse **sin Python en el equipo de destino** para Linux x64 y para Mac Intel o Apple Silicon. Cada paquete debe generarse en su propio sistema operativo, por lo que el repositorio incluye el workflow **Actions → Compilar portátiles Linux y macOS**. Consulte [el manual de portabilidad](docs/PORTABLE_LINUX_MAC.md).

El archivo `.github/workflows/portables-linux-macos.yml` prepara tres artefactos descargables; el proceso usa PyInstaller y ejecuta pruebas, incluida una prueba `--selftest` del binario. **Hasta probarlo en equipos reales, el soporte debe considerarse experimental**. Linux puede necesitar bibliotecas gráficas/Qt en el sistema; en macOS se recomienda firmar y notarizar los `.app` para distribución pública. Los datos y las claves API siguen locales y en modo USB la configuración se guarda fuera de la aplicación.

Para compilar en Linux o Mac con Python 3.13 disponible:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-build.txt
python scripts/build_portable_unix.py --test
```

El formato de distribución será `.tar.gz` en Linux y `.zip` con `.app` en Mac, adecuados para añadirlos a la carpeta `descargas/` de la landing. La compilación Windows y el instalador Inno Setup se mantienen por separado.


## Actualización 1.1.1-beta — Corrección de «Preparar módulo»

Se ha corregido el bloqueo de la interfaz en «Cargando…» al seleccionar «Preparar módulo». El controlador mostraba la animación, pero no invocaba el componente guiado. Ahora se llama a `viewPrepare()` y se muestra un error legible si una sección futura no está reconocida.

**Pruebas:** 84 pruebas existentes y prueba de regresión de navegación; recorrido de UI en navegador con API HTTP real y datos ficticios: alta de módulo, elección de ruta curricular y acceso a importación.

**Actualización del EXE portátil:** un ejecutable PyInstaller contiene su copia de `web/app.js` dentro del paquete. No basta con sustituir el JavaScript de la landing pública: debe recompilarse desde estas fuentes. Antes de instalar o ejecutar una nueva versión en un USB con calificaciones reales, realice copia de seguridad del SQLite y los documentos.

## Beta 1.1.3 — Temporalización curricular, calendario lectivo, FEOE y Gantt

Se incorpora al paso 5 del asistente una planificación **editable** con horas semanales, horas por día, horas totales del módulo, calendario de Canarias 2026-2027, cierres de evaluaciones, días no lectivos del centro, unidades y CE, selección de CE para FEOE, horas de docencia en el centro durante FEOE, instrumentos y recursos por unidad, actividades complementarias y extraescolares. El paso 6 muestra el Gantt semanal y la exportación DOCX/PDF incluye portada e índice. **No se alteran calificaciones ni los pesos docentes existentes.**

La cifra del 10–20 % de CE es **orientativa**; la normativa de FEOE regula RA y duración del periodo, que han de verificarse para el ciclo. Esta beta añade 8 pruebas específicas a las 92 de 1.1.2. Véase [Temporalización y FEOE](docs/TEMPORALIZACION_FEOE_1.1.3.md).


## Beta 1.1.9 — Biblioteca nacional de fuentes y horas

El asistente incluye accesos a portales de FP de los 19 ámbitos educativos, importación de cuadros horarios completos desde Excel/CSV, almacenamiento de fuentes revisadas y calendarios del centro vinculados al territorio y curso, y un intérprete opcional con IA que exige cita literal. No hay un catálogo nacional completo de horas preinstalado ni verificación automática de vigencia. Consulte [Cambios 1.1.9](CAMBIOS_v119_BETA.md) y [guía técnica de fuentes nacionales](docs/FUENTES_NACIONALES_1.1.9.md).
