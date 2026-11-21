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
