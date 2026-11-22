param([string]$GameArgs = "-gdpr-compliant -debug_mode", [string]$Exe = "victoria3.exe")
$bin = "C:\Program Files (x86)\Steam\steamapps\common\Victoria 3\binaries"
$p = Start-Process -FilePath (Join-Path $bin $Exe) -ArgumentList $GameArgs -WorkingDirectory $bin -PassThru
"started pid=$($p.Id) args=$GameArgs"
