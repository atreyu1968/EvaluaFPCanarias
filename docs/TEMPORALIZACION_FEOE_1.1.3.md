# EvalúaFP 1.1.3 beta — Temporalización, evaluación y FEOE

## Objetivo

Planificar cada módulo **por evaluaciones y horas lectivas reales**, descontando los días no lectivos, asignando unidades a sus RA/CE y mostrando un Gantt. Se toman como referencia la estructura didáctica de la programación `Proceso integral de la actividad comercial (PNG)` aportada por el usuario (2026/2027: 202 horas totales, 6 semanales) y las fuentes oficiales del calendario escolar. **Los datos de esa programación son un ejemplo, no una carga horaria universal para todos los módulos**.

## Paso 5 — Temporalización y FEOE

1. **Horas del módulo.** Indicar horas semanales y horas totales; el valor inicial de 6 h/semana es solo un punto de partida editable. Las horas totales se introducen desde la programación/currículo del módulo y no se presuponen.
2. **Horario real.** Se permite introducir las horas de clase de lunes a viernes. Deben sumar exactamente las horas semanales. Si se dejan los cinco días a cero se aplica una *estimación proporcional* de una quinta parte cada día: la aplicación **advierte** que el cálculo de festivos no es exacto.
3. **Periodo y evaluaciones.** Por defecto para FP 2026-2027 en Canarias: inicio 16/09/2026, fin 22/06/2027 para los grupos que correspondan, con cierres orientativos 21/12/2026, 19/03/2027 y 22/06/2027. **No son las fechas oficiales de cada sesión de evaluación** y deben confirmarse con el centro; para segundo curso de determinados ciclos, el fin de clases puede ser distinto y debe adaptarse.
4. **Calendario escolar.** No se cuentan sábados, domingos, vacaciones de Navidad (22/12/2026–07/01/2027), Semana Santa (22–26/03/2027), festivos estatales y autonómicos relevantes, insulares conocidos y las fiestas locales de Guía de Isora cuando se selecciona ese municipio. La aplicación permite añadir todos los días de libre disposición, festivos municipales de otros municipios y otros no lectivos que confirme el centro. No presupone que carnaval sea no lectivo en todos los centros.
5. **Unidades.** Crear una unidad por RA como propuesta editable o configurar varias unidades libremente. En cada unidad se guardan título, código, evaluación, horas, CE, instrumentos y recursos. Se calculan fechas de inicio y fin; el algoritmo **no traslada automáticamente las horas de una evaluación saturada a otra**.
6. **FEOE.** Se pueden seleccionar y contar los CE propuestos para trabajar en empresa, mostrando porcentaje sobre todos los CE del módulo y RA vinculados. El objetivo configurable del 10–20 % de **criterios** es solo una **preferencia pedagógica** solicitada: la norma se refiere a **resultados de aprendizaje** de la oferta formativa y a duración del periodo en empresa, por lo que **no se certifica cumplimiento normativo** calculando CE del módulo. El docente debe validar los RA, el plan de formación, el régimen dual y el cómputo a nivel de ciclo.
7. **FEOE y horas lectivas.** Si se introducen fechas FEOE, también se puede especificar el horario semanal que seguirá impartiéndose en el centro durante esos días. Si no se introduce, no se descuentan horas de aula y se muestra una advertencia: **no se inventa un horario de empresa**.
8. **Actividades.** Añadir actividades complementarias (en horario escolar) y extraescolares, indicando fecha, unidad asociada, finalidad y recursos. Las propuestas se dejan pendientes de autorización.
9. **Exportaciones.** Word y PDF incluyen portada, índice, secciones pedagógicas, información de horas, tablas y el Gantt; el PDF usa semanas y Word una vista mensual para facilitar edición.

## Validaciones

- Cuadran las horas distribuidas por días con las semanales.
- Las fechas de las evaluaciones avanzan cronológicamente y están dentro de las fechas lectivas.
- Los días adicionales son fechas válidas; los sábados y domingos nunca suman horas.
- El tiempo planificado de cada unidad no supera la capacidad libre de su evaluación sin generar una **alerta**.
- La suma de horas de unidades se compara con las horas totales declaradas del módulo, que no se rellenan ficticiamente.
- Cada criterio FEOE seleccionado debe existir en los CE que el docente confirmó; si no existe se avisa.
- Para 1–4 CE puede no existir un número entero equivalente al 10–20 %: se explica el problema, sin falsear el porcentaje.
- Las fechas de FEOE y horas presenciales en el centro se pueden modificar sin alterar los pesos de RA/CE ni añadir un porcentaje extra a la nota.
- La cobertura curricular de RA/CE continúa sometida a las validaciones de las versiones anteriores.

## Fuentes oficiales incorporadas al cálculo

- Resolución de 17 de marzo de 2026, calendario escolar de Canarias 2026-2027 (BOC 30/03/2026): https://www.gobiernodecanarias.org/boc/2026/061/1025.html
- Calendario visual oficial: https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/otros/calendario_escolar_26_27.pdf
- Festivos de 2027 para Canarias: Decreto 115/2026, BOC 03/07/2026: https://www.gobiernodecanarias.org/boc/2026/133/2334.html
- Fiestas locales de 2027, BOC 21/08/2026: https://www.gobiernodecanarias.org/boc/2026/168/3035.html
- Real Decreto 659/2023 (régimen dual, duración y RA): https://www.boe.es/eli/es/rd/2023/07/18/659/con

## Limitaciones y publicación

Esta versión es **beta de código fuente**, no un nuevo EXE compilado. La comprobación se realizó con una base aislada, 100 pruebas automatizadas y un navegador con respuestas de API simuladas. Los Gantt y datos exportados son **borradores**; deben revisarse con el calendario y la PGA del centro, la relación real de CE y los acuerdos de FEOE antes de una aprobación formal. Para publicar los ejecutables portátiles Windows, Linux y macOS hay que compilar esta nueva versión en sus sistemas de destino.
