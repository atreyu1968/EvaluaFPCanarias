# Evita expresiones PowerShell -Command con comillas anidadas desde CMD.
[CmdletBinding()]
param([Parameter(Mandatory=$true)][string]$ProjectRoot)
$ErrorActionPreference = 'Stop'
try {
    $root = (Resolve-Path -LiteralPath $ProjectRoot).Path
    $exe = Join-Path $root 'dist\EvaluaFPCanarias.exe'
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { exit 1 }
    $builtAt = (Get-Item -LiteralPath $exe).LastWriteTimeUtc
    foreach ($source in @(
        'app.py', 'database.py','logic.py','materiales.py','ia.py',
        'requirements.txt','requirements-build.txt',
        'web\index.html','web\app.js','web\style.css',
        'web\logo.svg','web\favicon.ico','assets\EvaluaFPCanarias.ico','instalador\EvaluaFPCanarias.iss'
    )) {
        $file = Join-Path $root $source
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { exit 1 }
        if ((Get-Item -LiteralPath $file).LastWriteTimeUtc -gt $builtAt) { exit 1 }
    }
    exit 0
} catch {
    Write-Host "No se pudo comprobar la antiguedad del EXE: $($_.Exception.Message)"
    exit 1
}
