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

## Adaptaciones realizadas

1. Interfaz identificada como «EvalúaFP Canarias · Administración y Gestión».
2. Selector de comunidad limitado a Canarias y selector de ciclo con los cuatro títulos identificados.
3. Validación **en el servidor**: no admite crear módulos de otro territorio o ciclo ajeno a la familia en esta edición.
4. Consulta GET autenticada \`/api/canarias-ag/catalog\` con títulos, fuentes y estado de verificación curricular.
5. Almacenamiento SQLite independiente: directorio local \`EvaluaFPCanarias\` y carpetas portátiles \`EvaluaFPCanarias_Datos\` y \`EvaluaFPCanarias_Copias\`.
6. Variables de entorno propias: \`EVALUAFP_CANARIAS_DATA_DIR\`, \`EVALUAFP_CANARIAS_PORTABLE\` y \`EVALUAFP_CANARIAS_PORTABLE_HOME\`.
7. Identidad de credenciales IA separada del proyecto original. La IA continúa siendo opcional y requiere supervisión docente.
8. Conserva la importación/revisión de programaciones, RA/CE, evaluación, exámenes, informes, corrección asistida, FEOE y calendarios de la base.
9. Fiscalidad didáctica canaria: los casos de tributación indirecta deben utilizar IGIC cuando corresponda y verificar los tipos aplicables.

## IMPORTANTE: fuentes y currículo

Los **títulos** están identificados, pero esta beta **no contiene un catálogo de módulos, horas, RA y CE completo y validado para 2026-2027**. Para crear un módulo se elige su ciclo y se incorpora su programación o documentación oficial. La herramienta permite revisar y confirmar las propuestas del docente, sin certificar normas por IA ni inventar resultados.

Fuentes normativas de referencia:
- [LO 3/2022](https://www.boe.es/eli/es/lo/2022/03/31/3/con)
- [RD 659/2023](https://www.boe.es/eli/es/rd/2023/07/18/659/con)
- [Currículos de CFGB Canarias](https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/fpgb/curriculos_fpgb/)
- [Oferta oficial de títulos Canarias](https://www.gobiernodecanarias.org/educacion/web/formacion_profesional/ensenanzas/titulos/)
- [BOC 2026/227 (Grados B y C nivel 1)](https://www.gobiernodecanarias.org/boc/2026/227/3917.html)

## Instalación y pruebas

Requiere Python 3.13 y dependencias de \`requirements.txt\`. En una carpeta nueva:
\`\`\`bash
python -m pip install -r requirements.txt
python app.py
\`\`\`
En Windows pueden utilizarse \`INICIAR_EVALUAFP.bat\` y \`CREAR_VERSION_PENDRIVE.bat\` (el nombre histórico del primer lanzador se conserva temporalmente). Los scripts de compilación se han diferenciado para producir paquetes EvaluaFPCanarias.

\`\`\`bash
python -m unittest discover -s tests -v
\`\`\`

GitHub Actions contiene comprobación de pruebas y un flujo manual de portátiles Linux/macOS. **No se afirma que haya ejecutables generados o validados para esta edición** hasta verificar los artefactos y una prueba real de apertura en cada sistema.

## Documentación

[Guía de la edición canaria](docs/CANARIAS_ADMINISTRACION_GESTION.md) · [Documentación de la base](README_BASE_EVALUAFP.md) · [Repositorio de la base](https://github.com/atreyu1968/EvaluaFP)

**Protección de datos:** no transmitir a servicios IA datos identificativos de alumnado sin base jurídica y autorización correspondiente. Mantener copias de seguridad, restringir el acceso al equipo y verificar cualquier calificación antes de considerarla definitiva.

© Francisco Javier González Rolo. Edición para uso docente.
