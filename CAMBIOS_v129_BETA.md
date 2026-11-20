# EvalúaFP 1.2.9 beta — Lectura de anexos y revisión opcional con IA

## Desarrollos

1. **Tablas mixtas en DOCX/PDF:** identifica cabeceras explícitas de *etapa*, *inicio* y *fin* de clases, y solo extrae filas que señalan FP; las filas de ESO, Primaria o Bachillerato quedan fuera. El resultado incluye el texto de la cabecera y la fila. Si el PDF no tiene estructura tabular recuperable, mantiene la lectura de líneas.
2. **Líneas fragmentadas:** reconstruye una etiqueta de inicio/fin o vacaciones seguida inmediatamente de una fecha completa, dentro de la misma página; no empareja texto de páginas distintas.
3. **PDF escaneado:** se mantiene el OCR local, optativo, con Tesseract en español y máximo de 8 páginas con poco texto seleccionable; el tratamiento tabular posterior aprovecha lo recuperable sin prometer lectura infalible.
4. **Preparación local para IA:** crea un fragmento reducido (máximo 10.500 caracteres) con contexto territorial y fechas. Un botón copia ese fragmento al cuadro editable; esta acción **no envía ningún dato**.
5. **Interpretación IA autorizada:** el usuario pega o modifica un fragmento y marca una autorización específica. Solo se remite ese texto al modelo de análisis configurado, sin enviar automáticamente el PDF/Word ni las calificaciones.
6. **Comprobación de citas:** cada propuesta IA exige una cita reproducida literalmente en el fragmento, fecha completa que corresponda a la propuesta y contexto explícito. Las filas tabulares con dos fechas deben contar con una cabecera literal que establezca el orden de las columnas. Se rechazan invenciones y contradicciones.
7. **Validación del módulo:** la API autentica el acceso, comprueba el territorio y el curso académico del módulo guardado y no acepta textos sin referencia literal a comunidad, curso y FP antes de llamar a la IA.
8. **Revisión humana:** los resultados se muestran como propuestas, se seleccionan uno por uno y, si se aplican, pasan al borrador con el calendario sin confirmar. No se modifican RA/CE, horas, FEOE, notas, ni se crea una ficha archivada automáticamente.

## Pruebas nuevas

- Tablas DOCX con FP, Bachillerato y ESO: solo datos de FP.
- PDF cuyas fechas aparecen en líneas contiguas.
- Separación entre páginas; OCR y fechas no acreditadas nunca completan información ausente.
- Citas inventadas, fechas erróneas, columnas cruzadas y contradicciones de la IA: descarte.
- Autorización explícita y coincidencia de ámbito antes de la llamada externa.
- Endpoint HTTP autenticado; pruebas de que no se guardan borradores, notas ni revisiones tras analizar.

## Limitaciones

Las resoluciones oficiales pueden mezclar enseñanzas, cursos, modificaciones y centros. Esta funcionalidad **no certifica la vigencia normativa** ni sustituye la comprobación del docente. La IA solo coteja la literalidad con el fragmento facilitado; no certifica que el fragmento sea una publicación auténtica o actual. Para PDFs escaneados, la calidad OCR depende de Tesseract y de la legibilidad. No se han incorporado automáticamente todos los calendarios de las 19 administraciones educativas.

**Entrega:** código fuente beta, sin ejecutables recompilados.