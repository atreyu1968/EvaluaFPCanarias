# Manual de usuario · Windows x64
EvalúaFP Canarias 1.2.10-AG-CN-beta.5 · Versión preliminar

## Requisitos y arranque
Windows 10/11 de 64 bits y Microsoft Edge WebView2 Runtime compatible. No necesita Python instalado. Descomprima EvaluaFPCanarias_Portatil_1.2.10-AG-CN-beta.5_windows_x64.zip y abra EvaluaFPCanarias.exe junto al archivo portable.json. La configuración se conserva en EvaluaFPCanarias.portable.json. No ejecute directamente desde el archivo comprimido.

## Comprobar integridad
En PowerShell: `Get-FileHash -Algorithm SHA256 "ruta_del_paquete.zip"`. Compare la salida con el fichero de huella. Ante avisos de seguridad, consulte las políticas TIC del centro. Si el EXE no abre, revise WebView2, permisos, espacio disponible y los registros de inicio de la carpeta de datos si existen.

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
