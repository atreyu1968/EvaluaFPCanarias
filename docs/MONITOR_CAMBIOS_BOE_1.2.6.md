# Nota técnica: vigilancia de metadatos BOE — EvalúaFP 1.2.6 beta

## Esquema y flujo

- `normative_monitor.py`: valida el identificador, obtiene los metadatos oficiales a través de `boe_discovery.inspect_boe_id`, normaliza los campos y calcula una huella SHA-256 de JSON canónico. No analiza la aplicabilidad de la disposición.
- `boe_monitor_sources`: conserva la primera y la última fecha de consulta, huella y metadatos actuales, fecha del último cambio detectado y del último acuse docente, con una clave primaria compuesta por `(module_id, territory_code, academic_year, module_code, boe_id)`.
- `boe_monitor_events`: conserva los pares `before/after` exclusivamente cuando cambia la huella observada. Cada registro está ligado al mismo ámbito territorial/temporal.
- Las fuentes reconocibles en las fichas curriculares se localizan si el URL HTTPS apunta a `boe.es` o `www.boe.es`, con identificador en `/buscar/act.php?id=...` o `/diario_boe/txt.php?id=...`; no se siguen redirecciones desde URL proporcionadas por el usuario.
- Una consulta fallida o sin análisis identificable no altera las observaciones previas. Una consulta idéntica sí actualiza la fecha de consulta, pero conserva cualquier alerta pendiente.

## Validaciones obligatorias

1. El módulo debe existir y tener un código oficial de cuatro cifras.
2. El ámbito se obtiene del borrador y del curso del módulo, no de parámetros libres de la petición.
3. Cada consulta del BOE requiere `teacher_confirmed` booleano verdadero.
4. El BOE debe devolver un identificador idéntico, título y análisis jurídico identificable. Si no, la consulta no se considera referencia válida.
5. El acuse requiere una alerta pendiente del mismo módulo/ámbito, confirmación y texto de revisión de 12–1000 caracteres.

## Verificación

`python -m unittest discover -s tests -v`

`node --check web/app.js`

Comprobar además manualmente con un ID del BOE conocido, sin usar información de estudiantes. La API pública y su estructura pueden cambiar. No se han ensayado solicitudes reales en esta fase; se deben repetir las pruebas funcionales en una instalación con acceso al BOE antes del despliegue.