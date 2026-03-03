param(
    [string]$TaskName = "SeoulMNA_MnakrScheduler_Watchdog"
)

$ErrorActionPreference = "Stop"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Output "unregistered task: $TaskName"
