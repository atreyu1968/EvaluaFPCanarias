# EvalúaFP 1.1.2-beta — Informe de auditoría de navegación y asistente

**Fecha:** 19 de noviembre de 2026  
**Versión revisada:** 1.1.1-beta; correcciones integradas en la versión de código fuente 1.1.2-beta.  
**Ámbito:** rutas de interfaz, controladores de eventos, comunicación HTTP con la API local, asistentes de programación y errores silenciosos.

## Alcance y metodología

Se revisaron `web/app.js`, `web/index.html` y sus endpoints principales en `app.py`; se compararon las acciones HTML con sus controladores; se ejecutaron las pruebas automáticas `unittest` y varios recorridos de interfaz en Chromium con API simulada. Se reprodujeron respuestas de error, navegación concurrente y operaciones sobre unidades didácticas. Las pruebas contra una API real existentes en la suite utilizan bases SQLite aisladas.

El entorno de navegador deniega la conexión HTTP de Chromium a `127.0.0.1` mediante una política administrativa. Para evitar dar por validadas rutas no comprobadas, los recorridos de interfaz se hicieron con Chromium renderizando el HTML y el JavaScript reales, sustituyendo las respuestas de `fetch()` por respuestas simuladas; las rutas HTTP reales se cubrieron mediante las pruebas Python existentes.

## Incidencias encontradas y corregidas

| Código | Severidad | Incidencia en 1.1.1 | Solución 1.1.2 | Estado |
|---|---|---|---|---|
| NAV-01 | Alta | Una consulta HTTP que no responde podía dejar la pantalla en «Cargando…» sin fin. | `AbortController` con tiempos límite (20 segundos GET; 180 segundos POST) y mensaje claro. | Corregida |
| NAV-02 | Alta | Una respuesta tardía de una pantalla antigua podía sobrescribir otra recién seleccionada. | Cancelación de consultas GET obsoletas y número de revisión por navegación. | Corregida |
| NAV-03 | Media | Los errores en controladores `click` y `change` asíncronos podían quedar solo en la consola. | Captura global en esos controladores y aviso visible al docente. | Corregida |
| NAV-04 | Media | Un fallo al abrir pantalla no ofrecía una recuperación guiada. | Pantalla de error con botón «Reintentar» y enlace «Volver al inicio». | Corregida |
| NAV-05 | Media | Si se eliminaba una unidad intermedia, añadir otra podía repetir su código y bloquear el guardado. | Generador que busca el primer código `UDxx` libre. | Corregida |
| NAV-06 | Baja | Activar/desactivar un material leía el atributo desde el elemento pulsado, que podía ser un hijo. | El estado se consulta desde el botón `data-action` encontrado por `closest()`. | Corregida |

## Pruebas ejecutadas

- **92 pruebas Python**, todas satisfactorias: las 86 anteriores y 6 nuevas pruebas de regresión.
- Verificación sintáctica de JavaScript (`node --check`) y Python (`compileall`).
- Chromium controlado: navegación por las ocho secciones, creación de módulo, selección de las tres vías de preparación y recorrido de los seis pasos del asistente. Sin excepciones JavaScript no controladas.
- Chromium controlado, casos extremos: error HTTP y reintento; consulta anterior pendiente y cancelación al navegar; eliminar una unidad intermedia y añadir otra sin códigos repetidos.
- Comprobación estática de que todos los `data-action` literales de la interfaz tienen rama de atención y todas las secciones del menú están en el controlador principal.

## Limitaciones y pruebas pendientes

- Estas verificaciones **no prueban que nunca pueda surgir un bloqueo** bajo cualquier condición o proveedor de IA.
- No se han probado visualmente los ejecutables nuevos en Windows, Linux, macOS Intel ni macOS Apple Silicon. Los binarios antiguos 1.0.6/1.1.1 no incluyen los cambios.
- La latencia y los errores reales de proveedores externos de IA, la consulta del BOE y los archivos grandes dependen de red, permisos y equipos reales.
- Es recomendable reproducir las funciones con una programación de prueba y datos ficticios, sin remitir datos del alumnado a servicios externos, antes de la distribución.

## Instalación

Para desarrollar o recompilar EvalúaFP, **hacer antes una copia de seguridad del directorio de datos SQLite**. Sobre las fuentes completas 1.1.1 aplica el ZIP del parche manteniendo estructura; alternativamente extrae el ZIP completo 1.1.2. Ejecuta las pruebas automáticas y compila de nuevo en cada plataforma. No basta con sustituir el HTML de la landing promocional.
