param(
    [string]$TaskName = "SeoulMNA_All_Startup"
)

$ErrorActionPreference = "Stop"

Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Output "unregistered task: $TaskName"
