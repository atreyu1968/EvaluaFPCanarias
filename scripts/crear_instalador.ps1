# EvaluaFPCanarias 0.8.0 - Creacion de instalador SIN winget.
# PowerShell 5.1, Windows 10/11 x64. Nunca modifica datos SQLite ni originales.
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][string]$ProjectRoot,
    [switch]$NoDownload
)
$ErrorActionPreference = 'Stop'
$ProjectRoot = (Resolve-Path -LiteralPath $ProjectRoot).Path
$InstallerScript = Join-Path $ProjectRoot 'instalador\EvaluaFP.iss'
$Exe = Join-Path $ProjectRoot 'dist\EvaluaFPCanarias.exe'
$Output = Join-Path $ProjectRoot 'dist\Instalar_EvaluaFPCanarias.exe'
$LogFolder = Join-Path $env:LOCALAPPDATA 'EvaluaFPCanarias\logs'
$LogFile = Join-Path $LogFolder 'compilacion_inno.log'
$InnoVersion = '6.7.4'
$InnoName = 'innosetup-6.7.4.exe'
$DownloadFolder = Join-Path $env:LOCALAPPDATA 'EvaluaFPCanarias\tools\inno-setup'
$DownloadedInstaller = Join-Path $DownloadFolder $InnoName
$InnoLocal = Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6'
$Urls = @(
    'https://github.com/jrsoftware/issrc/releases/download/is-6_7_4/innosetup-6.7.4.exe',
    'https://files.jrsoftware.org/is/6/innosetup-6.7.4.exe'
)
function Info([string]$Message) { Write-Host $Message }
function Get-Candidates {
    $paths = New-Object System.Collections.Generic.List[string]
    foreach ($p in @(
        $env:INNO_ISCC,
        (Join-Path $InnoLocal 'ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 7\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Programs\Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Inno Setup 6\ISCC.exe'),
        (Join-Path $env:LOCALAPPDATA 'Inno Setup 7\ISCC.exe')
    )) { if (-not [string]::IsNullOrWhiteSpace($p)) { $paths.Add($p) } }
    foreach ($root in @($env:ProgramFiles, [Environment]::GetEnvironmentVariable('ProgramFiles(x86)'))) {
        if ([string]::IsNullOrWhiteSpace($root)) { continue }
        foreach ($ver in @('6','7')) { $paths.Add((Join-Path $root "Inno Setup $ver\ISCC.exe")) }
    }
    try {
        $command = Get-Command 'ISCC.exe' -ErrorAction SilentlyContinue | Select-Object -First 1
        if ($null -ne $command) { $paths.Add($command.Source) }
    } catch {}
    foreach ($reg in @(
        'HKCU:\Software\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall',
        'HKLM:\SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall'
    )) {
        if (-not (Test-Path -LiteralPath $reg)) { continue }
        foreach ($key in @(Get-ChildItem -LiteralPath $reg -ErrorAction SilentlyContinue)) {
            if ($key.PSChildName -notlike '*Inno Setup*') { continue }
            $entry = Get-ItemProperty -LiteralPath $key.PSPath -ErrorAction SilentlyContinue
            if ($entry -and $entry.InstallLocation) { $paths.Add((Join-Path $entry.InstallLocation 'ISCC.exe')) }
        }
    }
    return @($paths | Select-Object -Unique)
}
function Find-Compiler {
    foreach ($p in @(Get-Candidates)) {
        if (Test-Path -LiteralPath $p -PathType Leaf) { return $p }
    }
    return $null
}
function Test-SignedInstaller([string]$FilePath) {
    if (-not (Test-Path -LiteralPath $FilePath -PathType Leaf)) { return $false }
    if ((Get-Item -LiteralPath $FilePath).Length -lt 1000000) { return $false }
    $signature = Get-AuthenticodeSignature -LiteralPath $FilePath
    if ($signature.Status -ne 'Valid' -or $null -eq $signature.SignerCertificate) {
        Info "Firma Authenticode no valida ($($signature.Status))."
        return $false
    }
    if ($signature.SignerCertificate.Subject -notmatch 'Pyrsys B\.V\.') {
        Info "Firmante inesperado: $($signature.SignerCertificate.Subject)"
        return $false
    }
    return $true
}
function Download-OfficialInno {
    New-Item -ItemType Directory -Path $DownloadFolder -Force | Out-Null
    if (Test-SignedInstaller $DownloadedInstaller) {
        Info 'Instalador oficial ya descargado y firmado correctamente; se reutilizara.'
        return $DownloadedInstaller
    }
    if (Test-Path -LiteralPath $DownloadedInstaller) { Remove-Item -LiteralPath $DownloadedInstaller -Force }
    [Net.ServicePointManager]::SecurityProtocol = [Net.ServicePointManager]::SecurityProtocol -bor [Net.SecurityProtocolType]::Tls12
    foreach ($url in $Urls) {
        try {
            Info "Descargando Inno Setup $InnoVersion desde $url"
            Invoke-WebRequest -Uri $url -OutFile $DownloadedInstaller -UseBasicParsing -MaximumRedirection 8 -ErrorAction Stop
            if (Test-SignedInstaller $DownloadedInstaller) { return $DownloadedInstaller }
            Info 'La descarga no supera la comprobacion de firma. No se ejecutara.'
        } catch {
            Info "No se ha podido descargar de ese origen: $($_.Exception.Message)"
        }
        if (Test-Path -LiteralPath $DownloadedInstaller) { Remove-Item -LiteralPath $DownloadedInstaller -Force }
    }
    throw 'Descarga oficial de Inno Setup no disponible o firma no valida. Puede instalarlo manualmente desde https://jrsoftware.org/inno-setup/downloads y volver a ejecutar el BAT.'
}
function Ensure-Inno {
    $compiler = Find-Compiler
    if ($compiler) { Info "ISCC encontrado: $compiler"; return $compiler }
    Info 'No se encuentra Inno Setup 6 ni 7.'
    if ($NoDownload) { throw 'No se ha encontrado Inno Setup. Instalelo desde su web oficial y repita.' }
    $answer = Read-Host 'Desea descargar e instalar Inno Setup 6.7.4 oficial (S/N)'
    if ($answer -notmatch '^(s|si|sí|y|yes)$') { throw 'Instalacion cancelada por el usuario. El EXE portable sigue disponible.' }
    $installer = Download-OfficialInno
    Info 'Instalando Inno Setup para el usuario actual (sin winget)...'
    $installArguments = @('/CURRENTUSER','/VERYSILENT','/SUPPRESSMSGBOXES','/NORESTART', ('/DIR="' + $InnoLocal + '"'))
    $process = Start-Process -FilePath $installer -ArgumentList $installArguments -Wait -PassThru -ErrorAction Stop
    Info "Codigo de salida del instalador Inno Setup: $($process.ExitCode)"
    if ($process.ExitCode -ne 0) { throw "Inno Setup devolvio codigo $($process.ExitCode). Ejecute el instalador descargado manualmente si es necesario: $installer" }
    $compiler = Find-Compiler
    if (-not $compiler) { throw "Inno Setup indico exito pero ISCC.exe no se ha encontrado. Revise la instalacion en $InnoLocal y las carpetas de Programas." }
    Info "ISCC verificado: $compiler"
    return $compiler
}
$started = $false
try {
    New-Item -ItemType Directory -Path $LogFolder -Force | Out-Null
    Start-Transcript -Path $LogFile -Append -ErrorAction Stop | Out-Null
    $started = $true
    Info 'EvaluaFPCanarias 0.8.0 - instalador sin dependencia de winget'
    if (-not (Test-Path -LiteralPath $Exe -PathType Leaf)) { throw "No existe el EXE: $Exe. Ejecute primero crear_exe_windows.bat." }
    if (-not (Test-Path -LiteralPath $InstallerScript -PathType Leaf)) { throw "No existe el archivo .iss: $InstallerScript" }
    $compiler = Ensure-Inno
    if (Test-Path -LiteralPath $Output) { Remove-Item -LiteralPath $Output -Force }
    Info "Compilando instalador mediante $compiler"
    # Argumento como una ruta, sin python -c ni traducciones de comillas.
    & $compiler $InstallerScript
    $exitCode = $LASTEXITCODE
    if ($exitCode -ne 0) { throw "ISCC.exe fallo con codigo $exitCode. Consulte los mensajes de compilacion anteriores." }
    if (-not (Test-Path -LiteralPath $Output -PathType Leaf)) { throw "ISCC no creo el archivo esperado: $Output" }
    $bytes = (Get-Item -LiteralPath $Output).Length
    if ($bytes -lt 100000) { throw "El instalador generado es demasiado pequeno: $bytes bytes." }
    Info ''
    Write-Host "INSTALADOR GENERADO CORRECTAMENTE: $Output ($bytes bytes)" -ForegroundColor Green
    exit 0
} catch {
    Write-Host "ERROR CREANDO INSTALADOR: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "El EXE portable no se ha eliminado: $Exe" -ForegroundColor Yellow
    exit 1
} finally {
    if ($started) { Stop-Transcript | Out-Null }
}
