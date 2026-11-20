# Arquitectura técnica

**Backend:** Python (`app.py`) con servidor HTTP local y endpoints de aplicación. **Persistencia:** SQLite (`database.py`, `evaluacion.py`). **Frontend:** `web/` en HTML, CSS y JavaScript. **Ventana nativa:** `pywebview` utilizando WebView2 en Windows. **PDF:** ReportLab, con procesamiento de PDF e imágenes mediante PyMuPDF y Pillow. **Word:** `python-docx`. **Excel:** `xlsxwriter` y `xlwt`.

## Módulos

- `logic.py`: construcción de exámenes, bancos de preguntas, entregas y evidencias.
- `ia.py`: proveedores IA, transcripción y corrección asistida.
- `materiales.py`: documentos de referencia y pasajes.
- `exam_pdf.py`: examen y solucionario con rúbrica.
- `evaluacion.py`: instrumentos, puntuaciones, RA/CE, cierre y auditoría.
- `exportaciones.py`: libro de evaluación y archivos para Additio.
- `storage_config.py`: ubicación de SQLite, archivos originales y copias.
- `scripts/`: preparador, diagnóstico, compilación y validación.

## Datos y seguridad

Los datos no se versionan. La instalación habitual utiliza `%LOCALAPPDATA%\EvaluaFP`; el modo portátil permite carpetas relativas al EXE. La localización de las rutas es configurable y las migraciones deben preservar originales y copia SQLite. La clave API se cifra y se desbloquea mediante contraseña; SQLite y documentos no están cifrados por esa sola característica.

## Flujo de evaluación

Programación -> RA/CE -> materiales -> banco de preguntas -> modelos PDF -> entrega multipágina -> transcripción IA -> propuesta de nota por pregunta/rúbrica -> revisión docente -> evidencia e instrumento -> agregado por CE/RA -> validación -> exportación e informe.

## Limitaciones

El OCR manuscrito y la corrección automática dependen de las capacidades del proveedor de IA. Las referencias documentales deben ser revisadas. El cálculo curricular requiere ponderaciones consistentes y una política docente validada.
