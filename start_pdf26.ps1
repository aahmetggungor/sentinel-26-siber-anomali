$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$python = Join-Path $projectRoot '.venv\Scripts\python.exe'
if (-not (Test-Path -LiteralPath $python)) {
    throw "Sanal ortam yok. README.md içindeki kurulum adımlarını çalıştırın: $python"
}

$model = Join-Path $projectRoot 'artifacts\isolation_forest.joblib'
if (-not (Test-Path -LiteralPath $model)) {
    & $python (Join-Path $projectRoot 'download_data.py')
    if ($LASTEXITCODE -ne 0) { throw 'Veri indirme/doğrulama başarısız.' }
    & $python (Join-Path $projectRoot 'train.py')
    if ($LASTEXITCODE -ne 0) { throw 'Model eğitimi başarısız.' }
}

$ready = $false
try {
    $ready = (Invoke-WebRequest -Uri 'http://127.0.0.1:8502/' -TimeoutSec 2 -UseBasicParsing).StatusCode -eq 200
} catch {}
if (-not $ready) {
    Start-Process -FilePath $python -ArgumentList @('-m','streamlit','run','app.py',
        '--server.address','127.0.0.1','--server.port','8502','--browser.gatherUsageStats','false') `
        -WorkingDirectory $projectRoot -WindowStyle Hidden | Out-Null
}
for ($attempt = 0; $attempt -lt 25; $attempt++) {
    try {
        $response = Invoke-WebRequest -Uri 'http://127.0.0.1:8502/' -TimeoutSec 2 -UseBasicParsing
        if ($response.StatusCode -eq 200) { $ready = $true; break }
    } catch {}
    Start-Sleep -Milliseconds 500
}
if (-not $ready) { throw 'SENTINEL 26 arayüzü başlatılamadı. 8502 portunu kontrol edin.' }
Write-Host 'SENTINEL 26 hazır: http://127.0.0.1:8502/'
Start-Process -FilePath 'http://127.0.0.1:8502/' | Out-Null
