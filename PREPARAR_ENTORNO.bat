@echo off
setlocal EnableExtensions
cd /d "%~dp0"
set "MODO=%~1"
if /i not "%MODO%"=="build" set "MODO=runtime"
echo.
echo ==========================================================
echo  EVALUAFP LOCAL 0.6.1 - PREPARACION AUTOMATICA
 echo ==========================================================
echo.
echo Se buscara Python compatible o se instalara Python oficial
 echo solo para el usuario actual, sin modificar el PATH.
echo.
where powershell.exe >nul 2>&1
if errorlevel 1 goto :powershell_falta
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\preparar_entorno.ps1" -Mode "%MODO%"
if errorlevel 1 exit /b 1
exit /b 0
:powershell_falta
echo ERROR: No se ha encontrado Windows PowerShell.
echo Se necesita Windows 10 o 11 con PowerShell disponible.
exit /b 2
