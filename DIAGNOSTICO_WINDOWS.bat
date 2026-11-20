@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title Diagnostico de arranque y preparacion EvaluaFP
if not exist "%LOCALAPPDATA%\EvaluaFP\logs" mkdir "%LOCALAPPDATA%\EvaluaFP\logs" 2>nul
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\diagnostico.ps1"
echo.
echo Presione una tecla para terminar.
pause >nul
