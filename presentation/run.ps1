#Requires -Version 5.1
<#
.SYNOPSIS  Launches the AI Presentation Gradio app.
.EXAMPLE   .\run.ps1
#>

$python = "C:/Python312/python.exe"
$app    = Join-Path $PSScriptRoot "app.py"

if (-not (Test-Path $python)) {
    # fall back to whatever python is on PATH
    $python = "python"
}

Write-Host ""
Write-Host "  Starting presentation at http://localhost:7860" -ForegroundColor Cyan
Write-Host "  Press Ctrl+C to stop." -ForegroundColor DarkGray
Write-Host ""

& $python $app
