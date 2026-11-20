$ErrorActionPreference = 'Continue'
$DataDir = Join-Path $env:LOCALAPPDATA 'EvaluaFP'
$Logs = Join-Path $DataDir 'logs'
New-Item -ItemType Directory -Path $Logs -Force | Out-Null
$Target = Join-Path $Logs 'diagnostico_v06.txt'
$Root = Split-Path -Parent $PSScriptRoot
$UvExe = Join-Path $DataDir 'tools\uv\uv.exe'
$VenvPython = Join-Path $Root '.venv\Scripts\python.exe'
$Output = New-Object System.Collections.Generic.List[string]
function Add([string]$Value) { $Output.Add($Value); Write-Host $Value }
Add 'DIAGNOSTICO EVALUAFP 0.6.1'
Add "Fecha: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
Add "Windows: $([Environment]::OSVersion.VersionString)"
Add "Sistema 64 bits: $([Environment]::Is64BitOperatingSystem)"
Add "PowerShell: $($PSVersionTable.PSVersion)"
Add "Carpeta de proyecto: $Root"
Add "Python anterior (instalacion directa) NO SE UTILIZA en version 0.6."
Add "Gestor uv: $(Test-Path -LiteralPath $UvExe)"
if (Test-Path -LiteralPath $UvExe) {
    Add "Version uv: $((& $UvExe --version 2>&1) -join ' ')"
}
Add "Entorno Python: $(Test-Path -LiteralPath $VenvPython)"
if (Test-Path -LiteralPath $VenvPython) {
    Add "Version del entorno: $((& $VenvPython -V 2>&1) -join ' ')"
    $Probe = Join-Path $PSScriptRoot 'verificar_python.py'
    if (Test-Path -LiteralPath $Probe) {
        Add 'Resultado de la comprobacion real:'
        try {
            $result = @(& $VenvPython $Probe 2>&1)
            $code = $LASTEXITCODE
            foreach ($line in $result) { Add "  $line" }
            Add "Codigo final de Python: $code"
        } catch { Add "Excepcion al verificar Python: $($_.Exception.Message)" }
    } else { Add "Falta script verificador: $Probe" }
}
$MainLog = Join-Path $Logs 'preparacion_windows.log'
Add "Registro preparacion disponible: $(Test-Path -LiteralPath $MainLog)"
if (Test-Path -LiteralPath $MainLog) {
    Add 'ULTIMAS 35 LINEAS DEL REGISTRO:'
    Get-Content -LiteralPath $MainLog -Tail 35 | ForEach-Object { Add $_ }
}
[IO.File]::WriteAllLines($Target, $Output, [Text.Encoding]::UTF8)
Add "Diagnostico guardado en: $Target"
