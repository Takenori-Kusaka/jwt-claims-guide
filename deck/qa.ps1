param([string]$pptx, [string]$outDir)
$ErrorActionPreference = 'Stop'
New-Item -ItemType Directory -Force -Path $outDir | Out-Null
Get-ChildItem $outDir -Filter *.png | Remove-Item
$app = New-Object -ComObject PowerPoint.Application
$pres = $app.Presentations.Open($pptx, $true, $false, $false)
$report = @()
foreach ($sl in $pres.Slides) {
  foreach ($sh in $sl.Shapes) {
    if ($sh.HasTextFrame -and $sh.TextFrame.HasText) {
      $tr = $sh.TextFrame2.TextRange
      $bh = $sh.TextFrame.TextRange.BoundHeight
      if ($bh -gt $sh.Height + 2) {
        $t = $sh.TextFrame.TextRange.Text; if ($t.Length -gt 30) { $t = $t.Substring(0,30) }
        $report += "S{0} over {1:N0}pt (box {2:N0}): {3}" -f $sl.SlideIndex, ($bh - $sh.Height), $sh.Height, ($t -replace "`r|`n"," ")
      }
    }
    if ($sh.HasTable) {
      $bottom = $sh.Top + $sh.Height
      if ($bottom -gt 474) { $report += "S{0} table bottom {1:N0}pt" -f $sl.SlideIndex, $bottom }
      foreach ($o in $sl.Shapes) {
        if ($o.Name -eq $sh.Name -or $o.HasTable) { continue }
        $ox = ($o.Left -lt $sh.Left + $sh.Width - 2) -and ($o.Left + $o.Width -gt $sh.Left + 2)
        if ($ox -and $o.Top -gt $sh.Top + 2 -and $o.Top -lt $bottom - 2) {
          $report += "S{0} overlaps table (shape top {1:N0}pt < table bottom {2:N0}pt)" -f $sl.SlideIndex, $o.Top, $bottom
          break
        }
      }
    }
  }
  $sl.Export((Join-Path $outDir ("s{0:D3}.png" -f $sl.SlideIndex)), "PNG", 1600, 900)
}
$pres.Close(); $app.Quit()
$report | Out-File -Encoding utf8 (Join-Path $outDir 'overflow.txt')
"slides: " + (Get-ChildItem $outDir -Filter *.png).Count
