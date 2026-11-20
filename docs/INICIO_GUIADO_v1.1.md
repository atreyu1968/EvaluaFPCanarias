# EvalúaFP 1.1.0-beta — Guía del asistente de programación y experiencia docente

**Ámbito:** Windows, Linux y macOS. Los datos se conservan en la base SQLite local del equipo o dispositivo USB; esta beta se distribuye como **código fuente**, no como aplicaciones portátiles ya compiladas.

## Qué cambia

El inicio presenta cuatro tareas comprensibles: preparar un módulo, crear un examen, cargar trabajos y consultar la evaluación. El menú separa las funciones de uso frecuente de la edición avanzada de RA/CE, ponderaciones y configuración de la IA. La presentación obligatoria de diez segundos desaparece. Crear un examen mediante IA tiene un formulario sencillo; se conservan los ajustes detallados en un bloque desplegable.

## Preparar el módulo: tres alternativas

1. **Ya tengo una programación.** Elija un módulo, suba PDF/DOCX/TXT/Markdown y conserve su original. Para analizar su texto con la API de IA, autorice expresamente la transferencia. Examine los RA y CE propuestos en campos normales, corríjalos y confirme personalmente antes de guardarlos. Los PDF escaneados sin texto requieren OCR previo.
2. **Crear mi programación.** Incorpore previamente RA/CE desde su documento, desde la normativa del BOE o por introducción manual. Revise la correspondencia con el módulo y la normativa autonómica. Cumplimente por pasos identificación, marco normativo, objetivos, metodología, evaluación, unidades, tratamiento de empresa y observaciones. Descargue el **borrador** en DOCX, PDF o Markdown.
3. **Solo configurar la evaluación.** Utilice el mismo asistente con menos requisitos documentales. Los RA y CE confirmados son imprescindibles para evaluar; no se exige redactar una programación completa para usar el cuaderno de evaluación.

## Validación y limitaciones

La comprobación automática advierte si faltan RA o CE, hay RA sin CE, porcentajes inconsistentes, falta cobertura de CE en las unidades o la formación en empresa está sin describir. No acredita la vigencia normativa ni sustituye la comprobación docente. Los porcentajes existentes se muestran, **no se corrigen automáticamente desde este asistente**. Los borradores jamás se consideran oficialmente aprobados. Un documento exportado incluye la leyenda «BORRADOR».

Esta beta es un editor guiado con exportación, **no un generador autónomo de programaciones oficiales completas mediante IA**. Los apartados narrativos y el reparto de las unidades requieren decisiones y datos introducidos por el docente. Las propuestas de extracción curricular del BOE y de IA siguen sujetas a verificación humana.

## Dónde se almacenan los borradores

Se añade la tabla SQLite `programming_drafts`, con un único borrador por módulo. Cada guardado actualiza ese borrador y registra una operación de auditoría sin introducir cambios en `outcomes`, `criteria`, `weight_origins`, alumnado, exámenes ni calificaciones. Se recomienda realizar una copia de seguridad del directorio de EvalúaFP antes de actualizar.

## Comportamiento de los portátiles

El proyecto conserva su mecanismo actual de almacenamiento portable (`EvaluaFP.portable.json`, `EVALUAFP_PORTABLE_HOME` y carpetas relativas de datos/copias). Para obtener nuevas compilaciones hay que ejecutar los flujos GitHub Actions de Windows, Linux y macOS y probar sus interfaces gráficas en cada sistema.

## Próximas pruebas necesarias

- Evaluación de usabilidad con profesores ajenos al desarrollo, especialmente de la vía de importación, el generador de borradores y el nuevo formulario de exámenes.
- Prueba gráfica real en Windows, Linux y las dos arquitecturas macOS; el entorno automático puede impedir abrir una ventana Chromium contra un servidor local.
- Probar importaciones de programaciones reales heterogéneas de distintas familias profesionales, preservando las advertencias de ausencia de cobertura y normativa.
- Revisar la redacción del documento generado y personalizar el modelo de programación conforme a los criterios propios de cada centro.
