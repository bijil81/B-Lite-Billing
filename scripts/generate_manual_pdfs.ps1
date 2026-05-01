$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
$manualDir = Join-Path $root "docs\manuals"
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

if (-not (Test-Path $edge)) {
    throw "Microsoft Edge not found at $edge"
}

$targets = @(
    @{
        Html = Join-Path $manualDir "B_Lite_Management_V5.6_Client_User_Guide.html"
        Pdf  = Join-Path $root "BOBYS_Beauty_Salon_Complete_User_Guide_v5_Client.pdf"
    },
    @{
        Html = Join-Path $manualDir "B_Lite_Management_V5.6_Tutorial_Guide.html"
        Pdf  = Join-Path $root "BOBYS_Beauty_Salon_Complete_User_Guide_v5 tutorial .pdf"
    },
    @{
        Html = Join-Path $manualDir "B_Lite_Management_V5.6_Owner_Handover.html"
        Pdf  = Join-Path $root "BOBYS_Beauty_Salon_Owner_Handover_Notes_v5.pdf"
    }
)

$backupDir = Join-Path $manualDir "archive_original_pdfs"
if (-not (Test-Path $backupDir)) {
    New-Item -ItemType Directory -Path $backupDir | Out-Null
}

foreach ($item in $targets) {
    if (-not (Test-Path $item.Html)) {
        throw "Missing source HTML: $($item.Html)"
    }

    if (Test-Path $item.Pdf) {
        $backupPath = Join-Path $backupDir ([System.IO.Path]::GetFileName($item.Pdf))
        Copy-Item -LiteralPath $item.Pdf -Destination $backupPath -Force
    }

    if (Test-Path $item.Pdf) {
        Remove-Item -LiteralPath $item.Pdf -Force
    }

    $uri = "file:///" + (($item.Html -replace '\\','/') -replace ' ','%20')
    & $edge `
        --headless=new `
        --disable-gpu `
        --allow-file-access-from-files `
        --enable-local-file-accesses `
        --run-all-compositor-stages-before-draw `
        --virtual-time-budget=3000 `
        --no-pdf-header-footer `
        "--print-to-pdf=$($item.Pdf)" `
        $uri | Out-Null

    if (-not (Test-Path $item.Pdf)) {
        throw "PDF generation failed: $($item.Pdf)"
    }
}

Write-Output "Manual PDFs regenerated successfully."
