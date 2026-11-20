# Guía de uso — Generador inteligente EvalúaFP 1.1.6 beta

## Antes de empezar

1. Cree el módulo indicando el **ciclo formativo y la denominación oficial** del módulo.
2. Seleccione «Preparar módulo» y «Crear mi programación», o «Ya tengo una programación» para recuperar el contenido original.
3. Incorpore el currículo RA/CE desde documentación o disposición verificada y confirme explícitamente su correspondencia con el módulo y curso. No se suponen resultados inexistentes.
4. Con RA y CE confirmados, se rellenarán **27 apartados pedagógicos** con un borrador local que puede modificarse sin conectar con IA externa.
5. Si desea propuestas desarrolladas, configure su API en «IA y almacenamiento» y pulse «Desarrollar todos los apartados con IA». El programa pedirá autorización y **no sustituirá** los campos que ya haya editado el profesor.
6. Para mejorar un texto escrito manualmente pulse «Mejorar redacción con IA», compare ambos textos y elija aplicar la propuesta o conservar su original.
7. En evaluación, revise la **cuadrícula RA/CE**: reparto automático igual por CE o reparto manual completo con el 100,00 % validado. La aplicación impide cambiar pesos con cierres finales previos desde ese asistente.
8. En temporalización, compruebe las horas totales/semanales y la fuente de la distribución. **Confirme** el dato: el Gantt no debe considerarse válido hasta verificarlo. Añada el horario real por días y festivos propios del centro.
9. Genere unidades por RA o cree su matriz manual. Las horas se distribuyen por evaluaciones y se muestran los déficits. Puede solicitar con IA instrumentos y recursos específicos de las unidades y aceptarlos sin sobrescribir textos personalizados.
10. Marque los CE previstos para FEOE y revise su participación real en RA, fechas y plan formativo. Añada actividades complementarias y extraescolares.
11. Exporte el borrador a Word o PDF. La portada, índice, tablas y Gantt se generan automáticamente; el documento queda pendiente de revisión y aprobación docente.

## Procedencia y verificación

- Las referencias legales que se muestran son una **lista documentada para comprobar**, no un informe de vigencia jurídica automatizado. Los enlaces oficiales aparecen en el propio borrador.
- La tabla horaria local cubre únicamente Gestión Administrativa y Administración y Finanzas de Canarias, con fuente 2024. El usuario debe consultar las modificaciones aplicables al curso vigente antes de confirmar.
- El calendario de Canarias 2026-2027 contiene fechas generales y festivos conocidos, no todos los días específicos del municipio o del centro; deben completarse en el formulario.
- Sin una clave de IA no hay llamadas al proveedor: siguen disponibles los textos básicos y exportaciones locales.
- Los datos del docente tienen prioridad. Cada propuesta muestra origen o queda identificada como pendiente de revisión.
- El porcentaje FEOE de CE es **pedagógico orientativo**, no un cálculo automático de cumplimiento de RA a nivel de ciclo.

## Protecciones de datos

No incluya datos personales identificativos del alumnado, diagnósticos individuales, documentación empresarial confidencial ni contenidos de terceros sin las autorizaciones necesarias en textos enviados a servicios externos. Las claves se guardan según los mecanismos locales de cifrado/credenciales de la aplicación.

## Compilación y pruebas Windows

Desde el ZIP de fuentes descomprimido, ejecute `CREAR_VERSION_PENDRIVE.bat`. Antes de distribuir el EXE a docentes reales, realice copia de seguridad de su SQLite, pruebas de importación y exportación y una revisión con datos ficticios.
