@echo off
setlocal EnableExtensions
cd /d "%~dp0"
title EvaluaFPCanarias - Instalador sin winget

echo.
echo =========================================================
echo  EVALUAFP 1.0.0 - CREAR INSTALADOR SIN WINGET
echo =========================================================
echo.
echo [1/2] Buscando un EXE ya compilado y actualizado...
set "EXE=%~dp0dist\EvaluaFPCanarias.exe"
set "REBUILD=0"
if not exist "%EXE%" set "REBUILD=1"
if exist "%EXE%" (
  powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\comprobar_exe.ps1" -ProjectRoot "%~dp0"
  if errorlevel 1 set "REBUILD=1"
)
if "%REBUILD%"=="0" (
  echo Encontrado: "%EXE%"
  echo Ejecutando autocomprobacion del EXE existente...
  "%EXE%" --selftest
  if errorlevel 1 set "REBUILD=1"
)
if "%REBUILD%"=="1" (
  echo No hay un EXE valido/actualizado. Se compilara ahora.
  call "%~dp0crear_exe_windows.bat" /auto
  if errorlevel 1 goto :error
)
if not exist "%EXE%" goto :error

echo.
echo [2/2] Buscando o instalando Inno Setup 6, y creando instalador...
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\crear_instalador.ps1" -ProjectRoot "%~dp0"
if errorlevel 1 goto :error
if not exist "%~dp0dist\Instalar_EvaluaFPCanarias.exe" goto :error

echo.
echo EXITO: "%~dp0dist\Instalar_EvaluaFPCanarias.exe"
echo EXE portatil: "%EXE%"
pause
exit /b 0

:error
echo.
echo No se ha generado un instalador nuevo.
echo El EXE existente sigue estando en dist\EvaluaFPCanarias.exe si se ha compilado.
echo Registro: %LOCALAPPDATA%\EvaluaFPCanarias\logs\compilacion_inno.log
pause
exit /b 1
