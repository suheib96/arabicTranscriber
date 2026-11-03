$ErrorActionPreference = 'Stop'
if (-not $env:WINDOWS_CERTIFICATE_PFX_BASE64) {
    Write-Host 'Unsigned Windows development build.'
    exit 0
}
$certPath = Join-Path $env:RUNNER_TEMP 'arabic-transcriber-signing.pfx'
try {
    [IO.File]::WriteAllBytes($certPath, [Convert]::FromBase64String($env:WINDOWS_CERTIFICATE_PFX_BASE64))
    $password = ConvertTo-SecureString $env:WINDOWS_CERTIFICATE_PASSWORD -AsPlainText -Force
    $certificate = Import-PfxCertificate -FilePath $certPath -CertStoreLocation Cert:\CurrentUser\My -Password $password
    $signtool = (Get-ChildItem 'C:\Program Files (x86)\Windows Kits\10\bin\*\x64\signtool.exe' | Sort-Object FullName -Descending | Select-Object -First 1).FullName
    if (-not $signtool) { throw 'Windows SDK signtool is required' }
    $targets = @('dist\Arabic Transcriber\Arabic Transcriber.exe')
    $targets += @(Get-ChildItem 'dist\release\*-Setup.exe' -ErrorAction SilentlyContinue | ForEach-Object FullName)
    foreach ($file in $targets) {
        & $signtool sign /sha1 $certificate.Thumbprint /s My /fd SHA256 /tr 'http://timestamp.digicert.com' /td SHA256 $file
        if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing failed' }
        & $signtool verify /pa $file
        if ($LASTEXITCODE -ne 0) { throw 'Authenticode verification failed' }
    }
} finally {
    Remove-Item $certPath -ErrorAction SilentlyContinue
    if ($certificate) { Remove-Item "Cert:\CurrentUser\My\$($certificate.Thumbprint)" -ErrorAction SilentlyContinue }
}
