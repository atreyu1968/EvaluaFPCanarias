# EvaluaFP 0.6.1 - Correccion de validacion de Python en PowerShell 5.1.
# uv 0.13.7 x64, archivo oficial y SHA-256 publicado en el manifiesto Scoop.
# Python 3.13 se descarga en %LOCALAPPDATA%\EvaluaFP\python-gestionado.
param([ValidateSet('runtime','build')][string]$Mode = 'runtime')
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$Root = Split-Path -Parent $PSScriptRoot
$DataDir = Join-Path $env:LOCALAPPDATA 'EvaluaFP'
$LogDir = Join-Path $DataDir 'logs'
$ToolsDir = Join-Path $DataDir 'tools\uv'
$UvExe = Join-Path $ToolsDir 'uv.exe'
$UvZip = Join-Path $DataDir 'descargas\uv-0.13.7-x64.zip'
$VenvDir = Join-Path $Root '.venv'
$Python = Join-Path $VenvDir 'Scripts\python.exe'
$UvVersion = '0.13.7'
# SHA-256 de https://github.com/ScoopInstaller/Main/blob/master/bucket/uv.json
# para uv-x86_64-pc-windows-msvc.zip, version 0.13.7.
$UvSha = '0cdc5b38fe5a8168ed6a25814f5ba43c21d313dd3187314fccb37b7cec46e021'
$UvUrls = @(
  'https://github.com/astral-sh/uv/releases/download/0.13.7/uv-x86_64-pc-windows-msvc.zip',
  'https://releases.astral.sh/github/uv/releases/download/0.13.7/uv-x86_64-pc-windows-msvc.zip'
)
function Step([string]$message) { Write-Host $message -ForegroundColor Cyan }
# La comprobacion se realiza mediante un archivo .py, no con `python -c`.
# PowerShell 5.1 puede alterar las comillas de argumentos de ejecutables externos,
# provocando falsos negativos al ejecutar `python -c` con codigo entrecomillado.
$PythonProbe = Join-Path $PSScriptRoot 'verificar_python.py'
$DependenciesProbe = Join-Path $PSScriptRoot 'verificar_dependencias.py'
function Valid-Python([string]$Exe, [bool]$VerboseOutput = $false) {
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) {
        if ($VerboseOutput) { Write-Host "NO EXISTE el interprete: $Exe" -ForegroundColor Yellow }
        return $false
    }
    if (-not (Test-Path -LiteralPath $PythonProbe -PathType Leaf)) {
        throw "Falta el archivo de verificacion: $PythonProbe. Extraiga el ZIP completo."
    }
    $output = @()
    try {
        # El archivo, pasado como argumento independiente, evita el problema
        # con comillas dobles internas de Windows PowerShell 5.1.
        $output = @(& $Exe $PythonProbe 2>&1)
        $code = $LASTEXITCODE
        if ($VerboseOutput -or $code -ne 0) {
            Write-Host "COMPROBANDO: $Exe" -ForegroundColor Cyan
            foreach ($line in $output) { Write-Host "  $line" }
            Write-Host "Resultado verificacion Python: codigo $code"
        }
        return ($code -eq 0)
    } catch {
        Write-Host "ERROR al ejecutar $Exe : $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}
function Valid-Uv {
    if (-not (Test-Path -LiteralPath $UvExe -PathType Leaf)) { return $false }
    try {
        $v = (& $UvExe --version 2>&1 | Out-String).Trim()
        return (($LASTEXITCODE -eq 0) -and $v.StartsWith("uv $UvVersion"))
    } catch { return $false }
}
function Run-Uv([string[]]$Arguments, [string]$Context) {
    Write-Host "EJECUTANDO: uv $($Arguments -join ' ')"
    & $UvExe @Arguments
    $code = $LASTEXITCODE
    if ($code -ne 0) {
        throw "$Context (codigo $code). Revise el registro $LogDir\preparacion_windows.log; si hay un proxy o antivirus, se mostrara en el error de uv."
    }
}
function Install-Uv {
    if (Valid-Uv) { Step "[1/5] Gestor uv $UvVersion ya instalado y comprobado."; return }
    Step '[1/5] Descargando gestor portatil de Python (uv)...'
    New-Item -ItemType Directory -Path (Split-Path -Parent $UvZip), $ToolsDir -Force | Out-Null
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    $validZip = $false
    if (Test-Path -LiteralPath $UvZip -PathType Leaf) {
        $validZip = ((Get-FileHash -LiteralPath $UvZip -Algorithm SHA256).Hash.ToLowerInvariant() -eq $UvSha)
    }
    if (-not $validZip) {
        if (Test-Path -LiteralPath $UvZip) { Remove-Item -LiteralPath $UvZip -Force }
        $errors = @()
        foreach ($url in $UvUrls) {
            try {
                Write-Host "Descargando desde: $url"
                Invoke-WebRequest -Uri $url -OutFile $UvZip -UseBasicParsing -MaximumRedirection 8 -ErrorAction Stop
                $actual = (Get-FileHash -LiteralPath $UvZip -Algorithm SHA256).Hash.ToLowerInvariant()
                if ($actual -ne $UvSha) {
                    throw "SHA-256 no coincide: esperado $UvSha, obtenido $actual"
                }
                $validZip = $true
                break
            } catch {
                $errors += "$url : $($_.Exception.Message)"
                if (Test-Path -LiteralPath $UvZip) { Remove-Item -LiteralPath $UvZip -Force }
            }
        }
        if (-not $validZip) {
            throw "No se pudo descargar el gestor uv oficial o fallo su SHA-256. Detalles: $($errors -join ' // '). Consulte $LogDir\preparacion_windows.log"
        }
    }
    $tempDir = Join-Path $env:TEMP ('EvaluaFP-uv-' + [guid]::NewGuid().ToString('N'))
    try {
        New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
        Expand-Archive -LiteralPath $UvZip -DestinationPath $tempDir -Force
        $candidate = Get-ChildItem -LiteralPath $tempDir -Filter 'uv.exe' -File -Recurse | Select-Object -First 1
        if ($null -eq $candidate) { throw 'El archivo ZIP verificado no contiene uv.exe.' }
        Copy-Item -LiteralPath $candidate.FullName -Destination $UvExe -Force
    } finally {
        if (Test-Path -LiteralPath $tempDir) { Remove-Item -LiteralPath $tempDir -Recurse -Force -ErrorAction SilentlyContinue }
    }
    if (-not (Valid-Uv)) { throw 'uv.exe se ha descargado pero no puede ejecutarse. Revise la politica de seguridad de Windows.' }
    Write-Host "uv validado en $UvExe" -ForegroundColor Green
}
function Prepare {
    if (-not [Environment]::Is64BitOperatingSystem) { throw 'EvaluaFP requiere Windows de 64 bits.' }
    if ([Environment]::OSVersion.Platform -ne 'Win32NT') { throw 'Este preparador solo se ejecuta en Windows.' }
    foreach ($required in @('app.py','requirements.txt','requirements-build.txt','web\index.html')) {
        if (-not (Test-Path -LiteralPath (Join-Path $Root $required))) { throw "Falta $required. Extraiga todo el ZIP." }
    }
    Install-Uv
    # No se tocan el registro, el PATH ni las instalaciones globales del equipo.
    $env:UV_PYTHON_INSTALL_DIR = Join-Path $DataDir 'python-gestionado'
    $env:UV_CACHE_DIR = Join-Path $DataDir 'uv-cache'
    $env:UV_PYTHON_INSTALL_BIN = '0'
    $env:UV_NO_CONFIG = '1'
    $env:UV_NO_PROGRESS = '1'
    Step '[2/5] Instalando/verificando Python 3.13 de 64 bits dentro de EvaluaFP...'
    Run-Uv @('python','install','3.13') 'No se pudo preparar Python gestionado por uv'
    if (-not (Valid-Python $Python $true)) {
        if (Test-Path -LiteralPath $VenvDir) {
            Write-Host 'El entorno anterior no supera la prueba. Reconstruyendo solo .venv (los datos SQLite no se modifican)...' -ForegroundColor Yellow
            Remove-Item -LiteralPath $VenvDir -Recurse -Force
        }
        Run-Uv @('venv','--python','3.13','--managed-python',$VenvDir) 'No se pudo crear el entorno virtual'
    } else {
        Write-Host 'Entorno virtual existente verificado. No es necesario crearlo de nuevo.' -ForegroundColor Green
    }
    if (-not (Valid-Python $Python $true)) {
        $fileList = if (Test-Path -LiteralPath (Join-Path $VenvDir 'Scripts')) {
            (Get-ChildItem -LiteralPath (Join-Path $VenvDir 'Scripts') -Force | Select-Object -ExpandProperty Name) -join ', '
        } else { 'Carpeta Scripts no encontrada' }
        throw "El interprete no supera la verificacion. Archivos en .venv\Scripts: $fileList. Consulte la salida COMPROBANDO en este registro."
    }
    Step '[3/5] Instalando/verificando dependencias de EvaluaFP...'
    Run-Uv @('pip','install','--python',$Python,'-r',(Join-Path $Root 'requirements.txt')) 'Fallo la instalacion de bibliotecas'
    if ($Mode -eq 'build') {
        Step '[4/5] Instalando/verificando PyInstaller y dependencias de compilacion...'
        Run-Uv @('pip','install','--python',$Python,'-r',(Join-Path $Root 'requirements-build.txt')) 'Fallo la instalacion de herramientas de compilacion'
    } else { Step '[4/5] No se necesitan herramientas de compilacion para iniciar la aplicacion.' }
    Step '[5/5] Verificando dependencias, arquitectura y modulos...'
    Run-Uv @('pip','check','--python',$Python) 'Existen conflictos entre dependencias'
    $verifyArgs = @($DependenciesProbe)
    if ($Mode -eq 'build') { $verifyArgs += '--build' }
    & $Python @verifyArgs
    if ($LASTEXITCODE -ne 0) {
        throw 'La verificacion de dependencias ha fallado; revise el error Python que aparece encima.'
    }
    Write-Host 'ENTORNO VERIFICADO: Python portable y dependencias correctas.' -ForegroundColor Green
}
$code = 0
$transcriptStarted = $false
try {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
    Start-Transcript -Path (Join-Path $LogDir 'preparacion_windows.log') -Append -ErrorAction Stop | Out-Null
    $transcriptStarted = $true
    Write-Host "Registro general: $LogDir\preparacion_windows.log"
    Write-Host "Sistema: $([Environment]::OSVersion.VersionString); x64: $([Environment]::Is64BitOperatingSystem)"
    Prepare
} catch {
    Write-Host ''
    Write-Host "ERROR PREPARANDO EVALUAFP: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "Fase: $($_.ScriptStackTrace)" -ForegroundColor DarkYellow
    Write-Host 'No se ha certificado ningun EXE ni instalador.' -ForegroundColor Red
    $code = 1
} finally {
    if ($transcriptStarted) { Stop-Transcript | Out-Null }
}
exit $code
