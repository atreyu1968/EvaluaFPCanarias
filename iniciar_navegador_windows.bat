@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EvaluaFP - Modo navegador opcional
call "%~dp0PREPARAR_ENTORNO.bat" runtime
if errorlevel 1 (pause & exit /b 1)
echo Abriendo EvaluaFP en navegador. Mantenga esta consola abierta.
"%~dp0.venv\Scripts\python.exe" -u "%~dp0app.py" --browser
pause
