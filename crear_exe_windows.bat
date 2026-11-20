@echo off
setlocal EnableExtensions
REM Fuerza UTF-8 en tests y PyInstaller (Windows usa cp1252 por defecto).
set "PYTHONUTF8=1"
set "PYTHONIOENCODING=utf-8"
cd /d "%~dp0"
title EvaluaFPCanarias - Preparar y compilar EXE
echo.
echo ========================================================
echo  EVALUAFP 1.2.10 BETA - CREAR EXE PARA WINDOWS
 echo ========================================================
echo.
echo [1/4] Detectando/instalando Python y dependencias...
call "%~dp0PREPARAR_ENTORNO.bat" build
if errorlevel 1 goto :error
set "PYTHON=%~dp0.venv\Scripts\python.exe"
echo.
echo [2/4] Comprobando el programa con las pruebas automatizadas...
"%PYTHON%" -m unittest discover -s tests -v
if errorlevel 1 goto :tests_error
echo.
echo [3/4] Generando el ejecutable sin dependencia de Python externo...
"%PYTHON%" -m PyInstaller --noconfirm --clean --onefile --windowed --name "EvaluaFPCanarias" --icon "assets\EvaluaFP.ico" --add-data "web;web" --collect-all fitz --collect-all PIL --collect-all docx --collect-all keyring --collect-all webview --collect-all reportlab --collect-all cryptography --collect-all xlsxwriter --hidden-import xlwt --hidden-import webview.platforms.winforms --hidden-import desktop_caption --hidden-import general_calendar_library --hidden-import calendar_versions --hidden-import calendar_document --hidden-import calendar_annex --hidden-import calendar_ai app.py
if errorlevel 1 goto :build_error
if not exist "dist\EvaluaFPCanarias.exe" (
  echo ERROR: No existe dist\EvaluaFPCanarias.exe tras finalizar PyInstaller.
  echo Revise la salida de PyInstaller y, si es necesario, el historial del antivirus.
  goto :error
)
echo.
echo [4/4] Probando que el ejecutable abre sus componentes y SQLite...
echo Ejecutable: "%~dp0dist\EvaluaFPCanarias.exe"
if not exist "%~dp0dist\EvaluaFPCanarias.exe" (
  echo ERROR: El ejecutable ha desaparecido de dist antes de la prueba.
  echo Revise el historial de proteccion de Windows Defender.
  goto :error
)
"%~dp0dist\EvaluaFPCanarias.exe" --selftest
if errorlevel 1 (
  echo ERROR: La prueba interna del EXE no ha terminado correctamente.
  echo Revise el registro_aplicacion.log en la carpeta de datos de EvaluaFPCanarias.
  goto :error
)
echo Verificacion del EXE completada.
echo [4/4] Comprobando el archivo generado...
for %%I in ("dist\EvaluaFPCanarias.exe") do echo %%~fI - %%~zI bytes
if not exist "dist\EvaluaFPCanarias.exe" (
  echo ERROR: PyInstaller no ha dejado el ejecutable en dist\EvaluaFPCanarias.exe.
  echo Compruebe si Windows Defender lo ha puesto en cuarentena.
  goto :error
)
echo.
echo EXITO: dist\EvaluaFPCanarias.exe
echo Este archivo incorpora Python y las bibliotecas necesarias.
echo Compruebe su apertura real en Windows; debe mostrar ventana propia.
if /i "%~1"=="/auto" exit /b 0
pause
exit /b 0
:tests_error
echo.
echo ERROR: Las pruebas automatizadas han fallado; PyInstaller NO se ha ejecutado.
echo Consulte el primer traceback de Python, no un supuesto bloqueo de Windows Defender.
goto :error
:build_error
echo.
echo ERROR: PyInstaller ha fallado. Compruebe los mensajes anteriores.
goto :error
:error
echo.
echo ERROR: Compilacion detenida. Consulte el mensaje anterior.
echo Registro: %LOCALAPPDATA%\EvaluaFPCanarias\logs\preparacion_windows.log
if /i "%~1"=="/auto" exit /b 1
pause
exit /b 1
