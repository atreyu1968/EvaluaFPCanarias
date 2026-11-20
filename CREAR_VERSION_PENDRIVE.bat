@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EvaluaFPCanarias - Version autonoma para memoria USB
set "DESTINO=%~dp0dist\EvaluaFPCanarias_Portatil"
echo.
echo ====================================================
echo    EVALUAFP - CREAR EJECUTABLE PORTATIL PARA USB
 echo ====================================================
echo.
call "%~dp0crear_exe_windows.bat" /auto
if errorlevel 1 goto :error
if not exist "dist\EvaluaFPCanarias.exe" goto :error
if not exist "%DESTINO%" mkdir "%DESTINO%"
copy /y "dist\EvaluaFPCanarias.exe" "%DESTINO%\EvaluaFPCanarias_Portatil.exe" >nul
if errorlevel 1 goto :error
copy /y "%~dp0IMPORTAR_DATOS_DEL_PC.bat" "%DESTINO%\IMPORTAR_DATOS_DEL_PC.bat" >nul
if not exist "%DESTINO%\EvaluaFPCanarias.portable.json" (
  >"%DESTINO%\EvaluaFPCanarias.portable.json" echo {"mode":"portable","data_dir":"EvaluaFPCanarias_Datos","backup_dir":"EvaluaFPCanarias_Copias"}
)
if not exist "%DESTINO%\EvaluaFPCanarias_Datos" mkdir "%DESTINO%\EvaluaFPCanarias_Datos"
if not exist "%DESTINO%\EvaluaFPCanarias_Copias" mkdir "%DESTINO%\EvaluaFPCanarias_Copias"
echo.
echo VERSION PORTATIL PREPARADA EN:
echo %DESTINO%
echo.
echo Copie TODA esta carpeta al pendrive. La ruta de la unidad puede cambiar.
echo La clave API solo se guarda cifrada y necesita contrasena al iniciar.
echo No retire el USB mientras la aplicacion se encuentre abierta.
pause
exit /b 0
:error
echo ERROR: No se ha podido preparar el paquete portatil. Compruebe la compilacion.
pause
exit /b 1
