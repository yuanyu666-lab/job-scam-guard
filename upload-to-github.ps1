# Upload job-scam-guard to GitHub
# Run in PowerShell: .\upload-to-github.ps1

$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Git {
    $candidates = @(
        "git",
        "D:\Git\cmd\git.exe",
        "C:\Program Files\Git\cmd\git.exe",
        "C:\Program Files\Git\bin\git.exe",
        "$env:LOCALAPPDATA\Programs\Git\cmd\git.exe"
    )
    foreach ($c in $candidates) {
        if (Get-Command $c -ErrorAction SilentlyContinue) {
            return (Get-Command $c).Source
        }
        if (Test-Path $c) { return $c }
    }
    return $null
}

$git = Find-Git
if (-not $git) {
    Write-Host "[ERROR] Git not found. Install with: winget install Git.Git"
    Write-Host "Or download: https://git-scm.com/download/win"
    exit 1
}

$gh = "C:\Program Files\GitHub CLI\gh.exe"
if (-not (Test-Path $gh)) {
    $ghCmd = Get-Command gh -ErrorAction SilentlyContinue
    if ($ghCmd) { $gh = $ghCmd.Source } else { $gh = $null }
}

if (-not $gh) {
    Write-Host "[ERROR] GitHub CLI not found. Install with: winget install GitHub.cli"
    exit 1
}

& $gh auth status 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Please login to GitHub first..."
    & $gh auth login
}

if (-not (Test-Path ".git")) {
    & $git init
    & $git branch -M main
}

& $git add .
& $git status

$hasCommit = & $git rev-parse HEAD 2>$null
if (-not $hasCommit) {
    & $git commit -m "Initial commit: job scam guard MVP"
}

$repoName = "job-scam-guard"
Write-Host "Creating GitHub repo and pushing: $repoName"

& $gh repo create $repoName --public --source=. --remote=origin --push --description "Recruitment anti-fraud system MVP"

if ($LASTEXITCODE -eq 0) {
    $url = & $gh repo view --json url -q .url
    Write-Host "Done: $url"
} else {
    Write-Host "If repo already exists, run:"
    Write-Host "  git remote add origin https://github.com/YOUR_USERNAME/$repoName.git"
    Write-Host "  git push -u origin main"
}
