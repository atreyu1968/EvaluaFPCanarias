# Calendarios en anexos y asistencia IA — guía 1.2.9 beta

## Lectura local sin IA

En **Preparar módulo → Temporalización y FEOE**, use «Leer calendario escolar desde PDF, Word o texto». Aporte un documento con fuente y curso contrastables; el lector acepta PDF, DOCX, TXT y MD hasta 15 MB. La extracción es local y no envía los archivos a Internet. Las tablas con encabezados *Etapa*, *Inicio de clases* y *Fin de clases* se interpretan exclusivamente si la fila identifica Formación Profesional sin mezclar otra etapa.

En PDF se analizan hasta 80 páginas. El OCR, si se activa y está instalado Tesseract con español, se limita a 8 páginas con poco texto seleccionable. Las fechas repartidas en líneas sucesivas solo se reconstruyen cuando el contexto y el salto de línea permiten una asociación inequívoca dentro de la misma página. Las propuestas se acompañan de cabeceras, filas y referencias de página.

## Preparar y revisar un fragmento para IA

Cuando el lector haya reconocido conjuntamente comunidad, curso y FP, pulse «Preparar fragmento del documento para revisarlo con IA (sin enviarlo)». Esta operación copia a un campo editable un extracto local; **no se comunica con la API de IA**.

Compruebe el fragmento: debe contener la comunidad autónoma, el año académico y la referencia a FP, además de las fechas y sus cabeceras. Quite nombres personales, datos de estudiantes o contenido no necesario. A continuación marque la casilla de autorización y pulse «Interpretar fragmento con IA y verificar sus citas». Aparecerá una segunda confirmación antes del envío externo.

Un ejemplo tabular adecuado:

```text
Canarias, calendario escolar Formación Profesional, curso 2026-2027.
Etapa | Inicio de clases | Fin de clases
FP Grado D | 16/09/2026 | 22/06/2027
```

**Importante:** los valores del ejemplo son ilustrativos de cómo redactar una cita; el docente debe utilizar exclusivamente la resolución oficial que corresponda a su centro, curso, territorio y régimen de FP.

## Criterios de seguridad de la IA

El servidor verifica que la cita propuesta aparezca en el fragmento original y que las fechas completas figuren en esa cita. Si dos columnas contienen fechas, se comprueba el orden de *Inicio* y *Fin* contra la cabecera citada. Si el texto contiene otra etapa, no se traslada a FP. Las propuestas con citas inexistentes, fechas contradictorias o ámbitos incompatibles se eliminan.

El modelo no modifica SQLite. Las propuestas se muestran en una vista previa y el docente decide cuáles cargar. Cualquier carga requiere confirmar de nuevo el calendario; no altera los RA, los CE, las ponderaciones, las notas ni la FEOE.

## Límites y cobertura territorial

- No se deducen años omitidos ni se completan automáticamente festivos nacionales o locales.
- No se verifica la autenticidad, la última corrección o la vigencia jurídica de un boletín.
- Los documentos escaneados de baja calidad y las tablas complejas pueden requerir cotejo manual.
- Los enlaces territoriales disponibles para las 17 comunidades autónomas, Ceuta y Melilla no suponen disponer de todas sus fechas oficiales verificadas.
- Los extractos se transmiten al proveedor IA **solo tras autorización**, de acuerdo con la configuración y política de dicho proveedor.
- Código fuente beta pendiente de pruebas funcionales con una colección amplia de calendarios oficiales y de compilación nativa.

## API

`POST /api/national/calendar-ai-interpret` (JSON, autenticación local requerida) recibe `module_id`, `region`, `academic_year`, `fragment` y `authorize_ai: true`. La respuesta es una vista previa compatible con la lectura documental, con `candidates`, `warnings`, `scope_ok`, `evidence_check` y `no_changes_saved: true`. El texto no se guarda.

La lectura documental previa `POST /api/national/calendar-document-preview` añade `suggested_ai_fragment` para copiarlo de manera local.