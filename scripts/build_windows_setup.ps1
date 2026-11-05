# Run on Windows 11 x64 after installing uv and Inno Setup 6.
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
Push-Location $root
try {
    $compiler = (Get-Command ISCC.exe -ErrorAction SilentlyContinue).Source
    if (-not $compiler) { $compiler = 'C:\Program Files (x86)\Inno Setup 6\ISCC.exe' }
    if (-not (Test-Path $compiler)) { throw 'Install Inno Setup 6 from https://jrsoftware.org/isinfo.php first.' }
    uv sync --frozen --extra dev --python 3.12
    if ($LASTEXITCODE -ne 0) { throw 'Dependency setup failed' }
    uv run python scripts/build.py
    if ($LASTEXITCODE -ne 0) { throw 'Native build failed' }
    $application = Join-Path $root 'dist/Arabic Transcriber/Arabic Transcriber.exe'
    foreach ($check in @('--self-check', '--worker-check')) {
        $report = if ($check -eq '--self-check') { 'build/package-check.json' } else { 'build/worker-check.json' }
        $process = Start-Process -FilePath $application -ArgumentList $check, '--smoke-report', $report -Wait -PassThru
        if ($process.ExitCode -ne 0) { throw "Frozen application check failed: $check" }
    }
    if (-not $env:RUNNER_TEMP) { $env:RUNNER_TEMP = [IO.Path]::GetTempPath() }
    & "$PSScriptRoot/sign_windows.ps1"
    $installer = Join-Path $root 'build/MicrosoftEdgeWebview2Setup.exe'
    Invoke-WebRequest 'https://go.microsoft.com/fwlink/p/?LinkId=2124703' -OutFile $installer
    $signature = Get-AuthenticodeSignature $installer
    if ($signature.Status -ne 'Valid' -or $signature.SignerCertificate.Subject -notmatch 'Microsoft Corporation') {
        throw 'Invalid Microsoft WebView2 installer signature'
    }
    & $compiler "$PSScriptRoot/windows-installer.iss"
    if ($LASTEXITCODE -ne 0) { throw 'Installer creation failed' }
    & "$PSScriptRoot/sign_windows.ps1"
    uv run python scripts/archive_package.py
    if ($LASTEXITCODE -ne 0) { throw 'Package checksum creation failed' }
    Write-Host 'Setup ready in dist/release. Recipients run the Setup EXE; no Python installation needed.'
} finally {
    Pop-Location
}
