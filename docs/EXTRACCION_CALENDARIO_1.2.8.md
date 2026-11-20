# Guía técnica de extracción de calendarios escolares — EvalúaFP 1.2.8

## Arquitectura

- `calendar_document.py`: parser local y solo de lectura, a partir de documentos PDF/DOCX/TXT/MD. Se utiliza PyMuPDF para PDFs y python-docx para Word, ya disponibles entre las dependencias del proyecto. El OCR, cuando está disponible, usa Tesseract y no se envía texto a servidores externos.
- `app.py`: endpoint multipart autenticado `/api/national/calendar-document-preview`, que compara comunidad autónoma y curso con la fila real de `modules`, exige un único documento y rechaza archivos excesivos.
- `web/app.js`: panel de vista previa, indicaciones de origen y advertencias, casillas de selección por fecha o periodo y carga de los campos seleccionados en el borrador. No escribe en la base desde este botón.
- `schedule_engine.py` y `calendar_versions.py`: conservan sus validaciones de fechas y su historial de revisiones; **no se modifica su cálculo de días lectivos ni de sesiones** en esta fase.

## Reglas del lector

1. El año forma parte obligatoria de cada fecha. Formatos aceptados: `AAAA-MM-DD`, `DD/MM/AAAA`, `DD-MM-AAAA`, `DD de mes de AAAA`.
2. El rango del curso va desde el 1 de septiembre del primer año al 31 de agosto del segundo. Fechas fuera de ese intervalo se descartan.
3. Las líneas/filas han de aportar términos que relacionen explícitamente la fecha con comienzo/fin de clases, vacaciones, días festivos o no lectivos. Se evitan líneas que identifican otra etapa educativa sin referencia a FP.
4. Si existen fechas de comienzo/fin incompatibles, la propuesta queda vacía para ese campo. Igual ocurre cuando los intervalos del mismo tipo de vacaciones son incompatibles.
5. Los vínculos con la norma y sus correcciones **se aportan manualmente** y deben ser HTTPS; leer un archivo local no demuestra su origen institucional.
6. `scope_ok` exige presencia literal de territorio, curso académico y una alusión a FP en el texto. Aunque cumpla estas tres condiciones, es obligatorio cotejar la etapa y el anexo.
7. El servidor no modifica datos. La UI carga un borrador no confirmado después de una acción expresa, y exige pasar por las verificaciones habituales para guardarlo o archivarlo.

## Pruebas recomendadas con documentos reales

- Resoluciones de calendarios donde las fechas consten en tablas y texto.
- Normas autonómicas generales para varias etapas educativas con fechas diferentes: confirmar que no se mezclan.
- PDF escaneados y digitalizados, con Tesseract disponible o ausente.
- Correcciones de una fecha anterior, que deben revisarse frente a la disposición base, sin aplicar automáticamente la más reciente.
- Documentos que contienen referencias a cursos anteriores y datos de otros territorios.
- Importación repetida, cambio de módulo o de comunidad a mitad de la revisión y cancelaciones de usuario.

## Ejecución de pruebas

```
python -m unittest discover -s tests -v
node --check web/app.js
```

Esta beta no crea un catálogo nacional completo de calendarios ni entrega ejecutables recompilados.