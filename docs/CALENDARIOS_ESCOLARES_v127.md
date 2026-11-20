# Arquitectura y criterios de aceptación — Calendarios FP 1.2.7

## Entidades y validación

- `schedule_engine.clean`: validación de calendario, fuente y hasta ocho URL de correcciones HTTPS. Las propuestas del sistema no aparecen confirmadas por defecto.
- `national_registry.save_calendar`: sigue guardando la última referencia de centro para mantener compatibilidad con los módulos ya existentes y llama a la capa de archivo inmutable.
- `calendar_versions.record_from_draft`: archiva el calendario confirmado por docente tras comprobar que el territorio y curso del módulo coinciden. Rechaza fechas ajenas al curso. Usa SHA-256 de un JSON canónico para evitar duplicados consecutivos.
- `calendar_versions.list_versions`: filtro por territorio + curso + centro + municipio + isla + etapa `fp_grado_d`; nunca se consulta el historial de otro centro solo por su nombre.
- `calendar_versions.compare_versions`: referencias de versiones limitadas al mismo ámbito; presenta diferencias de fechas, festivos, periodo, centro y fuentes. No altera ningún dato.
- `calendar_versions.source_directory`: portal oficial por administración; enlaces directos solo cuando se han contrastado como puntos de consulta. No genera calendarios, horas ni confirmaciones por sí solo.

## No alterar la evaluación

Las versiones contienen exclusivamente identificadores y fechas del calendario, sin horario del módulo, matrícula, notas, pesos, resultados de aprendizaje, criterios de evaluación, planes de empresa ni claves. El navegador carga una lista cerrada de campos en el borrador y establece `calendar_confirmed=false`. Cualquier persistencia exige después el guardado habitual y, para archivar como validado, nueva confirmación humana.

## Pruebas para aceptación

1. Los 19 ámbitos muestran un portal oficial de consulta, sin afirmar un calendario validado donde no existe.
2. Guardar una primera referencia crea una sola revisión, y guardar otra idéntica no añade filas.
3. La corrección de fechas y la incorporación de una modificación crea nueva revisión, sin perder la primera.
4. La comparación solo permite versiones del mismo curso, administración, centro, municipio e isla.
5. No se archivan fuentes HTTP de corrección, URL locales ni fechas de otros cursos.
6. La API mantiene autenticación; no modifica calificaciones, CE, RA ni otros registros de evaluación.
7. La temporalización y los datos ya existentes se conservan tras la migración; pruebas de regresión globales completas.

**Pruebas manuales adicionales pendientes:** abrir la aplicación real en los tres sistemas operativos, revisar los enlaces oficiales en vivo, simular una corrección real posterior y comparar calendarios particulares de centros con fiestas locales.