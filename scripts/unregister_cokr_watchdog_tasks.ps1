$ErrorActionPreference = "Stop"

$taskNames = @(
    "SeoulMNA_CoKr_Listing_Watchdog",
    "SeoulMNA_CoKr_Notice_Watchdog",
    "SeoulMNA_CoKr_AdminMemo_Watchdog",
    "SeoulMNA_CoKr_SiteHealth_Watchdog",
    "SeoulMNA_Permit_Data_Watchdog",
    "SeoulMNA_Ops_Watchdog"
)

foreach ($name in $taskNames) {
    $task = Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue
    if ($task) {
        Unregister-ScheduledTask -TaskName $name -Confirm:$false
        Write-Output ("unregistered task: {0}" -f $name)
    }
}
