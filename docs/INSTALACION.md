# Instalación y distribución de EvalúaFP

## Requisitos

- Windows 10/11 de 64 bits.
- Microsoft Edge WebView2 Runtime para la ventana de escritorio (puede estar ya instalado).
- Conexión a Internet en la preparación inicial y para llamadas a proveedores de IA.
- Permiso de escritura en los directorios seleccionados para datos y copias.

## Usar desde el código fuente

1. Descomprime el proyecto en una carpeta nueva.
2. Ejecuta `PREPARAR_ENTORNO.bat` o directamente `INICIAR_EVALUAFP.bat`.
3. El preparador utiliza `uv` para gestionar Python en el entorno del usuario y crear `.venv`, instala bibliotecas y realiza comprobaciones.
4. El lanzador abre la aplicación.

Si falla, consulta los mensajes y `DIAGNOSTICO_WINDOWS.bat`, junto con `%LOCALAPPDATA%\EvaluaFP\logs`.

## EXE autónomo

Ejecuta `crear_exe_windows.bat`. Antes de compilar se ejecuta el conjunto de pruebas; PyInstaller genera `dist\EvaluaFP.exe` y se ejecuta el autocontrol `--selftest`. Debe comprobarse finalmente la apertura gráfica y la impresión en un PC Windows real.

## Instalador Inno Setup

Ejecuta `crear_instalador_windows.bat` con el EXE compilado. Inno Setup 6/7 es una herramienta **de compilación**: no la necesitan los usuarios finales. Si no se detecta, sigue las instrucciones del script o consulta https://jrsoftware.org/inno-setup/downloads . El instalador resultante se genera en `dist\Instalar_EvaluaFP.exe` si Inno Setup termina correctamente.

## Pendrive

`CREAR_VERSION_PENDRIVE.bat` crea `dist\EvaluaFP_Portatil\`. Copia toda la carpeta al USB; los datos y backups se mantienen en rutas relativas. `IMPORTAR_DATOS_DEL_PC.bat` permite copiar los archivos locales existentes cuando corresponda, sin sobrescribir bases que ya existan en el USB.

## Exportación e importación Additio

Los archivos curriculares se obtienen desde Evaluación del módulo y se separan en RA, CE y relaciones/ponderaciones. Las calificaciones se proporcionan por **RA y CE**, no por instrumentos. Comprueba el formato real de tu instancia de Additio antes de importar.
