# Manual de usuario · macOS Intel y Apple Silicon
EvalúaFP Canarias 1.2.10-AG-CN-beta.5 · Versión preliminar

## Seleccionar arquitectura
En el menú Apple > Acerca de este Mac, compruebe si aparece Procesador Intel o Chip de Apple. Descargue macos_x64 para Intel o macos_arm64 para Apple Silicon. Los paquetes se construyen en macOS 15; no se garantiza compatibilidad con versiones anteriores.

## Arranque
Extraiga el ZIP conservando la estructura de la carpeta, incluida la aplicación .app y el fichero INICIAR_EVALUAFP.command. Abra este último para fijar la ubicación portátil de los datos. Si el sistema impide abrir por falta de notarización, consulte las políticas del centro y las opciones de seguridad para aplicaciones de origen conocido; no desactive Gatekeeper globalmente. Compruebe que la carpeta es escribible.

## Comprobar integridad
En Terminal, ejecute `shasum -a 256 archivo.zip` y compare con el fichero .sha256. Si falla el inicio, compruebe que ha elegido la arquitectura correcta.

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
