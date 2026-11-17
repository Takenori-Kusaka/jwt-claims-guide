# Export the deck to PDF and to 1920x1080 PNGs (PowerPoint COM). Usage: export.ps1 -pptx <abs path> -pdf <abs path> -pngDir <abs dir>
param([string]$pptx, [string]$pdf, [string]$pngDir)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $pngDir | Out-Null
Get-ChildItem $pngDir -Filter s*.png | Remove-Item
Get-ChildItem $pngDir -Filter s*.webp | Remove-Item
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($pptx, $true, $false, $false)
$pres.SaveAs($pdf, 32)
foreach ($sl in $pres.Slides) {
  $sl.Export((Join-Path $pngDir ("s{0:D3}.png" -f $sl.SlideIndex)), "PNG", 2560, 1440)
}
"slides: " + $pres.Slides.Count
$pres.Close(); $app.Quit()
