# PowerShell script to generate interactive HTML dossiers
$root = Split-Path -Parent $PSScriptRoot
$headerPath = Join-Path $root "web\dossier_header.html"
$footerPath = Join-Path $root "web\dossier_footer.html"

$resultsMdPath = Join-Path $root "results\final_verified_results_dossier.md"
$archMdPath = Join-Path $root "results\master_architecture_report.md"

if (-not (Test-Path $headerPath) -or -not (Test-Path $footerPath)) {
    Write-Error "Required template files (header/footer) not found."
    exit 1
}

$header = [System.IO.File]::ReadAllText($headerPath, [System.Text.Encoding]::UTF8)
$footer = [System.IO.File]::ReadAllText($footerPath, [System.Text.Encoding]::UTF8)

# -----------------------------------------------------------------------------
# 1. Generate Results Dossier
# -----------------------------------------------------------------------------
if (Test-Path $resultsMdPath) {
    $resultsMd = [System.IO.File]::ReadAllText($resultsMdPath, [System.Text.Encoding]::UTF8)

    # Standalone results HTML
    $outResults1 = Join-Path $root "results\final_verified_results_dossier.html"
    $fullHtml1 = $header + "`n" + $resultsMd + "`n" + $footer
    [System.IO.File]::WriteAllText($outResults1, $fullHtml1, [System.Text.Encoding]::UTF8)
    Write-Host "Generated: $outResults1"

    # Web results HTML
    $outResults2 = Join-Path $root "web\results_dossier.html"
    $outResults3 = Join-Path $root "public\results_dossier.html"
    $webResultsHeader = $header.Replace('href="../web/index.html"', 'href="/"')
    $fullHtml2 = $webResultsHeader + "`n" + $resultsMd + "`n" + $footer
    [System.IO.File]::WriteAllText($outResults2, $fullHtml2, [System.Text.Encoding]::UTF8)
    if (Test-Path (Join-Path $root "public")) {
        [System.IO.File]::WriteAllText($outResults3, $fullHtml2, [System.Text.Encoding]::UTF8)
    }
    Write-Host "Generated: $outResults2 & $outResults3"
}

# -----------------------------------------------------------------------------
# 2. Generate Master Architecture Report
# -----------------------------------------------------------------------------
if (Test-Path $archMdPath) {
    $archMd = [System.IO.File]::ReadAllText($archMdPath, [System.Text.Encoding]::UTF8)

    $archHeader = $header -replace '<title>.*?</title>', '<title>Crescendo Multi-Turn Jailbreak Defense - Master Architectural Blueprint</title>'
    $archHeader = $archHeader -replace '<h1>CRESCENDO DEFENSE LAB.*?</h1>', '<h1>CRESCENDO DEFENSE LAB - ARCHITECTURAL BLUEPRINT</h1>'
    $archHeader = $archHeader -replace '<p>Inference-Time.*?</p>', '<p>Stateful Inference-Time Multi-Turn Jailbreak Defense and Systems Blueprint</p>'
    $archHeader = $archHeader -replace 'ASR: 0.00%', 'Zero-Token Defense'
    $archHeader = $archHeader -replace 'DDR: 100.00%', 'Decoupled Proxy'

    # Standalone architecture HTML
    $outArch1 = Join-Path $root "results\master_architecture_report.html"
    $fullArchHtml1 = $archHeader + "`n" + $archMd + "`n" + $footer
    [System.IO.File]::WriteAllText($outArch1, $fullArchHtml1, [System.Text.Encoding]::UTF8)
    Write-Host "Generated: $outArch1"

    # Web architecture HTML
    $outArch2 = Join-Path $root "web\master_architecture_report.html"
    $outArch3 = Join-Path $root "public\master_architecture_report.html"
    $webArchHeader = $archHeader.Replace('href="../web/index.html"', 'href="/"')
    $fullArchHtml2 = $webArchHeader + "`n" + $archMd + "`n" + $footer
    [System.IO.File]::WriteAllText($outArch2, $fullArchHtml2, [System.Text.Encoding]::UTF8)
    if (Test-Path (Join-Path $root "public")) {
        [System.IO.File]::WriteAllText($outArch3, $fullArchHtml2, [System.Text.Encoding]::UTF8)
    }
    Write-Host "Generated: $outArch2 & $outArch3"
}


Write-Host "All interactive HTML dossiers compiled successfully!"
