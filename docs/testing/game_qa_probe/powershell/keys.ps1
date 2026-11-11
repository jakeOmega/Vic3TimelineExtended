# -Seq: comma-separated steps. "sc:29" scancode tap (hex), "t:text" unicode type, "w:500" wait ms, "c:x,y" click at client px (use ; inside), "enter","esc","space","tick"
param([string]$Seq, [switch]$NoFocus)
. "$PSScriptRoot\lib.ps1"
$g = Get-Game; if (-not $g) { "no game window"; exit 1 }
$prev = [U]::GetForegroundWindow()
if (-not $NoFocus) { $ok = [U]::Focus($g.MainWindowHandle); "focus=$ok"; if (-not $ok) { "ABORT: the game window is not in front; nothing typed"; exit 3 } }
$c = Get-ClientRect $g.MainWindowHandle
foreach ($s in $Seq.Split('|')) {
  if ([U]::GetForegroundWindow() -ne $g.MainWindowHandle) { "ABORT: lost the foreground before step '$s'; stopped"; exit 3 }
  switch -Regex ($s) {
    '^sc:(.+)$'  { [U]::Tap([Convert]::ToUInt16($Matches[1],16), $false) }
    '^t:(.*)$'   { [U]::Type($Matches[1]) }
    '^w:(\d+)$'  { Start-Sleep -Milliseconds ([int]$Matches[1]) }
    '^c:(\d+);(\d+)$' { [U]::Click($c.X + [int]$Matches[1], $c.Y + [int]$Matches[2]) }
    '^enter$'    { [U]::Tap(0x1C, $false) }
    '^esc$'      { [U]::Tap(0x01, $false) }
    '^space$'    { [U]::Tap(0x39, $false) }
    '^tick$'     { [U]::Tap(0x29, $false) }
    '^m:(\d+);(\d+)$' { [U]::SetCursorPos($c.X + [int]$Matches[1], $c.Y + [int]$Matches[2]) | Out-Null }
    '^vk:(.+)$' { $v=[Convert]::ToByte($Matches[1],16); [U]::keybd_event($v,0,0,[UIntPtr]::Zero); Start-Sleep -Milliseconds 50; [U]::keybd_event($v,0,2,[UIntPtr]::Zero) }
    '^back$'     { [U]::SetForegroundWindow($prev) | Out-Null }
    default      { "unknown step '$s'" }
  }
}
"done fg='$([U]::Title([U]::GetForegroundWindow()))'"
