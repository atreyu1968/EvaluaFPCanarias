# Seguridad de EvalúaFP Local

## Datos de carácter personal

El repositorio está destinado al **código fuente**, no al almacenamiento de datos de alumnado ni expedientes de evaluación. No subas nunca archivos `.sqlite3`, imágenes de exámenes, PDFs de entregas, exportaciones reales de notas, contraseñas, tokens ni claves API.

## Claves API

Las claves se guardan cifradas de forma reversible para poder llamar al proveedor, y requieren contraseña maestra. No se deben guardar claves reales en archivos de configuración versionados ni en el código. Un hash irreversible no sirve para recuperar una clave que deba enviarse en una solicitud autorizada a la API.

## Configuraciones portátiles

El ejecutable puede utilizar una carpeta de datos en USB. El cifrado de la clave API **no cifra la base SQLite ni los exámenes**: utiliza cifrado de disco/pendrive y copias externas. Expulsa el dispositivo solo tras cerrar la aplicación.

## Servicios externos de IA

Antes de procesar exámenes reales, consulta el marco de protección de datos, acuerdos con proveedores y las medidas del centro. El docente debe revisar transcripciones y calificaciones. No cargues datos personales innecesarios a proveedores externos.

## Notificación de vulnerabilidades

No publiques credenciales ni datos personales en incidencias públicas de GitHub. Contacta de forma privada con el mantenedor del repositorio.
