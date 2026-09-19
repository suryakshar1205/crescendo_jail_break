# PowerShell script to generate interactive HTML dossier from final_verified_results_dossier.md
$root = Split-Path -Parent $PSScriptRoot
$mdPath = Join-Path $root "results\final_verified_results_dossier.md"
$headerPath = Join-Path $root "web\dossier_header.html"
$footerPath = Join-Path $root "web\dossier_footer.html"
$out1 = Join-Path $root "results\final_verified_results_dossier.html"
$out2 = Join-Path $root "web\results_dossier.html"

if (-not (Test-Path $mdPath) -or -not (Test-Path $headerPath) -or -not (Test-Path $footerPath)) {
    Write-Error "Required source files not found."
    exit 1
}

$header = [System.IO.File]::ReadAllText($headerPath, [System.Text.Encoding]::UTF8)
$md = [System.IO.File]::ReadAllText($mdPath, [System.Text.Encoding]::UTF8)
$footer = [System.IO.File]::ReadAllText($footerPath, [System.Text.Encoding]::UTF8)

$fullHtml = $header + "`n" + $md + "`n" + $footer
[System.IO.File]::WriteAllText($out1, $fullHtml, [System.Text.Encoding]::UTF8)
Write-Host "Generated: $out1"

$webHeader = $header.Replace('href="../web/index.html"', 'href="/"')
$webHtml = $webHeader + "`n" + $md + "`n" + $footer
[System.IO.File]::WriteAllText($out2, $webHtml, [System.Text.Encoding]::UTF8)
Write-Host "Generated: $out2"
