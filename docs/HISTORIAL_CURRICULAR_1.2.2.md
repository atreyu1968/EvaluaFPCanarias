# Historial curricular — especificación técnica 1.2.2

## Tabla y clave de ámbito

`curriculum_source_snapshots` almacena referencias documentales con las claves `module_id`, `territory_code`, `academic_year`, `module_code` y `document_sha256`, preservando el título, URL HTTPS de la disposición, fecha de registro, nombre original del archivo y dos hashes SHA-256: documento y contenido normalizado de RA/CE. Cada módulo y curso admite hasta 50 versiones documentales.

El catálogo local de consulta se construye a partir de las referencias disponibles en esta instalación, **sin datos de alumnado**, y se filtra estrictamente por territorio y curso. No contiene por defecto el catálogo nacional completo de títulos y módulos.

## Validación de una fuente

Se acepta una versión únicamente si:

- El docente marca expresamente que ha verificado el documento y su procedencia.
- El archivo es PDF, DOCX, TXT o MD de hasta 15 MB y está identificado como disposición curricular oficial.
- El módulo tiene un código oficial de cuatro cifras registrado en la programación.
- Nombre y código coinciden en el documento y el bloque curricular correspondiente.
- Se han localizado RA y CE con numeración, enunciados completos y estructura coherente.
- La fuente tiene URL pública HTTPS y título identificable.
- El documento original se vuelve a extraer en el **servidor**: un JSON manipulado por el navegador no se considera prueba documental.

La confirmación del profesor no es una certificación automática de vigencia. El enlace sirve como procedencia que debe revisarse y no se solicita a la red en el proceso de archivado.

## Comparación

Los RA se alinean por `RA1`, `RA2`, etc., y los criterios por `RA1.a`, `RA1.b`, etc. Se comprueba si cada código fue añadido, eliminado o tuvo cambios en el texto. Las variaciones de blancos y mayúsculas/minúsculas no se consideran cambios. La localización en el documento permanece accesible en la previsualización, pero no forma parte de la identidad semántica utilizada para comparar versiones.

## Aislamiento e integridad

Las consultas al historial excluyen registros de otro módulo, otra comunidad, otro curso o un código oficial diferente. Los registros de calificaciones, ponderaciones, evaluaciones e instrumentos no se leen ni escriben durante el archivado de fuentes. La migración de SQLite es aditiva e idempotente. Al duplicar exactamente el documento, la API devuelve el identificador existente sin crear una nueva versión.

## Futuro

Para completar la cobertura estatal se necesita conectar de forma supervisada el catálogo oficial de TodoFP y las fuentes curriculares de cada administración educativa, incorporar las normas de desarrollo autonómicas por curso y verificar los calendarios mediante las resoluciones de cada comunidad y centro. El historial creado ahora proporcionará la base de comparación, sin anticipar una homologación automática.
