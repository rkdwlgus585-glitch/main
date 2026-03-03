param(
    [string]$TaskName = "SeoulMNA_Blog_StartupOnce"
)

$ErrorActionPreference = "SilentlyContinue"
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
Write-Output "unregistered task: $TaskName"
