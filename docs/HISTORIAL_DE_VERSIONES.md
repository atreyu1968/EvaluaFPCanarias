## Versión 1.0.6 — Ponderaciones automáticas y landing de presentación

- CE con idéntico peso global si la programación no dispone otra ponderación; RA proporcionales al número de CE.
- Registro de procedencia por criterio y resultado en SQLite, con respeto de pesos manuales y documentados.
- Reequilibrado automático al incorporar nuevos criterios.
- Landing gratuita en docs/index.html con capturas reales de una demostración sin datos personales.
- 72 pruebas automatizadas superadas. Compilación Windows y despliegue de Pages pendientes.

## v1.0.5 — Asignación autónoma de RA/CE y fuentes oficiales

- Clasificador de preguntas de exámenes manuales a RA/CE confirmados por el docente; justificaciones, indicador de confianza y asignación múltiple.
- SQLite: nueva relación `exam_question_criteria` y preservación de datos antiguos.
- Registro consolidado y sincronización de exámenes validados según la distribución de puntos por CE.
- Consulta de normativa curricular en BOE, con extracción determinista, fuente, fecha de consulta y confirmación docente.
- Borradores manuales conservados al consultar normativa desde el examen.
- 65 pruebas automatizadas superadas; publicación del instalador de Windows pendiente de validar.

## 1.0.4 — Rendimiento y análisis curricular fiable

- Banco de preguntas multcriterio, menor número de llamadas secuenciales y pasajes deduplicados.
- Propuestas RA/CE acreditadas contra texto literal; informe de cobertura y alertas.
- Orden de extracción de párrafos y tablas DOCX corregido.
- Indicador de tiempo transcurrido sin estimaciones ficticias de progreso.
- Detecta casos curriculares conflictivos de Técnica Contable (código 0299/0441, RA204, 125 %).

## 1.0.3 — Corrección de nombres UTF-8 en subida de documentos

- Arreglado el fallo de `email.header.Header` en `multipart/form-data` con nombres acentuados.
- Compatibilidad con nombres Unicode y parámetros de nombre RFC 2231.
- Pruebas de regresión para PDF/DOCX y subida de programaciones.

# EvalúaFP Local 1.0.2 — Exportación curricular para Additio (FP)

Esta actualización corrige los archivos destinados a Additio: **las notas exportadas se organizan por RA y CE, no por examen ni instrumento**. Los instrumentos siguen en el expediente interno de EvalúaFP para justificar cada calificación.

## Exportar la configuración curricular

En **Evaluación del módulo → Resultados** puede descargar:

- **Additio: configurar RA y CE (ZIP)**, que contiene tres libros de Excel y una guía de importación.
- **RA: hoja de configuración**: sigla Additio, código original de RA, descripción y porcentaje. Su finalidad es facilitar el **alta o revisión manual de los RA como competencias específicas**. No se garantiza una importación automática de RA desde este libro.
- **CE: importar desde Excel**: libro `.xlsx` con una sola columna, sin encabezado, en formato `CÓDIGO. DESCRIPCIÓN. SIGLA_RA`, siguiendo el tutorial específico para Formación Profesional de la Consejería de Cantabria. Es un formato preparado para el asistente de criterios de Additio; conviene verificarlo con la versión concreta de su cuenta.
- **RA/CE: ponderaciones y relaciones**: matriz de equivalencia entre códigos originales y códigos Additio, pesos del RA y los CE, unidades y trimestres asociados. Estos pesos **deben configurarse o comprobarse en Additio**.

Las siglas llevan un prefijo `EFP<NÚMERO DE MÓDULO>_`, p. ej. `EFP4_RA2`. Esto evita que dos módulos con `RA1` colisionen en la configuración de Additio. La correspondencia entre prefijo y programación figura en el libro de detalle. Los CE del tipo `RA2.a` se identifican en Additio como `2.a` para adoptar la convención de importación indicada en el tutorial.

**Orden sugerido:** 1) importar el alumnado, 2) dar de alta RA a partir del libro RA, 3) importar CE desde el libro monocolumna, 4) comprobar las relaciones RA–CE y las ponderaciones, 5) transferir las notas RA/CE.

## Exportar las calificaciones

- **Additio: notas RA/CE Excel**, **CSV** y **TSV**: contienen `Codigo`, `Alumno`, una columna por RA y otra por CE. **No tienen columnas de exámenes, rúbricas, portfolios o instrumentos.**
- En las notas definitivas solo se muestra una calificación cuando existe un **cierre docente vigente**; las demás celdas quedan vacías.
- **RA/CE seguimiento provisional CSV**: opción separada que muestra únicamente RA y CE completos a partir de evidencias ya validadas por el docente, aunque no se haya cerrado el módulo. No debe confundirse con la evaluación definitiva.
- **Estado de validación CSV**: muestra las advertencias y los cierres por separado, para no introducir columnas ajenas al currículo en Additio.

**El sistema no sincroniza automáticamente las notas de Additio**. Es necesario verificar el orden del alumnado, los códigos, las columnas disponibles y la compatibilidad del asistente de importación, o realizar una transferencia mediante copia/pegado controlada.

**Aviso de la programación aportada:** Técnica Contable 2026/2027 incluye 5 RA con 20 % cada uno y menciona un 25 % adicional de formación en empresa, sumando 125 %. EvalúaFP no resolverá esa contradicción por su cuenta y no cerrará calificaciones finales hasta que el docente valide una política coherente.

**Actualización:** aplicar el parche a la carpeta del código fuente de la versión 1.0.1, no al `.exe` ya compilado; después ejecutar `crear_exe_windows.bat` o `CREAR_VERSION_PENDRIVE.bat`. Realice antes una copia de seguridad de SQLite y los documentos. No se requieren cambios en el esquema SQLite para esta actualización.

**Pruebas:** se verifican generación, conexión RA–CE, ZIP de configuración, notas definitivas/provisionales, ausencia de instrumentos y descargas HTTP. El proceso de compilación y el importador real de Additio deben confirmarse en Windows y Additio respectivamente.

Fuentes de consulta:
- https://codigoescuelaeducantabria.es/cursos/TUTORIAL_DE_ADDITIO/d_especial_fp_importar_currculo_desde_excel.html
- https://www.educa.jcyl.es/crol/es/recursos-educativos/additio-app.ficheros/1675433-materiales%20Additio%20APP.pdf

---

# EvalúaFP Local 1.0 — Evaluación por RA/CE y modo USB portátil

Esta versión es **acumulativa** sobre la 0.9.1. Mantiene los módulos anteriores (generador PDF de exámenes, manuscritos, rúbricas, materiales, SQLite y corrección supervisada) y añade el módulo de **Evaluación del módulo** y el almacenamiento portátil con API cifrada.

## A. Utilizar EvalúaFP en un pendrive

En Windows, ejecute **`CREAR_VERSION_PENDRIVE.bat`** desde la carpeta del código fuente. Este script primero instala y comprueba las dependencias, ejecuta las pruebas y genera el EXE. Después prepara `dist\EvaluaFP_Portatil\` con:

```
EvaluaFP_Portatil/
├── EvaluaFP_Portatil.exe
├── EvaluaFP.portable.json       # Rutas relativas; no contiene secretos
├── EvaluaFP_Datos/
│   ├── datos/evaluafp.sqlite3
│   ├── almacen/                # Exámenes y originales
│   └── seguridad/api_cifrada.json
└── EvaluaFP_Copias/            # ZIP de seguridad
```

**Copie la carpeta entera** al USB para trasladar también los datos. En el primer inicio las subcarpetas necesarias se crean automáticamente. Si desea distribuir solo el EXE sin información preexistente, el ejecutable llamado `EvaluaFP_Portatil.exe` activa automáticamente el modo USB y crea nuevas carpetas al lado; los datos se generan al utilizarlo.

Al conectar el USB a otra máquina Windows puede cambiar la letra de la unidad. Las carpetas se configuran **relativas al ejecutable** y las rutas absolutas de los documentos ya registrados se actualizan al abrir SQLite; no se pierde la vinculación entre originales, páginas y notas. En **API de IA y almacenamiento** puede cambiar tanto la carpeta de datos como la de copias. El sistema copia la base de datos y los documentos al nuevo destino, sin sobrescribir archivos existentes, y exige cerrar y abrir la aplicación para activar los cambios. NO borre la carpeta de origen hasta comprobar que todo está correcto.

### Importar notas y exámenes de la instalación anterior

Con EvalúaFP cerrado, copie al pendrive la carpeta `dist\EvaluaFP_Portatil`, conecte ese pendrive al ordenador donde están los datos originales y ejecute **`IMPORTAR_DATOS_DEL_PC.bat`** (incluido en el kit USB). El asistente copia `%LOCALAPPDATA%\EvaluaFP` al almacenamiento del USB y traslada las copias antiguas a `EvaluaFP_Copias`. **No sobrescribirá una base de datos ya existente en el USB.** Al abrir EvalúaFP portátil se reescribirán las referencias de los documentos a la ubicación nueva. La clave API guardada en las credenciales de Windows debe introducirse nuevamente y cifrarse con contraseña para el USB.

**Requisitos:** Windows x64 con Microsoft Edge WebView2 Runtime disponible, permiso de ejecución y escritura en la unidad y espacio suficiente. El compilador sí necesita Windows para producir el EXE; aquí se entrega código y scripts, no un ejecutable ya construido. La versión portátil no necesita Inno Setup ni una instalación de Python en cada PC. No extraiga el EXE dentro de la carpeta de datos; utilice la estructura indicada. No extraiga el pendrive durante una operación de lectura/escritura de SQLite.

### Protección de la API

- Las claves API **no se guardan como hash**: una huella irreversible no podría utilizarse para autenticar solicitudes. Se almacenan mediante **AES-256-GCM y derivación scrypt**, con sal y nonce aleatorios; la contraseña maestra debe contener al menos 12 caracteres.
- En cada nuevo inicio del modo USB, abra **API de IA y almacenamiento** y pulse **Desbloquear** con la contraseña maestra. La contraseña no queda guardada. Sin desbloquear, la aplicación sigue trabajando con SQLite y documentos, pero no puede llamar a la API externa.
- La clave cifrada viaja en `EvaluaFP_Datos/seguridad/api_cifrada.json`. Las copias ZIP portátiles también incluyen ese archivo **cifrado**, nunca la contraseña. En la modalidad instalada permanece la opción anterior del gestor de credenciales de Windows.
- **Importante:** SQLite, fotografías y PDF no están cifrados por este mecanismo. Para datos reales de alumnado es necesario un pendrive con cifrado de volumen (BitLocker To Go u otra solución autorizada por el centro), medidas de protección de datos y una copia adicional en otro dispositivo seguro.

## B. Módulo de evaluación de módulo profesional

En el menú **Evaluación del módulo** se pueden crear unidades vinculadas a CE y trimestre; instrumentos de tipo examen, práctica, problema, portfolio, proyecto, observación, empresa o externo; y calificaciones introducidas a mano o importadas de CSV. Las calificaciones de un examen EvalúaFP previamente validado por el docente pueden sincronizarse como evidencias en el instrumento correspondiente, sin sobrescribir datos manuales por defecto.

Para importar desde CSV, utilice una fila por alumno y CE y el encabezado:

```csv
codigo_alumno;criterio;nota;comentario
ALU001;RA2.a;7,5;Registra correctamente los asientos
ALU002;RA2.a;6;Revisar redondeos
```

Se rechazan filas con alumnos o CE desconocidos, notas fuera de 0 a 10 y duplicados. Si alguna fila falla, no se importa ninguna. Cada modificación queda auditada.

### Cálculo de calificaciones y advertencias

1. Cada CE reúne notas de sus instrumentos mediante el **peso asignado a cada uno**, que debe totalizar 100 %. Los criterios de un mismo RA deben estar ponderados y sumar 100 % dentro de ese RA.
2. Cada RA se calcula a partir de las puntuaciones CE y sus pesos. La aplicación muestra qué porcentaje de CE está superado (umbral configurable). Los trimestres muestran resultados provisionales de sus instrumentos y sus evidencias pendientes.
3. La calificación del módulo se calcula únicamente si **todos los RA y CE, instrumentos y notas están completos y la política de ponderaciones ha sido validada por el docente**. El botón **Validar cierre** crea un registro histórico inmutable y genera informes individuales PDF; si después se modifica una evidencia, el cierre anterior queda señalado como desactualizado.
4. En la programación aportada de **Técnica Contable 2026/2027** aparecen cinco RA con 20 % cada uno más un 25 % adicional de formación en empresa: **125 %**. Por eso, por defecto, no se permite cerrar el módulo sin resolver ese conflicto. El docente podrá documentar una integración de las evidencias FE dentro de los RA, o ajustar formalmente los pesos RA para que sumen el 75 % si la FE conserva un 25 % independiente. La aplicación no corrige automáticamente la programación.
5. La superación por CE se interpreta mediante la nota umbral configurada (inicialmente 5/10); el mínimo de CE superados por RA se configura (inicialmente 50 %). Se trata de parámetros que requieren revisión frente a la programación aprobada; la aplicación no presume que una interpretación sustituya la decisión docente.

En **Evaluación del módulo** podrá exportar el cuadro de notas a CSV y descargar el informe justificativo de cada alumno en PDF.

## C. Instalación y actualización

- EXE Windows (instalación habitual): `crear_exe_windows.bat` → `dist\EvaluaFP.exe` (datos por defecto en `%LOCALAPPDATA%\EvaluaFP`).
- Instalador habitual: `crear_instalador_windows.bat` (requiere Inno Setup; no es necesario para USB).
- Pendrive: `CREAR_VERSION_PENDRIVE.bat` → `dist\EvaluaFP_Portatil\EvaluaFP_Portatil.exe` (usa carpetas junto al EXE).
- Ejecutar proyecto sin compilar: `INICIAR_EVALUAFP.bat` (requiere preparación inicial, no adecuado como distribución a profesores sin Python).

Para actualizar desde 0.9.1, aplique el parche al **código fuente**, haga copia de seguridad y compile de nuevo. No copie un archivo SQLite antiguo dentro de un USB que ya contenga calificaciones diferentes; realice primero una migración controlada.

### Verificación

Las pruebas automatizadas se ejecutan con `python -m unittest discover -s tests -v`. Se han verificado la generación y la corrección existentes, cifrado y desbloqueo de la API con contraseña incorrecta, rutas relativas del USB, migración no destructiva, importaciones CSV y cálculo de RA y FE con pesos coherentes. El EXE/WebView2 e Inno Setup **deben probarse en Windows real** antes de distribuirse en un centro educativo.

---

## Historial de la versión anterior

# EvalúaFP Local 0.9.1 — PDF A4, modelos y problemas prácticos

Esta versión es una actualización acumulativa de la 0.8.0: incluye también los modelos A–F, la dificultad baja/media/alta, el banco triple de preguntas, la barra superior azul marino en Windows 11, el modal de 10 segundos, el icono y el alta de alumnado no registrado.

## Principales novedades de la versión 0.9.1

- **Exportación PDF auténtica con ReportLab:** descarga directa `PDF modelo A`, `PDF modelo B`… sin depender de la impresión del navegador.
- **Encabezado personalizado:** en la pantalla de generación introduzca nombre del centro, fecha de examen y duración. Además se incluyen curso académico, ciclo, grupo, módulo, RA/CE, dificultad, modelo, puntuación máxima y campos de identificación del alumno.
- **Problemas prácticos:** seleccione «Solo problemas prácticos» o introduzca el número de problemas que desea mezclar con preguntas test/desarrollo. Los problemas requieren datos, apartados y solución detallada y se evalúan con una rúbrica ponderada por criterios y procedimiento. Las puntuaciones del modelo mantienen los pesos de los RA y CE.
- **Espacio de trabajo:** las preguntas de desarrollo muestran renglones para contestar y los problemas disponen de tres bloques de renglones para cálculos y operaciones. Los enunciados y sus títulos se mantienen unidos en los saltos de página siempre que quepan en una página.
- **Documentos separados:** «Descargar PDF alumnado» carece de soluciones y rúbricas; «PDF soluciones y rúbrica» contiene la clave de corrección para el docente.
- **Descarga por lotes:** «ZIP modelos» contiene **solo PDF para alumnado**. «ZIP solucionarios (docente)» contiene únicamente los solucionarios; no distribuya este segundo archivo al alumnado.
- **Migración de SQLite no destructiva:** agrega `center_name`, `exam_date`, `duration_minutes` a la tabla `exams` conservando datos existentes.
- **ReportLab integrado en el EXE:** `requirements.txt` y `crear_exe_windows.bat` incluyen la biblioteca de generación PDF.

### Cómo generar el examen

1. En **Exámenes y rúbricas**, seleccione módulo y, si procede, la programación didáctica y sus materiales asociados.
2. Escoja tipo de preguntas: test, desarrollo, mixto o solo problemas. En los tres primeros casos puede definir además cuántos serán problemas prácticos (de 0 al total).
3. Establezca dificultad, número de modelos (1–6), preguntas por modelo, total de puntos, centro, fecha y duración.
4. Marque los CE que se evaluarán. La aplicación debe contar con RA y CE ponderados expresamente en la programación.
5. Pulse **Generar examen y rúbrica** y revise el resultado. El banco tendrá al menos 3 veces el número de preguntas de un modelo; cuando se soliciten más de tres modelos, aumentará para asignar preguntas distintas. Se rechazan enunciados idénticos o muy próximos; la revisión docente sigue siendo necesaria para detectar equivalencias semánticas.
6. En **Exámenes disponibles**, descargue cada PDF y, si desea repartirlos todos, el **ZIP modelos**. Descargue las rúbricas en la sección de docente.

### Modificaciones de compilación y distribución

Extraiga el ZIP en una carpeta nueva. Ejecute `crear_exe_windows.bat`; este preparará Python gestionado por uv, instalará también ReportLab, ejecutará las pruebas y generará `dist\EvaluaFP.exe`. Para el instalador, ejecute `crear_instalador_windows.bat`, que usa Inno Setup sin depender de winget. Si ya utiliza la versión 0.8.0 puede aplicar el parche en la raíz del proyecto y recompilar el EXE: **sobrescribir el código fuente no cambia el ejecutable anterior**.

Los datos se mantienen en `%LOCALAPPDATA%\EvaluaFP`. Realice una copia de seguridad antes de actualizar. Los archivos de entrada de los libros y las fotografías de los exámenes no se alteran.

### Pruebas y limitaciones

- Se han superado 27 pruebas automáticas en el entorno de desarrollo, incluidas generación sin duplicados con una IA simulada, PDF/ZIP, contenido del encabezado, ausencia de soluciones en PDF de alumno y persistencia SQLite.
- Se ha comprobado visualmente un PDF de ejemplo renderizado en A4 con problemas multipágina.
- **Pendiente:** aceptación real del EXE y del instalador en Windows, pruebas con varios modelos externos reales y comprobación de precisión de corrección manuscrita. Las respuestas y rúbricas generadas por IA requieren revisión del docente antes de usarse.
- Utilice los libros de texto conforme a sus licencias y a las condiciones de protección de datos del centro.

---

# Historial: EvalúaFP Local 0.9.0 · Modelos de examen y barra azul marino

Esta edición actualiza la 0.8 y mantiene SQLite y los datos previos bajo `%LOCALAPPDATA%\EvaluaFP`.

## Funciones nuevas

- Dificultad obligatoria seleccionable: **baja, media, alta**. Se indica en los prompts de IA, listados e impresos.
- **1 a 6 modelos** diferentes (A, B, C...). Cada modelo conserva la cantidad por CE, el tipo y la ponderación.
- Banco persistente con al menos **3 veces** las preguntas solicitadas para un modelo. Si hay más de 3 modelos, aumenta al mínimo necesario para que *tampoco se repitan preguntas entre modelos*.
- Detección de enunciados idénticos y casi idénticos (normalización y semejanza textual). Si el modelo IA no genera suficientes preguntas originales, se cancela el guardado sin crear exámenes parciales. La equivalencia semántica profunda requiere comprobación docente.
- SQLite conserva todas las preguntas de reserva, asignaciones a modelos y metadatos. En Exámenes > **Banco**, exportación TXT del banco.
- Barra de cabecera HTML y, en **Windows 11**, petición al sistema de pintar el marco superior *nativo* en `#102B45` con texto blanco, sin eliminar botones de minimizar/maximizar/cerrar. En otras versiones Windows la barra nativa puede conservar el color del sistema.

## Compilación en Windows

1. Extraiga el paquete completamente.
2. Ejecute `crear_exe_windows.bat` para preparar Python/uv, ejecutar pruebas y generar `dist\EvaluaFP.exe`.
3. Si desea instalador convencional, ejecute `crear_instalador_windows.bat` (requiere Inno Setup; la versión portable no).

No distribuya la carpeta de fuentes ni la clave API. Al generar un banco grande se realizan múltiples peticiones a la API; espere mayor coste y duración. Revise manualmente rúbricas, respuestas correctas y dificultad antes de usar con alumnado.

## Comprobación

Ejecute `python -m unittest discover -s tests -v`. Esta compilación no se ha probado en Windows desde este entorno; pruebe el exe en un equipo real antes de distribuir.

---

## Historial y referencias de la versión 0.8

# EvalúaFP Local v0.8.0 — Icono, presentación y alta de alumnado

Esta versión conserva toda la funcionalidad de v0.7.1 y añade:

- Icono propio de EvalúaFP en el EXE Windows (PyInstaller `--icon`), instalador (Inno `SetupIconFile`), pestaña web (favicon) y cabecera de la aplicación.
- Presentación centrada al iniciar, mostrando nombre de la aplicación, versión y desarrollador **FRANCISCO JAVIER GONZALEZ ROLO**. Desaparece a los **10 segundos**, con opción de «Entrar ahora».
- Alta de alumnado desde la propia pantalla de subida individual.
- Detección previa de códigos de alumno desconocidos en importaciones masivas de ZIP, con alta simultánea y continuación de la misma importación tras confirmar los nombres.
- SQLite: altas de alumnado persistentes y auditadas. Las tablas existentes no se borran ni requieren migración.

## Instalación y actualización

Para usar el programa con ventana propia, extraiga el ZIP completo, entre en su carpeta y ejecute `crear_exe_windows.bat` desde Windows. Necesita conexión para la preparación inicial, no para el uso de SQLite. Una vez compilado el EXE, estará en `dist\EvaluaFP.exe`. El instalador opcional se crea con `crear_instalador_windows.bat` y requiere Inno Setup (la descarga no depende de winget en este proyecto).

**Si actualiza desde v0.7.1**, también puede aplicar el parche reducido a la carpeta que contiene el proyecto, reemplazar los archivos solicitados y ejecutar nuevamente `crear_exe_windows.bat` para integrar el icono y la presentación en el binario. El EXE anterior no se modifica automáticamente.

Los datos locales se mantienen en `%LOCALAPPDATA%\EvaluaFP` y no deben eliminarse al actualizar. Es conveniente realizar una copia de seguridad de `%LOCALAPPDATA%\EvaluaFP\datos` y `%LOCALAPPDATA%\EvaluaFP\almacen` antes de efectuar cambios.

## Registro de alumnado durante la importación

- **Una entrega:** vaya a Entregas escaneadas y pulse «+ Crear alumno» junto al selector. Escriba código y nombre y pulse «Guardar alumno». La pantalla recuperará el nuevo alumno seleccionado sin eliminar la cola de páginas que ya había preparado.
- **Lote ZIP:** mantenga el formato `CÓDIGO/001.jpg`, `CÓDIGO/002.jpg`… En caso de códigos desconocidos, el servidor responde con la lista sin importar nada. La interfaz solicita los nombres de todos ellos y, si confirma el alta, repite la carga utilizando el mismo ZIP. Si cancela, no se modificará el registro del alumnado ni las entregas.
- Se evita crear alumnos duplicados dentro de un mismo módulo. Si falla una entrada de un alta múltiple, la transacción SQLite no guardará ninguna del lote.

## Límites y verificación

Las pruebas automatizadas verifican la lógica de alta, la respuesta a los códigos ausentes, la importación masiva y los recursos de iconos y modal. El icono real del EXE y la ventana WebView2 deben comprobarse al generar el binario en Windows. Este ZIP contiene los fuentes y scripts, no un EXE precompilado.

---

# EvalúaFP Local 0.7.1 — Corrección del instalador de Windows

El problema de `winget` («Error al abrir los orígenes») se ha eliminado del proceso: **ya no se utiliza winget**.

## Crear el instalador

1. Extraiga este paquete en una carpeta nueva, o aplique el parche sobre el proyecto **0.7** ya extraído.
2. Ejecute `crear_instalador_windows.bat`.
3. Si `dist\EvaluaFP.exe` ya existe, está actualizado y supera `--selftest`, se reutiliza. Si no existe o está desactualizado, se compila de nuevo.
4. Si no encuentra Inno Setup 6 o 7, solicita permiso para descargar la versión **6.7.4** directamente de los orígenes oficiales. Comprueba que el archivo está firmado digitalmente por **Pyrsys B.V.** antes de ejecutarlo. Instala Inno Setup solamente para el usuario actual, sin modificar el PATH.
5. Compila `instalador\EvaluaFP.iss` y comprueba que aparece `dist\Instalar_EvaluaFP.exe`.

Si no puede descargar Inno Setup desde GitHub ni desde el servidor oficial, instálelo manualmente desde https://jrsoftware.org/inno-setup/downloads y ejecute de nuevo el BAT. Si ya lo instaló en una carpeta no estándar, puede indicar el compilador al lanzar el BAT desde una terminal usando `set "INNO_ISCC=C:\ruta\ISCC.exe"`.

**Registros:** `%LOCALAPPDATA%\EvaluaFP\logs\compilacion_inno.log`.

**Datos y seguridad:** el procedimiento no borra SQLite ni las carpetas de exámenes. El instalador se genera sin necesitar Python en el equipo de destino; para la ventana gráfica podría necesitarse Microsoft Edge WebView2 Runtime. El código del compilador solo se ha comprobado de forma estática en este entorno Linux; es necesaria una ejecución real en Windows para confirmar el instalador.

---

# EvalúaFP Local v0.7 — Aplicación de escritorio para Windows

## Cambio principal

`EvaluaFP.exe` ahora abre **una ventana propia**, con la interfaz HTML
integrada en **Microsoft Edge WebView2**. No abre Edge, Chrome ni otro
navegador externo. Si cierra la ventana, el servidor local se detiene.

La versión anterior abría el navegador por diseño: no era un error del
ordenador. Esta versión corrige el comportamiento predeterminado y agrega
`pywebview` a las dependencias y al empaquetado de PyInstaller.

### Crear un EXE nuevo (sin instalar Inno Setup)

1. Descomprima este proyecto completo en una carpeta nueva.
2. Ejecute **`crear_exe_windows.bat`** (NO `crear_instalador_windows.bat`).
3. El script reutilizará el gestor uv y Python 3.13 anteriores, instalará las
   dependencias que falten, ejecutará las pruebas y compilará `dist\EvaluaFP.exe`.
4. Abra ese archivo **nuevo**. No reutilice el `.exe` de la versión 0.6.1.

**Inno Setup no hace falta para generar o ejecutar el EXE.** Si también desea
un instalador, instale Inno Setup 6 desde https://jrsoftware.org/isinfo.php
y ejecute `crear_instalador_windows.bat`. Si falla Inno Setup, el EXE
portátil generado continúa disponible en `dist`.

### Alternativas

- `INICIAR_EVALUAFP.bat`: ejecuta la ventana de escritorio desde el código
  fuente, con una consola de desarrollo abierta.
- `iniciar_navegador_windows.bat`: abre la aplicación en el navegador solo si
  usted elige expresamente esta opción.
- `EvaluaFP.exe --browser`: modo navegador alternativo desde la consola.

### Dependencia gráfica de Windows

El programa necesita Microsoft **Edge WebView2 Runtime**. Windows 11
normalmente lo tiene instalado. Si no se puede crear la ventana, se
registrará el error y se mostrará una notificación con instrucciones. Se
puede instalar desde el sitio oficial de Microsoft:
https://developer.microsoft.com/microsoft-edge/webview2/

### Datos persistentes

La base de datos y los exámenes originales continúan en las rutas anteriores:
`%LOCALAPPDATA%\EvaluaFP\datos` y `%LOCALAPPDATA%\EvaluaFP\almacen`.
El proyecto v0.7 no borra ni migra estos datos. No copie un `.venv` o `dist`
anterior sobre el proyecto actualizado.

### Comprobación y limitaciones

Se han añadido cuatro pruebas del arranque como aplicación. La prueba
`--selftest` sigue verificando el empaquetado de la interfaz y SQLite,
**no garantiza** que el motor gráfico llegue a abrir una ventana.
La compilación PyInstaller y la apertura efectiva con WebView2 deben
verificarse en Windows. Esta versión continúa siendo un prototipo docente;
no utilizar con datos reales de alumnado ni para notas oficiales sin una
revisión de seguridad y cumplimiento normativo.

---

# EvaluaFP Local 0.6.1 — Correccion de validacion Python en PowerShell 5.1

**Esta revision corrige el bloqueo tras `uv venv`:** el instalador ya habia creado Python 3.13 y el entorno, pero el script anterior usaba `python -c` con comillas internas desde PowerShell 5.1. Ese paso podia fallar por la transmision de argumentos, provocando un falso error de Python incompatible. Ahora la comprobacion se ejecuta desde archivos `.py` independientes y registra cualquier error real.

## Instalacion recomendada

1. Extraer el ZIP completo a una carpeta nueva (se pueden conservar las versiones anteriores).
2. Ejecutar `crear_instalador_windows.bat` para compilar EXE e instalador, o `INICIAR_EVALUAFP.bat` para ejecutar sin compilar.
3. Se reutilizan `uv` y Python descargados previamente en `%LOCALAPPDATA%\EvaluaFP`. El nuevo entorno `.venv` se crea solo si no existe o si no supera la prueba.
4. El proceso no modifica ni borra la base de datos SQLite ni los originales de los examenes.
5. Si sigue fallando, ejecutar `DIAGNOSTICO_WINDOWS.bat` y revisar `%LOCALAPPDATA%\EvaluaFP\logs\preparacion_windows.log`.

**Limitacion:** los BAT y el instalador final todavia no se han probado sobre Windows en este entorno. Las pruebas automaticas realizadas en Linux no sustituyen esa verificacion. **La aplicacion sigue siendo un prototipo, no lista para calificar alumnado real.**

---

# Documentacion funcional heredada de la version 0.6

La correccion abandona la instalacion silenciosa de Python 3.14 que devolvia
exito sin permitir localizar el interprete. Utiliza `uv` x64, con version
fija y comprobacion de integridad, para disponer de Python 3.13 dentro del
espacio de EvaluaFP. Se conservan la biblioteca documental, los examenes,
los originales, las transcripciones, las rubricas y SQLite de la v0.5.

Lea `SOLUCION_ERROR_PYTHON.txt` si viene de las versiones anteriores.

**Aviso:** es un prototipo para pruebas; no utilizar con datos reales de
alumnado ni para calificaciones oficiales sin revision de seguridad,
proteccion de datos y cumplimiento normativo.

---

## 1. Funcionamiento previsto

1. **Programaciones:** registrar curso académico, ciclo, módulo y grupo; importar una programación en PDF, DOCX, TXT o Markdown; extraer texto y, si se desea, pedir a la IA que proponga los RA, CE y sus porcentajes. Los porcentajes ausentes se registran como `null` y no se inventan. El docente confirma y puede editar cada resultado, criterio y peso.
2. **Materiales de consulta (incorporado en v0.3):** tras subir la programación, asociar uno o varios documentos de apuntes, unidades, manuales o libros a la programación concreta (PDF, DOCX, TXT, MD). Cada original se conserva íntegro y se indexa por página de PDF o bloque lógico de DOCX/texto. Los materiales pueden activarse o desactivarse sin borrar sus originales.
3. **Generación fundamentada:** si existen materiales **activos** en el módulo, elija la programación concreta. Solo se usarán pasajes de sus materiales en la solicitud al proveedor. Cada pregunta debe citar un fragmento literal verificable y guardar documento, página/bloque y fragmento. Si una cita no existe, la solicitud falla **sin guardar el examen**. Esta trazabilidad ayuda a revisar el fundamento, pero no demuestra por sí sola que la pregunta esté libre de errores: el docente debe revisarla. Se solicita autorización explícita para transferir extractos a una API externa. El modelo no recibe los libros completos.
4. **Alumnado:** registrar por módulo el código y el nombre. Se recomienda utilizar códigos al importar conjuntos de documentos.
5. **Exámenes:** elegir CE individuales o marcar todos los de un RA, indicar modalidad (test, desarrollo o mixto), número de preguntas y puntuación. La asignación de puntos usa `peso RA × peso CE dentro del RA`, normalizado entre los criterios seleccionados. La IA devuelve enunciados, respuestas modelo y rúbricas; la aplicación verifica la estructura y los pesos antes de guardar. También puede crearse un examen manual sin API.
6. **Impresión:** desde el examen se abre una versión A4 imprimible, con los enunciados, espacio de respuesta y puntuación, sin revelar las soluciones ni la rúbrica.
7. **Recepción:** para un alumno, seleccionar a la vez o agregar sucesivamente PDF y/o imágenes PNG, JPEG, WEBP o BMP. Las entradas se guardan **en el orden confirmado**; cada PDF se despliega en páginas consecutivas. Puede cambiarse el orden con las flechas de la cola.
8. **Subida de varios alumnos:** archivo ZIP con una carpeta por código de alumno y archivos de cada carpeta con nombres ordenables (`001.jpg`, `002.jpg`, `003.pdf`). Los códigos deben existir previamente; la importación falla sin sobrescribir entregas previas.
9. **Archivo local:** cada documento original conserva sus bytes y una huella SHA-256; en otra carpeta se almacenan copias JPEG numeradas para la lectura y el visor.
10. **Visor:** al elegir una entrega se muestran miniaturas y la página seleccionada, ampliable, junto con los archivos originales descargables. Las preguntas muestran las páginas identificadas y enlazan con ellas.
11. **IA de manuscritos:** la transcripción se hace página por página, enviando la página anterior solo como contexto cuando existe. Se solicita expresamente al modelo que reconozca continuaciones sin repetir el número de pregunta y **no duplique** el texto de la hoja anterior. Se registran fragmentos por página, asignación a pregunta, dudas y textos sin asignar. La detección es probabilística y puede equivocarse.
12. **Corrección:** cada respuesta transcrita se presenta al modelo junto con el CE, rúbrica, respuesta modelo y puntos máximos. Devuelve propuesta de nota, evidencias, observaciones y señales de revisión. No se permite superar los puntos máximos. Una respuesta no identificada queda marcada para revisión.
13. **Supervisión humana:** el profesor puede corregir la transcripción y repetir la evaluación. Debe validar **cada pregunta**. Cuando cambia la puntuación propuesta por la IA, debe justificar la modificación. La nota definitiva solo aparece cuando todas las preguntas están validadas.
14. **Historial e informes:** SQLite conserva exámenes, preguntas, rúbricas, archivos, páginas, transcripciones, correcciones, validaciones y auditoría. Se imprime un informe justificativo por pregunta y se consultan las notas definitivas por examen y el desglose por RA/CE. El registro consolidado se puede exportar a CSV.
15. **Copias de seguridad:** botón en Ajustes para generar y descargar un ZIP con SQLite y todos los archivos originales y derivados. La clave API nunca se incluye en el ZIP.

## 2. Estructura del proyecto

```text
EvaluaFP_Local/
├── app.py                          Servidor local, API y rutas de impresión
├── database.py                     Base SQLite y tablas relacionadas
├── logic.py                        Importación, pesos, IA y corrección
├── materiales.py                   Biblioteca didáctica, indexado y citas verificables
├── ia.py                           OpenAI Chat Completions / compatible
├── web/
│   ├── index.html                  Interfaz
│   ├── style.css                   Estilos adaptativos
│   └── app.js                      Navegación, visor, formularios y CSV
├── tests/                          Pruebas automáticas sin llamadas reales
├── ejemplos/                       Ejemplo didáctico ficticio
├── instalador/EvaluaFP.iss         Instalador Inno Setup (Windows)
├── requirements.txt                Dependencias de ejecución
├── requirements-build.txt          Dependencias de compilación
├── scripts/preparar_entorno.ps1    Gestiona Python con uv y valida entorno
├── scripts/verificar_python.py     Comprueba Python 3.13 x64 y SQLite sin python -c
├── scripts/verificar_dependencias.py  Comprueba bibliotecas sin python -c
├── PREPARAR_ENTORNO.bat            Prepara y verifica dependencias automáticamente
├── INICIAR_EVALUAFP.bat            Inicio guiado: prepara y abre el navegador
├── iniciar_windows.bat             Acceso alternativo al inicio guiado
├── iniciar_navegador_windows.bat   Acceso alternativo al inicio guiado
├── crear_exe_windows.bat           Prepara, prueba y produce dist/EvaluaFP.exe
├── crear_instalador_windows.bat    Prepara, prueba y produce dist/Instalar_EvaluaFP.exe
└── README.md
```

## 3. Inicio y compilacion en Windows (v0.6)

La version 0.6 **no emplea el instalador tradicional de Python** que fallo
en las versiones 0.4 y 0.5. Descarga el gestor de entornos `uv` 0.13.7 para
Windows x64, comprueba la huella SHA-256 fija del archivo y usa sus versiones
gestionadas de Python. No modifica Python global, ni `PATH`, ni registro.

**Para ejecutar:** extraer todo el ZIP en una carpeta nueva y abrir
`INICIAR_EVALUAFP.bat`. La primera ejecucion necesita Internet para descargar
el gestor, Python 3.13 y las bibliotecas. Una vez preparado, abre la interfaz
en el navegador. Mantenga la terminal abierta mientras utiliza la aplicacion.

**Para crear un instalador:** ejecute directamente
`crear_instalador_windows.bat`. Por orden:

1. Descarga y valida `uv` x64, si no existe.
2. Instala Python 3.13 x64 gestionado en `%LOCALAPPDATA%\EvaluaFP\python-gestionado`.
3. Crea `.venv` en la carpeta del proyecto y comprueba el interprete.
4. Instala requisitos de la aplicacion y PyInstaller; comprueba conflictos.
5. Ejecuta las pruebas y compila `dist\EvaluaFP.exe`.
6. Ejecuta `dist\EvaluaFP.exe --selftest`.
7. Localiza o instala Inno Setup 6, y genera `dist\Instalar_EvaluaFP.exe`.

Para crear solo el ejecutable, abra `crear_exe_windows.bat`.

**Si vuelve a fallar**, abra `DIAGNOSTICO_WINDOWS.bat`, que guarda el
registro en `%LOCALAPPDATA%\EvaluaFP\logs\diagnostico_v06.txt`.
El archivo `preparacion_windows.log` conserva la salida completa de las
operaciones. La causa podria ser la conectividad a GitHub, las descargas
de Python gestionado o PyPI, restricciones del antivirus o permisos.
No desactive las defensas del equipo para eludir el error.

**Datos y originales:** se conservan en `%LOCALAPPDATA%\EvaluaFP\datos` y
`%LOCALAPPDATA%\EvaluaFP\almacen`. No borre esas carpetas. La version
0.6 mantiene el esquema SQLite de la 0.5. No traslade `.venv` ni `dist`
desde versiones anteriores.

**Limitacion de validacion:** las pruebas de codigo y las comprobaciones
estaticas del preparador se ejecutan en este entorno; los BAT de Windows,
la descarga x64 de uv, la construccion PyInstaller en Windows y el
instalador de Inno Setup deben verificarse en un ordenador Windows real.
No se ha incluido un `.exe` compilado en el ZIP.

## 5. Almacenamiento local y SQLite

En Windows:

```text
%LOCALAPPDATA%\EvaluaFP\
├── datos\
│   └── evaluafp.sqlite3
├── almacen\
│   ├── programaciones\
│   ├── materiales\
│   │   └── MODULO\PROGRAMACION\...\
│   └── 2026-2027\
│       └── Nombre_del_modulo_ID\
│           └── Titulo_del_examen_ID\
│               └── CODIGO_ALUMNO_ID\
│                   ├── originales\
│                   │   ├── 001_examen.pdf
│                   │   └── 002_foto.jpg
│                   └── paginas\
│                       ├── pagina_0001.jpg
│                       ├── pagina_0002.jpg
│                       └── pagina_0003.jpg
└── copias\
    └── copia_evaluafp_AAAAMMDD_HHMMSS.zip
```

La ruta se puede cambiar configurando la variable de entorno `EVALUAFP_DATA_DIR` **antes de iniciar la aplicación**. La estructura de archivos es externa al ejecutable. La aplicación activa claves foráneas en SQLite y modo WAL. Evite almacenar la base en una carpeta sincronizada en tiempo real por varios procesos de manera concurrente; para este prototipo se recomienda **un único usuario y un único proceso**.

Las tablas principales son `modules`, `programmings`, `outcomes`, `criteria`, `students`, `exams`, `exam_questions`, `submissions`, `source_files`, `pages`, `transcription_runs`, `page_segments`, `corrections`, `audit_log` y `preferences`.

**No se cifra automáticamente la base SQLite ni el repositorio de exámenes.** Para datos personales reales deben usarse controles del equipo, perfil y disco cifrado (por ejemplo, BitLocker si está disponible y autorizado), bloqueos de sesión, permisos de acceso, copias protegidas, retención definida y políticas del centro. El servidor usa una sesión local aleatoria y no se expone a la red de manera predeterminada; esto no sustituye una auditoría de seguridad.

## 6. Proveedores de IA

La versión inicial utiliza **Chat Completions** (`POST /v1/chat/completions`), por su amplia compatibilidad. Admite imágenes con URL `data:image/jpeg;base64,...` para el modelo de visión. Las respuestas se solicitan en JSON; si un proveedor rechaza la opción `response_format`, la aplicación reintenta sin ella y después valida la estructura obtenida.

Ajustes configurables:

| Campo | Ejemplo |
|---|---|
| Proveedor | OpenAI |
| URL de API | `https://api.openai.com/v1` |
| Modelo para programación | Un modelo con capacidad de texto |
| Modelo para crear preguntas | Un modelo con capacidad de texto |
| Modelo para transcripción | **Modelo con visión** |
| Modelo para corregir | Modelo con capacidad de texto y seguimiento de rúbricas |
| Clave | La del proveedor; en APIs locales puede no ser necesaria |

Puede utilizar servicios compatibles que expongan la misma estructura, por ejemplo `http://127.0.0.1:11434/v1` para un servidor local adecuado. **Ser compatible en HTTP no garantiza que el modelo admita imágenes, respuestas estructuradas o lectura fiable de manuscritos.** La aplicación muestra los errores de la API sin inventar resultados. Algunos modelos requieren nombres o parámetros distintos, por lo que es necesario probar el proveedor elegido.

La clave se intenta almacenar en el gestor de credenciales del sistema mediante `keyring`; si no está disponible, la clave vive solo en memoria en la sesión. No se almacena como texto plano ni en SQLite.

**Costes:** un examen de muchas páginas implica varias llamadas de visión (una por página, con la anterior como contexto) y llamadas de corrección (una por pregunta). Revise tarifas, límites y políticas de retención del proveedor. El sistema no almacena un cálculo presupuestario de tokens en esta versión.

## 7. Cargas individuales y masivas

### Entrega individual ordenada

Puede introducir una sucesión como `001.pdf`, `002.jpg`, `003.jpg`, en el orden exacto en que debe leerse. Si `001.pdf` contiene dos páginas, el visor presentará las páginas 1 y 2 procedentes de ese PDF, después la página 3 (`002.jpg`) y la 4 (`003.jpg`). La conservación del orden no depende de que la IA interprete correctamente la numeración manuscrita.

### ZIP de varios alumnos

```text
lote_examenes.zip
├── ALU001/
│   ├── 001.jpg
│   ├── 002.jpg
│   └── 003.pdf
├── ALU002/
│   └── 001.pdf
└── ALU003/
    ├── 001.jpg
    ├── 002.jpg
    └── 003.jpg
```

Cada código debe coincidir exactamente con uno ya registrado en el módulo. Los archivos internos se ordenan de forma natural por nombre. No se sobrescribe una entrega anterior del mismo examen y alumno. Límites actuales: 80 MB por archivo, 240 MB por entrega y 250 páginas; los ZIP admiten hasta 1.200 ficheros y 500 MB de datos descomprimidos. Estos límites son preventivos y pueden ajustarse en el código para un entorno más potente, después de evaluar memoria y rendimiento.

## 8. Criterios de puntuación

- Las ponderaciones deben proceder de la programación y ser **confirmadas por el docente**. Si falta un peso de RA o CE, la generación automática se detiene con un mensaje de error.
- Los puntos del examen se distribuyen en proporción a los pesos efectivos `RA (%) × CE (%) / 100` de los **criterios seleccionados**. Una ponderación de un CE no se considera directamente equivalente al porcentaje global del módulo.
- Cada criterio seleccionado recibe al menos una pregunta; después se reparten las restantes en proporción a los pesos. Las pequeñas diferencias de redondeo se ajustan para mantener la suma exacta del examen.
- La rúbrica de desarrollo muestra indicadores y porcentaje interno de cada indicador. La IA propone una nota por pregunta y evidencias; la calificación oficial corresponde siempre a la validación docente.
- El registro por RA/CE refleja lo observado en los exámenes corregidos. **No automatiza todavía las reglas completas de evaluación trimestral, recuperación, mínimos, ponderaciones por instrumento ni el cálculo de la calificación final del módulo**; esas reglas pueden ser distintas entre programaciones y deberán incorporarse antes de su uso oficial.

## 9. Seguridad, protección de datos y Reglamento europeo de IA

La evaluación del aprendizaje mediante IA en centros educativos y de Formación Profesional figura en el **anexo III del Reglamento (UE) 2024/1689** como ámbito de alto riesgo, sujeto al análisis de clasificación y a las obligaciones que correspondan. Además, el RGPD exige analizar las decisiones automatizadas, las transferencias de datos y las medidas técnicas y organizativas del tratamiento. Mantener la calificación final en manos del docente es una medida útil, **pero no basta por sí sola** para acreditar conformidad normativa.

Para un despliegue real deben determinarse, con la dirección del centro y su delegado de protección de datos, al menos la base jurídica y finalidad, la elección del proveedor y su contrato, transferencias internacionales si existen, minimización y conservación de datos, evaluación de impacto cuando proceda, controles de acceso, cifrado, información al alumnado, pruebas de sesgo/error y revisión humana efectiva. La utilización de nombres reales y fotografías identificables exige precaución adicional.

Referencias:

- Reglamento (UE) 2024/1689 (IA): https://eur-lex.europa.eu/legal-content/ES/TXT/?uri=CELEX:32024R1689
- AEPD, derecho a no ser objeto de decisiones individuales automatizadas: https://www.aepd.es/derechos-y-deberes/conoce-tus-derechos/derecho-no-ser-objeto-de-decisiones-individuales
- AEPD, medidas de seguridad: https://www.aepd.es/derechos-y-deberes/cumple-tus-deberes/medidas-de-cumplimiento/seguridad-de-los-tratamientos
- OpenAI, imágenes y visión: https://developers.openai.com/api/docs/guides/images-vision?api-mode=chat

## 10. Limitaciones identificadas y siguientes desarrollos

- Revisión manual de porcentajes y transcripciones; ningún OCR manuscrito es infalible. La continuidad entre páginas se **intenta detectar**, pero no se garantiza para todas las caligrafías o formatos.
- Tanto la programación como los materiales PDF necesitan texto extraíble. Los libros digitalizados sin capa de texto se rechazan con una advertencia: aplique OCR previamente (esta versión todavía no incorpora OCR de materiales). DOCX, TXT y Markdown se leen directamente. Para DOCX y TXT no se inventa numeración de páginas, sino bloques consecutivos.
- La versión inicial no incorpora roles, autenticación multiusuario, segregación de grupos, gestión de derechos de acceso por centro ni una política automática de eliminación. Se diseñó para un **único docente en un único equipo**.
- No hay sincronización Moodle, LTI, nube ni aplicación móvil independiente. El navegador móvil puede seleccionar o fotografiar archivos **solo cuando la interfaz se ejecute en el dispositivo correspondiente**; el servidor local del prototipo no se expone a la red y no permite acceder desde otro dispositivo de forma directa. Para hacer fotos con un móvil y enviarlas al ordenador se deben transferir previamente al equipo, o desarrollar más adelante una pasarela local segura.
- La generación IA puede fallar si el modelo elegido devuelve preguntas ambiguas, JSON incorrecto o una referencia documental inventada; se detiene antes de almacenar un examen inconsistente. El recuperador usa coincidencias léxicas locales, por lo que determinados conceptos expresados con sinónimos pueden requerir revisar o dividir los documentos.
- El modelo de rúbrica no incluye todavía penalizaciones por error en test, reglas complejas de recuperación, evaluación agregada por periodos o exportación a formatos oficiales del centro. Son extensiones previstas.
- SQLite incorpora ahora migración no destructiva de las columnas de fuentes didácticas. Se ha probado la actualización desde v0.2 en una base de prueba; sigue siendo recomendable crear una copia de seguridad antes de actualizar.
- Este proyecto **no ha pasado pruebas de aceptación en equipos Windows ni evaluaciones de exactitud con manuscritos reales**; sí dispone de pruebas automáticas de sus componentes locales y un recorrido funcional simulado.

## 11. Pruebas técnicas

Desde la carpeta del proyecto:

```bat
python -m unittest discover -s tests -v
```

Las 7 pruebas automatizadas no requieren clave de IA: sustituyen las llamadas externas por respuestas simuladas. Verifican cálculos de ponderación, persistencia de originales, importación PDF multipágina, asignación de una continuación entre dos páginas, transcripción, corrección, registro, API local, informe, validación y revisión de puntuaciones. Añaden la incorporación de material a una programación, la obligación de aceptar el envío de pasajes al proveedor, la vinculación de citas y el rechazo de citas inventadas o PDF sin texto extraíble.

**Recomendación operativa:** comenzar con programaciones y exámenes ficticios de un módulo, comprobar el contenido de los pesos, generar un examen breve y escanear 2–3 páginas de prueba. Solo después de superar verificaciones y autorizaciones corresponde plantear un piloto con datos reales.


## 12. Ejemplo de uso de materiales (versión 0.3)

1. En **Programaciones y CE**, cree un módulo y suba su programación.
2. En el apartado **Material didáctico asociado a la programación**, seleccione la programación correspondiente y suba, por ejemplo, `Tema_01_Tecnica_Contable.pdf` y `Apuntes_IGIC.docx`. Puede seleccionar ambos a la vez.
3. Compruebe que figuran en la biblioteca documental como **Activos**, con número de páginas/bloques y pasajes extraídos. Si necesita excluir temporalmente uno, pulse **Desactivar**.
4. Revise los RA, CE y ponderaciones de la programación (sin pesos explícitos no puede generarse el examen automáticamente).
5. En **Exámenes y rúbricas**, elija la programación, los CE y el número de preguntas. La interfaz indicará que hay **generación fundamentada**.
6. Confirme expresamente el envío de extractos al proveedor de IA, compruebe la pregunta, solución, rúbrica y la fuente de cada pregunta. Puede abrir el original para verificar el contexto completo.

**Precaución sobre materiales sujetos a derechos de autor:** la existencia de un libro en formato digital no supone automáticamente permiso para transmitir extractos de su contenido a servicios de terceros. Antes de utilizar una API externa, verifique licencias, autorizaciones y normas de su centro.


## Actualización 1.0.1 — Exportar evaluación a Excel y Additio

En **Evaluación del módulo → Resultados** hay seis descargas nuevas:

- **Excel (.xlsx)**: informe completo del módulo con resumen, alumnado, notas por RA/CE/instrumento, evidencias y advertencias de ponderación.
- **Excel clásico (.xls)**: libro nativo BIFF8 (requiere la biblioteca `xlwt`, instalada por el preparador).
- **Additio grupo Excel (.xlsx)**: hoja única con código, nombre y apellidos para importar el grupo desde Excel, asignando campos en el asistente de Additio.
- **Additio grupo CSV**: código, nombre y apellidos. Si el nombre se almacena como «Apellidos, Nombre», se separa; en otro caso se conserva íntegro para evitar atribuciones incorrectas. Revise las columnas en el asistente de Additio.
- **Additio notas CSV**: matriz por alumno y columnas de notas, preparada para comparar o adaptar antes de importar.
- **Additio pegar TSV**: matriz delimitada por tabuladores para copiar valores a un grupo de Additio cuyo orden de alumnado y columnas se haya comprobado.

**No existe un formato universal confirmado para importar directamente el cuaderno completo de notas de Additio.** La importación de alumnado desde Excel sí está documentada por Additio; las columnas de calificaciones deben verificarse y, cuando proceda, copiarse/pegarse. EvalúaFP no publica notas provisionales como finales: el campo final queda en blanco si no hay cierre docente vigente. No se duplican ponderaciones RA/CE.

**Error WinError 32:** las conexiones SQLite se cierran explícitamente durante la migración de carpetas; hay una prueba de regresión para Windows. La prueba automática se ejecuta antes de intentar compilar el EXE.

**Recompilación:** extraiga todos los archivos y ejecute `crear_exe_windows.bat` o `CREAR_VERSION_PENDRIVE.bat`. El preparador instalará las dos nuevas dependencias. Este ZIP contiene el proyecto, no un EXE ya compilado.
