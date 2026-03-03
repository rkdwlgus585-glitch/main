param(
    [string]$TaskName = "SeoulMNA_Ops_Watchdog"
)

$ErrorActionPreference = "Stop"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Output "unregistered task: $TaskName"
