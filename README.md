# EvalúaFP Canarias · Administración y Gestión

**Edición independiente (beta de desarrollo)** basada en EvalúaFP 1.2.10. Destinada a los docentes de la **familia profesional de Administración y Gestión** de **Canarias**.

**Repositorio propio:** https://github.com/atreyu1968/EvaluaFPCanarias  
**Origen (solo lectura):** https://github.com/atreyu1968/EvaluaFP

Esta copia no modifica el repositorio original; las mejoras de esta edición se almacenan únicamente aquí.

## Ofertas incluidas en la primera fase (Grado D)

| Grado | Ciclo | Denominación |
| --- | --- | --- |
| Básico | CFGB Servicios Administrativos | Técnico Básico en Servicios Administrativos |
| Medio | CFGM Gestión Administrativa | Técnico en Gestión Administrativa |
| Superior | CFGS Administración y Finanzas | Técnico Superior en Administración y Finanzas |
| Superior | CFGS Asistencia a la Dirección | Técnico Superior en Asistencia a la Dirección |

La relación de títulos se ha comprobado en el catálogo de la [Consejería de Educación del Gobierno de Canarias](https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/titulos/).

Los Grados A, B y C de la familia **no son equivalentes automáticamente a los Grados D**. Su integración en el selector se abordará de forma separada, comenzando por las ofertas de nivel 1 recogidas en la [Resolución canaria de 29 de octubre de 2026](https://www.gobiernodecanarias.org/boc/2026/227/3917.html).

Se ha documentado el **primer grupo de cuatro certificados de Grado C (nivel 1)** del Anexo I del BOC 2026/227, con sus códigos ADG_C_001_3B a ADG_C_004_3B, y se mantiene expresamente separado del selector de cuatro títulos de Grado D. [Ver alcance y normativa de los Grados B/C](docs/CERTIFICADOS_B_C_NIVEL_1_CANARIAS.md).

## Adaptaciones realizadas

1. Interfaz identificada como «EvalúaFP Canarias · Administración y Gestión».
2. Selector de comunidad limitado a Canarias y selector de ciclo con los cuatro títulos identificados.
3. Validación **en el servidor**: no admite crear módulos de otro territorio o ciclo ajeno a la familia en esta edición.
4. Consulta GET autenticada `/api/canarias-ag/catalog` con títulos, fuentes y estado de verificación curricular.
5. Almacenamiento SQLite independiente: directorio local `EvaluaFPCanarias` y carpetas portátiles `EvaluaFPCanarias_Datos` y `EvaluaFPCanarias_Copias`.
6. Variables de entorno propias: `EVALUAFP_CANARIAS_DATA_DIR`, `EVALUAFP_CANARIAS_PORTABLE` y `EVALUAFP_CANARIAS_PORTABLE_HOME`.
7. Identidad de credenciales IA separada del proyecto original. La IA continúa siendo opcional y requiere supervisión docente.
8. Conserva la importación/revisión de programaciones, RA/CE, evaluación, exámenes, informes, corrección asistida, FEOE y calendarios de la base.
9. Fiscalidad didáctica canaria: los casos de tributación indirecta deben utilizar IGIC cuando corresponda y verificar los tipos aplicables.


## Selección asistida de módulos (beta.4)

En **Preparar módulo**, al seleccionar un ciclo, se consulta el índice documental de módulos de Gestión Administrativa, Administración y Finanzas y Asistencia a la Dirección. El docente puede filtrar por **1.º o 2.º curso**, elegir el módulo en un selector legible o escribir su denominación manualmente. La consulta se realiza en el servidor, sin necesidad de instalar un catálogo externo.

- **15 referencias** de CFGM Gestión Administrativa.
- **16 referencias** de CFGS Administración y Finanzas.
- **15 referencias** de CFGS Asistencia a la Dirección.
- **16 referencias** de CFGB Servicios Administrativos, incluidas materias de los ámbitos generales sin código RD. Se excluye Tutoría por no constituir un módulo con RA/CE.
- La optativa queda como entrada manual porque requiere la oferta concreta del centro.
- Cada ciclo muestra un enlace al **Real Decreto estatal del título** (BOE). Esta fuente es orientativa para identificar RA/CE: no equivale a verificar su vigencia, modificaciones, currículo autonómico ni ponderaciones.

**Importante:** códigos, denominaciones y horas son una **referencia de los anexos V (CFGB) y VI (GM/GS) de 2024**, no una certificación automática de vigencia para el curso 2026-2027. La aplicación NO rellena las horas de programación ni los RA/CE a partir de este índice.

[Documentación del índice curricular](docs/INDICE_MODULOS_CANARIAS_AG.md).

## Ficha de procedencia al crear un módulo

Al elegir un módulo en el selector, EvalúaFP registra una **copia de referencia** que
identifica ciclo, módulo, código (cuando existe), curso primero o segundo, distribución
horaria del anexo de 2024, página y enlace de procedencia. El registro se almacena en
SQLite en `canarias_module_references` y se muestra al entrar en «Preparar mi módulo».

**Esta ficha no es una programación ni una validación curricular.** Las horas históricas
no pasan al calendario, el código no se da por validado en la programación, y no se
crean RA, CE, ponderaciones ni calificaciones. La validación debe hacerse por curso,
centro y normativa aplicable. Las optativas y módulos escritos manualmente no
generan una ficha de 2024 ficticia.

Los datos de referencia se validan nuevamente en el servidor, por nombre, código,
ciclo y curso; una selección manipulada o incoherente se rechaza. Las bases SQLite
de la edición general y de la edición Canarias continúan separadas.

## IMPORTANTE: fuentes y currículo

Los **títulos** están identificados, pero esta beta **no contiene un catálogo de módulos, horas, RA y CE completo y validado para 2026-2027**. Para crear un módulo se elige su ciclo y se incorpora su programación o documentación oficial. La herramienta permite revisar y confirmar las propuestas del docente, sin certificar normas por IA ni inventar resultados.

Fuentes normativas de referencia:
- [LO 3/2022](https://www.boe.es/eli/es/lo/2022/03/31/3/con)
- [RD 659/2023](https://www.boe.es/eli/es/rd/2023/07/18/659/con)
- [Currículos de CFGB Canarias](https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/fpgb/curriculos_fpgb/)
- [Oferta oficial de títulos Canarias](https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/titulos/)
- [BOC 2026/227 (Grados B y C nivel 1)](https://www.gobiernodecanarias.org/boc/2026/227/3917.html)

## Compilaciones portátiles (fase de verificación)

Se incorpora un flujo de GitHub Actions para compilar **Windows x64** y se mantiene el flujo para **Linux x64, macOS Intel y Apple Silicon**, con pruebas y comprobación de arranque de los binarios. Los archivos resultantes son artefactos temporales de Actions, **sin firma de código ni notarización**; la generación automática no sustituye una apertura real y una prueba funcional en cada sistema. Los ZIP/TAR.GZ no incorporan información personal.

**Candidato auditado de 21/11/2026 (versión interna 1.2.10-AG-CN-beta.4, commit e317fd88):** [Windows x64](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727417758) · [Linux x64](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727154145) · [macOS Intel](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727566138) · [macOS Apple Silicon](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727497151). Requiere sesión en GitHub. Conservación hasta el 21/12/2026. Las cuatro autopruebas de arranque y 391 pruebas automatizadas han superado los controles; falta validación visual real. Véase [la compilación completa](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151) y la [landing](docs/index.html#descargas).

## Instalación y pruebas

Requiere Python 3.13 y dependencias de `requirements.txt`. En una carpeta nueva:
```bash
python -m pip install -r requirements.txt
python app.py
```
En Windows pueden utilizarse `INICIAR_EVALUAFP.bat` y `CREAR_VERSION_PENDRIVE.bat` (el nombre histórico del primer lanzador se conserva temporalmente). Los scripts de compilación se han diferenciado para producir paquetes EvaluaFPCanarias.

```bash
python -m unittest discover -s tests -v
```

La compilación auditada del 21/11/2026 ha superado **391 pruebas automatizadas**, sintaxis Python y JavaScript, y cuatro autopruebas nativas de arranque. Candidatos: [Windows x64](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727417758) · [Linux x64](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727154145) · [macOS Intel](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727566138) · [macOS Apple Silicon](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44955417151/artifacts/14727497151). Los artefactos incluyen huellas SHA-256 y caducan el 21/12/2026. No constituyen versiones definitivas firmadas, notarizadas ni probadas visualmente en equipos reales.

## Documentación

[Guía de la edición canaria](docs/CANARIAS_ADMINISTRACION_GESTION.md) · [Documentación de la base](README_BASE_EVALUAFP.md) · [Repositorio de la base](https://github.com/atreyu1968/EvaluaFP)

**Protección de datos:** no transmitir a servicios IA datos identificativos de alumnado sin base jurídica y autorización correspondiente. Mantener copias de seguridad, restringir el acceso al equipo y verificar cualquier calificación antes de considerarla definitiva.

© Francisco Javier González Rolo. Edición para uso docente.

## Consulta curricular de los módulos contables

Los módulos 0441 y 0443 permiten consultar la publicación original del RD 1631/2009 sin escribir su identificador. Se exige que la extracción incluya todos los RA y CE consecutivos: 0441 (5 RA, 41 CE), 0443 (4 RA, 34 CE). La consulta no crea notas ni asigna ponderaciones y requiere revisión docente. La fuente original debe contrastarse con el RD 499/2024 y la normativa canaria. Las pruebas utilizan documentos artificiales y no certifican la vigencia curricular.

## Ampliación a los nueve módulos específicos de Gestión Administrativa

El extractor permite recuperar los RA y CE de la publicación original del RD 1631/2009 para los nueve módulos específicos actuales del índice canario. Comprueba 54 RA y 440 CE en total (no son una certificación autonómica de vigencia). En caso de falta o duplicación de criterios rechaza la extracción antes de ofrecerla. Se mantienen fuera de esta recuperación los módulos transversales del nuevo sistema hasta identificar sus normas aplicables. No se importan horas ni ponderaciones desde la norma estatal.

| Código | Módulo | RA | CE |
| --- | --- | ---: | ---: |
| 0437 | Comunicación empresarial y atención al cliente | 8 | 76 |
| 0438 | Operaciones administrativas de compraventa | 5 | 43 |
| 0439 | Empresa y administración | 7 | 50 |
| 0440 | Tratamiento informático de la información | 8 | 62 |
| 0441 | Técnica contable | 5 | 41 |
| 0442 | Operaciones administrativas de recursos humanos | 6 | 50 |
| 0443 | Tratamiento de la documentación contable | 4 | 34 |
| 0446 | Empresa en el aula | 7 | 49 |
| 0448 | Operaciones auxiliares de gestión de tesorería | 4 | 35 |

## Administración y Finanzas: consulta del currículo de origen

El anexo I original del RD 1584/2011 ([BOE-A-2011-19533](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2011-19533)) aporta 60 RA y 510 CE en diez módulos específicos. La recuperación se selecciona por ciclo; el software admite encabezados con créditos ECTS y el RA4 de 0651 numerado sin punto, comprueba código, recuento y secuencia y añade huella SHA-256 del documento recibido. No certifica vigencia autonómica, no aplica ponderaciones ni importa horas. Los módulos compartidos con Asistencia a la Dirección requieren cotejar su propio título; no se usa el anexo de Administración y Finanzas como sustituto automático. Se debe revisar el RD 500/2024 y la normativa autonómica.

| Código | Módulo | RA | CE |
|---|---|---:|---:|
| 0647 | Gestión de la documentación jurídica y empresarial | 5 | 40 |
| 0648 | Recursos humanos y responsabilidad social corporativa | 5 | 37 |
| 0649 | Ofimática y proceso de la información | 9 | 76 |
| 0650 | Proceso integral de la actividad comercial | 7 | 60 |
| 0651 | Comunicación y atención al cliente | 7 | 69 |
| 0652 | Gestión de recursos humanos | 4 | 33 |
| 0653 | Gestión financiera | 6 | 46 |
| 0654 | Contabilidad y fiscalidad | 6 | 55 |
| 0655 | Gestión logística y comercial | 5 | 43 |
| 0656 | Simulación empresarial | 6 | 51 |

## Asistencia a la Dirección: recuperación curricular independiente

Se han añadido nueve módulos del anexo I original del [RD 1582/2011](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2011-19531), incluidos los cinco comunes con Administración y Finanzas y Segunda lengua extranjera. Se comprueban 54 RA y 461 CE, diferenciando las referencias por disposición y código. Ante una denominación común sin ciclo ni disposición explícita, el asistente rechaza una elección arbitraria. El texto de origen no acredita por sí solo el currículo vigente; deben contrastarse el RD 500/2024 y las normas canarias aplicables.

| Código | Módulo | RA | CE |
|---|---|---:|---:|
| 0647 | Gestión de la documentación jurídica y empresarial | 5 | 40 |
| 0648 | Recursos humanos y responsabilidad social corporativa | 5 | 37 |
| 0649 | Ofimática y proceso de la información | 9 | 76 |
| 0650 | Proceso integral de la actividad comercial | 7 | 60 |
| 0651 | Comunicación y atención al cliente | 7 | 69 |
| 0180 | Segunda lengua extranjera | 5 | 36 |
| 0661 | Protocolo empresarial | 6 | 57 |
| 0662 | Organización de eventos empresariales | 5 | 46 |
| 0663 | Gestión avanzada de la información | 5 | 40 |

## Servicios Administrativos (Grado Básico)

Se incorporan las seis referencias profesionales del anexo I del [RD 127/2014](https://www.boe.es/diario_boe/txt.php?id=BOE-A-2014-2360): 24 RA y 182 CE. El extractor aísla el anexo I para impedir la recuperación accidental de un módulo homónimo de otro título del mismo decreto. Se enlaza el Decreto canario 9/2023 y el RD 498/2024. Los ámbitos comunes requieren un modelo basado en competencias específicas y CE; no se recuperan como RA profesionales las materias antiguas suprimidas, tutoría ni las nuevas enseñanzas sin fuente contrastada. La fuente original sigue siendo una propuesta pendiente de validación docente.

| Código | Módulo | RA | CE |
|---|---|---:|---:|
| 3001 | Tratamiento informático de datos | 4 | 34 |
| 3002 | Aplicaciones básicas de ofimática | 4 | 26 |
| 3003 | Técnicas administrativas básicas | 4 | 31 |
| 3004 | Archivo y comunicación | 4 | 35 |
| 3005 | Atención al cliente | 4 | 31 |
| 3006 | Preparación de pedidos y venta de productos | 4 | 25 |

## Módulos transversales y proyectos intermodulares

Se incorporan las referencias de los anexos III y V–X del RD 659/2023, el proyecto GB (RD 498/2024), el proyecto GM (RD 499/2024) y los proyectos específicos de GS, con las denominaciones actualizadas conforme al RD 500/2024. La fuente de 1713 contiene una repetición de a) en RA5: se bloquea su importación automática si se detecta esta numeración. No se renumera silenciosamente. Los ámbitos de GB y las optativas requieren fuentes y estructuras propias.

| Código | Referencia | RA | CE |
|---|---|---:|---:|
| 3159 | itinerario personal para la empleabilidad | 5 | 20 |
| 1709 | itinerario personal para la empleabilidad i | 5 | 39 |
| 1710 | itinerario personal para la empleabilidad ii | 5 | 35 |
| 1664 | digitalizacion aplicada a los sectores productivos (gm) | 5 | 33 |
| 1665 | digitalizacion aplicada a los sectores productivos (gs) | 6 | 45 |
| 1708 | sostenibilidad aplicada al sistema productivo | 6 | 34 |
| 0156 | ingles profesional (gm) | 5 | 46 |
| 0179 | ingles profesional (gs) | 5 | 43 |
| 3160 | proyecto intermodular de aprendizaje colaborativo | 5 | 27 |
| 1713 | proyecto intermodular | 5 | 39 |
| 0657 | proyecto de administracion y finanzas | 4 | 33 |
| 0664 | proyecto de asistencia a la direccion | 4 | 33 |

Los recuentos corresponden a las publicaciones estatales cotejadas, no a un certificado de currículo vigente en Canarias. La consulta sigue requiriendo conexión y revisión docente.

## Currículos canarios específicos (BOC de 8/05/2025)

En Preparar mi módulo se ofrece una consulta independiente y preferente al BOC para 3159, Prevención y salud laboral (sin código RD), 3160 y 1713. Referencia: Resolución de 25 de abril de 2025, anexos V y VI, [BOC 91, anuncio 1728](https://www.gobiernodecanarias.org/boc/2025/091/1728.html). La versión HTML es informativa: se debe cotejar el PDF firmado. Se verifican nombre, código cuando existe, duración, anexo y secuencia de los 20 RA y 113 CE; la carga horaria no se confirma ni se modifica. El RA5 de 1713 en la fuente autonómica aparece con criterios a), b), c), d); no se renumera el BOE. Se conserva el enlace y la huella de la consulta en la propuesta. El enlace del anexo V de horarios de 2024 apunta ahora directamente a la Consejería. Los ámbitos generales aún requieren su propio modelo de competencias específicas.

## Ámbitos comunes de CFGB Servicios Administrativos

Para las cuatro materias de los ámbitos comunes del catálogo canario, **Preparar mi módulo** muestra un editor competencial independiente. Referencia: [Decreto 9/2023, anexo 1](https://www.gobiernodecanarias.org/boc/2023/025/001.html) y [PDF de los ámbitos comunes](https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/formacion_profesional/_galerias/descargas/cfgb/1_ambitos_comunes.pdf). Comunicación y Ciencias Sociales dispone de ocho competencias de referencia, y Ciencias Aplicadas de once, incluidas las relativas a Actividad Física y Bienestar Emocional.

Se permite transcribir los enunciados, criterios numerados, descriptores operativos y saberes básicos trabajados por cada materia. Los borradores se guardan por módulo local en common_scope_drafts, con auditoría de la revisión docente y de la referencia normativa; no modifican outcomes, criteria, notas ni pesos. La consulta oficial y confirmación guiada de RA profesionales se bloquean para estas materias. La revisión es de los elementos introducidos, no una certificación de la totalidad del ámbito. No incluye extracción automática del PDF, evaluación colegiada global, consolidación entre materias ni cálculo de calificaciones de ámbito: esas funciones requieren una fase posterior y no deben simularse mediante las notas profesionales existentes.

### Consulta del anexo oficial de ámbitos comunes y cálculo orientativo

El editor ofrece la consulta autorizada del [anexo 1 en PDF](https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/formacion_profesional/_galerias/descargas/cfgb/1_ambitos_comunes.pdf). El lector acota las páginas de cada bloque, exige la secuencia completa de competencias y criterios consecutivos con descriptores, y rechaza mezclas detectables de las columnas. Los saberes se presentan como referencia del ámbito, sin atribución automática a un curso o materia. La consulta queda registrada con la huella SHA-256; el docente puede copiar una competencia a campos vacíos, revisar y guardar manualmente. El lector se ha diseñado a partir de la estructura del PDF oficial; aún requiere prueba de integración contra los bytes reales del PDF mediante una conexión disponible. No se certifica la literalidad ni la vigencia de una extracción.

El componente common_scope_grading.py incorpora la instrucción séptima del anexo I de la [Resolución de 9 de junio de 2025](https://www.gobiernodecanarias.org/boc/2025/118/2219.html): equivalencias IN=3, SU=5, BI=6, NT=7,5, SB=9 y cálculo ponderado con la carga horaria confirmada. En ordinaria deben superarse todas las materias; en extraordinaria basta media ponderada de al menos cinco, sin redondeo para decidir el resultado. Se exige completar las materias del ámbito y curso. Es un motor independiente, aún sin integración en la interfaz de evaluación del alumnado ni en las actas; no infiere una calificación cualitativa oficial ni sustituye al equipo docente. Incluye pruebas sintéticas de extracción y de cálculo pendientes de ejecución verificable.

### Cuaderno competencial de materias de ámbitos comunes

Desde **Preparar mi módulo > Abrir cuaderno de evaluación competencial**, el docente puede registrar el alumnado local, crear actividades por situación de aprendizaje, instrumento, evaluación y fecha, y vincular los criterios revisados del currículo. El cuaderno conserva una copia de los criterios de cada actividad, registra observaciones y referencias textuales de evidencias y permite sucesivas valoraciones NE, IN, SU, BI, NT y SB. La última valoración se muestra en el seguimiento individual; las anteriores permanecen disponibles en el historial.

Las tablas independientes scope_activities y scope_evidence no modifican los RA, las notas ni las ponderaciones profesionales. No se admite alumnado de otra materia ni criterios ajenos a la actividad; los cambios curriculares dejan visibles las evidencias antiguas y exigen revisar la correspondencia antes de añadir otras. La cobertura de criterios con evidencias valoradas no representa una calificación ni un grado automático de dominio. NE significa no evaluado. No se adjuntan archivos ni se transmiten datos del alumnado a IA o servicios externos desde este cuaderno.

La consolidación entre materias, la evaluación colegiada, la recuperación específica y la exportación de actas todavía no se incluyen. Las pruebas de regresión sintéticas verifican el comportamiento previsto; su ejecución queda pendiente de comprobación.

### Consolidación de materias y acuerdos del equipo docente

Desde el cuaderno competencial, **Consolidar calificaciones del ámbito** permite registrar valoraciones cualitativas de cada materia por trimestre y convocatoria final, con horas semanales contrastadas, fuente y justificación docente. La consolidación exige el mismo ciclo, territorio, curso de referencia seleccionado en el índice, grupo y año académico; se bloquea si una materia está ausente o duplicada, o si no coinciden el código y el nombre del alumno. La coincidencia se debe verificar expresamente antes del acuerdo.

En las convocatorias finales se aplica el motor orientativo de la Resolución de 9 de junio de 2025, sin redondear para determinar la superación. No se deduce automáticamente la calificación cualitativa: el usuario registra la acordada por el equipo docente, con motivación y referencia de la sesión. Las decisiones y valoraciones se conservan por versiones; una nueva valoración deja desactualizada la decisión previa. El ámbito tiene un ancla canónica para que las materias consulten el mismo acuerdo. No se emiten actas oficiales ni se sustituye el procedimiento colegiado del centro; se trata de un registro local y no de una plataforma multiusuario con firmas. No se calcula una nota final a partir de valoraciones trimestrales ni de evidencias.

Pendientes: pruebas de integración y ejecución, planes individualizados de recuperación, exportación Excel y gestión de materias creadas manualmente sin curso de referencia. Se conserva el aislamiento respecto a la evaluación profesional.

### Refuerzo, recuperación y exportación de ámbitos comunes

El cuaderno competencial permite crear planes individualizados con criterios, objetivos, actividades, instrumentos y fecha de revisión. Cada revisión conserva su estado, observaciones y las referencias de evidencias, comprobando la identidad del alumno y la versión del criterio. Finalizar un plan no actualiza automáticamente ninguna nota.

La opción de pendiente de primero busca exclusivamente registros del año académico anterior con curso primero, el mismo ámbito e identidad coincidente, y un acuerdo extraordinario insuficiente vigente. El docente selecciona la materia de origen y confirma la documentación del centro. Se conserva la referencia al acuerdo de origen y una copia de los criterios. No es un censo oficial de pendientes: los casos no registrados en la aplicación, sin acuerdo extraordinario o de procedencia no verificable requieren contraste externo.

Los informes XLSX de la materia, colectivos o de un alumno, incluyen ficha, alumnado, currículo, últimas evidencias, planes, revisiones y consolidación de la evaluación seleccionada. Solo muestran como acuerdo vigente el registro que corresponde a las últimas valoraciones; los datos del resto del alumnado quedan excluidos del informe individual. Las cadenas potencialmente interpretables como fórmulas se escriben como texto. Son documentos internos de seguimiento, no actas, y deben custodiarse según las reglas de protección de datos del centro.

Se añaden pruebas sintéticas para persistencia, trazabilidad, aislamiento de alumnado y exportación. Su ejecución y las pruebas de interfaz siguen pendientes de verificación. La promoción, titulación, acceso a empresa y gestión de pendientes de origen externo requieren una fase posterior.

### Asistente de decisiones académicas (Canarias, 2026-2027)

En Inicio > Comprobar decisiones académicas se ofrece una comprobación orientativa sin guardar datos personales: promoción de primero a segundo, permanencia, acceso a FEOE y titulación. Ámbito limitado a los cuatro ciclos A&G de nueva ordenación, matrícula presencial ordinaria de dos cursos. Los datos se introducen y contrastan con el expediente por el docente; no se consolidan automáticamente calificaciones ni se emiten actas.

Fuentes: [Resolución de 9 de junio de 2025](https://www.gobiernodecanarias.org/boc/2025/118/2219.html), [modificación de 3 de diciembre de 2025](https://www.gobiernodecanarias.org/boc/2025/249/4298.html), [Resolución de 5 de noviembre de 2024 sobre formación dual](https://www.gobiernodecanarias.org/boc/2024/230/3794.html) y [Resolución de 6 de octubre de 2026 sobre certificación académica de PRL específica](https://www.gobiernodecanarias.org/boc/2026/210/3623.html). Reglas contrastadas el 21/11/2026; revisar modificaciones posteriores y PDFs firmados.

GB: en ordinaria solo se propone promoción con todo superado; en extraordinaria se contempla el límite de seis horas semanales de módulos pendientes y un ámbito común pendiente, o todos los módulos profesionales superados aunque queden ámbitos comunes. GM/GS: 20 % de primero, con excepción colegiada de un solo módulo que exceda el límite; excluir del recuento de promoción los módulos con RA del centro superados y solo FEOE pendiente. El límite ordinario de permanencia no resuelve por sí mismo renuncias, convocatorias, adaptaciones ni autorizaciones excepcionales. FEOE: edad, PRL, valoración colegiada documentada, condiciones de incorporación y certificación específica si la empresa la exige. La certificación del BOC de octubre de 2026 no es acreditación del nivel básico de PRL. Titulación: comprobar totalidad del expediente y proyecto, ámbitos en GB, FEOE superada o exención formal procedente, sin sustituir acuerdo colegiado.

La aplicación no acredita requisitos, no certifica PRL ni decide promoción o titulación. No aplica estas reglas a itinerarios de tres cursos, planes extinguidos, modalidad semipresencial/virtual ni supuestos especiales. Incluye pruebas sintéticas de límites y resultados; se requiere ejecución verificable y validación funcional. Queda pendiente la integración con el expediente de ciclo, el registro motivado de decisiones y los informes de acuerdos.

### Expediente académico interno de ciclo

En **Inicio > Expediente académico**, seleccione un módulo de referencia con grupo y curso identificado en el índice, el alumno y la convocatoria que desea consultar. La aplicación reúne registros del mismo año, ciclo, territorio, grupo y curso; exige coincidencia del código y nombre normalizado del alumno. Muestra los módulos ausentes o duplicados, registros sin clasificación y posibles antecedentes de primero del año anterior. Estos antecedentes requieren contraste y no equivalen a una matrícula o convalidación acreditada.

La vista distingue el cierre profesional vigente (sin convocatoria identificada en el modelo de cierre actual) del acuerdo de ámbito vigente en la convocatoria seleccionada. No utiliza notas provisionales como definitivas. Las materias de un mismo ámbito pueden mostrar el mismo acuerdo, sin convertirse en calificaciones independientes.

El asistente académico recibe datos que el docente introduce tras contrastar el expediente completo. Se registra la actuación o acuerdo motivado con referencia documental, resultado orientativo, entradas, versión normativa y una instantánea SHA-256. Un cambio posterior del expediente invalida la coincidencia con la instantánea anterior, pero no borra el historial. Las actuaciones se consultan en el módulo de referencia donde se registraron. Se puede descargar un informe HTML imprimible de cada actuación, con el aviso expreso de que no constituye acta oficial. No se expiden títulos ni se actualizan notas o expedientes oficiales.

Pendientes: catalogación de optativas y matrículas no incluidas en el índice histórico, cierre profesional por convocatoria, validación de antecedentes y convalidaciones, expediente único interanual y consolidación de decisiones entre módulos, integración automática de requisitos con las normas aplicables, pruebas de ejecución y validación funcional.

### Seguimiento local de formación en empresa (FEOE)

Desde Inicio > Formación en empresa se registran empresas y centros de trabajo, tutores, alumno, régimen, calendario, horas previstas y referencias documentales de convenio, plan, PRL, anexo V, edad e incorporación. La comprobación documental no autoriza la estancia ni sustituye GDCAN. Cada estancia local permite seleccionar RA de los módulos identificados del mismo grupo, curso y alumno, con CE opcionales y lugar de desarrollo (centro, empresa o compartido). Se conserva una instantánea curricular; el plan confirmado queda bloqueado frente a modificaciones directas.

Se registra asistencia efectiva diaria y ausencias con historial; los cambios del mismo día no suman dos veces. El informe de empresa se transcribe por RA como superado/no superado, con observaciones y referencia documental. El docente registra su revisión; una nueva valoración exige una nueva revisión. En el cuaderno profesional > Evidencias cualitativas FEOE del módulo se consultan las valoraciones de planes confirmados, sin convertirlas en notas, y se advierte si el currículo ha cambiado.

Fuentes de seguimiento: [Resolución de 2024, BOC 230, anuncio 3794](https://www.gobiernodecanarias.org/boc/2024/230/3794.html) y [Resolución de 9 de junio de 2025, BOC 118, anuncio 2219](https://www.gobiernodecanarias.org/boc/2025/118/2219.html). Las referencias y las valoraciones son aportadas por el docente. El modelo local todavía necesita gestión de un único plan por alumno con varias estancias, revisiones formales del plan, informes descargables y comprobación integrada de requisitos. No calcula porcentajes de estancia, no firma anexos oficiales, no envía datos a empresas y no altera calificaciones existentes. Las pruebas sintéticas se han añadido, pero requieren ejecución verificable e integración.

### Auditoría: copias verificadas y recuperación aislada

En Ajustes, el botón de copia ZIP utiliza una instantánea SQLite mediante backup API, un directorio temporal exclusivo, nombres únicos y un manifiesto SHA-256 que cubre cada miembro. Se comprueba el archivo antes de publicarlo; las rutas externas y enlaces del almacén se rechazan. Realice la copia sin modificar registros ni cargar documentos: la instantánea de SQLite es consistente, pero el sistema de archivos no comparte una transacción con la base de datos. El ZIP contiene datos personales sin cifrar (solo la clave API portátil se añade cifrada). SHA-256 permite detectar alteraciones accidentales; el manifiesto no está firmado y no autentica el origen de una copia.

Desde el código fuente, con Python 3.13:
- Verificar: `python canarias_backup.py "ruta/copia.zip"`.
- Recuperar: `python canarias_backup.py "ruta/copia.zip" --restore-to "ruta/carpeta_nueva"`.

La recuperación verifica rutas, duplicados, tamaños y hashes; comprueba SQLite y reubica las referencias del almacén. Solo admite una carpeta nueva y no activa ni sobrescribe la base en uso. Conserve la original, cierre la aplicación y compruebe la carpeta recuperada antes de arrancar con EVALUAFP_CANARIAS_DATA_DIR apuntando a ella en modo no portátil. En el modo portable, prepare una carpeta de datos según las reglas de almacenamiento del dispositivo y reinicie. Las copias anteriores sin manifiesto requieren otro procedimiento; no se eliminan. La recuperación aislada también se ofrece desde Ajustes para las copias locales compatibles; la activación permanece separada.

Los cierres de evaluación incluyen las valoraciones FEOE de planes confirmados, la versión de currículo y la revisión docente en su huella. Si cambia la evidencia, el cierre queda desactualizado. Una valoración pendiente de revisión o de cotejo curricular bloquea una nueva nota final; no se traduce una valoración cualitativa en números. Los cierres previos permanecen en el historial.

Se añaden pruebas sintéticas de restauración, detección de rutas maliciosas, alteración de archivos y revisión de cierres. La validación definitiva depende de los resultados de CI y las comprobaciones funcionales.

### Experiencia guiada y recuperación gráfica (auditoría)

Inicio muestra un selector de módulo y cinco tareas ordenadas: preparar, crear pruebas, recoger, corregir y consultar el cuaderno. Las herramientas de gestión académica, FEOE y edición avanzada aparecen en el modo avanzado (también accesible al entrar directamente desde otra pantalla). Cambiar el modo no modifica datos y no reconstruye un formulario en uso; se aplica al abrir una vista. El cuaderno profesional pliega las opciones de configuración ya validadas, las unidades e instrumentos definidos y las exportaciones. Las materias de ámbitos comunes se dirigen al cuaderno competencial.

En Ajustes > Recuperar una copia de seguridad, seleccione una copia local y confirme. La aplicación verifica el manifiesto e intenta recuperar los archivos a una nueva carpeta hermana de la carpeta activa. Muestra su ruta y no modifica la configuración de arranque ni sobrescribe la base de datos actual. Las copias antiguas sin manifiesto no son compatibles con este procedimiento. La activación de los datos recuperados sigue siendo una operación separada, tras cerrar la aplicación y contrastar su contenido. El ZIP no cifra datos académicos. No use copias de origen desconocido.

La ejecución 112 de GitHub Actions verificó 390 pruebas y sintaxis JavaScript antes de esta intervención de UX. La ejecución 126 y el flujo de candidatos verificaron 391 pruebas, sintaxis y arranque en las cuatro plataformas. Quedan pendientes pruebas interactivas reales.


### Candidato auditado: comprobaciones de aceptación

El 21/11/2026 se integró la [solicitud n.º 1](https://github.com/atreyu1968/EvaluaFPCanarias/pull/1) en main (merge dac7c283). Los artefactos identificados arriba se construyeron desde e317fd88, no desde las posteriores modificaciones documentales. La numeración interna de los binarios se conserva; no se ha publicado una nueva release permanente.

Para una prueba de aceptación, extraiga el ZIP de GitHub y luego el archivo de distribución. Compruebe el SHA-256 del archivo interior, arranque desde una carpeta escribible con datos ficticios, compruebe la ventana nativa, el selector de módulo, el flujo guiado, una calificación de prueba y su cierre, el cuaderno competencial, las evidencias FEOE, los informes PDF/XLSX y una copia con recuperación aislada. Compruebe que los datos permanecen después de reiniciar. En macOS utilice el lanzador incluido, en Linux compruebe las bibliotecas gráficas y en Windows WebView2. No desactive globalmente las protecciones del sistema ante avisos de ejecutables sin firma. Anote sistema operativo, arquitectura, versión, resultado y diagnóstico, evitando datos personales. No use datos reales antes de la aceptación.


## Beta.5: distribución verificada (21/11/2026)

La versión 1.2.10-AG-CN-beta.5 está integrada en main: 391 pruebas automatizadas superadas, cuatro compilaciones con autopruebas de arranque y cuatro manuales ilustrados (69 páginas). La ejecución verificada es [44957136836](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44957136836). Falta confirmar la publicación permanente en [GitHub Releases](https://github.com/atreyu1968/EvaluaFPCanarias/releases); hasta entonces, utilizar estos artefactos temporales, con sesión en GitHub y retención hasta el 21/12/2026.

| Sistema | Descarga |
|---|---|
| Windows x64 | [Portable](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44957136836/artifacts/14727529843) |
| Linux x64 | [Portable](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44957136836/artifacts/14727997630) |
| macOS Intel | [Portable](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44957136836/artifacts/14727787313) |
| macOS Apple Silicon | [Portable](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44957136836/artifacts/14727833266) |
| Manuales PDF | [Cuatro documentos ilustrados](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44957136836/artifacts/14728426288) |

El flujo de promoción comprueba que el árbol de código compilado coincide con la integración 67c81480, los trabajos del CI son satisfactorios y las cuatro huellas SHA-256 coinciden antes de publicar. No sobrescribe una publicación anterior. Consulte las [notas](docs/BETA5_RELEASE.md). Los paquetes no disponen de firma comercial ni notarización; queda pendiente aceptación visual y funcional en equipos reales. Use datos ficticios antes de la aceptación y haga una copia externa de los datos anteriores.
