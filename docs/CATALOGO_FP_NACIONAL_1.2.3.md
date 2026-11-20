# Registro local de títulos y módulos — Especificación técnica 1.2.3

## Fuente de datos

El módulo `fp_catalog.py` recibe un CSV de 6 columnas, validado antes de efectuar escrituras. La información se atribuye al ámbito y curso introducidos por el docente. EvalúaFP no asume por sí mismo que un título esté implantado, que su código sea oficial o que siga vigente.

```csv
Código título;Ciclo;Grado;Familia;Código módulo;Módulo
CODIGO_FICTICIO;Ciclo de ejemplo;Medio;Familia de ejemplo;9999;Módulo de ejemplo
```

Los grados admitidos son Básico, Medio, Superior y Especialización. Se permiten hasta 500 filas por lote y 120.000 caracteres de contenido. Para consultar se limita la respuesta a los primeros 100 registros coincidentes, informando si hay más.

## Tablas SQLite

`fp_catalog_entries`: id, territorio, curso académico, código/nombre del título, grado, familia, código/nombre del módulo, fuente HTTPS, título de la fuente, SHA-256 del lote, fecha de revisión y marca de confirmación docente. Clave única: `(territorio, curso, código título, código módulo)`.

`fp_catalog_revisions`: copia de la ficha anterior cuando el docente permite expresamente una actualización contradictoria. Los módulos formativos que ya se han creado no se reescriben ni se alteran al cambiar una ficha de catálogo.

## Creación segura de un módulo

La interfaz permite seleccionar una ficha, rellenar ciclo/módulo y enviar `catalog_entry_id`. El servidor comprueba que la ficha existe en la misma comunidad y curso y que ambos nombres coinciden **exactamente** con los de la ficha. Entonces inicia el borrador con código del título, código del módulo, título/URL de la fuente y `curriculum_confirmed=false`.

**No se copian RA/CE, ponderaciones, sesiones, horas, calendario, FEOE ni notas de ninguna ficha.** Los módulos existentes no se modifican cuando entra una versión posterior del catálogo.

## Pruebas de aceptación

1. Alta y consulta de fichas en los 19 territorios, aislando estrictamente cursos distintos.
2. Rechazo de fuentes no HTTPS, grados no válidos, duplicados o códigos contradictorios.
3. Migración idempotente en SQLite.
4. Dos importaciones idénticas no generan versiones falsas.
5. Cambio autorizado de ficha conserva copia anterior; discrepancia no autorizada no escribe nada.
6. Creación mediante API con `catalog_entry_id` y comprobación de que el borrador sigue pendiente de revisión.
7. Recorrido real de la interfaz en Chromium con SQLite/HTTP de prueba.

## Fuentes públicas para consultar y contrastar

- https://todofp.es/catalogos-registros-sistema-fp.html
- https://www.todofp.es/que-estudiar/material-descargable.html
- https://www.boe.es/eli/es/rd/2025/02/04/69
