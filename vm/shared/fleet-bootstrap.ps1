$ErrorActionPreference='Stop'
$shared='\\host.lan\Data'
# Make Windows interpret future UTC RTC boots consistently; sync once during setup.
& tzutil.exe /s UTC
$clock=Get-Content "$shared\control\host-clock.json" -Raw | ConvertFrom-Json
$target=[DateTime]::Parse($clock.utc).ToUniversalTime()
Set-Date -Date $target | Out-Null
$startup=[Environment]::GetFolderPath('CommonStartup')
'@echo off', 'powershell.exe -NoProfile -ExecutionPolicy Bypass -File \\host.lan\Data\guest-control.ps1' | Set-Content "$startup\BugCraftController.cmd"
@{utc=[DateTime]::UtcNow.ToString('o');timezone=(Get-TimeZone).Id;controller_startup=$true} | ConvertTo-Json | Set-Content "$shared\control\fleet-bootstrap.json"
