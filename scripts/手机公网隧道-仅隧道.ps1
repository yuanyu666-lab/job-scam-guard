# Cloudflare tunnel -> save trycloudflare URL for mobile app
$root = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$urlFile = Join-Path $root "手机填这个地址.txt"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host " Job-Scam-Guard public tunnel" -ForegroundColor Cyan
Write-Host " Do NOT close this window" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "Wait for: https://xxxx.trycloudflare.com" -ForegroundColor Yellow
Write-Host "Copy that URL into the mobile app." -ForegroundColor Yellow
Write-Host ""

$saved = $false
& cloudflared tunnel --url http://127.0.0.1:8765 2>&1 | ForEach-Object {
    $line = "$_"
    Write-Host $line
    if (-not $saved -and $line -match "(https://[a-zA-Z0-9\-]+\.trycloudflare\.com)") {
        $url = $Matches[1]
        $text = @"
Copy this URL into the mobile app server field:

$url

Test in phone browser:
$url/api/mobile/status

Saved at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')
"@
        Set-Content -Path $urlFile -Value $text -Encoding UTF8
        Write-Host ""
        Write-Host "[OK] URL saved to:" -ForegroundColor Green
        Write-Host "     $urlFile" -ForegroundColor Green
        Write-Host "[OK] $url" -ForegroundColor Green
        $saved = $true
    }
}

Write-Host ""
Write-Host "Tunnel stopped." -ForegroundColor Gray
