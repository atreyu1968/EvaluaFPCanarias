# EvalúaFP 1.2.10 beta — Biblioteca de calendarios generales de FP

## Objetivo
Reducir la transcripción repetida de fechas de un mismo calendario escolar general en centros de la misma comunidad autónoma o ámbito educativo y **del mismo curso académico**, sin mezclar festivos locales, insulares o decisiones de la PGA.

## Cambios incorporados
1. Nueva biblioteca SQLite `national_general_fp_calendars` con revisiones inmutables, por código territorial y curso académico, para la etapa `fp_grado_d`. Cada revisión almacena fecha de revisión, disposición, correcciones, SHA-256 y origen de revisión docente.
2. El registro se realiza exclusivamente desde un borrador guardado y confirmado, tras **una segunda confirmación expresa** de que las fechas son generales. No se aceptan fechas arbitrarias enviadas por separado a la API.
3. Se conservan únicamente fecha de inicio y fin de las clases generales, periodos vacacionales, días generales y procedencia normativa. **No se almacenan** nombre del centro, municipio, isla, sesiones de evaluación, horas del módulo, FEOE ni días añadidos por el centro.
4. Bloqueo de festividades insulares de Canarias que constan en el catálogo como no comunes a todas las islas, si aparecen entre los días «generales». Para otros territorios y supuestos debe comprobarlo el docente.
5. Comparador de revisiones y comprobación del ámbito. Un calendario de otra comunidad o curso no puede consultarse como si fuera el seleccionado.
6. Desde «Preparar módulo → Temporalización», el docente puede cargar una revisión compartida como **borrador sin confirmar**, manteniendo municipio, isla, días adicionales, evaluación, horas, unidades, FEOE, RA/CE y notas. Debe revisar de nuevo las fiestas locales y la PGA.
7. Nueva API autenticada: GET `/api/national/general-calendar`, GET `/api/national/general-calendar/compare` y POST `/api/national/general-calendar/save`.
8. Se actualiza la identificación interna a `1.2.10-beta` y el script de compilación Windows añade explícitamente los módulos de calendarios a PyInstaller.

## Seguridad y limitaciones
- «Revisado por un docente» **no significa «norma certificada»**. La aplicación no comprueba automáticamente el BOE o boletín autonómico en cada consulta.
- No se incorporan automáticamente los 19 calendarios escolares oficiales de España ni se transfieren fechas entre cursos diferentes.
- Para reutilizar los datos generales hay que comprobar las modificaciones posteriores, festivos municipales, fiestas insulares, calendario concreto de FP y posibles adaptaciones de la formación dual.
- No se sobrescriben las revisiones archivadas; una ficha idéntica no crea una nueva versión.
- Al restaurar una ficha general se elimina el identificador del perfil escolar por defecto y se exige una nueva confirmación.
- Es una beta en código fuente. La compilación y apertura de los ejecutables en equipos de usuarios todavía requieren pruebas.

## Comprobaciones
Pruebas de conservación de revisión, idempotencia, aislamiento territorial y por curso, restricciones de fuente y fechas, festivos insulares y API HTTP autenticada. El flujo de GitHub Actions comprueba Python en Windows y la sintaxis de `web/app.js`.