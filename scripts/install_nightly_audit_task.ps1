# Registers a Windows Scheduled Task that runs the nightly mod audit
# via WSL. The task triggers at logon AND daily at 04:00 — combined with
# the catch-up gate in scripts/run_nightly_audit.sh, that means the audit
# runs whenever the machine is awake on or after 04:00 each day, and you
# never need to keep the box on overnight to catch a fixed slot.
#
# Run once from a Windows PowerShell session (no admin needed — the task
# runs as the current user, which matches the WSL user's identity). Open
# `powershell.exe` (not cmd — cmd refuses UNC paths as CWD), `cd` to the
# repo on the WSL share, then:
#
#     powershell -ExecutionPolicy Bypass -File .\scripts\install_nightly_audit_task.ps1
#
# Use built-in `powershell.exe` (PS 5.1) — not `pwsh.exe`, which needs a
# separate PowerShell 7 install. The ScheduledTasks cmdlets used here ship
# with Windows since 8, so PS 5.1 is fine.
#
# Re-run after changing the WSL distro name / repo path / username — it
# overwrites any existing task with the same name.

[CmdletBinding()]
param(
    [string]$TaskName = "Vic3TimelineExtended Nightly Audit",
    [string]$WslDistro,
    [string]$RepoPathInWsl = "/home/jakef/src/Vic3TimelineExtended",
    [string]$DailyTime = "04:00"
)

if (-not $WslDistro) {
    $WslDistro = (wsl.exe --list --quiet | Where-Object { $_ -and $_.Trim() } | Select-Object -First 1).Trim()
    if (-not $WslDistro) {
        throw "Could not detect a default WSL distro. Pass -WslDistro <name> explicitly."
    }
    Write-Host "Auto-detected WSL distro: $WslDistro"
}

# Action: wsl.exe -d <distro> -- bash -lc 'cd <repo> && ./scripts/run_nightly_audit.sh'
# Using `bash -lc` so the user's login profile is sourced — gives the script
# the same PATH and env (including the venv's `claude` binary, if it's on
# the user's $PATH) as an interactive shell would.
$bashCmd = "cd $RepoPathInWsl && ./scripts/run_nightly_audit.sh"
$action  = New-ScheduledTaskAction `
    -Execute "wsl.exe" `
    -Argument "-d $WslDistro -- bash -lc `"$bashCmd`""

# Two triggers — covered both "wake up after machine was off" and the
# fixed nightly slot. The script's date-marker gate dedups when both fire.
$triggers = @(
    (New-ScheduledTaskTrigger -AtLogOn),
    (New-ScheduledTaskTrigger -Daily -At $DailyTime)
)

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2) `
    -MultipleInstances IgnoreNew

# Run as the current interactive user so the WSL user identity matches the
# repo owner. No admin required.
$principal = New-ScheduledTaskPrincipal `
    -UserId $env:UserName `
    -LogonType Interactive `
    -RunLevel Limited

# Idempotent: unregister any existing task with the same name first.
if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) {
    Write-Host "Unregistering existing task: $TaskName"
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
}

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $action `
    -Trigger $triggers `
    -Settings $settings `
    -Principal $principal `
    -Description "Runs the Vic3TimelineExtended nightly mod audit via WSL. Catch-up gate in scripts/run_nightly_audit.sh dedups when the logon and daily triggers both fire." `
    | Out-Null

Write-Host "Registered: $TaskName"
Write-Host "  Distro:        $WslDistro"
Write-Host "  Repo (in WSL): $RepoPathInWsl"
Write-Host "  Daily time:    $DailyTime (plus on every logon)"
Write-Host ""
Write-Host "Verify with: Get-ScheduledTask -TaskName '$TaskName'"
Write-Host "Run now:     Start-ScheduledTask -TaskName '$TaskName'"
Write-Host "Remove:      Unregister-ScheduledTask -TaskName '$TaskName' -Confirm:`$false"
