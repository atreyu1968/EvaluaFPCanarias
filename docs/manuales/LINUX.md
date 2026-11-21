# Manual de usuario · Linux x64
EvalúaFP Canarias 1.2.10-AG-CN-beta.5 · Versión preliminar

## Requisitos y arranque
Binario x86-64 construido en Ubuntu 22.04. Necesita sesión gráfica y bibliotecas compatibles con Qt WebEngine; no se garantiza toda distribución. Extraiga el TAR.GZ manteniendo directorios y permisos: `tar -xzf archivo.tar.gz`. Desde la carpeta extraída ejecute `./INICIAR_EVALUAFP.sh`. Si falta permiso, `chmod +x INICIAR_EVALUAFP.sh`. No ejecute como root. Si Qt indica bibliotecas ausentes, consulte la documentación de su distribución y el departamento TIC.

## Comprobar integridad
Ejecute `sha256sum archivo.tar.gz` y compare con el fichero .sha256. En caso de fallo de arranque, ejecute el lanzador desde una terminal de la sesión gráfica y conserve el diagnóstico sin datos personales.

## Primer uso
1. Descargue únicamente el paquete de su arquitectura desde GitHub Releases. Compare su SHA-256 con el fichero .sha256 correspondiente.
2. Extraiga todo el contenido en una carpeta escribible, no ejecute dentro del ZIP. No mezcle archivos de versiones distintas. Conserve un respaldo externo de los datos anteriores.
3. Inicie con datos ficticios. Compruebe que se abre la ventana, seleccione Inicio > Preparar el módulo y cree un módulo de prueba con ciclo, grupo, curso y año.
4. Revise currículo, programación y ponderaciones. En el cuaderno registre evidencias y valide las notas únicamente después de contrastarlas.
5. Cierre y vuelva a abrir. Verifique persistencia de datos. Ajustes > Almacenamiento permite crear una copia verificable; recuperar una copia crea una carpeta separada, no la activa.
6. La clave API es opcional para gestión local; no remita datos de alumnado a servicios externos sin autorización. La clave cifrada no cifra SQLite ni los originales.

## Criterios de aceptación
- Ventana nativa, navegación y selector de módulo correctos.
- Creación de prueba, registro de evidencias, cierre y exportaciones PDF/XLSX.
- Comprobación del cuaderno de ámbitos comunes en GB; expediente y FEOE en modo avanzado.
- Copia ZIP, recuperación aislada y persistencia después de reiniciar.

## Diagnóstico
Anote sistema, arquitectura, versión, operación y mensaje de error sin incluir datos personales. Pruebe una carpeta escribible nueva y no borre la original. La beta no cuenta con firma comercial ni notarización; no desactive globalmente las protecciones del equipo. Dirija incidencias al repositorio de EvaluaFP Canarias.
