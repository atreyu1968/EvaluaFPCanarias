# Índice documental de módulos de Administración y Gestión

**Fuente:** Resolución de la Dirección General de FP de 30/10/2024, Anexos V (Grado Básico) y VI (Grados Medio y Superior), publicada en el BOC n.º 226 de 13/11/2024.

Anexo V CFGB: https://www3.gobiernodecanarias.org/medusa/proyecto/38001553-0006/wp-content/uploads/sites/1326/2024/11/anexo-5-resolucion-instrucciones-implantacion-distribucion-horaria-curriculos-24.pdf

URL: https://www.gobiernodecanarias.org/cmsgob1/export/sites/educacion/web/_galerias/descargas/otros/anexo-6-resolucion-instrucciones-implantacion-distribucion-horaria-curriculos-24.pdf

- CFGM Gestión Administrativa: página BOC 38875 (15 módulos identificados con código).
- CFGS Administración y Finanzas: página BOC 38876 (16 módulos identificados con código).
- CFGS Asistencia a la Dirección: página BOC 38877 (15 módulos identificados con código).
- CFGB Servicios Administrativos: página BOC 38847 (anexo V), **16 referencias** entre módulos profesionales y materias generales. Se excluye Tutoría. Las materias sin código de Real Decreto se identifican como tales.

Se omite el código del **módulo profesional optativo**, porque el anexo no facilita un único código y la oferta concreta depende del centro. Puede añadirse manualmente.

## Seguridad jurídica y funcional

El catálogo proporciona **denominaciones y distribuciones horarias de referencia de 2024** para facilitar la selección, **sin confirmar vigencia para 2026-2027**. No modifica horas de las programaciones ni importa RA/CE. La confirmación exige cotejar la normativa y sus eventuales modificaciones, así como el calendario del curso y las instrucciones de la Consejería.

La selección está disponible en `GET /api/canarias-ag/modules?cycle=<nombre>&academic_year=<AAAA-AAAA>`, con parámetros opcionales `course=1|2` y `territory=Canarias`. Responde con `count`, `total_count`, `filter_course`, referencias de fuente y `status=reference_requires_current_verification`. Todas las entradas informan `curriculum_confirmed=false` y `hours_confirmed=false`. Se exige sesión local y se rechazan otros territorios, ciclos y cursos no válidos. La interfaz ofrece un selector de módulo y un filtro por primero o segundo, manteniendo entrada libre para optativas no catalogadas.
