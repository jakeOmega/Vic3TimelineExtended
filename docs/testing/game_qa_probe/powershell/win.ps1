# list game process + window state
Add-Type @"
using System; using System.Runtime.InteropServices; using System.Text;
public class W {
  [DllImport("user32.dll")] public static extern IntPtr GetForegroundWindow();
  [DllImport("user32.dll")] public static extern int GetWindowText(IntPtr h, StringBuilder s, int n);
  [DllImport("user32.dll")] public static extern bool GetWindowRect(IntPtr h, out RECT r);
  public struct RECT { public int L, T, R, B; }
}
"@
$fg = [W]::GetForegroundWindow(); $sb = New-Object System.Text.StringBuilder 256; [W]::GetWindowText($fg, $sb, 256) | Out-Null
"foreground: '$($sb.ToString())'"
Get-Process victoria3 -ErrorAction SilentlyContinue | ForEach-Object {
  $r = New-Object W+RECT; [W]::GetWindowRect($_.MainWindowHandle, [ref]$r) | Out-Null
  "pid=$($_.Id) title='$($_.MainWindowTitle)' hwnd=$($_.MainWindowHandle) rect=$($r.L),$($r.T),$($r.R),$($r.B) mem=$([int]($_.WorkingSet64/1MB))MB responding=$($_.Responding)"
}
Get-NetTCPConnection -State Listen -ErrorAction SilentlyContinue | Where-Object { $_.OwningProcess -in (Get-Process victoria3 -ErrorAction SilentlyContinue).Id } | ForEach-Object { "LISTEN $($_.LocalAddress):$($_.LocalPort)" }
