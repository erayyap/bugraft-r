Get-Process powershell -ErrorAction SilentlyContinue | Where-Object {$_.Id -ne $PID} | Stop-Process -Force
Start-Sleep -Seconds 2
& Z:\disable-overlays.ps1
try { & Z:\guest-control.ps1 } catch { $_ | Out-String | Set-Content Z:\control\controller-error.txt }
