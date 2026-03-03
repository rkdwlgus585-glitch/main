param(
    [string]$TaskName = "SeoulMNA_Tistory_DailyOnce"
)

$ErrorActionPreference = "SilentlyContinue"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Output "unregistered task: $TaskName"
