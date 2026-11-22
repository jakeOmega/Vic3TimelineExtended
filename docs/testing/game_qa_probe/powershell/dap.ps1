# minimal Debug Adapter Protocol client: send each JSON line of -Requests (file), print everything received
param([int]$Port, [string]$ReqFile, [int]$WaitMs = 1500)
$c = New-Object System.Net.Sockets.TcpClient
try { $c.Connect("127.0.0.1", $Port) } catch { "connect failed: $($_.Exception.Message)"; exit 1 }
$st = $c.GetStream(); $st.ReadTimeout = $WaitMs
function Recv { $buf = New-Object byte[] 65536; $out = ""; try { while ($true) { $n = $st.Read($buf, 0, $buf.Length); if ($n -le 0) { break }; $out += [Text.Encoding]::UTF8.GetString($buf, 0, $n) } } catch {}; $out }
"connected"; $r = Recv; if ($r) { "<< $r" }
$seq = 1
foreach ($line in Get-Content $ReqFile) {
  if (-not $line.Trim()) { continue }
  $body = $line.Replace('"seq":0', '"seq":' + $seq); $seq++
  $bytes = [Text.Encoding]::UTF8.GetBytes($body)
  $hdr = [Text.Encoding]::ASCII.GetBytes("Content-Length: $($bytes.Length)`r`n`r`n")
  $st.Write($hdr, 0, $hdr.Length); $st.Write($bytes, 0, $bytes.Length); $st.Flush()
  ">> $body"; $r = Recv; "<< $r"
}
$c.Close()
