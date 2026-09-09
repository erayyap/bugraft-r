$ErrorActionPreference='Stop'
& C:\Windows\Microsoft.NET\Framework64\v4.0.30319\csc.exe /nologo /target:exe /out:C:\BugCraft\capture.exe \\host.lan\Data\Capture.cs 2>&1 | Set-Content \\host.lan\Data\control\capture-build.txt
if($LASTEXITCODE -ne 0){throw 'Native capture build failed'}
'Native wrapper built' | Add-Content \\host.lan\Data\control\capture-build.txt
& \\host.lan\Data\restart-controller.ps1
