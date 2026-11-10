param([string]$Out = "$env:TEMP\te_qa\g.png", [int]$MaxW = 1600, [string]$Crop = "")
. "$PSScriptRoot\lib.ps1"
$g = Get-Game; if (-not $g) { "no game window"; exit 1 }
$c = Get-ClientRect $g.MainWindowHandle
$x=$c.X; $y=$c.Y; $w=$c.W; $h=$c.H
if ($Crop) { $a = $Crop.Split(',') | ForEach-Object { [int]$_ }; $x+=$a[0]; $y+=$a[1]; $w=$a[2]; $h=$a[3] }
$bmp = New-Object System.Drawing.Bitmap $w, $h
$gr = [System.Drawing.Graphics]::FromImage($bmp); $gr.CopyFromScreen($x, $y, 0, 0, $bmp.Size)
$scale = [Math]::Min(1.0, $MaxW / $w)
$small = New-Object System.Drawing.Bitmap $bmp, ([int]($w*$scale)), ([int]($h*$scale))
$small.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
"client=$($c.W)x$($c.H) at $($c.X),$($c.Y) crop=$x,$y,$w,$h scale=$scale fg='$([U]::Title([U]::GetForegroundWindow()))' -> $Out"
