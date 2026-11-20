# Especificación del explorador de fuentes TodoFP — EvalúaFP 1.2.4

## Entrada y alcance

Ruta POST JSON protegida por sesión de EvalúaFP:

```json
{
  "url": "https://www.todofp.es/que-estudiar/familias-profesionales/administracion-gestion/administracion-finanzas.html",
  "region": "Canarias",
  "academic_year": "2026-2027",
  "cycle_name": "CFGS Administración y Finanzas",
  "module_name": "Proceso integral de la actividad comercial"
}
```

`cycle_name` y `module_name` son opcionales para la creación de un módulo desde cero. Cuando se proporcionan, el resultado indica si existe coincidencia exacta normalizada con la ficha del Ministerio. La interfaz bloquea la adición de enlaces que no coincidan con el ciclo y módulo seleccionados.

### Ruta

`POST /api/national/todofp/explore`

Respuesta: `profile` (denominación del título, grado cuando sea identificable, lista de módulos y códigos realmente indicados en el texto), `regional_curricula` (lista de enlaces del ámbito consultado), `approval_required`, `suitable_for_current_module`, `consulted_at`, `notice`.

Si se consulta directamente `/curriculos-ccaa.html`, `profile` es `null` para evitar inferir módulos no publicados.

## Modelo de confianza

| Fuente | Qué puede acreditar | Qué NO puede acreditar |
|---|---|---|
| Ficha del ciclo en TodoFP | Denominaciones que aparecen, módulos orientativos y enlaces oficiales | Códigos no escritos, horas semanales, implantación en el centro, distribución de unidades o FEOE |
| Página Currículos CCAA de TodoFP | Publicación de enlaces por comunidad, tipos «currículo» y «modificación» | Vigencia automática, modificaciones no enlazadas, calendario escolar aplicable |
| Disposición en boletín oficial | Texto oficial publicado, que debe revisarse con sus modificaciones | Distribución horaria de otro ámbito o de otro curso sin norma de aplicación |

## Validaciones técnicas

- Acepta solo URL `https` y dominio exacto `todofp.es` / `www.todofp.es` bajo `/que-estudiar/...html`, con longitud máxima y sin parámetros o fragmentos arbitrarios.
- Rechaza redirecciones a otro servidor, respuestas que no son HTML, más de 2 MB o tiempos de espera excesivos.
- Utiliza el lector de HTML de la biblioteca estándar de Python, por compatibilidad con ejecutables portátiles.
- Las salidas se escapan al representarse en la interfaz; los enlaces se abren con `noopener noreferrer`.
- La exploración no escribe en SQLite. Añadir referencias a una programación requiere aprobación docente y se guarda como **pendiente de validar**.
- Al cambiar la comunidad, el curso o el módulo seleccionado se invalidan los resultados de consultas que hayan quedado fuera de ámbito.

La aplicación deberá adaptarse cuando TodoFP modifique el HTML; la ausencia de módulos o fuentes debe mostrarse como una carencia de información, nunca como evidencia de que el título no existe.
