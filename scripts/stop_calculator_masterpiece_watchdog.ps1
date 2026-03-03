param()

$rows = Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match "^powershell(?:\.exe)?$" -and $_.CommandLine -match "calculator_masterpiece_watchdog\.ps1"
}

$count = 0
foreach ($r in $rows) {
    try {
        Stop-Process -Id $r.ProcessId -Force
        $count += 1
    } catch {
    }
}

Write-Output ("stopped={0}" -f $count)

