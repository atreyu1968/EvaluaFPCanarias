@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "ORIGEN=%LOCALAPPDATA%\EvaluaFPCanarias"
set "DESTINO=%~dp0EvaluaFPCanarias_Datos"
set "COPIAS=%~dp0EvaluaFPCanarias_Copias"
echo.
echo IMPORTAR DATOS DEL EQUIPO A EVALUAFP PORTATIL
echo.
echo ATENCION: Cierre antes todas las ventanas de EvaluaFPCanarias.
echo Los datos del equipo NO se borraran.
echo.
if not exist "%ORIGEN%\datos\evaluafp.sqlite3" (
  echo ERROR: No existe una base EvaluaFPCanarias instalada en este equipo.
  pause
  exit /b 1
)
if exist "%DESTINO%\datos\evaluafp.sqlite3" (
  echo ERROR: Este USB ya tiene una base de datos. No se permite mezclar ni sobrescribir datos.
  echo Use antes las opciones de exportacion/copia de seguridad si desea combinar registros.
  pause
  exit /b 1
)
choice /c SN /m "Confirma que EvaluaFPCanarias esta cerrado y desea COPIAR los datos existentes"
if errorlevel 2 exit /b 1
if not exist "%DESTINO%" mkdir "%DESTINO%"
robocopy "%ORIGEN%" "%DESTINO%" /E /R:1 /W:1 /XD "%ORIGEN%\copias" >nul
if errorlevel 8 goto :error
if exist "%ORIGEN%\copias" (
  if not exist "%COPIAS%" mkdir "%COPIAS%"
  robocopy "%ORIGEN%\copias" "%COPIAS%" /E /R:1 /W:1 >nul
  if errorlevel 8 goto :error
)
echo.
echo Datos importados. La primera apertura portatil adaptara las rutas de los originales.
echo La clave API del gestor de credenciales de Windows NO se copia: debera cifrarla en Ajustes.
echo.
pause
exit /b 0
:error
echo ERROR: No se ha completado la copia. Compruebe espacio libre/permisos y evite abrir EvaluaFPCanarias.
pause
exit /b 1
