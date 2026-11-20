# Especificación técnica: consulta oficial y anexos horarios (1.2.0 beta)

## Servicios

| Ruta | Método | Acción | Persistencia |
|---|---|---|---|
| `/api/national/boe-search` | POST JSON | Busca normas consolidadas candidatas por denominación del ciclo y ámbito académico | Ninguna |
| `/api/national/boe-inspect` | POST JSON | Obtiene metadatos y análisis para un identificador BOE-A | Ninguna |
| `/api/national/document-preview` | POST multipart | Analiza un PDF/DOCX local y devuelve tabla CSV con horas detectadas | Ninguna |
| `/api/national/hours-table` | POST JSON | Importa la tabla revisada después de la confirmación docente | SQLite, limitado a ámbito y módulo |

Todas las rutas reutilizan el control de sesión local de EvalúaFP. El acceso a la API del BOE utiliza dirección fija HTTPS, identificadores saneados, límite de tiempo y tamaño de respuesta. La API pública exige red para las consultas; no se requiere red para los documentos locales.

## Contratos y seguridad

- La consulta nacional no modifica RA ni CE ni ponderaciones, no aprueba ninguna norma y no determina el currículo autonómico vigente.
- Los documentos se interpretan en memoria. Máximo 15 MB y 80 páginas, OCR opcional hasta ocho páginas escaneadas, sujeto a Tesseract `spa` instalado localmente.
- Las tablas requieren columnas de código, denominación del módulo, horas totales y horas semanales. No se admiten cifras inexistentes ni códigos repetidos contradictorios.
- La importación en bloque requiere coincidencia con el módulo seleccionado; se rechaza una tabla de otro ciclo **antes de insertar registros**.
- La biblioteca diferencia territorio, curso, ciclo y módulo; los calendarios diferencian además el centro. Las horas deben seguir contrastándose con su disposición y modificaciones posteriores.

## Limitaciones y próximos incrementos

1. Crear catálogo vivo de los títulos y módulos oficiales, con actualización controlada y versión normativa por territorio.
2. Completar fuentes y calendarios publicados **por curso académico** para todos los territorios, verificando correcciones y festivos del centro.
3. Mejorar la extracción de tablas complejas y proporcionar instalador opcional de OCR para cada plataforma.
4. Implementar lectura estructurada de RA/CE desde normativa estatal/autonómica, con comparación de versiones y validación docente.
5. Hacer pruebas reales de conectividad BOE, navegadores y portátiles Windows, Linux y macOS con títulos de diferentes familias profesionales.
