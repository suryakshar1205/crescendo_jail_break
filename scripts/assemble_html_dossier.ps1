$header = [System.IO.File]::ReadAllText("web/dossier_header.html", [System.Text.Encoding]::UTF8)
$md = [System.IO.File]::ReadAllText("results/final_verified_results_dossier.md", [System.Text.Encoding]::UTF8)
$footer = [System.IO.File]::ReadAllText("web/dossier_footer.html", [System.Text.Encoding]::UTF8)

$fullHtml = $header + "`n" + $md + "`n" + $footer

[System.IO.File]::WriteAllText("results/final_verified_results_dossier.html", $fullHtml, [System.Text.Encoding]::UTF8)
Write-Host "Successfully generated results/final_verified_results_dossier.html"

$webHeader = $header.Replace('href="../web/index.html"', 'href="/"')
$webHtml = $webHeader + "`n" + $md + "`n" + $footer
[System.IO.File]::WriteAllText("web/results_dossier.html", $webHtml, [System.Text.Encoding]::UTF8)
Write-Host "Successfully generated web/results_dossier.html"
