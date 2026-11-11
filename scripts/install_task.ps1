<#
Registers (or removes) the nightly data build in Windows Task Scheduler.
Pattern from dip-dashboard scripts\install_task.ps1 (commit f14d55c).

  powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1              # Tue-Sat 00:30, local time
  powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1 -Time 00:45
  powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1 -WakeToRun   # also wake the PC from sleep
  powershell -ExecutionPolicy Bypass -File scripts\install_task.ps1 -Remove

Why Tuesday to Saturday at 00:30: US stocks close at 16:00 New York (23:00 in Helsinki) and Europe at about 17:30 CET,
so 00:30 in Helsinki is after both, and a run after midnight Tuesday to Saturday covers the Monday to Friday sessions.
00:30 also keeps clear of the dip-dashboard task at 00:15, which uses the same Yahoo source. The time is the PC's
LOCAL time. The task runs only while you are logged in (it needs your user's Python environment). If the PC was off
at the start time, Windows runs it as soon as possible after the next start (StartWhenAvailable).
Time limit 2 hours: a run, a 20-minute wait and one retry after exit code 2 (see run_nightly.bat).
#>
param(
    [string]$Time = "00:30",
    [switch]$WakeToRun,
    [switch]$Remove
)
$ErrorActionPreference = "Stop"
$name = "MarketLeaderboard"
$root = Split-Path -Parent $PSScriptRoot
$bat  = Join-Path $root "scripts\run_nightly.bat"

if ($Remove) {
    Unregister-ScheduledTask -TaskName $name -Confirm:$false
    Write-Host "Removed task $name"
    return
}
if (-not (Test-Path (Join-Path $root ".venv\Scripts\python.exe"))) {
    throw "No .venv found in $root. Run 'uv sync' there first (see README.md), then run this again."
}
$action   = New-ScheduledTaskAction -Execute $bat -WorkingDirectory $root
$trigger  = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Wednesday,Thursday,Friday,Saturday -At $Time
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -RunOnlyIfNetworkAvailable `
            -ExecutionTimeLimit (New-TimeSpan -Hours 2) -MultipleInstances IgnoreNew
if ($WakeToRun) { $settings.WakeToRun = $true }
Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings `
    -Description "Market leaderboard: refresh the data files after the market close" -Force | Out-Null
Write-Host "Registered task ${name}: Tue-Sat at $Time (local time), runs $bat"
Write-Host "Test it now:   Start-ScheduledTask -TaskName $name     then read output\nightly.log"
