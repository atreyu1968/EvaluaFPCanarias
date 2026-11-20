# Fuentes nacionales y fichas locales verificadas (1.1.9 beta)

## Estructura

Esta versión añade `national_registry.py`. Sus tablas SQLite, independientes de las notas, son:

| Tabla | Clave | Contenido |
|---|---|---|
| `national_hour_records` | territorio + año académico + ciclo + módulo | Horas totales, horas semanales, título y URL de la disposición, fecha de revisión |
| `national_center_calendars` | territorio + año académico + centro | Fechas de inicio/fin, evaluaciones, vacaciones, festivos y fuente |

La correspondencia no se basa en coincidencias aproximadas de nombres: el código oficial del módulo tiene preferencia y el nombre normalizado actúa como búsqueda exacta de respaldo. Las horas y calendarios recuperados se presentan **sin marcar como confirmados** para el nuevo grupo.

## API local de la aplicación

| Verbo | Ruta | Función |
|---|---|---|
| GET | `/api/national/sources?module_id=N` | Devuelve portales de consulta, horas guardadas y calendario del centro |
| POST | `/api/national/table-preview` | Extrae y valida filas de una tabla copiada, sin modificar SQLite |
| POST | `/api/national/table-import` | Guarda por lotes con confirmación docente |
| POST | `/api/national/extract-hours` | Solicita análisis IA consentido de un extracto literal |
| POST | `/api/national/save-hours` | Guarda una ficha horaria verificada por el docente |
| POST | `/api/national/save-calendar` | Guarda el calendario del centro previamente confirmado en el borrador |

Todos los recursos utilizan la sesión local protegida de EvalúaFP. Las peticiones de IA envían solo el fragmento que el docente introduzca y autorice; no se transmiten otras programaciones automáticamente.

## Importación desde una tabla publicada

```text
Código;Módulo;Horas totales;Horas semanales
0650;Proceso integral de la actividad comercial;202;6
0651;Comunicación y atención al cliente;170;5
```

La tabla anterior **ilustra el formato**, no acredita que sean las cifras vigentes en otra comunidad. Debe importarse exclusivamente desde la norma correspondiente al ciclo, territorio y curso seleccionados. En la interfaz, el docente verá primero la tabla y luego deberá indicar la URL y el título de su fuente.

## Si falta una fuente

La app no establece una carga horaria ficticia. Solicita comprobar disposición estatal y autonómica aplicable, registrar la fuente, verificar su vigencia y introducir las horas. El calendario escolar puede completarse manualmente por año y centro, sin copiar festivos de otra comunidad.

## Qué no hace todavía

- No dispone de un catálogo nacional completo ni de sincronización automática de todas las disposiciones autonómicas.
- No verifica por sí sola que la URL aportada sea una norma vigente y aplicable: valida la estructura de la dirección y exige confirmación docente.
- No interpreta PDF escaneados de anexos horarios mediante OCR automático.
- No incluye una comprobación de aceptación del ejecutable reconstruido en cada sistema operativo.
