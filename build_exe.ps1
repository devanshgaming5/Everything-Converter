$ErrorActionPreference = "Stop"

$ffmpeg = Join-Path $PSScriptRoot "bin\ffmpeg.exe"
if (-not (Test-Path -LiteralPath $ffmpeg)) {
    throw "Missing bin\ffmpeg.exe. Add a Windows FFmpeg binary before building."
}

$buildPython = Join-Path $PSScriptRoot ".venv-build\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $buildPython)) {
    $buildPython = "python"
}

Push-Location $PSScriptRoot
try {
    & $buildPython -m PyInstaller --clean --noconfirm converter.spec
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE."
    }
    Copy-Item -LiteralPath "$PSScriptRoot\dist\converter.exe" -Destination "$PSScriptRoot\converter.exe" -Force
    Write-Host "Standalone app created at: $PSScriptRoot\converter.exe"
}
finally {
    Pop-Location
}
