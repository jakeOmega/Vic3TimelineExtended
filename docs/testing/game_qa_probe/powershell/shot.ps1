param([string]$Out = "$env:TEMP\te_qa\shot.png", [int]$MaxW = 1600)
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
Add-Type @"
using System; using System.Runtime.InteropServices;
public class Dpi { [DllImport("user32.dll")] public static extern bool SetProcessDPIAware(); }
"@
[Dpi]::SetProcessDPIAware() | Out-Null
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
$scale = [Math]::Min(1.0, $MaxW / $b.Width)
$w = [int]($b.Width * $scale); $h = [int]($b.Height * $scale)
$small = New-Object System.Drawing.Bitmap $bmp, $w, $h
$small.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
"screen=$($b.Width)x$($b.Height) at $($b.Left),$($b.Top) saved=$w x $h scale=$scale -> $Out"
