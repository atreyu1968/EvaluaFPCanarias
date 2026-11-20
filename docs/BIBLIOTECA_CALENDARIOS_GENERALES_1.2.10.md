# Uso de la biblioteca general de calendarios FP — 1.2.10 beta

## ¿En qué se diferencia del historial del centro?
La **biblioteca general** conserva solo fechas compartibles por los centros de un ámbito educativo y curso escolar. El **historial del centro** conserva su programación particular, que puede incluir un municipio, una isla, los cierres de evaluación y los días de organización.

Ambas bibliotecas coexisten. Ni las versiones generales sustituyen el calendario aprobado por un centro ni se cambian calificaciones o RA/CE.

## Guardar una referencia general
1. Abra un módulo del curso correspondiente y acceda a **Temporalización y FEOE**.
2. Localice la resolución oficial que se aplica a la modalidad de FP del módulo. Incluya su URL HTTPS, denominación, fecha y correcciones.
3. Introduzca las fechas, vacaciones y días generales en el formulario.
4. Quite de la lista de días generales las festividades exclusivas de una isla, localidad o centro. Manténgalas, si procede, en **Días no lectivos adicionales**.
5. Confirme el calendario del módulo. En «Biblioteca de calendarios generales FP del territorio», marque la declaración específica de ámbito general y pulse **Archivar calendario general**.
6. Se crea una revisión con fuente y huella SHA-256. Si coincide con la última, no se duplica.

**Caso especial Canarias:** la aplicación rechaza festividades insulares conocidas cuando se intenta guardarlas entre los días generales de toda Canarias. Eso no sustituye la comprobación del calendario insular, municipal o del centro.

## Reutilizar y actualizar
Al abrir otro módulo del mismo territorio y curso, la biblioteca mostrará las revisiones locales disponibles. Pulse **Cargar propuesta general** para transferir fechas de clase, periodos vacacionales, días generales y fuente.

Se mantienen sin cambios las horas, la FEOE, los criterios, las evaluaciones, el municipio y los días adicionales. La confirmación del calendario se restablece en **pendiente**. Antes de usar la temporalización, revise festivos locales, insulares y de centro y las modificaciones de la disposición.

Utilice **Comparar** para identificar cambios entre revisiones. El sistema conserva la anterior; no decide por sí mismo cuál tiene vigencia.

## Alcance territorial
Se admiten los 19 ámbitos educativos españoles (17 comunidades autónomas, Ceuta y Melilla), pero la existencia de la estructura de datos **no equivale a haber importado o verificado automáticamente todos sus calendarios escolares**. Las fuentes deben incorporarse y cotejarse para cada territorio/curso. La biblioteca está almacenada en el dispositivo y no sincroniza información entre equipos.

## Compilación
En Windows, extraiga el ZIP del código fuente de esta versión y ejecute `crear_exe_windows.bat`. El script prepara dependencias, ejecuta las pruebas y compila con PyInstaller. Es necesario comprobar el EXE resultante en el equipo real, incluido el funcionamiento de la biblioteca SQLite tras reiniciar.