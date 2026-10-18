# Keeps the NeuroMind grader's WSL distribution running while this Windows user is signed in.
# WSL stops a distribution when no Windows process uses it; this task holds one idle process open in it.
#   Install:   powershell -ExecutionPolicy Bypass -File windows-keepalive.ps1
#   Remove:    Unregister-ScheduledTask -TaskName NeuroMind-Grader-KeepAlive -Confirm:$false
param([string]$Distro = 'NeuroMind-Grader')
$action   = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -Command wsl.exe -d $Distro -u root --exec sleep infinity"
$trigger  = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -ExecutionTimeLimit ([TimeSpan]::Zero) `
            -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1) -Hidden
Register-ScheduledTask -TaskName 'NeuroMind-Grader-KeepAlive' -Action $action -Trigger $trigger -Settings $settings `
  -Description 'Keeps the NeuroMind grading worker (WSL) running' -Force | Out-Null
Start-ScheduledTask -TaskName 'NeuroMind-Grader-KeepAlive'
Write-Host 'NeuroMind grader keep-alive task installed and started.'
