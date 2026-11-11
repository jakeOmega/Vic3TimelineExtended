# Attach, set one breakpoint, wait for a stop, then dump stack/scopes and evaluate expressions, then continue.
param([int]$Port = 6111, [string]$File, [int]$Line, [string]$ExprFile, [int]$StopWaitSec = 60, [string]$LogMessage = "")
$c = New-Object System.Net.Sockets.TcpClient; $c.Connect("127.0.0.1", $Port); $st = $c.GetStream()
$script:seq = 1; $script:buf = ""
function Send($cmd, $argsJson) {
  $body = '{"seq":' + $script:seq + ',"type":"request","command":"' + $cmd + '"' + $(if ($argsJson) { ',"arguments":' + $argsJson } else { '' }) + '}'
  $script:seq++; $b = [Text.Encoding]::UTF8.GetBytes($body); $h = [Text.Encoding]::ASCII.GetBytes("Content-Length: $($b.Length)`r`n`r`n")
  $st.Write($h, 0, $h.Length); $st.Write($b, 0, $b.Length); $st.Flush(); ">> $body"
}
function Recv([int]$ms, [string]$until = "") {
  $deadline = (Get-Date).AddMilliseconds($ms); $out = ""; $tmp = New-Object byte[] 65536
  while ((Get-Date) -lt $deadline) {
    if ($st.DataAvailable) { $n = $st.Read($tmp, 0, $tmp.Length); $out += [Text.Encoding]::UTF8.GetString($tmp, 0, $n); if ($until -and $out -match $until) { Start-Sleep -Milliseconds 150; if (-not $st.DataAvailable) { break } } }
    else { Start-Sleep -Milliseconds 50 }
  }
  $out = $out -replace "Content-Length: \d+\r\n\r\n", "`n<< "; $out
}
Send "initialize" '{"clientID":"te_qa","adapterID":"jomini","linesStartAt1":true,"columnsStartAt1":true}'; Recv 1500 '"initialized"'
Send "launch" '{}'; Recv 800 '"launch"'
$bp = '{"line":' + $Line + $(if ($LogMessage) { ',"logMessage":"' + $LogMessage + '"' } else { '' }) + '}'
Send "setBreakpoints" ('{"source":{"path":"' + $File.Replace('\','\\') + '"},"breakpoints":[' + $bp + ']}'); Recv 1500 '"setBreakpoints"'
Send "configurationDone" $null; Recv 800 '"configurationDone"'
"-- waiting up to $StopWaitSec s for a stop or output"
$r = Recv ($StopWaitSec * 1000) '"stopped"'; $r
if ($r -match '"stopped"') {
  Send "stackTrace" '{"threadId":1}'; $s = Recv 1500 '"stackTrace"'; $s
  $fid = if ($s -match '"id":(\d+)') { $Matches[1] } else { "0" }
  Send "scopes" ('{"frameId":' + $fid + '}'); $sc = Recv 1500 '"scopes"'; $sc
  foreach ($m in [regex]::Matches($sc, '"variablesReference":(\d+)')) { if ($m.Groups[1].Value -ne "0") { Send "variables" ('{"variablesReference":' + $m.Groups[1].Value + '}'); (Recv 1500 '"variables"') } }
  foreach ($e in Get-Content $ExprFile) { if ($e.Trim()) { Send "evaluate" ('{"expression":"' + $e.Replace('\','\\').Replace('"','\"') + '","frameId":' + $fid + ',"context":"watch"}'); Recv 1200 '"evaluate"' } }
  Send "continue" '{"threadId":1}'; Recv 1500 '"continue"'
}
Send "disconnect" '{}'; Recv 500; $c.Close()
