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

**Artefactos de prueba de la beta.4 (retención de 30 días, requiere inicio de sesión en GitHub):** [Windows x64](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44918796302) · [Linux x64 y macOS Intel/Apple Silicon](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44918800198). La [landing de la edición canaria](docs/index.html#descargas) permite encontrar cada plataforma. Las compilaciones han superado sus autopruebas, pero falta validación visual en sistemas reales.

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

GitHub Actions ha superado **307 pruebas** y ha generado los cuatro paquetes portátiles de la **beta.4**: [Windows x64](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44918796302) y [Linux x64, macOS Intel y macOS Apple Silicon](https://github.com/atreyu1968/EvaluaFPCanarias/actions/runs/44918800198). Los archivos se encuentran en la sección *Artifacts* (requiere acceso a GitHub), con conservación temporal de 30 días. Las pruebas de compilación y arranque automatizado no sustituyen la apertura y revisión visual real en cada sistema operativo; los portátiles no están firmados digitalmente.

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
