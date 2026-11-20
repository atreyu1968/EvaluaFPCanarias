@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EvaluaFP Local 0.7
echo.
echo ============ EVALUAFP LOCAL 0.7 ============
if not exist "app.py" goto :extract
if not exist "web\index.html" goto :extract
call "%~dp0PREPARAR_ENTORNO.bat" runtime
if errorlevel 1 goto :failed
echo.
echo INICIANDO EVALUAFP EN VENTANA DE ESCRITORIO...
echo Esta consola se mantiene abierta en modo desarrollo; el EXE no necesita consola.
"%~dp0.venv\Scripts\python.exe" -u "%~dp0app.py"
if errorlevel 1 goto :failed
echo La aplicacion se ha cerrado.
pause
exit /b 0
:extract
echo ERROR: Extraiga el ZIP completo antes de ejecutar este archivo.
goto :failed
:failed
echo ERROR al iniciar. Consulte los mensajes anteriores.
pause
exit /b 1
