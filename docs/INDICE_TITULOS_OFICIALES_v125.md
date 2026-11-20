# Buscador nacional de títulos TodoFP — Guía técnica 1.2.5

## Diseño

`official_title_index.py` utiliza la capa restringida `todofp_discovery.fetch_todofp` de la versión anterior, con límites de tiempo, tamaño y redirecciones. Consulta **un índice oficial** entre cuatro listados por grado. La función `parse_index()` extrae únicamente los vínculos a fichas de título bajo:

`https://www.todofp.es/que-estudiar/familias-profesionales/<familia>/<titulo>.html`

No acepta enlaces de sitios externos, `javascript:`, rutas de navegación, currículos sueltos, fichas LOGSE sin vigencia o resultados repetidos. La denominación del ciclo se conserva literalmente y sin deducir códigos; el grado es el del índice consultado.

## API

`POST /api/national/todofp/search-titles`

Campos JSON: `grade` (`Básico`, `Medio`, `Superior`, `Especialización`), `query` (hasta 120 caracteres), `region` (17 CCAA + Ceuta + Melilla) y `academic_year` (`AAAA-AAAA`).

La respuesta indica cantidad de resultados, grado, título, URL, fuente, región y curso **como contexto de consulta**; no atribuye vigencia territorial. Con `POST /api/national/todofp/explore` se abre la ficha individual y, cuando exista, el listado de currículos autonómicos.

## Precauciones

- **Dato estatal localizado ≠ currículo autonómico confirmado.** La búsqueda no fija horas semanales/anuales ni aprobación del título por la comunidad.
- Los enlaces oficiales no suponen vigencia; las disposiciones y sus modificaciones deben contrastarse antes de aprobar una programación.
- La página de un índice puede incluir denominaciones con variaciones de formato o títulos que no encajen en el patrón de extracción. En ese caso se conserva el enlace manual.
- La interfaz invalida búsquedas si cambia comunidad, curso o módulo. Las referencias no modifican RA, CE, ponderaciones ni evaluaciones cerradas.
- No se implementa un rastreo exhaustivo de webs autonómicas ni un servicio de actualización continua en esta versión.

## Pruebas y despliegue

Ejecutar desde la raíz: `python -m unittest discover -s tests -q` y `node --check web/app.js`. La interfaz ha sido comprobada en Chromium con respuestas de prueba. Verificar en un equipo conectado el acceso real a los cuatro índices de TodoFP antes de distribuir nuevos ejecutables.
